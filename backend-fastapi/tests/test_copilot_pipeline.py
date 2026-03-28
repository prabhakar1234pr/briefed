"""Tests for the copilot trigger pipeline — the core Q&A flow from
trigger detection through Gemini streaming, TTS, and audio injection."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from tests.data_fixtures import (
    AGENT_COPILOT,
    AGENT_FACTCHECK,
    AGENT_PROCTOR,
    AUTH_USERS,
    MEETING_LIVE,
    seed_tables,
)
from tests.fake_supabase import FakeSupabase


@pytest.fixture
def db() -> FakeSupabase:
    return FakeSupabase(seed_tables(), auth_users=AUTH_USERS)


class TestCopilotTriggerQA:
    """process_copilot_trigger with trigger_type='qa'."""

    @pytest.mark.asyncio
    async def test_qa_pipeline_produces_interaction(self, db: FakeSupabase, monkeypatch) -> None:
        """Full QA pipeline: ACK → context search → stream → TTS → inject → save interaction."""
        monkeypatch.setattr("app.main.get_supabase_service", lambda: db)

        # Mock context search → returns fake chunks
        mock_search = AsyncMock(return_value=["Rate limits are 1000 req/min."])
        monkeypatch.setattr("app.context_pipeline.search_context", mock_search)

        # Mock streaming — yield two sentences
        async def fake_stream(**kwargs):
            yield "The rate limit is one thousand requests per minute."
            yield "This applies to all workspaces."
        monkeypatch.setattr("app.ai_client.answer_question_streaming", fake_stream)

        # Mock TTS → return fake MP3 bytes
        mock_tts = AsyncMock(return_value=b"fake-mp3-data")
        monkeypatch.setattr("app.ai_client.text_to_speech_mp3", mock_tts)
        monkeypatch.setattr("app.ai_client.thinking_acknowledgement", AsyncMock(return_value=b"ack-mp3"))

        # Mock inject_audio → always succeed
        mock_inject = AsyncMock(return_value=True)
        monkeypatch.setattr("app.output_media.inject_audio", mock_inject)

        from app.main import process_copilot_trigger
        await process_copilot_trigger(
            meeting_id=MEETING_LIVE["id"],
            bot_id=MEETING_LIVE["bot_id"],
            trigger_type="qa",
            content="What are the rate limits?",
            agent=AGENT_COPILOT,
            spoken_at="2025-03-24T18:04:00+00:00",
        )

        # Verify interaction was saved
        interactions = [
            r for r in db.tables["meeting_interactions"]
            if r.get("interaction_type") == "qa"
            and r.get("trigger_text") == "What are the rate limits?"
        ]
        assert len(interactions) == 1
        assert "thousand" in interactions[0]["response_text"].lower()

        # Verify TTS was called once for the full response (single inject)
        assert mock_tts.await_count == 1
        # Verify inject was called: 1 ACK + 1 full response = 2
        assert mock_inject.await_count == 2

    @pytest.mark.asyncio
    async def test_proctor_mode_does_nothing(self, db: FakeSupabase, monkeypatch) -> None:
        monkeypatch.setattr("app.main.get_supabase_service", lambda: db)

        from app.main import process_copilot_trigger
        before = len(db.tables["meeting_interactions"])
        await process_copilot_trigger(
            meeting_id=MEETING_LIVE["id"],
            bot_id=MEETING_LIVE["bot_id"],
            trigger_type="qa",
            content="What are the rate limits?",
            agent=AGENT_PROCTOR,
            spoken_at="2025-03-24T18:04:00+00:00",
        )
        assert len(db.tables["meeting_interactions"]) == before


class TestCopilotTriggerScreenshot:

    @pytest.mark.asyncio
    async def test_screenshot_saves_interaction(self, db: FakeSupabase, monkeypatch) -> None:
        monkeypatch.setattr("app.main.get_supabase_service", lambda: db)

        # Mock take_screenshot → return base64
        mock_screenshot = AsyncMock(return_value="base64screenshotdata")
        monkeypatch.setattr("app.output_media.take_screenshot", mock_screenshot)

        # Mock TTS + inject
        monkeypatch.setattr("app.ai_client.text_to_speech_mp3", AsyncMock(return_value=b"mp3"))
        monkeypatch.setattr("app.output_media.inject_audio", AsyncMock(return_value=True))

        from app.main import process_copilot_trigger
        await process_copilot_trigger(
            meeting_id=MEETING_LIVE["id"],
            bot_id=MEETING_LIVE["bot_id"],
            trigger_type="screenshot",
            content="take a screenshot",
            agent=AGENT_COPILOT,
            spoken_at="2025-03-24T18:04:00+00:00",
        )

        screenshots = [
            r for r in db.tables["meeting_interactions"]
            if r.get("interaction_type") == "screenshot"
        ]
        assert len(screenshots) == 1
        assert "saved" in screenshots[0]["response_text"].lower()

    @pytest.mark.asyncio
    async def test_screenshot_unavailable(self, db: FakeSupabase, monkeypatch) -> None:
        monkeypatch.setattr("app.main.get_supabase_service", lambda: db)
        monkeypatch.setattr("app.output_media.take_screenshot", AsyncMock(return_value=None))
        monkeypatch.setattr("app.ai_client.text_to_speech_mp3", AsyncMock(return_value=b"mp3"))
        monkeypatch.setattr("app.output_media.inject_audio", AsyncMock(return_value=True))

        from app.main import process_copilot_trigger
        await process_copilot_trigger(
            meeting_id=MEETING_LIVE["id"],
            bot_id=MEETING_LIVE["bot_id"],
            trigger_type="screenshot",
            content="take a screenshot",
            agent=AGENT_COPILOT,
            spoken_at="2025-03-24T18:04:00+00:00",
        )

        screenshots = [
            r for r in db.tables["meeting_interactions"]
            if r.get("interaction_type") == "screenshot"
        ]
        assert len(screenshots) == 1
        assert "wasn't able" in screenshots[0]["response_text"].lower()


class TestCopilotTriggerFactCheck:

    @pytest.mark.asyncio
    async def test_factcheck_contradiction_injects_correction(
        self, db: FakeSupabase, monkeypatch
    ) -> None:
        monkeypatch.setattr("app.main.get_supabase_service", lambda: db)

        mock_search = AsyncMock(return_value=["Rate limits are 1000 req/min."])
        monkeypatch.setattr("app.context_pipeline.search_context", mock_search)

        mock_factcheck = AsyncMock(return_value={
            "contradicts": True,
            "correction": "Actually, the rate limit is one thousand, not five thousand.",
        })
        monkeypatch.setattr("app.ai_client.fact_check", mock_factcheck)

        mock_tts = AsyncMock(return_value=b"mp3-correction")
        monkeypatch.setattr("app.ai_client.text_to_speech_mp3", mock_tts)
        mock_inject = AsyncMock(return_value=True)
        monkeypatch.setattr("app.output_media.inject_audio", mock_inject)

        from app.main import process_copilot_trigger
        await process_copilot_trigger(
            meeting_id=MEETING_LIVE["id"],
            bot_id=MEETING_LIVE["bot_id"],
            trigger_type="factcheck",
            content="The rate limit is 5000 requests per minute",
            agent=AGENT_FACTCHECK,
            spoken_at="2025-03-24T18:04:00+00:00",
        )

        interactions = [
            r for r in db.tables["meeting_interactions"]
            if r.get("interaction_type") == "factcheck"
        ]
        assert len(interactions) == 1
        assert "one thousand" in interactions[0]["response_text"].lower()
        mock_inject.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_factcheck_no_contradiction_no_response(
        self, db: FakeSupabase, monkeypatch
    ) -> None:
        monkeypatch.setattr("app.main.get_supabase_service", lambda: db)

        monkeypatch.setattr(
            "app.context_pipeline.search_context",
            AsyncMock(return_value=["Some context"]),
        )
        monkeypatch.setattr(
            "app.ai_client.fact_check",
            AsyncMock(return_value={"contradicts": False, "correction": None}),
        )
        mock_inject = AsyncMock()
        monkeypatch.setattr("app.output_media.inject_audio", mock_inject)

        before = len(db.tables["meeting_interactions"])

        from app.main import process_copilot_trigger
        await process_copilot_trigger(
            meeting_id=MEETING_LIVE["id"],
            bot_id=MEETING_LIVE["bot_id"],
            trigger_type="factcheck",
            content="The rate limit is 1000 requests per minute",
            agent=AGENT_FACTCHECK,
            spoken_at="2025-03-24T18:04:00+00:00",
        )

        # No new interaction saved, no audio injected
        assert len(db.tables["meeting_interactions"]) == before
        mock_inject.assert_not_awaited()
