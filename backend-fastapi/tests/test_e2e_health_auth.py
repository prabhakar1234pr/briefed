from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

from tests.data_fixtures import MEETING_LIVE
from tests.fake_supabase import FakeSupabase


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["service"] == "briefed-backend"
    assert "model" in body  # model field added for observability


def test_meeting_requires_bearer_when_no_override(
    fake_db: FakeSupabase, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.main.get_supabase_service", lambda: fake_db)
    app.dependency_overrides.clear()
    get_settings.cache_clear()
    with TestClient(app) as c:
        r = c.get(f"/api/meetings/{MEETING_LIVE['id']}")
        assert r.status_code == 401
    app.dependency_overrides.clear()
