"""
TurnGate — direct answers + polite proactive interjections.

Sits in the pipeline BETWEEN the STT and the user context aggregator, so any
utterance it suppresses never reaches the LLM (the bot is silent by default).

Two paths on a finalized utterance:

  1. DIRECT QUESTION ("Bora, what's the deadline?" / clearly addressed to Bora)
     → release to the LLM immediately. No hand raise, no waiting.

  2. PROACTIVE INTERJECTION — everything else is checked by the Nebius/Qwen gate,
     which only fires when someone says something factually WRONG (vs the
     knowledge base or general knowledge) or the team is STUCK. On a confident
     flag, Bora RAISES ITS HAND (visible in the meeting) and waits. It never
     interrupts. When a human says "go on Bora", Bora speaks the specific
     correction/help the gate identified, grounded in the KB + recent talk.

State machine:

  IDLE
    ├─ name address ("Bora, …")  → release downstream (answer now)  → SPEAKING
    ├─ question (no name)        → addressed-classifier
    │     ├─ addressed → release downstream (answer now)            → SPEAKING
    │     └─ not addressed → async Nebius gate (below)
    └─ statement → record + async Nebius gate
         ├─ wrong_fact/stuck && conf > threshold → raise hand, stash point
         │                                          → HAND_RAISED
         └─ none → stay silent (turn recorded only)

  HAND_RAISED
    ├─ direct question → answer it now (release), keep hand state? no — a direct
    │     question supersedes; we drop the pending interjection and answer.
    ├─ permission ("go on Bora") → release the stashed point     → SPEAKING
    └─ NEBIUS_HAND_TIMEOUT with no permission → lower hand        → IDLE

  SPEAKING
    └─ LLMFullResponseEndFrame → lower hand, bot_state false      → IDLE

Control messages to the bot-page (via the session's bot-page WS):
  {"type": "hand", "raised": true|false}
  {"type": "bot_state", "speaking": true|false}
"""
from __future__ import annotations

import asyncio
import re
import time
from typing import TYPE_CHECKING

