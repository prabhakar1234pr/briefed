"""Clerk + Supabase JWT validation.

Validates access tokens issued by Clerk.
Falls back to Supabase JWKS for backwards compatibility.
"""

from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.config import get_settings

security = HTTPBearer(auto_error=False)


@lru_cache(maxsize=8)
def _clerk_jwks_client(clerk_issuer: str) -> PyJWKClient:
    return PyJWKClient(f"{clerk_issuer}/.well-known/jwks.json")


@lru_cache(maxsize=8)
def _supabase_jwks_client(supabase_url: str) -> PyJWKClient:
    base = supabase_url.rstrip("/")
    return PyJWKClient(f"{base}/auth/v1/.well-known/jwks.json")


def _decode_clerk(token: str) -> dict:
    """Decode a Clerk JWT. The issuer is embedded in the token."""
    unverified = jwt.decode(token, options={"verify_signature": False})
    issuer = unverified.get("iss", "")
    if not issuer:
        raise jwt.PyJWTError("Missing issuer")
    client = _clerk_jwks_client(issuer)
    signing_key = client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        options={"verify_aud": False},
    )


def _decode_supabase_fallback(token: str, supabase_url: str) -> dict:
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
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token")

    settings = get_settings()
    supabase_url = settings.get("supabase_url")

    token = creds.credentials
    payload: dict | None = None

    # Try Clerk first
    try:
        payload = _decode_clerk(token)
    except (jwt.PyJWTError, Exception):
        payload = None

    # Fallback to Supabase
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


# Backwards-compatible alias
get_supabase_user_id = get_user_id
