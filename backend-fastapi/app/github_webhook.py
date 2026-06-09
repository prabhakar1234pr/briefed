"""
Phase 4b: GitHub webhook for live code memory.

Flow:
  1. User connects a repo to an agent via POST /api/agents/{agent_id}/github
     → backend creates an agent_github_sources row, mints a webhook_secret,
       returns { webhook_url, webhook_secret } for the user to register
       on GitHub (Settings → Webhooks → Add webhook).
  2. User registers the webhook on GitHub with:
       - Payload URL: {PUBLIC_API_BASE}/api/webhooks/github
       - Content type: application/json
       - Secret: the secret we returned
       - Events: just the "push" event
  3. On every push, GitHub POSTs to /api/webhooks/github. We:
       - Validate X-Hub-Signature-256 against the per-row webhook_secret
       - Look up the source row by (repo_full_name, branch)
       - Diff `before`..`after` to find changed/added/removed files
       - For each changed file: delete_by_source(...) then re-ingest the
         current content via add_memory(kind="code")
       - Update last_synced_sha
       - Return 200 immediately; ingest runs as a background task
"""
from __future__ import annotations

import hashlib
import hmac
import secrets as _secrets
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Header, Request
from pydantic import BaseModel

from app.auth_deps import get_user_id
from app.config import get_settings
from app import repo as data_repo
from app.logger import get_logger
from app.pipeline import memory as mem
from app import github_app as gh_app

log = get_logger(__name__)
router = APIRouter()


# ─── User-facing: connect a repo to an agent ────────────────────────────────


class ConnectRepoBody(BaseModel):
    repo_full_name: str          # "owner/repo"
    branch: str = "main"
    installation_id: int | None = None  # set when using GitHub App; None for PAT mode


@router.post("/api/agents/{agent_id}/github")
async def connect_github_repo(
    agent_id: str,
    body: ConnectRepoBody,
    user_id: str = Depends(get_user_id),
) -> dict[str, Any]:
    """
    Connect a GitHub repo to an agent. Returns the webhook URL and secret
    for the user to register on GitHub. Does NOT do the initial repo walk —
    that's a separate POST /api/agents/{id}/context with the repo URL.
    """
    # Ownership check
    if not data_repo.get_agent(agent_id, user_id):
        raise HTTPException(status_code=404, detail="Agent not found")

    # In App mode the webhook secret is the app-wide one (env). In PAT mode
    # each row carries its own secret that the user pastes into GitHub.
    if body.installation_id and gh_app.app_mode_enabled():
        webhook_secret = get_settings().get("github_app_webhook_secret") or ""
    else:
        webhook_secret = _secrets.token_urlsafe(32)

    branch = body.branch.strip() or "main"
    try:
        data_repo.upsert_github_source(
            agent_id=agent_id,
            repo_full_name=body.repo_full_name.strip(),
            branch=branch,
            installation_id=body.installation_id,
            webhook_secret=webhook_secret,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}") from e

    public_base = (get_settings().get("public_api_base") or "").rstrip("/")
    webhook_url = f"{public_base}/api/webhooks/github" if public_base else "/api/webhooks/github"

    return {
        "webhook_url": webhook_url,
        "webhook_secret": webhook_secret,
        "events": ["push"],
        "content_type": "application/json",
        "branch": branch,
        "mode": "app" if body.installation_id and gh_app.app_mode_enabled() else "pat",
        "installation_id": body.installation_id,
    }


# ─── GitHub App install flow ────────────────────────────────────────────────


