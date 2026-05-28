"""
Hybrid turn-taking classifier.

Three short-circuit paths, in priority order:
  A. Name regex            — fast, explicit "Hey {AgentName}, ..."
  B. Addressed classifier  — Gemini-2.5-flash, ~200ms call, decides if utterance
                             is directed at the bot even without a name
  C. Fact-check eligibility — declarative statements get fact-checked silently

If none match, the bot stays quiet.

v1 bugs this fixes (from the v2 plan):
  - Bug #2: Bot was mute unless addressed by exact name. The classifier covers
    natural address: "what's the deadline on this?", "any thoughts on pricing?"
  - Bug #10: Regex brittleness ("Samantha", "samurai") — the regex stays as a
    cheap pre-filter, but the classifier is the real decision.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.config import get_settings
from app.logger import get_logger
from app.tracing import traced

log = get_logger(__name__)

TriggerKind = Literal["name", "addressed", "factcheck", "none"]


@dataclass(frozen=True)
class TurnDecision:
    kind: TriggerKind
    content: str             # the user utterance to act on
    confidence: float        # 0.0–1.0
    elapsed_ms: int          # for telemetry


# ─── Path A: name regex (reused from v1's _detect_trigger) ───────────────────


def _name_pattern(agent_name: str) -> re.Pattern[str]:
    safe = re.escape(agent_name.strip())
    # Match "Hey Sam, ...", "Sam: ...", "@Sam ...", "Sam what's up?"
    return re.compile(
        rf"(?:hey\s+|ok\s+|okay\s+|@)?(?<![a-z]){safe}(?![a-z])\s*[,:]?\s*(.+)",
        re.IGNORECASE,
    )


def match_name(agent_name: str, utterance: str) -> str | None:
    """Return the question if the utterance starts with the agent name."""
    if not agent_name or not utterance:
        return None
    m = _name_pattern(agent_name).match(utterance.strip())
    if not m:
        return None
    question = (m.group(1) or "").strip()
    return question if len(question) >= 5 else None


# ─── Path B: addressed-to-bot classifier ─────────────────────────────────────

_ADDRESSED_PROMPT = """You are a turn-taking classifier for a voice AI assistant named "{agent_name}" \
that listens in real-time meetings.

Recent meeting turns (most recent last):
{recent_turns}

Latest utterance:
"{utterance}"

Decide: is the latest utterance addressed to the assistant ("{agent_name}") \
or asking a question the assistant should answer?

Reply with one word only: YES or NO.

Guidance:
- YES if it's a question someone might ask an assistant (factual, lookup, summary, status).
- YES if the speaker is clearly addressing the assistant even without naming it.
- NO if it's small talk, side conversation, an answer to another participant, or thinking out loud.
- NO if it's a statement of opinion or a direction to another human."""


@traced(name="classify_addressed", run_type="llm", tags=["turn-taking", "classifier"])
async def classify_addressed(
    *,
    agent_name: str,
    utterance: str,
    recent_turns: list[str],
) -> tuple[bool, float]:
    """
    Returns (is_addressed, confidence). Lazy-imports google-genai client.

    Uses the live_qa_model (gemini-2.5-flash) with thinking_budget=0 for ~200ms latency.
    """
    if not utterance.strip():
        return False, 0.0

    try:
        from google import genai
        from google.genai import types as gtypes
    except ImportError:
        log.warning("genai_sdk_missing")
        return False, 0.0

    settings = get_settings()
    project = settings.get("gcp_project")
    location = settings.get("gcp_location") or "us-central1"
    model = settings.get("live_qa_model") or "gemini-2.5-flash"

    if not project:
        return False, 0.0

    client = genai.Client(vertexai=True, project=project, location=location)
    recent_str = "\n".join(f"- {t}" for t in recent_turns[-8:]) or "(no prior turns)"
    prompt = _ADDRESSED_PROMPT.format(
        agent_name=agent_name,
        recent_turns=recent_str,
        utterance=utterance.strip(),
    )

    try:
        resp = await client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=gtypes.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=8,
                thinking_config=gtypes.ThinkingConfig(thinking_budget=0),
            ),
        )
        text = (resp.text or "").strip().upper()
        is_yes = text.startswith("YES")
        # Confidence is binary for now — could parse logprobs later.
        return is_yes, (0.85 if is_yes else 0.85)
    except Exception as e:
        log.error("classify_addressed_failed", error=str(e)[:200])
        return False, 0.0


# ─── Path C: fact-check eligibility (reused from v1's _should_run_factcheck) ──


def is_factcheck_eligible(utterance: str) -> bool:
    """
    Declarative statements with enough substance to be fact-checked.

    v1 thresholds (aggressive for demo): >=20 chars, >=4 words, no '?'.
    """
    s = utterance.strip()
    if not s or s.endswith("?"):
        return False
    if len(s) < 20:
        return False
    if len(s.split()) < 4:
        return False
    return True


# ─── Combined entry point ────────────────────────────────────────────────────


@traced(name="decide_turn", run_type="chain", tags=["turn-taking"])
async def decide_turn(
    *,
    agent_name: str,
    utterance: str,
    recent_turns: list[str],
    proactive_fact_check: bool,
) -> TurnDecision:
    """
    Single call site for the pipeline. Returns the decision in priority order.
    """
    import time
    t0 = time.monotonic()

    # Path A: explicit name
    name_question = match_name(agent_name, utterance)
    if name_question:
        return TurnDecision(
            kind="name",
            content=name_question,
            confidence=1.0,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )

    # Path B: addressed classifier (only for question-like utterances to save tokens)
    looks_like_question = utterance.strip().endswith("?") or _question_words(utterance)
    if looks_like_question:
        is_addressed, conf = await classify_addressed(
            agent_name=agent_name,
            utterance=utterance,
            recent_turns=recent_turns,
        )
        if is_addressed:
            return TurnDecision(
                kind="addressed",
                content=utterance.strip(),
                confidence=conf,
                elapsed_ms=int((time.monotonic() - t0) * 1000),
            )

    # Path C: silent fact-check
    if proactive_fact_check and is_factcheck_eligible(utterance):
        return TurnDecision(
            kind="factcheck",
            content=utterance.strip(),
            confidence=0.7,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )

    return TurnDecision(
        kind="none",
        content="",
        confidence=0.0,
        elapsed_ms=int((time.monotonic() - t0) * 1000),
    )


_Q_WORDS = {"what", "when", "where", "why", "who", "how", "can", "could", "should",
            "would", "is", "are", "was", "were", "do", "does", "did", "will"}


def _question_words(utterance: str) -> bool:
    first = utterance.strip().split(maxsplit=1)[0].lower() if utterance.strip() else ""
    return first in _Q_WORDS
