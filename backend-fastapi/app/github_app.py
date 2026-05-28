"""
GitHub App helpers — App-level JWT minting and installation token exchange.

GitHub Apps don't use a long-lived token. Auth flow per request:
  1. Mint a short (~10-min) JWT signed with the App's private key — identifies
     the App to GitHub.
  2. Exchange the JWT for an installation access token via
     POST /app/installations/{id}/access_tokens — identifies a specific install.
     Installation tokens live 1 hour. Cache them.
  3. Use the installation token as `Authorization: Bearer <token>` on REST calls.

Used by:
  - github_webhook._sync_changed_files() — to fetch raw file content at a SHA
  - github_app install/callback routes — to look up which repos an install covers
"""
from __future__ import annotations

import time
from typing import Any

import httpx
import jwt as pyjwt

from app.config import get_settings
from app.logger import get_logger

log = get_logger(__name__)


# ─── App-mode detection ──────────────────────────────────────────────────────


def app_mode_enabled() -> bool:
    """True when GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY are configured."""
    s = get_settings()
    return bool(s.get("github_app_id") and s.get("github_app_private_key"))


# ─── App-level JWT (identifies the App itself, not an install) ───────────────


def _mint_app_jwt() -> str:
    """
    Sign a JWT with the App's private key. Valid for ~10 minutes.
    See https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-json-web-token-jwt-for-a-github-app
    """
    s = get_settings()
    app_id = s.get("github_app_id")
    private_key = s.get("github_app_private_key")
    if not (app_id and private_key):
        raise RuntimeError("GitHub App not configured: GITHUB_APP_ID + GITHUB_APP_PRIVATE_KEY required")

    now = int(time.time())
    payload = {
        "iat": now - 60,          # 60s clock skew tolerance
        "exp": now + 9 * 60,      # 9 minutes (max 10 per GitHub)
        "iss": str(app_id),
    }
    return pyjwt.encode(payload, private_key, algorithm="RS256")


# ─── Installation access token (cached) ──────────────────────────────────────


_token_cache: dict[int, tuple[str, float]] = {}  # installation_id → (token, expires_at)
_TOKEN_BUFFER_S = 5 * 60  # refresh if <5min left


async def get_installation_token(installation_id: int) -> str:
    """
    Return a valid installation access token for `installation_id`. Cached.
    """
    cached = _token_cache.get(installation_id)
    if cached and cached[1] > time.time() + _TOKEN_BUFFER_S:
        return cached[0]

    jwt_token = _mint_app_jwt()
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        r.raise_for_status()
        data = r.json()

    token = data["token"]
    # expires_at is ISO8601 — parse to epoch seconds. Default to now+50min on parse failure.
    try:
        from datetime import datetime
        expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00")).timestamp()
    except Exception:
        expires_at = time.time() + 50 * 60

    _token_cache[installation_id] = (token, expires_at)
    log.info("github_install_token_minted", installation_id=installation_id, ttl_s=int(expires_at - time.time()))
    return token


# ─── Helpers used by sync logic ──────────────────────────────────────────────


async def fetch_file_via_installation(
    *, installation_id: int, repo_full_name: str, sha: str, path: str
) -> str | None:
    """
    Fetch a file's raw content at a specific commit using an installation token.
    Returns None for 404 or binary files.
    """
    token = await get_installation_token(installation_id)
    raw_url = f"https://raw.githubusercontent.com/{repo_full_name}/{sha}/{path}"
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as c:
        r = await c.get(
            raw_url,
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": "BriefedBot/2.0",
            },
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        if b"\x00" in r.content[:4096]:
            return None  # binary
        text = r.text
        if len(text) > 350_000:
            text = text[:350_000]
        return text


async def list_installation_repos(installation_id: int) -> list[dict[str, Any]]:
    """
    Enumerate all repos this installation has access to. Used during the install
    callback to seed agent_github_sources rows.
    """
    token = await get_installation_token(installation_id)
    out: list[dict[str, Any]] = []
    url = "https://api.github.com/installation/repositories?per_page=100"
    async with httpx.AsyncClient(timeout=15.0) as c:
        while url:
            r = await c.get(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            r.raise_for_status()
            data = r.json()
            for repo in data.get("repositories", []):
                out.append({
                    "full_name": repo["full_name"],
                    "default_branch": repo.get("default_branch", "main"),
                    "private": repo.get("private", False),
                })
            # Pagination via Link header
            link = r.headers.get("link", "")
            next_url = None
            for part in link.split(","):
                if 'rel="next"' in part:
                    next_url = part.split(";")[0].strip().strip("<>")
                    break
            url = next_url
    return out
