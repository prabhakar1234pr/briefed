"""
Custom Pipecat transports for the split-socket meeting pipeline.

Why custom transports instead of FastAPIWebsocketTransport?
  1. One meeting uses TWO websockets: Recall pushes meeting audio to our
     `/ws/recall-audio/...` endpoint (INPUT), while the bot-page connects to
     `/ws/bot-bridge/...` to play TTS into the meeting (OUTPUT). The stock
     FastAPIWebsocketTransport assumes a single bidirectional socket.
  2. The stock transport drops every frame unless a `serializer` is configured
     (`if not self._params.serializer: continue/return` in pipecat 1.2.1's
     transports/websocket/fastapi.py). We send/receive RAW PCM16 with no
     serializer, so we own both byte paths directly.

RecallAudioInputTransport
  - No socket of its own. The Recall audio WS handler decodes PCM and calls
    `feed_pcm(bytes)`, which becomes an InputAudioRawFrame on the pipeline's
    audio-in queue. 16 kHz / mono / S16LE (matches what Recall sends and what
    Deepgram wants).

BotPageOutputTransport
  - Wraps the bot-page WebSocket. BaseOutputTransport already does all the
    chunking / interruption / bot-speaking bookkeeping and calls
    `write_audio_frame()` once per 10ms*chunks slice; we just send the raw bytes
    and emulate device pacing (copied from FastAPIWebsocketOutputTransport so the
    bot-page's AudioContext scheduler doesn't under/over-run). 24 kHz / mono.
  - Control messages (`{"type": "hand"|"bot_state", ...}`) are sent out-of-band
    via the MeetingSession holding the same WebSocket, not through this
    transport — see app/pipeline/session.py.

The input is constructed standalone in app/pipeline/recall_audio_ws.py (so audio
can start before the bot-page connects); the output is constructed in
app/pipeline/runner.py from the session's bot-page socket.
"""
from __future__ import annotations

import asyncio
import time

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from pipecat.frames.frames import (
    CancelFrame,
    EndFrame,
    Frame,
    InputAudioRawFrame,
    InterruptionFrame,
    OutputAudioRawFrame,
    StartFrame,
)
from pipecat.processors.frame_processor import FrameDirection
from pipecat.transports.base_input import BaseInputTransport
from pipecat.transports.base_output import BaseOutputTransport
from pipecat.transports.base_transport import TransportParams

from app.logger import get_logger

log = get_logger(__name__)


class RecallAudioInputTransport(BaseInputTransport):
    """Input transport fed externally by the Recall audio websocket handler."""

    # Max frames to hold before the pipeline starts. Recall keeps the audio WS
    # open and streams continuously, so this only matters in the window between
    # the Recall socket connecting and the bot-page connecting (pipeline start).
    # ~3000 frames covers a generous window of small chunks; on overflow we drop
    # the OLDEST so the bot hears the most recent speech, and log once.
    _PRESTART_MAX = 3000

    def __init__(self, params: TransportParams, **kwargs):
        super().__init__(params, **kwargs)
        # Frames that arrive before the pipeline has started (and thus before
        # `_audio_in_queue` exists) are buffered so we don't lose the opening
        # words. Bounded so a never-starting pipeline can't grow unbounded.
        self._prestart_buffer: list[InputAudioRawFrame] = []
        self._prestart_overflowed = False
        self._ready = False
        self._frames_in = 0
        # While the bot is speaking, the OUTPUT transport mutes us so Recall's
        # MIXED meeting audio (which includes the bot's own TTS bleeding back in)
        # doesn't get transcribed and either (a) make the bot answer itself or
        # (b) trip VAD and interrupt the bot mid-sentence (sounds like breakup).
        self._muted = False

    def set_muted(self, muted: bool) -> None:
        self._muted = muted

    async def start(self, frame: StartFrame):
        await super().start(frame)
        # Create the audio-in queue + task. The stock FastAPI input transport
        # does this from its receive loop; we have no receive loop (audio is
        # pushed in via feed_pcm), so we trigger it here.
        await self.set_transport_ready(frame)
        self._ready = True
        # Flush anything buffered before the pipeline was ready.
        if self._prestart_buffer:
            log.info("recall_input_flush_prestart", count=len(self._prestart_buffer))
            for f in self._prestart_buffer:
                await self.push_audio_frame(f)
            self._prestart_buffer.clear()

    async def feed_pcm(self, pcm: bytes) -> None:
        """Called by the Recall audio WS handler with raw PCM16 16k mono bytes."""
        if not pcm:
            return
        # Drop meeting audio while the bot is speaking (echo guard). Recall keeps
        # streaming continuously; dropping here keeps us at real time and stops
        # the bot from hearing itself.
        if self._muted:
            return
        self._frames_in += 1
        frame = InputAudioRawFrame(audio=pcm, sample_rate=16000, num_channels=1)
        if not self._ready:
            self._prestart_buffer.append(frame)
            if len(self._prestart_buffer) > self._PRESTART_MAX:
                self._prestart_buffer.pop(0)  # drop oldest; keep most recent speech
                if not self._prestart_overflowed:
                    self._prestart_overflowed = True
                    log.warning("recall_input_prestart_overflow", cap=self._PRESTART_MAX)
            return
        # BACKPRESSURE — the real cause of the 30s+ lag. Recall streams audio
        # continuously (even during silence). If downstream (VAD/STT) can't drain
        # the queue as fast as it fills, it grows unbounded and every utterance
        # waits behind tens of seconds of stale audio. Cap the queue: if it's
        # backed up, drop the OLDEST frames so we stay near real time. A few
        # dropped silence frames cost nothing; a 30s backlog is fatal.
        q = getattr(self, "_audio_in_queue", None)
        if q is not None:
            # ~50 frames of 200ms audio = ~10s hard ceiling; trim toward ~2s.
            if q.qsize() > 50:
                dropped = 0
                while q.qsize() > 10:
                    try:
                        q.get_nowait()
                        q.task_done()
                        dropped += 1
                    except Exception:
                        break
                if dropped:
                    log.warning("recall_input_backpressure_drop", dropped=dropped, qsize=q.qsize())
        await self.push_audio_frame(frame)

    @property
    def frames_in(self) -> int:
        return self._frames_in


