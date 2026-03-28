"""E2E tests for Unkey rate limiting integration."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


# ─── Unit tests for rate_limit module ─────────────────────────────────────────

class TestCheckRateLimit:
    """Test the Unkey ratelimit API wrapper."""

    @pytest.mark.asyncio
    @patch("app.rate_limit.get_settings", return_value={"unkey_root_key": "test-key"})
    @patch("httpx.AsyncClient.post")
    async def test_allowed_when_under_limit(self, mock_post, _settings):
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"success": True},
        )
        from app.rate_limit import check_rate_limit
        result = await check_rate_limit("qa_cooldown", "meet-1", 1, 15000)
        assert result is True

    @pytest.mark.asyncio
    @patch("app.rate_limit.get_settings", return_value={"unkey_root_key": "test-key"})
    @patch("httpx.AsyncClient.post")
    async def test_blocked_when_over_limit(self, mock_post, _settings):
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"success": False},
        )
        from app.rate_limit import check_rate_limit
        result = await check_rate_limit("qa_cooldown", "meet-1", 1, 15000)
        assert result is False

    @pytest.mark.asyncio
    @patch("app.rate_limit.get_settings", return_value={"unkey_root_key": None})
    async def test_no_key_configured_allows_all(self, _settings):
        """When UNKEY_ROOT_KEY is not set, everything is allowed (local dev)."""
        from app.rate_limit import check_rate_limit
        result = await check_rate_limit("qa_cooldown", "meet-1", 1, 15000)
        assert result is True

    @pytest.mark.asyncio
    @patch("app.rate_limit.get_settings", return_value={"unkey_root_key": "test-key"})
    @patch("httpx.AsyncClient.post", side_effect=Exception("Network error"))
    async def test_network_error_fails_open(self, _post, _settings):
        """On network failure, fail open to not disrupt meetings."""
        from app.rate_limit import check_rate_limit
        result = await check_rate_limit("qa_cooldown", "meet-1", 1, 15000)
        assert result is True


# ─── Convenience wrappers ─────────────────────────────────────────────────────

class TestConvenienceWrappers:

    @pytest.mark.asyncio
    @patch("app.rate_limit.check_rate_limit", new_callable=AsyncMock, return_value=True)
    async def test_check_qa_cooldown(self, mock_rl):
        from app.rate_limit import check_qa_cooldown
        result = await check_qa_cooldown("meet-1")
        assert result is True
        mock_rl.assert_awaited_once_with("qa_cooldown", "meet-1", 1, 15_000)

    @pytest.mark.asyncio
    @patch("app.rate_limit.check_rate_limit", new_callable=AsyncMock, return_value=True)
    async def test_check_fact_cooldown(self, mock_rl):
        from app.rate_limit import check_fact_cooldown
        result = await check_fact_cooldown("meet-1")
        assert result is True
        mock_rl.assert_awaited_once_with("fact_cooldown", "meet-1", 1, 28_000)

    @pytest.mark.asyncio
    @patch("app.rate_limit.check_rate_limit", new_callable=AsyncMock, return_value=False)
    async def test_check_fact_hourly_cap_blocked(self, mock_rl):
        from app.rate_limit import check_fact_hourly_cap
        result = await check_fact_hourly_cap("meet-1")
        assert result is False
        mock_rl.assert_awaited_once_with("fact_hourly", "meet-1", 12, 3_600_000)


# ─── API key verification ─────────────────────────────────────────────────────

class TestApiKeyAuth:

    @pytest.mark.asyncio
    @patch("app.api_key_auth.get_settings", return_value={"unkey_api_id": "api_test"})
    @patch("httpx.AsyncClient.post")
    async def test_valid_key_returns_owner(self, mock_post, _settings):
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"valid": True, "meta": {"owner_id": "user-123"}},
        )
        from fastapi.security import HTTPAuthorizationCredentials
        from app.api_key_auth import get_api_key_user
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="uk_test_key")
        owner = await get_api_key_user(creds)
        assert owner == "user-123"

    @pytest.mark.asyncio
    @patch("app.api_key_auth.get_settings", return_value={"unkey_api_id": "api_test"})
    @patch("httpx.AsyncClient.post")
    async def test_invalid_key_raises_401(self, mock_post, _settings):
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"valid": False},
        )
        from fastapi import HTTPException
        from fastapi.security import HTTPAuthorizationCredentials
        from app.api_key_auth import get_api_key_user
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="uk_bad_key")
        with pytest.raises(HTTPException) as exc_info:
            await get_api_key_user(creds)
        assert exc_info.value.status_code == 401
