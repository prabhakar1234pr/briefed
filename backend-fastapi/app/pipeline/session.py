"""
Per-meeting session coordinator.

One meeting drives TWO websockets that connect at different times:
  - INPUT  : Recall connects to /ws/recall-audio/{meeting_id}/  (meeting audio in)
  - OUTPUT : the bot-page connects to /ws/bot-bridge/{meeting_id} (TTS out + control)

`MeetingSession` is the rendezvous point both handlers attach to. The Pipecat
pipeline is built once BOTH the bot-page output socket and the Recall input
transport are present (the output socket is required to construct the output
transport). Either socket can drop and reconnect:
  - Recall auto-retries every 3s (≤30×); the bot-page reconnects every 3s.
  - On a bot-page reconnect we swap the live socket into the existing output
    transport instead of rebuilding the pipeline.
  - Full teardown happens on explicit meeting end (bot.call_ended/bot.done,
    handled in main.py) or when both sockets have been gone past a grace period.
"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.logger import get_logger
from app.pipeline.context import MeetingContext
from app.pipeline.transports import RecallAudioInputTransport

log = get_logger(__name__)

_sessions: dict[str, "MeetingSession"] = {}


def get_or_create(meeting_id: str, agent: dict[str, Any], bot_id: str | None = None) -> "MeetingSession":
    sess = _sessions.get(meeting_id)
    if sess is None:
        sess = MeetingSession(meeting_id=meeting_id, agent=agent, bot_id=bot_id)
        _sessions[meeting_id] = sess
    elif bot_id and not sess.bot_id:
        sess.bot_id = bot_id  # fill in once known (native audio injection needs it)
    return sess


def get(meeting_id: str) -> "MeetingSession | None":
    return _sessions.get(meeting_id)


def remove(meeting_id: str) -> None:
    _sessions.pop(meeting_id, None)


class MeetingSession:
    def __init__(self, *, meeting_id: str, agent: dict[str, Any], bot_id: str | None = None):
        self.meeting_id = meeting_id
        self.agent = agent
        self.bot_id = bot_id  # needed for native Recall audio injection
        self.context = MeetingContext(
            meeting_id=meeting_id,
            agent_id=agent["id"],
            agent_name=agent.get("name") or "Assistant",
        )
        self.recall_input: RecallAudioInputTransport | None = None
        self.bot_ws: WebSocket | None = None
        self.pipeline: Any = None  # MeetingPipeline (lazy import to avoid cycle)
        # The live TurnGate (set by runner._run). The native TTS injector calls
        # back into it to clear the SPEAKING state when a reply finishes, since
        # the gate sits UPSTREAM of the LLM and never sees LLMFullResponseEndFrame.
        self.turn_gate: Any = None
        self._started = False
        self._tearing_down = False
        self._lock = asyncio.Lock()
        self._closed = asyncio.Event()
        # Strong refs to in-flight control sends so they aren't GC'd mid-send.
        self._control_tasks: set[asyncio.Task] = set()

    # ── Attach points ────────────────────────────────────────────────────────
    async def attach_recall_input(self, transport: RecallAudioInputTransport) -> None:
        self.recall_input = transport
        log.info("session_recall_input_attached", meeting_id=self.meeting_id)
        await self.maybe_start()

    async def attach_bot_ws(self, websocket: WebSocket) -> None:
        # Always record the latest socket FIRST. The output transport is built
        # in runner._run() from self.bot_ws, so storing it here is what makes a
        # reconnect-during-startup self-heal (the transport reads the new socket
        # when it's eventually constructed).
        self.bot_ws = websocket
        # Reconnect into a running pipeline: hot-swap the socket into the live
        # output transport too (no-op until _output is built — the store above
        # already covers that window).
        if self._started and self.pipeline is not None:
            try:
                self.pipeline.swap_output_websocket(websocket)
                log.info("session_bot_ws_reconnected", meeting_id=self.meeting_id)
            except Exception as e:
                log.warning("session_bot_ws_swap_failed", meeting_id=self.meeting_id, error=str(e)[:160])
            return
        log.info("session_bot_ws_attached", meeting_id=self.meeting_id)
        await self.maybe_start()

    # ── Lifecycle ────────────────────────────────────────────────────────────
    async def maybe_start(self) -> None:
        async with self._lock:
            if self._started or self._tearing_down:
                return
            from app.config import get_settings
            native = (get_settings().get("voice_output_mode") or "recall_native") == "recall_native"
            if self.recall_input is None:
                return  # always need the meeting-audio input
            if not native and self.bot_ws is None:
                return  # bot-page mode also needs the output socket
            self._started = True
            from app.pipeline.runner import MeetingPipeline  # lazy: avoid import cycle
            self.pipeline = MeetingPipeline(session=self)
            await self.pipeline.start()
            log.info("session_pipeline_started", meeting_id=self.meeting_id)

    def push_control(self, msg: dict[str, Any]) -> None:
        """Fire-and-forget JSON control message to the bot-page (hand / bot_state)."""
        ws = self.bot_ws
        if ws is None or ws.client_state != WebSocketState.CONNECTED:
            return
        task = asyncio.create_task(self._send_control(ws, msg))
        self._control_tasks.add(task)
        task.add_done_callback(self._control_tasks.discard)

    async def _send_control(self, ws: WebSocket, msg: dict[str, Any]) -> None:
        try:
            await ws.send_json(msg)
        except Exception as e:
            log.debug("session_control_send_failed", meeting_id=self.meeting_id, error=str(e)[:120])

    async def on_recall_drop(self) -> None:
        # Recall retries automatically; keep the session for a grace window.
        log.info("session_recall_dropped", meeting_id=self.meeting_id)

    async def on_bot_ws_drop(self) -> None:
        # Bot-page reconnects automatically; keep the pipeline running.
        log.info("session_bot_ws_dropped", meeting_id=self.meeting_id)

    async def teardown(self, reason: str) -> None:
        # Mark tearing-down under the lock so a concurrent maybe_start() can't
        # build a pipeline after we've decided to stop (which would orphan it).
        async with self._lock:
            if self._tearing_down:
                return
            self._tearing_down = True
            pipeline = self.pipeline
        log.info("session_teardown", meeting_id=self.meeting_id, reason=reason)
        if pipeline is not None:
            try:
                await pipeline.cancel()
            except Exception as e:
                log.warning("session_pipeline_cancel_failed", error=str(e)[:160])
        remove(self.meeting_id)
        self._closed.set()

    async def wait_closed(self) -> None:
        await self._closed.wait()