@router.get("/api/github/install-url")
async def github_install_url(
    agent_id: str,
    user_id: str = Depends(get_user_id),
) -> dict[str, str]:
    """
    Returns the URL the frontend should redirect the user to in order to install
    the Briefed GitHub App. We round-trip `agent_id` through the `state` param
    so the callback knows which agent to wire the new install up to.
    """
    if not gh_app.app_mode_enabled():
        raise HTTPException(status_code=400, detail="GitHub App not configured on this server")

    # Verify the user owns the agent before issuing an install URL
    if not data_repo.get_agent(agent_id, user_id):
        raise HTTPException(status_code=404, detail="Agent not found")

    settings = get_settings()
    app_slug = settings.get("github_app_slug") or "briefed"
    state = f"{agent_id}:{_secrets.token_urlsafe(16)}"  # opaque; we re-check agent ownership on callback
    install_url = f"https://github.com/apps/{app_slug}/installations/new?state={state}"
    return {"install_url": install_url, "state": state}


@router.get("/api/github/install-callback")
async def github_install_callback(
    installation_id: int,
    setup_action: str = "",
    state: str = "",
) -> dict[str, Any]:
    """
    GitHub redirects users here after they install the App.
    Query params: ?installation_id=...&setup_action=install&state=<our state>

    We enumerate the repos this install covers and return them so the
    frontend can let the user pick which agent each repo belongs to.

    NOTE: this endpoint isn't user-authed (GitHub does the redirect, not the
    user's session). We trust the `installation_id` only enough to LIST repos —
    the actual connect step uses POST /api/agents/{id}/github which re-checks
    the user owns the agent.
    """
    if not gh_app.app_mode_enabled():
        raise HTTPException(status_code=400, detail="GitHub App not configured on this server")

    if setup_action not in ("install", "update", ""):
        return {"status": "cancelled", "setup_action": setup_action}

    try:
        repos = await gh_app.list_installation_repos(installation_id)
    except Exception as e:
        log.exception("github_install_callback_fetch_failed", error=str(e)[:200])
        raise HTTPException(status_code=502, detail=f"GitHub API error: {e}") from e

    return {
        "installation_id": installation_id,
        "state": state,
        "repositories": repos,
        # Frontend uses this to POST /api/agents/{agent_id}/github once per repo
        "next_step": "Have the user select an agent_id and POST each repo to /api/agents/{agent_id}/github with installation_id",
    }


# ─── GitHub-facing: webhook receiver ────────────────────────────────────────


@router.post("/api/webhooks/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(default=""),
    x_hub_signature_256: str = Header(default=""),
) -> dict[str, str]:
    """
    Receives GitHub webhook events. We only care about `push`.

    Per GitHub: respond 200 within ~10s or they'll retry. We do verification
    + lookup synchronously, then queue ingestion as a background task.
    """
    raw_body = await request.body()
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if x_github_event == "ping":
        return {"status": "pong"}

    # In App mode, signature is validated against the single app-wide secret
    # (not per-row, since one webhook URL serves all installations).
    settings = get_settings()
    app_secret = settings.get("github_app_webhook_secret")
    if app_secret and not _verify_signature(raw_body, x_hub_signature_256, app_secret):
        log.warning("github_webhook_bad_signature_app_mode", event=x_github_event)
        raise HTTPException(status_code=401, detail="Invalid signature")

    # App-install lifecycle: keep agent_github_sources rows in sync
    if x_github_event in ("installation", "installation_repositories"):
        background_tasks.add_task(_handle_installation_event, x_github_event, payload)
        return {"status": "queued", "event": x_github_event}

    if x_github_event != "push":
        # Acknowledge but ignore (we don't subscribe to other events)
        return {"status": "ignored", "event": x_github_event}

    repo = (payload.get("repository") or {}).get("full_name")
    ref = payload.get("ref") or ""  # "refs/heads/main"
    branch = ref.split("/", 2)[-1] if ref.startswith("refs/heads/") else ref

    if not repo or not branch:
        raise HTTPException(status_code=400, detail="Missing repo or branch")

    sources = data_repo.list_github_sources(repo_full_name=repo, branch=branch)
    if not sources:
        # Nobody subscribed — return 200 so GitHub doesn't retry forever.
        return {"status": "no_subscribers", "repo": repo, "branch": branch}

    # In App mode the signature was already validated above (app-wide secret).
    # In PAT mode we validate per-row.
    if app_secret:
        matched = sources
    else:
        matched = [s for s in sources if _verify_signature(raw_body, x_hub_signature_256, s["webhook_secret"])]
        if not matched:
            log.warning("github_webhook_bad_signature", repo=repo, branch=branch)
            raise HTTPException(status_code=401, detail="Invalid signature")

    before = payload.get("before") or ""
    after = payload.get("after") or ""
    commits = payload.get("commits") or []

    # GitHub already aggregates per-commit added/modified/removed. Combine.
    added_or_modified: set[str] = set()
    removed: set[str] = set()
    for c in commits:
        added_or_modified.update(c.get("added") or [])
        added_or_modified.update(c.get("modified") or [])
        removed.update(c.get("removed") or [])
    # If a file was modified then removed in the same push, drop from add set
    added_or_modified -= removed

    for src in matched:
        background_tasks.add_task(
            _sync_changed_files,
            src=src,
            after_sha=after,
            added_or_modified=list(added_or_modified),
            removed=list(removed),
        )

    log.info("github_webhook_accepted",
             repo=repo, branch=branch,
             agents=len(matched),
             added_or_modified=len(added_or_modified),
             removed=len(removed),
             before=before[:8], after=after[:8])
    return {"status": "queued", "agents": str(len(matched))}


