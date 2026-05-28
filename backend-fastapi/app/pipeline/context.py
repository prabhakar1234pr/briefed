"""
Per-meeting context: in-memory turn ring buffer + cross-meeting recall.

The ring buffer is the bot's *working memory* during a meeting — fast,
local, never hits a database. At meeting end it's flushed to Supermemory
as a "kind=meeting" memory so future meetings can recall what was said.

For Q&A, we compose three sources:
  1. Recent turns from THIS meeting (ring buffer)
  2. Long-term knowledge (Supermemory, kind=doc + kind=code)
  3. Prior-meeting context (Supermemory, kind=meeting)
"""
from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.logger import get_logger
from app.pipeline import memory as mem

log = get_logger(__name__)


@dataclass
class Turn:
    speaker: str
    text: str
    ts: datetime


class MeetingContext:
    """
    Per-meeting state owned by the pipeline runner.

    Thread-safe enough for the single-task-per-meeting pattern in runner.py.
    Don't share across meetings.
    """

    def __init__(self, *, meeting_id: str, agent_id: str, agent_name: str, max_turns: int = 60):
        self.meeting_id = meeting_id
        self.agent_id = agent_id
        self.agent_name = agent_name
        self._turns: deque[Turn] = deque(maxlen=max_turns)
        self._lock = asyncio.Lock()

    async def append_turn(self, speaker: str, text: str) -> None:
        text = text.strip()
        if not text:
            return
        async with self._lock:
            self._turns.append(Turn(speaker=speaker, text=text, ts=datetime.now(timezone.utc)))

    async def recent_turns_text(self, n: int = 20) -> list[str]:
        async with self._lock:
            tail = list(self._turns)[-n:]
        return [f"{t.speaker}: {t.text}" for t in tail]

    async def gather_for_qa(self, question: str, *, top_k: int = 6) -> dict[str, Any]:
        """
        Composite recall for live Q&A. Run all three lookups in parallel.

        Returns:
          {
            "recent_turns": [str],         # this meeting
            "knowledge":    [str],         # docs + code
            "prior_meetings": [str],       # cross-meeting recall
          }
        """
        recent_task = self.recent_turns_text(n=20)
        knowledge_task = mem.search_memory(
            agent_id=self.agent_id,
            query=question,
            top_k=top_k,
            kinds=["doc", "code"],
        )
        prior_task = mem.search_memory(
            agent_id=self.agent_id,
            query=question,
            top_k=3,
            kinds=["meeting"],
        )
        recent, knowledge, prior = await asyncio.gather(
            recent_task, knowledge_task, prior_task, return_exceptions=True
        )

        def _texts(result: Any) -> list[str]:
            if isinstance(result, Exception):
                log.error("gather_for_qa_partial", error=str(result)[:200])
                return []
            if not result:
                return []
            if isinstance(result, list) and result and isinstance(result[0], dict):
                return [r["content"] for r in result if r.get("content")]
            return list(result) if isinstance(result, list) else []

        return {
            "recent_turns": _texts(recent),
            "knowledge": _texts(knowledge),
            "prior_meetings": _texts(prior),
        }

    async def flush_to_long_term_memory(self, summary: str) -> None:
        """
        Called at meeting end. Persists this meeting's summary as a "meeting"
        memory so Sam's next meeting knows what happened in this one.

        Phase 4a — invoked from finalize_meeting() in main.py.
        """
        if not summary or len(summary) < 40:
            return
        await mem.add_memory(
            agent_id=self.agent_id,
            content=summary,
            source_url=f"meeting://{self.meeting_id}",
            kind="meeting",
            extra_metadata={"meeting_id": self.meeting_id},
        )
