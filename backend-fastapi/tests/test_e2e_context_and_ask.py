from __future__ import annotations

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from tests.data_fixtures import CONTEXT_CHUNKS


def test_list_context_groups_github_repo(client: TestClient, agent_id_copilot: str) -> None:
    r = client.get(f"/api/agents/{agent_id_copilot}/context")
    assert r.status_code == 200
    data = r.json()
    assert data["total_chunks"] == 3
    sources = {s["source_url"]: s for s in data["sources"]}
    gh_root = "https://github.com/acme/platform"
    assert gh_root in sources
    assert sources[gh_root]["chunk_count"] == 2
    assert sources["manual"]["chunk_count"] == 1


def test_add_context_text_ingest(
    client: TestClient, agent_id_copilot: str, fake_db, monkeypatch
) -> None:
    async def fake_ingest(agent_id: str, source_type: str, content: str, label: str | None):
        assert agent_id == agent_id_copilot
        assert source_type == "text"
        fake_db.tables["context_chunks"].append(
            {
                "id": "cc-e2e-new",
                "agent_id": agent_id,
                "source_url": label or "manual",
                "content": "chunk: " + content[:40],
                "created_at": "2025-03-25T10:00:00+00:00",
            }
        )
        return {"chunks_added": 1, "source_url": "e2e-manual"}

    monkeypatch.setattr("app.context_pipeline.ingest_source", fake_ingest)

    r = client.post(
        f"/api/agents/{agent_id_copilot}/context",
        json={
            "source_type": "text",
            "content": "Quarterly OKRs: grow ARR, harden security, reduce MTTR for incidents.",
            "label": "e2e-manual",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["chunks_added"] == 1


def test_clear_context_non_github_eq_source(
    client: TestClient, agent_id_copilot: str, fake_db
) -> None:
    r = client.delete(f"/api/agents/{agent_id_copilot}/context?source_url=manual")
    assert r.status_code == 200
    remaining = [c for c in fake_db.tables["context_chunks"] if c["agent_id"] == agent_id_copilot]
    assert all(c["source_url"] != "manual" for c in remaining)


def test_clear_context_github_prefix(client: TestClient, agent_id_copilot: str, fake_db) -> None:
    fake_db.tables["context_chunks"] = [dict(c) for c in CONTEXT_CHUNKS]
    repo_url = "https://github.com/acme/platform"
    r = client.delete(f"/api/agents/{agent_id_copilot}/context?source_url={repo_url}")
    assert r.status_code == 200
    left = fake_db.tables["context_chunks"]
    assert not any("github.com/acme/platform" in (c.get("source_url") or "") for c in left)


def test_ask_agent_uses_context_and_transcript(
    client: TestClient, agent_id_copilot: str, meeting_id: str, monkeypatch
) -> None:
    monkeypatch.setattr(
        "app.context_pipeline.search_context",
        AsyncMock(return_value=["Mock chunk: rate limits are 1000 rpm."]),
    )
    monkeypatch.setattr(
        "app.ai_client.answer_question",
        AsyncMock(return_value="One thousand requests per minute per workspace."),
    )
    r = client.post(
        f"/api/agents/{agent_id_copilot}/ask",
        json={"question": "What are our API rate limits?", "meeting_id": meeting_id},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "thousand" in body["answer"].lower()
    assert body["context_chunks_used"] == 1
