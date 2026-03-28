"""Unkey-backed rate limiting — replaces in-memory cooldowns."""

from __future__ import annotations

import httpx

from app.config import get_settings

_RATELIMIT_URL = "https://api.unkey.dev/v1/ratelimits.limit"


async def check_rate_limit(
    namespace: str,
    identifier: str,
    limit: int,
    duration_ms: int,
) -> bool:
    """Return True if the request is allowed, False if rate-limited.

    Uses the Unkey ratelimit API with a fixed-window strategy.
    Falls back to *allowing* the request if Unkey is unreachable
    (fail-open so meetings aren't disrupted).
    """
    root_key = get_settings().get("unkey_root_key")
    if not root_key:
        # Unkey not configured — allow everything (local dev)
        return True

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(
                _RATELIMIT_URL,
                headers={"Authorization": f"Bearer {root_key}"},
                json={
                    "namespace": namespace,
                    "identifier": identifier,
                    "limit": limit,
                    "duration": duration_ms,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("success", True)
            # Non-200 — fail open
            return True
    except (httpx.HTTPError, Exception):
        # Network error — fail open
        return True


async def check_qa_cooldown(meeting_id: str) -> bool:
    """1 Q&A trigger per 15 seconds per meeting."""
    return await check_rate_limit("qa_cooldown", meeting_id, 1, 15_000)


async def check_fact_cooldown(meeting_id: str) -> bool:
    """1 fact-check per 10 seconds per meeting."""
    return await check_rate_limit("fact_cooldown", meeting_id, 1, 10_000)


async def check_fact_hourly_cap(meeting_id: str) -> bool:
    """Max 30 fact-checks per hour per meeting."""
    return await check_rate_limit("fact_hourly", meeting_id, 30, 3_600_000)
