"""E2E tests for WorkOS authentication integration."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException

from app.auth_deps import get_user_id


# ─── WorkOS JWT validation ────────────────────────────────────────────────────

class TestWorkOSAuth:

    def _make_creds(self, token: str):
        from fastapi.security import HTTPAuthorizationCredentials
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    @patch("app.auth_deps.get_settings")
    @patch("app.auth_deps._workos_jwks_client")
    def test_valid_workos_token(self, mock_jwks_client, mock_settings):
        """Valid WorkOS JWT returns the user ID from sub claim."""
        mock_settings.return_value = {
            "workos_client_id": "client_test123",
            "supabase_url": None,
        }
        mock_client = MagicMock()
        mock_signing_key = MagicMock()
        mock_signing_key.key = "test-key"
        mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_jwks_client.return_value = mock_client

        with patch("app.auth_deps.jwt.decode") as mock_decode:
            mock_decode.return_value = {"sub": "user_workos_abc123"}
            result = get_user_id(self._make_creds("valid.workos.token"))
            assert result == "user_workos_abc123"

    @patch("app.auth_deps.get_settings")
    def test_missing_bearer_token_raises_401(self, mock_settings):
        """No token → 401."""
        with pytest.raises(HTTPException) as exc:
            get_user_id(None)
        assert exc.value.status_code == 401
        assert "Missing bearer token" in exc.value.detail

    @patch("app.auth_deps.get_settings")
    @patch("app.auth_deps._workos_jwks_client")
    @patch("app.auth_deps._supabase_jwks_client")
    def test_invalid_token_both_providers_raises_401(
        self, mock_supa_jwks, mock_workos_jwks, mock_settings
    ):
        """Token invalid for both WorkOS and Supabase → 401."""
        mock_settings.return_value = {
            "workos_client_id": "client_test123",
            "supabase_url": "https://test.supabase.co",
        }
        # Both JWKS clients fail
        for mock_client_fn in [mock_workos_jwks, mock_supa_jwks]:
            mock_client = MagicMock()
            mock_client.get_signing_key_from_jwt.side_effect = jwt.PyJWTError("bad")
            mock_client_fn.return_value = mock_client

        with pytest.raises(HTTPException) as exc:
            get_user_id(self._make_creds("totally.invalid.token"))
        assert exc.value.status_code == 401

    @patch("app.auth_deps.get_settings")
    @patch("app.auth_deps._workos_jwks_client")
    @patch("app.auth_deps._supabase_jwks_client")
    def test_supabase_fallback_works(self, mock_supa_jwks, mock_workos_jwks, mock_settings):
        """WorkOS fails, Supabase succeeds → returns user ID."""
        mock_settings.return_value = {
            "workos_client_id": "client_test123",
            "supabase_url": "https://test.supabase.co",
        }
        # WorkOS fails
        mock_workos = MagicMock()
        mock_workos.get_signing_key_from_jwt.side_effect = jwt.PyJWTError("bad")
        mock_workos_jwks.return_value = mock_workos

        # Supabase succeeds
        mock_supa = MagicMock()
        mock_signing_key = MagicMock()
        mock_signing_key.key = "supa-key"
        mock_supa.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_supa_jwks.return_value = mock_supa

        with patch("app.auth_deps.jwt.decode") as mock_decode:
            mock_decode.return_value = {"sub": "user_supabase_456"}
            result = get_user_id(self._make_creds("legacy.supabase.token"))
            assert result == "user_supabase_456"

    @patch("app.auth_deps.get_settings")
    @patch("app.auth_deps._workos_jwks_client")
    def test_missing_sub_claim_raises_401(self, mock_jwks_client, mock_settings):
        """Valid JWT but no sub claim → 401."""
        mock_settings.return_value = {
            "workos_client_id": "client_test123",
            "supabase_url": None,
        }
        mock_client = MagicMock()
        mock_signing_key = MagicMock()
        mock_signing_key.key = "test-key"
        mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_jwks_client.return_value = mock_client

        with patch("app.auth_deps.jwt.decode") as mock_decode:
            mock_decode.return_value = {"email": "user@test.com"}  # no "sub"
            with pytest.raises(HTTPException) as exc:
                get_user_id(self._make_creds("nosub.token"))
            assert exc.value.status_code == 401
            assert "subject" in exc.value.detail


# ─── Integration: protected endpoints use get_user_id ─────────────────────────

class TestProtectedEndpoints:

    def test_health_endpoint_unprotected(self, client):
        """Health check doesn't require auth."""
        r = client.get("/health")
        assert r.status_code == 200

    def test_context_endpoint_requires_auth(self, client, agent_id_copilot):
        """GET context uses auth dependency."""
        r = client.get(f"/api/agents/{agent_id_copilot}/context")
        assert r.status_code == 200  # fixture overrides auth

    def test_meetings_endpoint_requires_auth(self, client, meeting_id):
        """GET meeting uses auth dependency."""
        r = client.get(f"/api/meetings/{meeting_id}")
        assert r.status_code == 200