# ─── Background task: re-ingest changed files ───────────────────────────────


async def _sync_changed_files(
    *,
    src: dict[str, Any],
    after_sha: str,
    added_or_modified: list[str],
    removed: list[str],
) -> None:
    """
    For one agent_github_sources row, sync changed files to memory.

    - For removed: just delete_by_source.
    - For added/modified: delete_by_source (clear stale chunks), then fetch
      the current file content at `after_sha` and add_memory(kind="code").
    """
    agent_id = src["agent_id"]
    repo = src["repo_full_name"]
    branch = src["branch"]
    installation_id = src.get("installation_id")

    # Removed files
    for path in removed:
        source_url = _file_source_url(repo, path)
        try:
            await mem.delete_by_source(agent_id=agent_id, source_url=source_url)
        except Exception as e:
            log.warning("github_remove_failed", repo=repo, path=path, error=str(e)[:160])

    # Added/modified: refresh content
    for path in added_or_modified:
        source_url = _file_source_url(repo, path)
        try:
            # Prefer App installation token (private repos, higher rate limits).
            # Fall back to PAT/anon for repos connected via the manual flow.
            if installation_id and gh_app.app_mode_enabled():
                if _skip_path(path):
                    continue
                content = await gh_app.fetch_file_via_installation(
                    installation_id=int(installation_id),
                    repo_full_name=repo,
                    sha=after_sha,
                    path=path,
                )
            else:
                content = await _fetch_file_at(repo, after_sha, path)
            if content is None:
                continue
            # Wipe any older chunks for this path, then add fresh ones.
            await mem.delete_by_source(agent_id=agent_id, source_url=source_url)
            await mem.add_memory(
                agent_id=agent_id,
                content=content,
                source_url=source_url,
                kind="code",
                extra_metadata={"repo": repo, "branch": branch, "sha": after_sha, "path": path},
            )
        except Exception as e:
            log.warning("github_sync_failed", repo=repo, path=path, error=str(e)[:160])

    # Bookkeeping
    try:
        data_repo.update_github_source_sha(
            src["id"],
            last_synced_sha=after_sha,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        log.warning("github_bookkeeping_failed", error=str(e)[:160])

    log.info("github_sync_done", agent_id=agent_id, repo=repo,
             updated=len(added_or_modified), removed=len(removed),
             sha=after_sha[:8])


# ─── Helpers ────────────────────────────────────────────────────────────────


def _verify_signature(body: bytes, signature_header: str, secret: str) -> bool:
    """Verify GitHub's X-Hub-Signature-256: sha256=<hex>."""
    if not signature_header.startswith("sha256="):
        return False
    expected = signature_header.split("=", 1)[1]
    computed = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, computed)


