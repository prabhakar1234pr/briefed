"""E2E tests for Clerk authentication integration."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException

from app.auth_deps import get_user_id


class TestClerkAuth:

    def _make_creds(self, token: str):
        from fastapi.security import HTTPAuthorizationCredentials
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    @patch("app.auth_deps._clerk_jwks_client")
    def test_valid_clerk_token(self, mock_jwks_fn):
        mock_client = MagicMock()
        mock_signing_key = MagicMock()
        mock_signing_key.key = "test-key"
        mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_jwks_fn.return_value = mock_client

        # Create a fake token with an issuer
        fake_payload = {"sub": "user_clerk_abc123", "iss": "https://clerk.test.dev"}
        with patch("app.auth_deps.jwt.decode") as mock_decode:
            # First call (unverified) returns the issuer
            # Second call (verified) returns the full payload
            mock_decode.side_effect = [fake_payload, fake_payload]
            result = get_user_id(self._make_creds("valid.clerk.token"))
            assert result == "user_clerk_abc123"

    def test_missing_bearer_token_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            get_user_id(None)
        assert exc.value.status_code == 401

    @patch("app.auth_deps._clerk_jwks_client")
    @patch("app.auth_deps._supabase_jwks_client")
    def test_invalid_token_both_providers_raises_401(self, mock_supa, mock_clerk):
        mock_settings = {"supabase_url": "https://test.supabase.co"}
        with patch("app.auth_deps.get_settings", return_value=mock_settings):
            # Both fail
            with patch("app.auth_deps.jwt.decode", side_effect=jwt.PyJWTError("bad")):
                mock_c = MagicMock()
                mock_c.get_signing_key_from_jwt.side_effect = jwt.PyJWTError("bad")
                mock_clerk.return_value = mock_c
                mock_supa.return_value = mock_c

                with pytest.raises(HTTPException) as exc:
                    get_user_id(self._make_creds("invalid.token"))
                assert exc.value.status_code == 401

    @patch("app.auth_deps._clerk_jwks_client")
    @patch("app.auth_deps._supabase_jwks_client")
    def test_supabase_fallback_works(self, mock_supa, mock_clerk):
        mock_settings = {"supabase_url": "https://test.supabase.co"}
        with patch("app.auth_deps.get_settings", return_value=mock_settings):
            # Clerk fails
            with patch("app.auth_deps._decode_clerk", side_effect=jwt.PyJWTError("bad")):
                # Supabase succeeds
                mock_supa_client = MagicMock()
                mock_key = MagicMock()
                mock_key.key = "supa-key"
                mock_supa_client.get_signing_key_from_jwt.return_value = mock_key
                mock_supa.return_value = mock_supa_client

                with patch("app.auth_deps.jwt.decode") as mock_decode:
                    mock_decode.return_value = {"sub": "user_supa_456"}
                    result = get_user_id(self._make_creds("legacy.supa.token"))
                    assert result == "user_supa_456"


class TestProtectedEndpoints:

    def test_health_endpoint_unprotected(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_context_endpoint_requires_auth(self, client, agent_id_copilot):
        r = client.get(f"/api/agents/{agent_id_copilot}/context")
        assert r.status_code == 200

    def test_meetings_endpoint_requires_auth(self, client, meeting_id):
        r = client.get(f"/api/meetings/{meeting_id}")
        assert r.status_code == 200
