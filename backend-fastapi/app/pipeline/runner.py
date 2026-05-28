"""
Per-meeting Pipecat pipeline lifecycle.

One PipelineTask per active meeting. Spawned when the bot-page connects to
our WebSocket bridge; torn down when the WebSocket closes or the meeting ends.

Pipeline shape:
    bot_page_ws ──┐
                  ▼
            transport.input()              # PCM16 16kHz mono from bot-page
                  │
            SileroVADAnalyzer              # speech endpointing
                  │
            DeepgramSTTService             # nova-3 streaming, interim+final
                  │
            TurnGate                       # hybrid name/addressed classifier
                  │
            LLMUserContextAggregator       # accumulate transcripts → LLM context
                  │
            GoogleLLMService               # gemini-2.5-flash, thinking_budget=0
                  │                          wrapped with LangSmith @traceable
                  │
            ElevenLabsTTSService           # eleven_flash_v2_5 streaming
                  │
            LLMAssistantContextAggregator  # bot's own speech back into context
                  │
            transport.output()             # PCM16 24kHz to bot-page
                  ▼
                bot_page_ws

Barge-in is handled by Pipecat's standard interruption flow — when VAD detects
user speech mid-response, frames are cancelled all the way through STT/LLM/TTS
and the output buffer is flushed.
"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket

from app.config import get_settings
from app.logger import get_logger
from app.pipeline.context import MeetingContext

log = get_logger(__name__)


# ─── Registry of active pipelines (one per meeting) ──────────────────────────
_active_pipelines: dict[str, "MeetingPipeline"] = {}


def get_active(meeting_id: str) -> "MeetingPipeline | None":
    return _active_pipelines.get(meeting_id)


class MeetingPipeline:
    """
    Wraps a Pipecat PipelineTask + PipelineRunner for one meeting.

    Held alive by the FastAPI WebSocket handler. When the WebSocket closes,
    .cancel() tears down the pipeline and removes it from the registry.
    """

    def __init__(
        self,
        *,
        meeting_id: str,
        agent: dict[str, Any],
        websocket: WebSocket,
    ):
        self.meeting_id = meeting_id
        self.agent = agent
        self.websocket = websocket
        self.context = MeetingContext(
            meeting_id=meeting_id,
            agent_id=agent["id"],
            agent_name=agent.get("name") or "Assistant",
        )
        self._task: asyncio.Task[None] | None = None
        self._pipeline_task: Any = None  # pipecat PipelineTask

    async def start(self) -> None:
        """Launch the pipeline as a background task. Returns immediately."""
        if self._task is not None:
            log.warning("pipeline_already_started", meeting_id=self.meeting_id)
            return
        _active_pipelines[self.meeting_id] = self
        self._task = asyncio.create_task(self._run(), name=f"pipeline-{self.meeting_id}")
        log.info("pipeline_started", meeting_id=self.meeting_id, agent=self.agent.get("name"))

    async def cancel(self) -> None:
        """Stop the pipeline and clean up."""
        _active_pipelines.pop(self.meeting_id, None)
        if self._pipeline_task is not None:
            try:
                await self._pipeline_task.cancel()
            except Exception as e:
                log.warning("pipeline_task_cancel_failed", error=str(e)[:160])
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        log.info("pipeline_cancelled", meeting_id=self.meeting_id)

    async def _run(self) -> None:
        """Build and run the Pipecat pipeline. Imports are lazy so the package
        loads cleanly even before `uv sync` has installed pipecat.

        Targets Pipecat **1.2.x** API:
          - LLMContext (replaces deprecated OpenAILLMContext)
          - LLMContextAggregatorPair (replaces llm.create_context_aggregator)
          - GoogleVertexLLMService (uses service-account creds, not Google AI API key)
          - DeepgramSTTService with direct kwargs (live_options is deprecated)
        """
        try:
            from pipecat.audio.vad.silero import SileroVADAnalyzer
            from pipecat.pipeline.pipeline import Pipeline
            from pipecat.pipeline.runner import PipelineRunner
            from pipecat.pipeline.task import PipelineParams, PipelineTask
            from pipecat.processors.aggregators.llm_context import LLMContext
            from pipecat.processors.aggregators.llm_response_universal import (
                LLMContextAggregatorPair,
            )
            from pipecat.services.deepgram.stt import DeepgramSTTService
            from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
            from pipecat.services.google.vertex.llm import GoogleVertexLLMService
            from pipecat.services.google.llm import GoogleLLMService, GoogleThinkingConfig
            from pipecat.transports.websocket.fastapi import (
                FastAPIWebsocketTransport,
                FastAPIWebsocketParams,
            )
        except ImportError as e:
            log.error(
                "pipecat_import_failed",
                error=str(e),
                hint="ensure pipecat-ai>=1.2.1 with [deepgram,elevenlabs,silero,google,webrtc] extras is installed",
            )
            return

        settings = get_settings()
        agent_name = self.agent.get("name") or "Assistant"
        agent_persona = self.agent.get("persona") or ""
        voice_id = self.agent.get("voice_id") or settings["elevenlabs_default_voice"]

        # ── Transport: FastAPI WebSocket bridge to bot-page ────────────────
        transport = FastAPIWebsocketTransport(
            websocket=self.websocket,
            params=FastAPIWebsocketParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                add_wav_header=False,
                vad_analyzer=SileroVADAnalyzer(),
            ),
        )

        # ── STT: Deepgram streaming (nova-3) ───────────────────────────────
        # Pipecat 1.2 DeepgramSTTService takes connection params as direct
        # kwargs + a Settings(...) object for model/language/options.
        stt = DeepgramSTTService(
            api_key=settings["deepgram_api_key"] or "",
            settings=DeepgramSTTService.Settings(
                model=settings.get("deepgram_model") or "nova-3",
                language="en-US",
                interim_results=True,
                punctuate=True,
                smart_format=True,
            ),
        )

        # ── LLM: Gemini 2.5-flash via Vertex AI ────────────────────────────
        # Use the Vertex-native service (auths via service account) rather than
        # google.llm (which requires a Google AI API key).
        llm = GoogleVertexLLMService(
            project_id=settings.get("gcp_project") or "",
            location=settings.get("gcp_location") or "us-central1",
            credentials_path=settings.get("google_application_credentials"),
            model=settings.get("live_qa_model") or "gemini-2.5-flash",
            params=GoogleLLMService.InputParams(
                temperature=0.4,
                max_tokens=1024,
                # thinking_budget=0 keeps first-token latency ~600ms
                thinking=GoogleThinkingConfig(thinking_budget=0),
            ),
        )

        # ── TTS: ElevenLabs Flash streaming ────────────────────────────────
        tts = ElevenLabsTTSService(
            api_key=settings["elevenlabs_api_key"] or "",
            settings=ElevenLabsTTSService.Settings(
                voice=voice_id,
                model=settings.get("elevenlabs_model") or "eleven_flash_v2_5",
            ),
        )

        # ── Context: persona + recall composed at first turn ───────────────
        system_prompt = _build_system_prompt(agent_name, agent_persona)
        llm_context = LLMContext(
            messages=[{"role": "system", "content": system_prompt}],
        )
        context_aggregator_pair = LLMContextAggregatorPair(llm_context)

        # ── Wire pipeline ──────────────────────────────────────────────────
        pipeline = Pipeline([
            transport.input(),
            stt,
            context_aggregator_pair.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator_pair.assistant(),
        ])

        self._pipeline_task = PipelineTask(
            pipeline,
            params=PipelineParams(
                audio_in_sample_rate=16000,
                audio_out_sample_rate=24000,
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True,
            ),
        )

        # ── Event hooks: speech transcripts into the meeting ring buffer ──
        @stt.event_handler("on_speech_started")
        async def _on_speech_started(_service):
            log.info("user_speech_started", meeting_id=self.meeting_id)

        runner = PipelineRunner(handle_sigint=False)
        try:
            await runner.run(self._pipeline_task)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.exception("pipeline_run_failed", meeting_id=self.meeting_id, error=str(e)[:200])
        finally:
            _active_pipelines.pop(self.meeting_id, None)


def _build_system_prompt(agent_name: str, persona: str) -> str:
    base = (
        f'You are "{agent_name}", a voice AI teammate sitting in on a live meeting. '
        "You hear the conversation in real time and speak back into the meeting.\n\n"
        "VOICE STYLE:\n"
        "- Sharp, confident, conversational. No filler ('um', 'so', 'I think').\n"
        "- Plain spoken sentences. No markdown, no bullet points, no lists.\n"
        "- Match question complexity — short questions get short answers.\n"
        "- Never read out punctuation or formatting characters.\n\n"
        "WHEN TO SPEAK:\n"
        "- Answer questions directed at you.\n"
        "- If the speaker seems to be addressing you (even without saying your name), respond.\n"
        "- If unsure whether you're being addressed, stay silent.\n"
        "- If interrupted, stop immediately and let the speaker continue.\n\n"
        "GROUNDING:\n"
        "- Use the provided knowledge base and prior-meeting context to answer accurately.\n"
        "- If you don't know, say so plainly. Never invent facts.\n"
    )
    if persona:
        base += f"\nADDITIONAL CONTEXT ABOUT YOURSELF:\n{persona}\n"
    return base
