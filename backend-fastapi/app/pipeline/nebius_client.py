"""
Nebius/Qwen proactive-interjection gate.

The always-on, cheap "should Bora jump in *unprompted*?" classifier. It runs on
every utterance that is NOT a direct question to Bora (those are answered
immediately — see app/pipeline/turn_gate.py). It flags only two situations
worth interrupting a meeting for:

  - WRONG_FACT : someone stated something factually incorrect about the project
                 or in general.
  - STUCK      : the participants are struggling / going in circles on a point
                 Bora could help unblock.

It does NOT decide to speak. On a confident flag the bot raises its hand; a human
decides whether to call on it. When called on, Bora says the correction/help
this gate identified (grounded in the knowledge base + recent conversation).

Model: Qwen/Qwen3-30B-A3B-Instruct-2507 on Nebius (OpenAI-compatible). Fast MoE,
not a reasoning model → clean JSON. Parsed defensively; FAILS CLOSED (no
interjection) on any error/timeout so Bora never barges in on a gate glitch.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Literal

from app.config import get_settings
from app.logger import get_logger
from app.tracing import tag_run, traced

log = get_logger(__name__)

InterjectKind = Literal["none", "wrong_fact", "stuck"]


@dataclass(frozen=True)
class InterjectDecision:
    kind: InterjectKind
    confidence: float
    # What Bora would say if called on — the correction or the help to offer.
    point: str
    reason: str

    @property
    def should_raise(self) -> bool:
        return self.kind in ("wrong_fact", "stuck")


_SILENT = InterjectDecision(kind="none", confidence=0.0, point="", reason="")

_SYSTEM_PROMPT = """You are a proactive-interjection gate for a voice AI teammate named "{agent_name}" \
that silently listens to a live meeting. {agent_name} answers DIRECT questions \
elsewhere — your job is ONLY to catch moments where {agent_name} should jump in \
UNPROMPTED. There are exactly two such moments:

1. "wrong_fact": a participant stated something factually INCORRECT — about this \
   project/company (use the provided knowledge base) or in general (use your own \
   knowledge). Only flag clear, consequential errors, not opinions or rounding.
2. "stuck": the participants are clearly struggling, going in circles, or asking \
   each other something none of them can answer, and {agent_name} could help.

Otherwise return "none". Be conservative — interrupting a meeting has a cost.

Reply with ONLY a JSON object, no prose:
{{"kind": "none"|"wrong_fact"|"stuck", "confidence": <0..1>, "point": "<one sentence: the correction to make or the help to offer, addressed to the room>", "reason": "<short>"}}

If kind is "none", set confidence low and point to "".
For "wrong_fact", point states the correct fact. For "stuck", point states the help."""


_cached_client = None


def _client():
    """Module-level AsyncOpenAI client (reuses the httpx connection pool)."""
    global _cached_client
    if _cached_client is None:
        from openai import AsyncOpenAI

        s = get_settings()
        _cached_client = AsyncOpenAI(
            api_key=s.get("nebius_api_key") or "",
            base_url=s.get("nebius_api_base") or "https://api.tokenfactory.nebius.com/v1",
            timeout=2.5,
        )
    return _cached_client


def _parse(text: str) -> InterjectDecision:
    """Tolerant JSON extraction — handles a bare object or one wrapped in prose."""
    if not text:
        return _SILENT
    candidate = text.strip()
    if not candidate.startswith("{"):
        m = re.search(r"\{.*\}", candidate, re.DOTALL)
        if not m:
            return _SILENT
        candidate = m.group(0)
    try:
        obj = json.loads(candidate)
    except (ValueError, TypeError):
        return _SILENT
    if not isinstance(obj, dict):
        return _SILENT
    kind = str(obj.get("kind") or "none").strip().lower()
    if kind not in ("wrong_fact", "stuck"):
        return _SILENT
    try:
        conf = float(obj.get("confidence", 0.0))
    except (TypeError, ValueError):
        conf = 0.0
    conf = max(0.0, min(1.0, conf))
    point = str(obj.get("point") or "")[:500]
    reason = str(obj.get("reason") or "")[:200]
    return InterjectDecision(kind=kind, confidence=conf, point=point, reason=reason)  # type: ignore[arg-type]


@traced(name="nebius_interject_gate", run_type="llm", tags=["turn-taking", "nebius"])
async def evaluate_turn(
    *,
    agent_name: str,
    recent_turns: list[str],
    latest_utterance: str,
    knowledge: list[str] | None = None,
    meeting_id: str | None = None,
) -> InterjectDecision:
    """Decide whether Bora should proactively raise its hand. Fails closed."""
    if not latest_utterance.strip():
        return _SILENT
    s = get_settings()
    if not s.get("nebius_api_key"):
        return _SILENT

    recent = "\n".join(f"- {t}" for t in recent_turns[-10:]) or "(no prior turns)"
    kb = "\n".join(f"- {k}" for k in (knowledge or [])[:6]) or "(no project knowledge retrieved)"
    user_msg = (
        f"Project knowledge base (for fact-checking project claims):\n{kb}\n\n"
        f"Recent turns (most recent last):\n{recent}\n\n"
        f'Latest utterance:\n"{latest_utterance.strip()}"'
    )
    tag_run(meeting_id=meeting_id, agent_name=agent_name)

    try:
        client = _client()
        kwargs = dict(
            model=s.get("nebius_trigger_model") or "Qwen/Qwen3-30B-A3B-Instruct-2507",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT.format(agent_name=agent_name)},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.0,
            max_tokens=200,
        )
        try:
            resp = await client.chat.completions.create(
                response_format={"type": "json_object"}, **kwargs
            )
        except Exception as first_err:
            status = getattr(first_err, "status_code", None) or getattr(first_err, "status", None)
            if status not in (400, 404, 422):
                raise
            resp = await client.chat.completions.create(**kwargs)
        out = (resp.choices[0].message.content or "") if resp.choices else ""
        decision = _parse(out)
        log.debug(
            "nebius_interject",
            meeting_id=meeting_id,
            kind=decision.kind,
            confidence=decision.confidence,
        )
        return decision
    except Exception as e:
        log.warning("nebius_gate_failed", meeting_id=meeting_id, error=str(e)[:200])
        return _SILENT
