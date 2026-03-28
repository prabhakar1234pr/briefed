"""Unkey API key verification — programmatic access to Briefed API."""

from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

_VERIFY_URL = "https://api.unkey.dev/v1/keys.verifyKey"

_bearer = HTTPBearer(auto_error=False)


async def get_api_key_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str:
    """Validate an Unkey API key and return the owner_id from metadata.

    Keys are created in the Unkey dashboard with metadata: {"owner_id": "<user_id>"}.
    This dependency can be used as an *alternative* to JWT auth for
    programmatic / server-to-server access.
    """
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token")

    api_id = get_settings().get("unkey_api_id")
    if not api_id:
        raise HTTPException(status_code=500, detail="Unkey API ID not configured")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                _VERIFY_URL,
                json={"apiId": api_id, "key": creds.credentials},
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Key verification unavailable") from exc

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid API key")

    data = resp.json()
    if not data.get("valid"):
        raise HTTPException(status_code=401, detail="Invalid or expired API key")

    meta = data.get("meta") or {}
    owner_id = meta.get("owner_id")
    if not owner_id:
        raise HTTPException(status_code=401, detail="API key missing owner_id metadata")

    return owner_id
