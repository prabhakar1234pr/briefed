"""Tests for trigger detection logic — the regex/keyword matching that decides
whether a transcript line should trigger Q&A, screenshot, or fact-check."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.main import _detect_trigger, _should_run_factcheck


# ─── Q&A trigger ──────────────────────────────────────────────────────────────

class TestQATrigger:
    """Agent name = 'Pal'"""

    @pytest.mark.parametrize("text,expected_question", [
        ("Hey Pal, what are the rate limits?", "what are the rate limits?"),
        ("hey pal what is our deadline?", "what is our deadline?"),
        ("Ok Pal, explain the auth flow", "explain the auth flow"),
        ("okay pal, who owns billing?", "who owns billing?"),
        ("@pal summarize the last quarter", "summarize the last quarter"),
        ("Pal, how does the API work?", "how does the api work?"),
        ("Pal: tell me about the roadmap", "tell me about the roadmap"),
    ])
    def test_qa_trigger_matches(self, text: str, expected_question: str) -> None:
        trigger, content = _detect_trigger(text, "Pal", screenshot_on=True)
        assert trigger == "qa"
        assert content is not None
        assert expected_question in content.lower()

    @pytest.mark.parametrize("text", [
        "I think we should ask Paul about this",
        "The palette looks good",                   # "pal" inside "palette" — must NOT match
        "Principal engineer joined the call",        # "pal" inside "Principal" — must NOT match
        "Let's move on to the next topic",
        "",
        "This is a great plan for the team",
        "Nepal is beautiful this time of year",
    ])
    def test_qa_trigger_no_match(self, text: str) -> None:
        trigger, _ = _detect_trigger(text, "Pal", screenshot_on=True)
        assert trigger != "qa", f"False positive: '{text}' matched as QA trigger"


# ─── Screenshot trigger ──────────────────────────────────────────────────────

class TestScreenshotTrigger:

    @pytest.mark.parametrize("text", [
        "Take a screenshot",
        "screenshot please",
        "Grab a screenshot of this",
        "Can you capture screen",
    ])
    def test_screenshot_trigger_matches(self, text: str) -> None:
        trigger, _ = _detect_trigger(text, "Pal", screenshot_on=True)
        assert trigger == "screenshot"

    def test_screenshot_disabled(self) -> None:
        trigger, _ = _detect_trigger("take a screenshot", "Pal", screenshot_on=False)
        assert trigger != "screenshot"

    def test_screenshot_takes_priority_over_qa(self) -> None:
        """If someone says 'Pal take a screenshot' both could match — screenshot wins."""
        trigger, _ = _detect_trigger(
            "Pal, take a screenshot of the dashboard", "Pal", screenshot_on=True
        )
        assert trigger == "screenshot"


# ─── Fact-check eligibility ──────────────────────────────────────────────────

class TestFactCheckEligibility:

    def _agent(self, **overrides: object) -> dict:
        base = {
            "mode": "copilot",
            "proactive_fact_check": True,
        }
        base.update(overrides)
        return base

    @pytest.mark.asyncio
    @patch("app.rate_limit.check_fact_cooldown", new_callable=AsyncMock, return_value=True)
    @patch("app.rate_limit.check_fact_hourly_cap", new_callable=AsyncMock, return_value=True)
    async def test_factcheck_eligible(self, _cap, _cool) -> None:
        text = "The API rate limit is 5000 requests per minute for all workspaces"
        assert await _should_run_factcheck("meet-1", text, self._agent())

    @pytest.mark.asyncio
    async def test_factcheck_skips_short_text(self) -> None:
        assert not await _should_run_factcheck("meet-1", "Yes", self._agent())

    @pytest.mark.asyncio
    async def test_factcheck_skips_questions(self) -> None:
        assert not await _should_run_factcheck("meet-1", "What is the rate limit for our API?", self._agent())

    @pytest.mark.asyncio
    async def test_factcheck_skips_proctor_mode(self) -> None:
        text = "The API rate limit is 5000 requests per minute for all workspaces"
        assert not await _should_run_factcheck("meet-1", text, self._agent(mode="proctor"))

    @pytest.mark.asyncio
    async def test_factcheck_skips_when_disabled(self) -> None:
        text = "The API rate limit is 5000 requests per minute for all workspaces"
        assert not await _should_run_factcheck(
            "meet-1", text, self._agent(proactive_fact_check=False)
        )

    @pytest.mark.asyncio
    async def test_factcheck_skips_few_words(self) -> None:
        text = "Too short"  # < 4 words
        assert not await _should_run_factcheck("meet-1", text, self._agent())
