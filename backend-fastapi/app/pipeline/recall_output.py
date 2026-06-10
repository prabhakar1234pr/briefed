"""
Native Recall audio output (replaces the bot-page Web Audio playback).

Instead of streaming TTS PCM to a webpage that Recall captures + re-encodes
(which introduced static / overlap we couldn't fix), we collect the LLM's full
response text, synthesize ONE clean mp3 with ElevenLabs, and hand it to Recall's
`/output_audio/` endpoint so Recall plays it natively into the meeting.

`NativeTTSInjector` sits where the TTS service + output transport used to be:
    ... → user_aggregator → LLM → NativeTTSInjector → assistant_aggregator
It passes every frame through (so the assistant aggregator still records the
reply for context) and, on each completed LLM response, fires the synth+inject
off the pipeline. While Recall is playing the clip it mutes the meeting-audio
input (echo guard) so the bot doesn't hear / transcribe itself.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import httpx

from pipecat.frames.frames import (
    Frame,
    InterruptionFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    TextFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from app.config import get_settings
from app.logger import get_logger
from app.output_media import inject_audio

if TYPE_CHECKING:
    from app.pipeline.session import MeetingSession

log = get_logger(__name__)

# Reuse one HTTP client for ElevenLabs (connection pooling → lower TTS latency).
_el_client: httpx.AsyncClient | None = None


def _client() -> httpx.AsyncClient:
    global _el_client
    if _el_client is None or _el_client.is_closed:
        _el_client = httpx.AsyncClient(timeout=30.0)
    return _el_client


async def tts_to_mp3(text: str, voice_id: str, model: str, api_key: str) -> bytes:
    """Synthesize the full reply as a single mp3 (clean, one synthesis pass)."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    r = await _client().post(
        url,
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": api_key, "content-type": "application/json"},
        json={"text": text, "model_id": model},
    )
    r.raise_for_status()
    return r.content


class NativeTTSInjector(FrameProcessor):
    def __init__(self, *, session: "MeetingSession", bot_id: str, voice_id: str, **kwargs):
        super().__init__(**kwargs)
        self._session = session
        self._bot_id = bot_id
        self._voice_id = voice_id
        self._buf: list[str] = []
        self._collecting = False
        s = get_settings()
        self._api_key = s.get("elevenlabs_api_key") or ""
        self._model = s.get("elevenlabs_model") or "eleven_flash_v2_5"
        self._unmute_task: asyncio.Task | None = None

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, LLMFullResponseStartFrame):
            self._buf = []
            self._collecting = True
        elif isinstance(frame, LLMFullResponseEndFrame):
            self._collecting = False
            text = "".join(self._buf).strip()
            self._buf = []
            if text:
                self.create_task(self._speak(text))
        elif isinstance(frame, TextFrame) and self._collecting and direction == FrameDirection.DOWNSTREAM:
            if frame.text:
                self._buf.append(frame.text)
        elif isinstance(frame, InterruptionFrame):
            self._buf = []
            self._collecting = False

        await self.push_frame(frame, direction)

    async def _speak(self, text: str) -> None:
        try:
            if not self._api_key or not self._bot_id:
                log.warning("native_tts_skipped", has_key=bool(self._api_key), has_bot=bool(self._bot_id))
                return
            try:
                mp3 = await tts_to_mp3(text, self._voice_id, self._model, self._api_key)
            except Exception as e:
                log.warning("native_tts_failed", meeting_id=self._session.meeting_id, error=str(e)[:160])
                return
            if not mp3:
                return
            # Echo guard: mute meeting-audio input while Recall plays the clip, so
            # the bot doesn't transcribe its own voice (loops back via audio_mixed).
            self._mute_input(True)
            try:
                ok = await inject_audio(self._bot_id, mp3)
            except Exception as e:
                # CRITICAL: if the inject POST fails we must re-open the mic, or the
                # input stays muted forever and the bot goes permanently deaf.
                log.warning("native_inject_failed", meeting_id=self._session.meeting_id, error=str(e)[:160])
                self._mute_input(False)
                return
            log.info(
                "native_audio_injected",
                meeting_id=self._session.meeting_id,
                chars=len(text), mp3_kb=round(len(mp3) / 1024, 1), ok=ok,
            )
            # Re-open the mic after the estimated clip duration (+tail). ElevenLabs
            # speaks ~14 chars/sec; floor at 1.5s. We can't get exact duration from
            # the mp3 cheaply, so estimate generously.
            est = max(1.5, len(text) * 0.075) + 0.8
            if self._unmute_task and not self._unmute_task.done():
                self._unmute_task.cancel()
            self._unmute_task = self.create_task(self._unmute_after(est))
        finally:
            # Release the TurnGate's SPEAKING state on EVERY path (success, skip,
            # synth/inject failure). The gate is upstream of the LLM so it never
            # sees LLMFullResponseEndFrame; without this it deadlocks in SPEAKING
            # after the first reply and the bot stops answering. See turn_gate.py.
            self._release_gate()

    def _release_gate(self) -> None:
        gate = getattr(self._session, "turn_gate", None)
        if gate is not None:
            try:
                gate.notify_response_complete()
            except Exception:
                pass

    async def _unmute_after(self, secs: float) -> None:
        try:
            await asyncio.sleep(secs)
        except asyncio.CancelledError:
            return
        self._mute_input(False)

    def _mute_input(self, muted: bool) -> None:
        inp = getattr(self._session, "recall_input", None)
        if inp is not None:
            try:
                inp.set_muted(muted)
            except Exception:
                pass
