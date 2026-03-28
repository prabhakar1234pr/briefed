from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings

from tests.data_fixtures import MEETING_LIVE


def _bot_status_body(event: str, bot_id: str | None = None) -> dict:
    bid = bot_id or MEETING_LIVE["bot_id"]
    return {"event": event, "data": {"bot": {"id": bid}}}


def test_recall_bot_status_updates_progress(webhook_client: TestClient) -> None:
    r = webhook_client.post(
        "/api/webhooks/recall/bot-status",
        json=_bot_status_body("bot.in_call_recording"),
    )
    assert r.status_code == 200
    assert r.json() == {"ok": "true"}


def test_recall_bot_done_schedules_finalize(
    webhook_client: TestClient, monkeypatch: pytest.MonkeyPatch, meeting_id: str
) -> None:
    finalize = AsyncMock()
    monkeypatch.setattr("app.main.finalize_meeting", finalize)
    r = webhook_client.post(
        "/api/webhooks/recall/bot-status",
        json=_bot_status_body("bot.done"),
    )
    assert r.status_code == 200
    finalize.assert_awaited_once_with(MEETING_LIVE["bot_id"])


def test_recall_realtime_appends_transcript(
    webhook_client: TestClient, fake_db, meeting_id: str
) -> None:
    before = len(
        [r for r in fake_db.tables["transcript_lines"] if r["meeting_id"] == meeting_id]
    )
    body = {
        "event": "transcript.data",
        "data": {
            "bot": {"id": MEETING_LIVE["bot_id"]},
            "data": {
                "words": [
                    {"text": "We", "start_timestamp": {"absolute": "2025-03-24T18:06:00Z"}},
                    {"text": "should", "start_timestamp": {"absolute": "2025-03-24T18:06:00.1Z"}},
                    {"text": "ship", "start_timestamp": {"absolute": "2025-03-24T18:06:00.2Z"}},
                ],
                "participant": {"name": "Sam Okonkwo"},
            },
        },
    }
    r = webhook_client.post(
        f"/api/webhooks/recall/realtime?meeting_id={meeting_id}",
        json=body,
    )
    assert r.status_code == 200
    after = len(
        [r for r in fake_db.tables["transcript_lines"] if r["meeting_id"] == meeting_id]
    )
    assert after == before + 1
    last = [r for r in fake_db.tables["transcript_lines"] if r["meeting_id"] == meeting_id][-1]
    assert "ship" in last["content"].lower()
    assert last["speaker_name"] == "Sam Okonkwo"


def test_recall_realtime_accepts_trailing_slash(
    webhook_client: TestClient, meeting_id: str
) -> None:
    r = webhook_client.post(
        f"/api/webhooks/recall/realtime/?meeting_id={meeting_id}",
        json={"event": "transcript.data", "data": {"data": {"words": [], "participant": {"name": "x"}}}},
    )
    assert r.status_code == 200


def test_recall_webhook_rejects_invalid_secret(
    webhook_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WEBHOOK_SECRET", "only-recall-may-call")
    get_settings.cache_clear()
    try:
        r = webhook_client.post(
            "/api/webhooks/recall/bot-status",
            json=_bot_status_body("bot.in_call_recording"),
        )
        assert r.status_code == 401
    finally:
        monkeypatch.setenv("WEBHOOK_SECRET", "")
        get_settings.cache_clear()
