from __future__ import annotations

import pytest

from app.auth_deps import get_user_id
from app.config import get_settings
from app.main import app

from tests.data_fixtures import (
    AGENT_COPILOT,
    AGENT_FACTCHECK,
    AUTH_USERS,
    MEETING_LIVE,
    USER_ID,
    seed_tables,
)
from tests.fake_supabase import FakeSupabase


@pytest.fixture
def fake_db() -> FakeSupabase:
    return FakeSupabase(seed_tables(), auth_users=AUTH_USERS)


@pytest.fixture(autouse=True)
def _test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_API_BASE", "https://api.briefed-e2e.test")
    monkeypatch.setenv("RECALL_API_BASE", "https://us-east-1.recall.ai")
    monkeypatch.setenv("RECALL_API_KEY", "recall-e2e-test-key")
    monkeypatch.setenv("SUPABASE_URL", "https://e2e.supabase.test")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "eyJ-e2e-service-role")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "e2e-jwt-unit-test-secret-min-32-chars!!")
    monkeypatch.setenv("GCP_PROJECT", "e2e-gcp-project")
    monkeypatch.setenv("WEBHOOK_SECRET", "")
    monkeypatch.setenv("RESEND_API_KEY", "re_test_fake_key_for_e2e")
    monkeypatch.setenv("RESEND_FROM", "test@briefed-e2e.test")
    # Default to legacy output_audio mode in tests (no Cartesia key)
    monkeypatch.setenv("CARTESIA_API_KEY", "")
    monkeypatch.setenv("Cartesia_API_key", "")
    get_settings.cache_clear()


@pytest.fixture
def client(fake_db: FakeSupabase, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.main.get_supabase_service", lambda: fake_db)
    monkeypatch.setattr("app.context_pipeline.get_supabase_service", lambda: fake_db)

    def _user() -> str:
        return USER_ID

    app.dependency_overrides[get_user_id] = _user
    from fastapi.testclient import TestClient

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture
def webhook_client(fake_db: FakeSupabase, monkeypatch: pytest.MonkeyPatch):
    """Recall webhooks without JWT."""
    monkeypatch.setattr("app.main.get_supabase_service", lambda: fake_db)
    monkeypatch.setattr("app.context_pipeline.get_supabase_service", lambda: fake_db)
    app.dependency_overrides.clear()
    from fastapi.testclient import TestClient

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    get_settings.cache_clear()


@pytest.fixture
def meeting_id() -> str:
    return MEETING_LIVE["id"]


@pytest.fixture
def agent_id_copilot() -> str:
    return AGENT_COPILOT["id"]


@pytest.fixture
def agent_id_factcheck() -> str:
    return AGENT_FACTCHECK["id"]