class BotPageOutputTransport(BaseOutputTransport):
    """Output transport that writes raw PCM16 24k mono to the bot-page WebSocket."""

    # Re-open the mic this many seconds after the LAST TTS chunk goes out. Covers
    # the round-trip tail of the bot's own audio (backend → bot-page jitter
    # buffer → Recall encode/mix → back to us) so we don't transcribe the end of
    # our own sentence. Kept short so the bot isn't "deaf" long after it stops.
    _ECHO_TAIL_SECS = 0.6

    def __init__(
        self,
        params: TransportParams,
        websocket: WebSocket,
        input_transport: "RecallAudioInputTransport | None" = None,
        **kwargs,
    ):
        super().__init__(params, **kwargs)
        self._ws = websocket
        # The INPUT transport we mute while we're playing TTS (echo guard).
        self._input = input_transport
        # Emulate an audio device clock so we don't blast the whole TTS buffer at
        # the bot-page at once (copied from FastAPIWebsocketOutputTransport).
        self._send_interval = 0.0
        self._next_send_time = 0.0
        self._initialized = False
        # Echo-mute bookkeeping.
        self._echo_muted = False
        self._last_audio_write = 0.0
        self._unmute_task: asyncio.Task | None = None

    def set_websocket(self, websocket: WebSocket) -> None:
        """Swap in a reconnected bot-page socket without rebuilding the pipeline."""
        self._ws = websocket

    async def start(self, frame: StartFrame):
        await super().start(frame)
        # audio_chunk_size / sample_rate is the duration of one written chunk;
        # halve it so we stay a little ahead of real time (same heuristic as the
        # stock FastAPI output transport).
        if self.sample_rate:
            # CRITICAL pacing fix. `audio_chunk_size` is in BYTES (Pipecat:
            # audio_bytes_10ms * audio_out_10ms_chunks), so the TRUE wall-clock
            # duration of one chunk is bytes / (sample_rate * 2-bytes-per-sample).
            # The previous code used (chunk_size / sample_rate) * 0.9, which is
            # ~1.8× the real duration → it sent TTS at ~0.55× real time → the
            # bot-page AudioContext starved → repeated 150ms jitter-gap fills →
            # the "broken / static" audio (and a 10s answer stretched to ~18s).
            # Send a hair FASTER than real time (×0.9) so the bot-page keeps a
            # small cushion ahead of playback instead of underrunning.
            bytes_per_sample = 2
            true_chunk_secs = self.audio_chunk_size / (self.sample_rate * bytes_per_sample)
            self._send_interval = true_chunk_secs * 0.9
        # CRITICAL: BaseOutputTransport.start() does NOT register the default
        # media sender — set_transport_ready() does. The stock FastAPI transport
        # calls it from start(); we must too, or every TTSAudioRawFrame is
        # dropped with "destination [None] not registered" and nothing is heard.
        if not self._initialized:
            self._initialized = True
            await self.set_transport_ready(frame)

    def _connected(self) -> bool:
        ws = self._ws
        return (
            ws is not None
            and ws.client_state == WebSocketState.CONNECTED
            and ws.application_state != WebSocketState.DISCONNECTED
        )

    async def write_audio_frame(self, frame: OutputAudioRawFrame) -> bool:
        if not self._connected():
            return False
        try:
            await self._ws.send_bytes(frame.audio)
        except Exception as e:
            log.warning("bot_output_send_failed", error=str(e)[:160])
            return False
        self._note_speaking()
        await self._write_audio_sleep()
        return True

    # ── Echo guard: mute the mic while we're playing audio ─────────────────────
    def _note_speaking(self) -> None:
        """Called on every outbound TTS chunk; mutes input and (re)arms unmute."""
        self._last_audio_write = time.monotonic()
        if self._input is not None and not self._echo_muted:
            self._echo_muted = True
            self._input.set_muted(True)
        if self._unmute_task is None or self._unmute_task.done():
            self._unmute_task = asyncio.create_task(self._unmute_watch())

    async def _unmute_watch(self) -> None:
        """Re-open the mic once no TTS has been sent for _ECHO_TAIL_SECS."""
        try:
            while True:
                await asyncio.sleep(0.1)
                if time.monotonic() - self._last_audio_write >= self._ECHO_TAIL_SECS:
                    break
        except asyncio.CancelledError:
            pass
        if self._input is not None:
            self._input.set_muted(False)
        self._echo_muted = False
        self._unmute_task = None

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        # Reset the send clock on interruption so post-barge-in audio starts fresh.
        if isinstance(frame, InterruptionFrame):
            self._next_send_time = 0.0

    async def _write_audio_sleep(self) -> None:
        current_time = time.monotonic()
        sleep_duration = max(0.0, self._next_send_time - current_time)
        await asyncio.sleep(sleep_duration)
        if sleep_duration == 0.0:
            self._next_send_time = time.monotonic() + self._send_interval
        else:
            self._next_send_time += self._send_interval