from pipecat.frames.frames import (
    Frame,
    InterimTranscriptionFrame,
    LLMFullResponseEndFrame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from app.config import get_settings
from app.logger import get_logger
from app.pipeline.context import MeetingContext
from app.pipeline.nebius_client import evaluate_turn
from app.pipeline.turn_taking import classify_addressed, match_name

if TYPE_CHECKING:
    from app.pipeline.session import MeetingSession

log = get_logger(__name__)

# Permission-to-speak phrases. The hand is already raised, so these are likely
# directed at the bot — but we still require the agent's name for otherwise
# ambiguous phrases ("what do you think") so we don't fire on human-to-human
# chatter. The name-free phrases are imperatives that read as yielding the floor.
_PERMISSION_PATTERNS = [
    r"\bgo on\b",
    r"\bgo ahead\b",
    r"\byour turn\b",
    r"\btake it away\b",
    r"\bgo for it\b",
    r"\byes\b[^.]*\b{name}\b",
    r"\b{name}\b[^.]*\b(go|please|speak|tell us|what.s your|thoughts?|weigh in)\b",
    r"\bplease\b[^.]*\b{name}\b",
    r"\b{name}\b[^.]*\bwhat do you think\b",
    r"\bwhat do you think\b[^.]*\b{name}\b",
]


# Cheap pre-filter so we only spend a classifier call on utterances that could
# plausibly be a question for the bot (mirrors turn_taking._question_words).
_Q_WORDS = {
    "what", "when", "where", "why", "who", "whom", "whose", "how", "which",
    "can", "could", "should", "would", "is", "are", "was", "were", "do",
    "does", "did", "will", "may", "might", "shall", "have", "has", "any",
}


def _looks_like_question(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    if t.endswith("?"):
        return True
    first = t.split(maxsplit=1)[0].lower().strip(",.!")
    return first in _Q_WORDS


class TurnGate(FrameProcessor):
    IDLE = "idle"
    HAND_RAISED = "hand_raised"
    SPEAKING = "speaking"

    def __init__(
        self,
        *,
        session: "MeetingSession",
        context: MeetingContext,
        agent_name: str,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._session = session
        self._context = context
        self._agent_name = agent_name
        s = get_settings()
        try:
            self._threshold = float(s.get("nebius_speak_threshold") or 0.7)
        except (TypeError, ValueError):
            self._threshold = 0.7
        try:
            self._hand_timeout = float(s.get("nebius_hand_timeout") or 20)
        except (TypeError, ValueError):
            self._hand_timeout = 20.0
        self._gate_enabled = bool(s.get("nebius_api_key"))

        self._state = self.IDLE
        self._pending_point: str | None = None
        self._timeout_task: asyncio.Task | None = None
        self._permission_res = [
            re.compile(p.replace("{name}", re.escape(agent_name)), re.IGNORECASE)
            for p in _PERMISSION_PATTERNS
        ]

    # ── Frame processing ─────────────────────────────────────────────────────
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        # Interim (partial) transcripts: never forward — they'd feed the LLM
        # half-sentences. Deepgram emits these as a distinct class.
        if isinstance(frame, InterimTranscriptionFrame) and direction == FrameDirection.DOWNSTREAM:
            return

        # A TranscriptionFrame from the STT is a completed utterance.
        if isinstance(frame, TranscriptionFrame) and direction == FrameDirection.DOWNSTREAM:
            await self._on_final_transcript(frame)
            return  # suppress; we decide if/when to re-emit downstream

        # Lower the hand once the bot has finished its answer.
        if isinstance(frame, LLMFullResponseEndFrame) and self._state == self.SPEAKING:
            await self._finish_speaking()

        await self.push_frame(frame, direction)

    async def _on_final_transcript(self, frame: TranscriptionFrame) -> None:
        text = (frame.text or "").strip()
        if not text:
            return
        await self._context.append_turn(getattr(frame, "user_id", "") or "speaker", text)

        # A direct question to Bora is always answered immediately, regardless of
        # state — it supersedes any pending proactive interjection.
        direct = match_name(self._agent_name, text)
        if direct:
            if self._state == self.HAND_RAISED:
                await self._lower_hand()  # drop the pending interjection
            await self._answer_now(frame, direct)
            return

        if self._state == self.SPEAKING:
            return  # mid-answer; ignore (interruptions handled by VAD)

        if self._state == self.HAND_RAISED:
            if self._is_permission(text):
                await self._grant_permission(frame)
            return

        # IDLE. Hybrid turn-taking:
        #   • question-like utterances → addressed-classifier; if it's for us,
        #     answer immediately (no name needed) — natural back-and-forth.
        #   • statements → the Nebius proactive gate may RAISE A HAND
        #     (corrections / unblocking); the bot never auto-speaks on them.
        if _looks_like_question(text):
            self.create_task(self._maybe_answer_question(text, frame))
        elif self._gate_enabled:
            self.create_task(self._evaluate(text, frame))

    # ── Addressed question → answer (no name required) ─────────────────────────
    async def _maybe_answer_question(self, text: str, frame: TranscriptionFrame) -> None:
        """A question was heard while IDLE — answer it if it's directed at us.

        Uses the lightweight Gemini-flash addressed-classifier (~200ms). If it is
        NOT for us, fall back to the proactive gate (a wrong fact phrased as a
        question can still raise a hand). Re-checks IDLE before acting because the
        classifier is async and the meeting may have moved on.
        """
        try:
            recent = await self._context.recent_turns_text(n=8)
            is_addressed, _conf = await classify_addressed(
                agent_name=self._agent_name,
                utterance=text,
                recent_turns=recent,
            )
        except Exception as e:
            log.warning(
                "turn_gate_classify_failed",
                meeting_id=self._session.meeting_id, error=str(e)[:160],
            )
            return
        if self._state != self.IDLE:
            return  # a direct question or interjection took over meanwhile
        if is_addressed:
            log.info("turn_gate_answer_addressed", meeting_id=self._session.meeting_id)
            await self._answer_now(frame, text)
        elif self._gate_enabled:
            await self._evaluate(text, frame)

    # ── Direct-question answer (no hand) ──────────────────────────────────────
    async def _answer_now(self, frame: TranscriptionFrame, question: str) -> None:
        self._state = self.SPEAKING
        self._session.push_control({"type": "bot_state", "speaking": True})
        out = TranscriptionFrame(
            text=question,
            user_id=getattr(frame, "user_id", "") or "speaker",
            timestamp=getattr(frame, "timestamp", "") or "",
        )
        await self.push_frame(out, FrameDirection.DOWNSTREAM)

    # ── Proactive-interjection gate ───────────────────────────────────────────
    async def _evaluate(self, text: str, frame: TranscriptionFrame) -> None:
        try:
            recent = await self._context.recent_turns_text(n=10)
            # Pull KB context so the gate can fact-check project-specific claims.
            knowledge: list[str] = []
            try:
                gathered = await self._context.gather_for_qa(text, top_k=5)
                knowledge = (gathered.get("knowledge") or []) + (gathered.get("prior_meetings") or [])
            except Exception:
                knowledge = []
            decision = await evaluate_turn(
                agent_name=self._agent_name,
                recent_turns=recent,
                latest_utterance=text,
                knowledge=knowledge,
                meeting_id=self._session.meeting_id,
            )
        except Exception as e:
            log.warning("turn_gate_eval_failed", meeting_id=self._session.meeting_id, error=str(e)[:160])
            return
        if self._state != self.IDLE:
            return  # meeting moved on
        if decision.should_raise and decision.confidence > self._threshold:
            await self._raise_hand(decision.kind, decision.point, decision.confidence)

    async def _raise_hand(self, kind: str, point: str, confidence: float) -> None:
        self._state = self.HAND_RAISED
        self._pending_point = point
        self._session.push_control({"type": "hand", "raised": True})
        log.info(
            "turn_gate_hand_raised",
            meeting_id=self._session.meeting_id, kind=kind, confidence=confidence,
        )
        if self._timeout_task:
            self._timeout_task.cancel()
        self._timeout_task = self.create_task(self._hand_timeout_watch())

    async def _hand_timeout_watch(self) -> None:
        try:
            await asyncio.sleep(self._hand_timeout)
        except asyncio.CancelledError:
            return
        if self._state == self.HAND_RAISED:
            log.info("turn_gate_hand_timeout", meeting_id=self._session.meeting_id)
            await self._lower_hand()

    async def _grant_permission(self, frame: TranscriptionFrame) -> None:
        point = self._pending_point or ""
        log.info("turn_gate_permission_granted", meeting_id=self._session.meeting_id)
        if self._timeout_task:
            self._timeout_task.cancel()
            self._timeout_task = None
        self._state = self.SPEAKING
        self._session.push_control({"type": "bot_state", "speaking": True})
        # Speak the specific correction/help the gate flagged, grounded in the
        # recent conversation (the gate already considered the KB to decide).
        try:
            recent = await self._context.recent_turns_text(n=12)
        except Exception:
            recent = []
        convo = "\n".join(recent)
        instruction = (
            "You raised your hand because you have something to add to the meeting, "
            "and you've now been invited to speak. Say this point concisely and "
            "naturally, out loud, to the room:\n"
            f"{point}\n\n"
        )
        if convo:
            instruction += f"Recent conversation for context:\n{convo}"
        out = TranscriptionFrame(
            text=instruction,
            user_id=getattr(frame, "user_id", "") or "speaker",
            timestamp=getattr(frame, "timestamp", "") or "",
        )
        await self.push_frame(out, FrameDirection.DOWNSTREAM)

    async def _finish_speaking(self) -> None:
        self._state = self.IDLE
        self._pending_point = None
        self._session.push_control({"type": "hand", "raised": False})
        self._session.push_control({"type": "bot_state", "speaking": False})
        log.info("turn_gate_finished_speaking", meeting_id=self._session.meeting_id)

    async def _lower_hand(self) -> None:
        self._state = self.IDLE
        self._pending_point = None
        self._session.push_control({"type": "hand", "raised": False})
        # Reset the bot-page status text — the "Raising hand…" indicator would
        # otherwise stick (no bot_state follows on the timeout path).
        self._session.push_control({"type": "bot_state", "speaking": False})

    def _is_permission(self, text: str) -> bool:
        return any(rx.search(text) for rx in self._permission_res)
