from __future__ import annotations

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from tests.data_fixtures import MEETING_INTERACTION, MEETING_LIVE


def test_get_meeting_with_transcript_lines(client: TestClient, meeting_id: str) -> None:
    r = client.get(f"/api/meetings/{meeting_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == meeting_id
    assert body["status"] == "in_meeting"
    assert body["meeting_link"] == MEETING_LIVE["meeting_link"]
    lines = body["transcript_lines"]
    assert len(lines) >= 2
    assert lines[0]["speaker_name"] == "Alex Rivera"
    assert "roadmap" in lines[0]["content"].lower()


def test_get_meeting_not_found(client: TestClient) -> None:
    r = client.get("/api/meetings/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_list_interactions(client: TestClient, meeting_id: str) -> None:
    r = client.get(f"/api/meetings/{meeting_id}/interactions")
    assert r.status_code == 200
    data = r.json()["interactions"]
    assert len(data) >= 1
    assert data[0]["interaction_type"] == MEETING_INTERACTION["interaction_type"]
    assert "rate limits" in data[0]["trigger_text"].lower()


def test_start_meeting_happy_path(
    client: TestClient, fake_db, agent_id_copilot: str, monkeypatch
) -> None:
    create = AsyncMock(return_value={"id": "recall-bot-e2e-new"})
    monkeypatch.setattr("app.main.recall.create_bot", create)

    before = len(fake_db.tables["meetings"])
    r = client.post(
        "/api/meetings/start",
        json={
            "agent_id": agent_id_copilot,
            "meeting_link": "https://meet.google.com/zzz-aaaa-bbb",
            "join_now": True,
        },
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert "meeting_id" in out and "bot_id" in out
    assert out["bot_id"] == "recall-bot-e2e-new"
    assert len(fake_db.tables["meetings"]) == before + 1
    row = next(m for m in fake_db.tables["meetings"] if m["id"] == out["meeting_id"])
    assert row["status"] == "joining"
    assert row["bot_id"] == "recall-bot-e2e-new"

    create.assert_awaited_once()
    payload = create.await_args.args[0]
    assert payload["meeting_url"] == "https://meet.google.com/zzz-aaaa-bbb"
    assert "automatic_audio_output" in payload
    rc = payload["recording_config"]
    assert rc["realtime_endpoints"][0]["url"].startswith(
        "https://api.briefed-e2e.test/api/webhooks/recall/realtime?meeting_id="
    )
    assert rc["realtime_endpoints"][0]["url"].count("meeting_id=") == 1
    assert "/realtime/?" not in rc["realtime_endpoints"][0]["url"]


def test_start_meeting_recall_error(
    client: TestClient, fake_db, agent_id_copilot: str, monkeypatch
) -> None:
    monkeypatch.setattr(
        "app.main.recall.create_bot",
        AsyncMock(side_effect=RuntimeError("Recall capacity")),
    )
    r = client.post(
        "/api/meetings/start",
        json={
            "agent_id": agent_id_copilot,
            "meeting_link": "https://meet.google.com/fail-case-test",
            "join_now": True,
        },
    )
    assert r.status_code == 502
    failed = [m for m in fake_db.tables["meetings"] if m.get("meeting_link") == "https://meet.google.com/fail-case-test"]
    assert failed and failed[0]["status"] == "failed"


def test_start_meeting_requires_join_at_when_not_join_now(
    client: TestClient, agent_id_copilot: str
) -> None:
    r = client.post(
        "/api/meetings/start",
        json={
            "agent_id": agent_id_copilot,
            "meeting_link": "https://meet.google.com/scheduled-only",
            "join_now": False,
        },
    )
    assert r.status_code == 400


def test_start_meeting_unknown_agent(client: TestClient) -> None:
    r = client.post(
        "/api/meetings/start",
        json={
            "agent_id": "agent-does-not-exist",
            "meeting_link": "https://meet.google.com/x",
            "join_now": True,
        },
    )
    assert r.status_code == 404
