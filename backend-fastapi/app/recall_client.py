import base64
from typing import Any

import httpx

from app.config import get_settings

# ─── Persistent HTTP client (connection pooling) ─────────────────────────────
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=60.0,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _client


def _headers() -> dict[str, str]:
    key = get_settings()["recall_api_key"]
    if not key:
        raise RuntimeError("RECALL_API_KEY not set")
    return {
        "Authorization": f"Token {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _http_error_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except Exception:
        body = response.text or ""
    if isinstance(body, dict):
        return str(body.get("detail") or body.get("message") or body)
    return str(body) if body else response.reason_phrase


def _api_base() -> str:
    return get_settings()["recall_api_base"]


async def create_bot(payload: dict[str, Any]) -> dict[str, Any]:
    base = _api_base()
    url = f"{base}/api/v1/bot/"
    client = _get_client()
    r = await client.post(url, json=payload, headers=_headers())
    if not r.is_success:
        raise RuntimeError(
            f"Recall.ai HTTP {r.status_code}: {_http_error_detail(r)}"
        ) from None
    return r.json()


async def retrieve_bot(bot_id: str) -> dict[str, Any]:
    base = _api_base()
    url = f"{base}/api/v1/bot/{bot_id}/"
    client = _get_client()
    r = await client.get(url, headers=_headers())
    if not r.is_success:
        raise RuntimeError(
            f"Recall.ai HTTP {r.status_code}: {_http_error_detail(r)}"
        ) from None
    return r.json()


async def fetch_transcript_json(download_url: str) -> Any:
    client = _get_client()
    r = await client.get(download_url)
    r.raise_for_status()
    return r.json()


async def fetch_audio_mixed_download_url(bot: dict[str, Any]) -> str | None:
    """
    Mixed MP3 is not exposed under recording media_shortcuts; list by recording_id.
    See https://docs.recall.ai/docs/media-shortcuts
    """
    base = _api_base()
    endpoint = f"{base}/api/v1/audio_mixed/"
    client = _get_client()
    for rec in bot.get("recordings") or []:
        if not isinstance(rec, dict):
            continue
        rid = rec.get("id")
        if not rid:
            continue
        for params in ({"recording_id": str(rid), "status_code": "done"}, {"recording_id": str(rid)}):
            r = await client.get(endpoint, headers=_headers(), params=params)
            if not r.is_success:
                continue
            payload = r.json()
            best: str | None = None
            for item in payload.get("results") or []:
                if not isinstance(item, dict):
                    continue
                dl = (item.get("data") or {}).get("download_url")
                if not isinstance(dl, str) or not dl.strip():
                    continue
                st = (item.get("status") or {}).get("code") or ""
                if str(st).lower() == "done":
                    return dl.strip()
                best = dl.strip()
            if best:
                return best
    return None


async def fetch_image_b64_for_video(image_url: str) -> str | None:
    """Recall video output expects base64 jpeg; skip if too large or not jpeg."""
    max_b64 = 1_800_000
    client = _get_client()
    r = await client.get(image_url)
    r.raise_for_status()
    b64 = base64.standard_b64encode(r.content).decode("ascii")
    if len(b64) > max_b64:
        return None
    return b64
