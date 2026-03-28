"""Tests for post-meeting email delivery via Resend."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from tests.data_fixtures import (
    AGENT_COPILOT,
    AGENT_NO_EMAIL,
    AUTH_USERS,
    MEETING_LIVE,
    USER_EMAIL,
    USER_ID,
    seed_tables,
)
from tests.fake_supabase import FakeSupabase


@pytest.fixture
def db() -> FakeSupabase:
    return FakeSupabase(seed_tables(), auth_users=AUTH_USERS)


SAMPLE_INTEL = {
    "summary": "The team discussed Q2 roadmap priorities and agreed on API rate limit changes.",
    "action_items": ["Alex: Update rate limit docs by Friday", "Jordan: Review auth flow PR"],
    "key_decisions": ["Rate limits increased to 2000 req/min"],
}


class TestPostMeetingEmail:

    @pytest.mark.asyncio
    async def test_sends_email_when_all_conditions_met(self, db: FakeSupabase, monkeypatch) -> None:
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
        monkeypatch.setenv("RESEND_FROM", "test@briefed.ai")
        from app.config import get_settings
        get_settings.cache_clear()

        mock_post = AsyncMock()
        mock_post.return_value = AsyncMock(is_success=True)

        with patch("app.post_meeting_email.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = mock_post
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from app.post_meeting_email import try_send_post_meeting_brief
            await try_send_post_meeting_brief(
                db,
                meeting_id=MEETING_LIVE["id"],
                user_id=USER_ID,
                agent_id=AGENT_COPILOT["id"],
                intel=SAMPLE_INTEL,
            )

            mock_post.assert_awaited_once()
            call_kwargs = mock_post.await_args
            payload = call_kwargs.kwargs.get("json") or call_kwargs.args[1] if len(call_kwargs.args) > 1 else call_kwargs.kwargs.get("json")
            # Verify the email was sent to the right address
            assert USER_EMAIL in str(call_kwargs)

        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_skips_when_email_disabled_on_agent(self, db: FakeSupabase, monkeypatch) -> None:
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
        from app.config import get_settings
        get_settings.cache_clear()

        with patch("app.post_meeting_email.httpx.AsyncClient") as mock_client_cls:
            from app.post_meeting_email import try_send_post_meeting_brief
            await try_send_post_meeting_brief(
                db,
                meeting_id=MEETING_LIVE["id"],
                user_id=USER_ID,
                agent_id=AGENT_NO_EMAIL["id"],
                intel=SAMPLE_INTEL,
            )
            mock_client_cls.assert_not_called()

        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_skips_when_no_intel(self, db: FakeSupabase) -> None:
        from app.post_meeting_email import try_send_post_meeting_brief
        # Should return without error
        await try_send_post_meeting_brief(
            db, meeting_id="x", user_id=USER_ID, agent_id=AGENT_COPILOT["id"], intel=None,
        )
        await try_send_post_meeting_brief(
            db, meeting_id="x", user_id=USER_ID, agent_id=AGENT_COPILOT["id"],
            intel={"summary": ""},
        )

    @pytest.mark.asyncio
    async def test_skips_when_no_resend_key(self, db: FakeSupabase, monkeypatch) -> None:
        monkeypatch.setenv("RESEND_API_KEY", "")
        from app.config import get_settings
        get_settings.cache_clear()

        with patch("app.post_meeting_email.httpx.AsyncClient") as mock_client_cls:
            from app.post_meeting_email import try_send_post_meeting_brief
            await try_send_post_meeting_brief(
                db,
                meeting_id=MEETING_LIVE["id"],
                user_id=USER_ID,
                agent_id=AGENT_COPILOT["id"],
                intel=SAMPLE_INTEL,
            )
            mock_client_cls.assert_not_called()

        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_skips_when_no_user_email(self, monkeypatch) -> None:
        """If the user has no email in auth, email should be skipped."""
        db_no_email = FakeSupabase(seed_tables(), auth_users={})  # no auth users
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
        from app.config import get_settings
        get_settings.cache_clear()

        with patch("app.post_meeting_email.httpx.AsyncClient") as mock_client_cls:
            from app.post_meeting_email import try_send_post_meeting_brief
            await try_send_post_meeting_brief(
                db_no_email,
                meeting_id=MEETING_LIVE["id"],
                user_id=USER_ID,
                agent_id=AGENT_COPILOT["id"],
                intel=SAMPLE_INTEL,
            )
            mock_client_cls.assert_not_called()

        get_settings.cache_clear()


class TestUserEmailLookup:

    def test_auth_admin_lookup(self, db: FakeSupabase) -> None:
        from app.post_meeting_email import _get_user_email
        email = _get_user_email(db, USER_ID)
        assert email == USER_EMAIL

    def test_fallback_to_users_table(self) -> None:
        """If auth admin fails, falls back to public.users table."""
        tables = seed_tables()
        tables["users"] = [{"id": USER_ID, "email": "fallback@test.com"}]
        db = FakeSupabase(tables, auth_users={})  # no auth users
        from app.post_meeting_email import _get_user_email
        email = _get_user_email(db, USER_ID)
        assert email == "fallback@test.com"

    def test_returns_none_when_not_found(self) -> None:
        db = FakeSupabase(seed_tables(), auth_users={})
        from app.post_meeting_email import _get_user_email
        email = _get_user_email(db, "nonexistent-user")
        assert email is None
