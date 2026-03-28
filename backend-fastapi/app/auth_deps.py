"""WorkOS JWT validation — replaces Supabase Auth.

Validates access tokens issued by WorkOS AuthKit.
Falls back to Supabase JWKS for backwards compatibility during migration.
"""

from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.config import get_settings

security = HTTPBearer(auto_error=False)

_DECODE_OPTS = {"verify_aud": False}  # WorkOS tokens don't use aud claim


@lru_cache(maxsize=8)
def _workos_jwks_client(client_id: str) -> PyJWKClient:
    """JWKS client for WorkOS AuthKit tokens."""
    return PyJWKClient(f"https://api.workos.com/sso/jwks/{client_id}")


@lru_cache(maxsize=8)
def _supabase_jwks_client(supabase_url: str) -> PyJWKClient:
    """JWKS client for Supabase tokens (migration fallback)."""
    base = supabase_url.rstrip("/")
    return PyJWKClient(f"{base}/auth/v1/.well-known/jwks.json")


def _decode_workos(token: str, client_id: str) -> dict:
    client = _workos_jwks_client(client_id)
    signing_key = client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        options=_DECODE_OPTS,
    )


def _decode_supabase_fallback(token: str, supabase_url: str) -> dict:
    """Fallback for Supabase JWTs during migration period."""
    client = _supabase_jwks_client(supabase_url)
    signing_key = client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256", "RS256"],
        audience="authenticated",
        options={"verify_aud": True},
    )


def get_user_id(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> str:
    """Extract user ID from WorkOS or Supabase JWT."""
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token")

    settings = get_settings()
    workos_client_id = settings.get("workos_client_id")
    supabase_url = settings.get("supabase_url")

    token = creds.credentials
    payload: dict | None = None

    # Try WorkOS first
    if workos_client_id:
        try:
            payload = _decode_workos(token, workos_client_id)
        except jwt.PyJWTError:
            payload = None

    # Fallback to Supabase (migration period)
    if payload is None and supabase_url:
        try:
            payload = _decode_supabase_fallback(token, supabase_url)
        except jwt.PyJWTError:
            payload = None

    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token") from None

    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise HTTPException(status_code=401, detail="Invalid token subject")
    return sub


# Backwards-compatible alias during migration
get_supabase_user_id = get_user_id
