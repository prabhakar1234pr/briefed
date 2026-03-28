"""Tests for the /ws/copilot/{meeting_id} WebSocket endpoint."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

from tests.data_fixtures import (
    AGENT_COPILOT,
    AUTH_USERS,
    MEETING_LIVE,
    USER_ID,
    seed_tables,
)
from tests.fake_supabase import FakeSupabase


@pytest.fixture
def fake_db() -> FakeSupabase:
    return FakeSupabase(seed_tables(), auth_users=AUTH_USERS)


@pytest.fixture
def ws_client(fake_db: FakeSupabase, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.main.get_supabase_service", lambda: fake_db)
    monkeypatch.setattr("app.context_pipeline.get_supabase_service", lambda: fake_db)
    app.dependency_overrides.clear()
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()


class TestWsCopilotEndpoint:

    def test_streams_tokens_and_done(
        self, ws_client: TestClient, fake_db: FakeSupabase, monkeypatch
    ) -> None:
        """Send a trigger, receive token messages and done."""
        mock_search = AsyncMock(return_value=["Rate limits are 1000 req/min."])
        monkeypatch.setattr("app.context_pipeline.search_context", mock_search)

        # Mock TTS and audio injection (needed by ACK + sentence injection)
        monkeypatch.setattr("app.ai_client.thinking_acknowledgement", AsyncMock(return_value=b"fake-ack-mp3"))
        monkeypatch.setattr("app.ai_client.text_to_speech_mp3", AsyncMock(return_value=b"fake-mp3"))
        monkeypatch.setattr("app.ai_client.embed_text", AsyncMock(return_value=[[0.0] * 768]))
        monkeypatch.setattr("app.output_media.inject_audio", AsyncMock())

        async def fake_stream(**kwargs):
            yield "The rate limit is one thousand requests per minute."
            yield "This applies to all workspaces."

        monkeypatch.setattr("app.ai_client.answer_question_streaming", fake_stream)

        with ws_client.websocket_connect(f"/ws/copilot/{MEETING_LIVE['id']}") as ws:
            ws.send_json({
                "type": "trigger",
                "question": "What are the rate limits?",
                "agent_id": AGENT_COPILOT["id"],
            })

            # Should receive two token messages
            msg1 = ws.receive_json()
            assert msg1["type"] == "token"
            assert "thousand" in msg1["text"].lower()

            msg2 = ws.receive_json()
            assert msg2["type"] == "token"
            assert "workspaces" in msg2["text"].lower()

            # Should receive done
            msg3 = ws.receive_json()
            assert msg3["type"] == "done"

        # Verify interaction was saved
        interactions = [
            r for r in fake_db.tables["meeting_interactions"]
            if r.get("trigger_text") == "What are the rate limits?"
        ]
        assert len(interactions) == 1

    def test_rejects_invalid_meeting(self, ws_client: TestClient) -> None:
        """WebSocket should close with 4004 for non-existent meeting."""
        with pytest.raises(Exception):
            with ws_client.websocket_connect("/ws/copilot/nonexistent-meeting-id") as ws:
                ws.receive_json()

    def test_rejects_completed_meeting(
        self, ws_client: TestClient, fake_db: FakeSupabase
    ) -> None:
        """WebSocket should close for meetings not in active status."""
        from tests.data_fixtures import MEETING_DONE
        with pytest.raises(Exception):
            with ws_client.websocket_connect(f"/ws/copilot/{MEETING_DONE['id']}") as ws:
                ws.receive_json()

    def test_error_on_missing_fields(
        self, ws_client: TestClient, fake_db: FakeSupabase
    ) -> None:
        """Sending trigger without question should return error."""
        with ws_client.websocket_connect(f"/ws/copilot/{MEETING_LIVE['id']}") as ws:
            ws.send_json({"type": "trigger", "question": "", "agent_id": ""})
            msg = ws.receive_json()
            assert msg["type"] == "error"

    def test_error_on_unknown_agent(
        self, ws_client: TestClient, fake_db: FakeSupabase
    ) -> None:
        """Sending trigger with non-existent agent_id should return error."""
        with ws_client.websocket_connect(f"/ws/copilot/{MEETING_LIVE['id']}") as ws:
            ws.send_json({
                "type": "trigger",
                "question": "Hello?",
                "agent_id": "nonexistent-agent",
            })
            msg = ws.receive_json()
            assert msg["type"] == "error"


class TestOutputMediaBotCreation:

    def test_start_meeting_output_media_mode(
        self, ws_client: TestClient, fake_db: FakeSupabase, monkeypatch
    ) -> None:
        """When Cartesia key + bot page URL are set, bot uses Output Media."""
        monkeypatch.setenv("CARTESIA_API_KEY", "sk_cart_test_key")
        monkeypatch.setenv("BOT_PAGE_URL", "https://storage.googleapis.com/briefed-bot-page/index.html")
        get_settings.cache_clear()

        # Need auth for this endpoint
        def _user() -> str:
            return USER_ID

        from app.auth_deps import get_user_id
        app.dependency_overrides[get_user_id] = _user

        create = AsyncMock(return_value={"id": "recall-bot-output-media"})
        monkeypatch.setattr("app.main.recall.create_bot", create)

        try:
            r = ws_client.post(
                "/api/meetings/start",
                json={
                    "agent_id": AGENT_COPILOT["id"],
                    "meeting_link": "https://meet.google.com/output-media-test",
                    "join_now": True,
                },
            )
            assert r.status_code == 200, r.text
            out = r.json()
            assert out["bot_id"] == "recall-bot-output-media"

            # Verify Recall payload
            create.assert_awaited_once()
            payload = create.await_args.args[0]
            assert payload.get("bot_variant") == "web_4_core"
            assert "output_media" in payload
            assert payload["output_media"]["camera"]["kind"] == "webpage"
            page_url = payload["output_media"]["camera"]["config"]["url"]
            assert "meeting_id=" in page_url
            assert "cartesia_key=" in page_url
            assert "agent_name=" in page_url
            assert "backend_ws=" in page_url
            # Should NOT have automatic_audio_output
            assert "automatic_audio_output" not in payload

            # Verify meeting row was created
            meeting_row = next(
                m for m in fake_db.tables["meetings"]
                if m["id"] == out["meeting_id"]
            )
            assert meeting_row["status"] == "joining"
        finally:
            app.dependency_overrides.clear()
            get_settings.cache_clear()

    def test_start_meeting_legacy_when_no_cartesia_key(
        self, ws_client: TestClient, fake_db: FakeSupabase, monkeypatch
    ) -> None:
        """Without Cartesia key, falls back to output_audio (legacy)."""
        monkeypatch.setenv("CARTESIA_API_KEY", "")
        get_settings.cache_clear()

        def _user() -> str:
            return USER_ID

        from app.auth_deps import get_user_id
        app.dependency_overrides[get_user_id] = _user

        create = AsyncMock(return_value={"id": "recall-bot-legacy"})
        monkeypatch.setattr("app.main.recall.create_bot", create)

        try:
            r = ws_client.post(
                "/api/meetings/start",
                json={
                    "agent_id": AGENT_COPILOT["id"],
                    "meeting_link": "https://meet.google.com/legacy-test",
                    "join_now": True,
                },
            )
            assert r.status_code == 200
            payload = create.await_args.args[0]
            assert "automatic_audio_output" in payload
            assert "output_media" not in payload
        finally:
            app.dependency_overrides.clear()
            get_settings.cache_clear()