def _file_source_url(repo: str, path: str) -> str:
    """Canonical source_url for a single file's memory chunks."""
    return f"github://{repo}/{path}"


async def _fetch_file_at(repo: str, sha: str, path: str) -> str | None:
    """
    Fetch a file's raw content at a specific commit via the GitHub Contents API.
    Uses GITHUB_TOKEN if set (avoids rate limits + private repos).
    Returns None for binary files or files we shouldn't ingest.
    """
    settings = get_settings()
    token = settings.get("github_token")
    # raw.githubusercontent.com works without auth for public repos
    raw_url = f"https://raw.githubusercontent.com/{repo}/{sha}/{path}"
    headers = {"User-Agent": "BriefedBot/2.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Filter out files we don't want to ingest
    if _skip_path(path):
        return None

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as c:
        r = await c.get(raw_url, headers=headers)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        # Bail on binaries — heuristic: if any null bytes in first 4KB, skip
        if b"\x00" in r.content[:4096]:
            return None
        text = r.text
        if len(text) > 350_000:
            # Same cap github_ingest uses for the initial walk
            text = text[:350_000]
        return text


_SKIP_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip",
    ".tar", ".gz", ".bz2", ".7z", ".mp3", ".mp4", ".mov", ".wav",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".pyc", ".pyo", ".so", ".dylib", ".dll", ".class", ".jar",
    ".min.js", ".min.css",
}
_SKIP_DIRS = {"node_modules/", ".git/", "dist/", "build/", ".next/", "__pycache__/", ".venv/"}


def _skip_path(path: str) -> bool:
    if any(path.startswith(d) or f"/{d}" in path for d in _SKIP_DIRS):
        return True
    lower = path.lower()
    return any(lower.endswith(ext) for ext in _SKIP_EXT)


# ─── Install-lifecycle handlers ─────────────────────────────────────────────


async def _handle_installation_event(event_name: str, payload: dict[str, Any]) -> None:
    """
    Handle `installation` and `installation_repositories` webhook events.

    On install:    create agent_github_sources rows for each repo (no agent_id yet —
                   user must associate via the install-callback flow).
    On uninstall:  delete rows for that installation.
    On repos added/removed (installation_repositories event): adjust rows accordingly.

    Rows created here have `agent_id = NULL` initially. The frontend's
    install-callback page lets the user pick which agent each repo belongs to.

    NOTE: this requires a `agent_id` nullable column. If your schema enforces
    NOT NULL, the install rows live in a separate `pending_github_installs`
    table — adapt accordingly. For now we just log unmapped installs so the
    user can manually associate via POST /api/agents/{id}/github.
    """
    action = payload.get("action")
    installation = payload.get("installation") or {}
    installation_id = installation.get("id")
    if not installation_id:
        log.warning("github_install_event_missing_id", event=event_name, action=action)
        return

    if event_name == "installation" and action in ("deleted", "suspend"):
        try:
            deleted = data_repo.delete_github_sources_by_installation(installation_id)
            log.info("github_install_removed", installation_id=installation_id,
                     rows_deleted=deleted)
        except Exception as e:
            log.error("github_install_delete_failed", error=str(e)[:200])
        return

    # For install/create/added events: log so user can finish hookup via UI.
    # We DON'T auto-create rows here because rows need an agent_id (which a
    # GitHub event doesn't know about). The frontend install-callback receives
    # the installation_id and lets the user map repos→agents, then upserts rows
    # via POST /api/agents/{id}/github with installation_id payload.
    repos = payload.get("repositories") or payload.get("repositories_added") or []
    log.info("github_install_event_logged",
             event=event_name, action=action,
             installation_id=installation_id,
             repo_count=len(repos),
             account=(installation.get("account") or {}).get("login"))
