"""
Recall.ai Output Media: inject audio into a live call.
Also handles screenshot capture.

Performance: uses a persistent httpx.AsyncClient (connection pooling)
to avoid TCP+TLS handshake on every inject_audio call.
"""
import base64
import asyncio
import inspect
import logging
from functools import lru_cache
from pathlib import Path
from datetime import datetime, timedelta, timezone
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
    retrieve_url = f"{_api_base()}/api/v1/bot/{bot_id}/screenshots/{{screenshot_id}}/"

    def _extract_inline_b64(payload: Any) -> str | None:
        if not isinstance(payload, dict):
            return None
        return (
            payload.get("data")
            or payload.get("screenshot")
            or payload.get("b64_data")
            or payload.get("image")
        )

    def _normalize_items(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]
        if isinstance(payload, dict):
            if isinstance(payload.get("results"), list):
                return [x for x in payload["results"] if isinstance(x, dict)]
            return [payload]
        return []

    def _latest_item(items: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not items:
            return None
        # Recall timestamps are ISO8601. We prefer the newest recorded_at value.
        def _ts(it: dict[str, Any]) -> datetime:
            raw = str(it.get("recorded_at") or "")
            try:
                return datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except Exception:
                return datetime.min.replace(tzinfo=timezone.utc)
        return max(items, key=_ts)

    async def _from_item(item: dict[str, Any], client: httpx.AsyncClient) -> str | None:
        inline = _extract_inline_b64(item)
        if inline:
            return inline

        img_url = item.get("url") or item.get("image_url")
        if isinstance(img_url, str) and img_url.strip():
            img_r = await client.get(img_url.strip())
            if img_r.is_success:
                return base64.standard_b64encode(img_r.content).decode("ascii")

        sid = item.get("id")
        if sid:
            r_detail = await client.get(
                retrieve_url.format(screenshot_id=sid),
                headers=_headers(),
            )
            if r_detail.is_success:
                detail = r_detail.json()
                detail_b64 = _extract_inline_b64(detail)
                if detail_b64:
                    return detail_b64
                detail_url = (detail or {}).get("url")
                if isinstance(detail_url, str) and detail_url.strip():
                    img_r = await client.get(detail_url.strip())
                    if img_r.is_success:
                        return base64.standard_b64encode(img_r.content).decode("ascii")
        return None

    async def _json_body(response: Any) -> Any:
        """Handle both httpx.Response.json() and async-mocked json() in tests."""
        body = response.json()
        if inspect.isawaitable(body):
            return await body
        return body

    try:
        client = _get_recall_client()
        started_at = datetime.now(timezone.utc)

        # Step 1: Create a screenshot request
        r = await client.post(create_url, json={}, headers=_headers())
        if r.is_success:
            data = await _json_body(r)
            item = _latest_item(_normalize_items(data))
            if item:
                b64 = await _from_item(item, client)
                if b64:
                    return b64
        else:
            logger.warning(
                "take_screenshot create HTTP %d: %s",
                r.status_code,
                r.text[:300],
            )

        # Fallback for newer Recall docs behavior (list/retrieve APIs):
        # poll for a fresh screenshot recorded after this request started.
        recorded_after = (started_at - timedelta(seconds=2)).isoformat().replace("+00:00", "Z")
        for _ in range(5):
            r_list = await client.get(
                create_url,
                headers=_headers(),
                params={"recorded_at_after": recorded_after},
            )
            if r_list.is_success:
                item = _latest_item(_normalize_items(await _json_body(r_list)))
                if item:
                    b64 = await _from_item(item, client)
                    if b64:
                        return b64
            await asyncio.sleep(0.7)

        # Last fallback: grab the newest available screenshot regardless of timestamp.
        r_latest = await client.get(create_url, headers=_headers())
        if not r_latest.is_success:
            logger.warning(
                "take_screenshot list HTTP %d: %s",
                r_latest.status_code,
                r_latest.text[:200],
            )
            return None

        item = _latest_item(_normalize_items(await _json_body(r_latest)))
        if not item:
            logger.warning("take_screenshot: no screenshots returned")
            return None
        return await _from_item(item, client)

    except Exception as e:
        logger.exception("take_screenshot failed: %s", e)
        return None
