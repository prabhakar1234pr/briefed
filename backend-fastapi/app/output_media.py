"""
Recall.ai Output Media: inject audio into a live call.
Also handles screenshot capture.

Performance: uses a persistent httpx.AsyncClient (connection pooling)
to avoid TCP+TLS handshake on every inject_audio call.
"""
import base64
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_BOOTSTRAP_REL = Path(__file__).resolve().parent / "assets" / "copilot_bootstrap.mp3"

# ─── Persistent HTTP client (connection pooling) ─────────────────────────────
_recall_client: httpx.AsyncClient | None = None


def _get_recall_client() -> httpx.AsyncClient:
    """Reusable httpx client with connection pooling for Recall.ai API."""
    global _recall_client
    if _recall_client is None or _recall_client.is_closed:
        _recall_client = httpx.AsyncClient(
            timeout=10.0,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _recall_client


@lru_cache(maxsize=1)
def copilot_bootstrap_mp3_b64() -> str:
    """Tiny silent MP3, base64. Recall requires automatic_audio_output so output_audio works."""
    return base64.standard_b64encode(_BOOTSTRAP_REL.read_bytes()).decode("ascii")


def _headers() -> dict[str, str]:
    key = get_settings()["recall_api_key"]
    if not key:
        raise RuntimeError("RECALL_API_KEY not set")
    return {
        "Authorization": f"Token {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _api_base() -> str:
    return get_settings()["recall_api_base"]


async def inject_audio(bot_id: str, mp3_bytes: bytes) -> bool:
    """
    Inject MP3 audio into a live call via Recall.ai Output Media API.
    Uses persistent client with connection pooling for low latency.
    Returns True on success.
    """
    b64 = base64.standard_b64encode(mp3_bytes).decode("ascii")
    url = f"{_api_base()}/api/v1/bot/{bot_id}/output_audio/"
    payload = {
        "kind": "mp3",
        "b64_data": b64,
    }
    try:
        client = _get_recall_client()
        r = await client.post(url, json=payload, headers=_headers())
        if r.is_success:
            return True
        logger.warning("inject_audio HTTP %d: %s", r.status_code, r.text[:200])
        return False
    except Exception as e:
        logger.exception("inject_audio failed: %s", e)
        return False


async def take_screenshot(bot_id: str) -> str | None:
    """
    Capture a screenshot from the bot's video feed via Recall.ai API.
    1. POST /api/v1/bot/{bot_id}/screenshots/ to request a new screenshot
    2. The response contains the screenshot data (or an ID to retrieve it)
    Returns base64 JPEG string or None.
    """
    create_url = f"{_api_base()}/api/v1/bot/{bot_id}/screenshots/"
    try:
        client = _get_recall_client()

        # Step 1: Create a screenshot request
        r = await client.post(create_url, json={}, headers=_headers())
        if not r.is_success:
            logger.warning("take_screenshot create HTTP %d: %s",
                           r.status_code, r.text[:300])
            # Fallback: try GET on the list endpoint to grab the latest
            r = await client.get(create_url, headers=_headers())
            if not r.is_success:
                logger.warning("take_screenshot list HTTP %d: %s",
                               r.status_code, r.text[:200])
                return None

        data = r.json()
        logger.info("screenshot_response type=%s keys=%s",
                     type(data).__name__,
                     list(data.keys()) if isinstance(data, dict) else "N/A")

        # Handle list response (array) — grab the latest screenshot
        if isinstance(data, list) and data:
            data = data[-1]  # latest
        elif isinstance(data, dict) and "results" in data:
            results = data["results"]
            if results:
                data = results[-1]
            else:
                logger.warning("take_screenshot: empty results list")
                return None

        if not isinstance(data, dict):
            logger.warning("take_screenshot: unexpected response type %s",
                           type(data).__name__)
            return None

        # Extract base64 data — Recall may use different keys
        b64 = (data.get("data") or data.get("screenshot") or
               data.get("b64_data") or data.get("image"))

        # If the response has a URL instead of inline b64, fetch it
        img_url = data.get("url") or data.get("image_url")
        if not b64 and img_url:
            logger.info("screenshot_fetching_url: %s", img_url[:100])
            img_r = await client.get(img_url)
            if img_r.is_success:
                import base64 as b64_mod
                b64 = b64_mod.standard_b64encode(img_r.content).decode("ascii")

        if not b64:
            logger.warning("screenshot_no_data, keys=%s, sample=%s",
                           list(data.keys()), str(data)[:300])
        return b64

    except Exception as e:
        logger.exception("take_screenshot failed: %s", e)
        return None
