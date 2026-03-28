"""
GitHub repository ingestion for RAG: tree walk, path filtering, raw file fetch, chunking.
Uses GitHub REST API (optional token) + raw.githubusercontent.com.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# Keep in sync with context_pipeline chunking
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200


def _clean_text(raw: str) -> str:
    raw = raw.replace("\x00", "")
    raw = re.sub(r"\n{4,}", "\n\n\n", raw)
    raw = re.sub(r" {4,}", "   ", raw)
    return raw.strip()


def _chunk_text(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


# Per-file cap (chars) — avoids huge generated / lock files
MAX_FILE_CHARS = 350_000
# Hard stop for a single repo ingest
MAX_FILES = 250
MAX_TOTAL_CHARS = 2_000_000

SKIP_PATH_SUBSTRINGS = frozenset(
    lower
    for lower in [
        "node_modules/",
        "/node_modules/",
        ".git/",
        "dist/",
        "/dist/",
        "build/",
        "/build/",
        "out/",
        "target/",
        "__pycache__/",
        ".venv/",
        "venv/",
        ".next/",
        ".turbo/",
        ".cache/",
        "coverage/",
        "Pods/",
        "deriveddata/",
        ".idea/",
        ".vscode/",
        "vendor/",
        "bower_components/",
        ".gradle/",
        "gradle/wrapper/",
    ]
)

SKIP_NAME_SUFFIXES = frozenset(
    [
        ".min.js",
        ".min.css",
        ".map",
        ".lock",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".ico",
        ".svg",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".mp4",
        ".mp3",
        ".pdf",
        ".zip",
        ".tar",
        ".gz",
        ".7z",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".pyc",
        ".class",
        ".o",
        ".a",
    ]
)

ALLOW_SUFFIXES = frozenset(
    [
        ".md",
        ".mdx",
        ".txt",
        ".rst",
        ".py",
        ".pyi",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".go",
        ".rs",
        ".java",
        ".kt",
        ".cs",
        ".rb",
        ".php",
        ".swift",
        ".scala",
        ".sql",
        ".sh",
        ".bash",
        ".zsh",
        ".yaml",
        ".yml",
        ".toml",
        ".json",
        ".html",
        ".htm",
        ".css",
        ".scss",
        ".sass",
        ".less",
        ".vue",
        ".svelte",
        ".graphql",
        ".dockerfile",
    ]
)

SPECIAL_FILENAMES = frozenset(
    [
        "dockerfile",
        "makefile",
        "gemfile",
        "rakefile",
        "cargo.toml",
    ]
)


@dataclass
class GitHubRepoRef:
    owner: str
    repo: str
    branch: str | None  # None → default branch from API
    path_prefix: str | None  # None or "" = whole repo


GITHUB_TREE_URL = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/tree/(?P<branch>[^/]+)(?:/(?P<subpath>.+))?$",
    re.IGNORECASE,
)
GITHUB_ROOT_URL = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/?$",
    re.IGNORECASE,
)


def raw_github_file_url(owner: str, repo: str, branch: str, path: str) -> str:
    safe_path = "/".join(quote(part, safe="") for part in path.split("/") if part)
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{safe_path}"


def parse_github_repo_url(url: str) -> GitHubRepoRef | None:
    url = url.strip().rstrip("/")
    m = GITHUB_TREE_URL.match(url)
    if m:
        return GitHubRepoRef(
            owner=m.group("owner"),
            repo=m.group("repo"),
            branch=m.group("branch"),
            path_prefix=(m.group("subpath") or "").strip() or None,
        )
    m = GITHUB_ROOT_URL.match(url)
    if m:
        return GitHubRepoRef(
            owner=m.group("owner"),
            repo=m.group("repo"),
            branch=None,
            path_prefix=None,
        )
    return None


def _github_headers() -> dict[str, str]:
    h = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Briefed-Copilot-RAG/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = get_settings().get("github_token")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _should_skip_path(path: str, lower_path: str) -> bool:
    if any(skip in lower_path for skip in SKIP_PATH_SUBSTRINGS):
        return True
    base = path.rsplit("/", 1)[-1].lower()
    if base in {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "go.sum"}:
        return True
    for suf in SKIP_NAME_SUFFIXES:
        if lower_path.endswith(suf):
            return True
    return False


def _is_allowed_file(path: str, lower_path: str) -> bool:
    base = path.rsplit("/", 1)[-1]
    if base.lower() in SPECIAL_FILENAMES:
        return "cargo.lock" not in base.lower()
    for suf in ALLOW_SUFFIXES:
        if lower_path.endswith(suf):
            return True
    return False


async def _api_get(client: httpx.AsyncClient, path: str) -> Any:
    r = await client.get(f"https://api.github.com{path}", headers=_github_headers())
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


async def ingest_github_repo_to_chunks(repo_url: str) -> list[tuple[str, str]]:
    """
    Returns list of (chunk_text, source_url) for embedding.
    chunk_text includes a file header for retrieval quality.
    """
    ref = parse_github_repo_url(repo_url)
    if not ref:
        return []

    owner, repo = ref.owner, ref.repo
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        repo_info = await _api_get(client, f"/repos/{owner}/{repo}")
        if not repo_info:
            raise RuntimeError(f"GitHub repo not found or not accessible: {owner}/{repo}")

        default_branch = repo_info.get("default_branch") or "main"
        branch = ref.branch or default_branch

        # Resolve branch tip SHA for tree API
        ref_data = await _api_get(client, f"/repos/{owner}/{repo}/git/ref/heads/{quote(branch, safe='')}")
        if not ref_data:
            # Try default if branch missing
            if ref.branch:
                branch = default_branch
                ref_data = await _api_get(
                    client, f"/repos/{owner}/{repo}/git/ref/heads/{quote(branch, safe='')}"
                )
            if not ref_data:
                raise RuntimeError(f"Could not resolve branch '{branch}' for {owner}/{repo}")

        commit_sha = ref_data["object"]["sha"]
        tree_data = await _api_get(
            client,
            f"/repos/{owner}/{repo}/git/trees/{commit_sha}?recursive=1",
        )
        if not tree_data or "tree" not in tree_data:
            raise RuntimeError("Could not load repository tree")
        if tree_data.get("truncated"):
            logger.warning(
                "github_ingest: tree truncated for %s/%s — use a /tree/branch/subfolder URL or GITHUB_TOKEN",
                owner,
                repo,
            )

        prefix = (ref.path_prefix or "").strip().lower().rstrip("/")
        candidates: list[dict[str, Any]] = []
        for item in tree_data["tree"]:
            if item.get("type") != "blob":
                continue
            path = item.get("path") or ""
            lower_path = path.lower()
            if prefix and not lower_path.startswith(prefix + "/") and lower_path != prefix:
                continue
            if _should_skip_path(path, lower_path):
                continue
            if not _is_allowed_file(path, lower_path):
                continue
            size = item.get("size") or 0
            if size > MAX_FILE_CHARS:
                continue
            candidates.append(item)

        candidates.sort(key=lambda x: x.get("path") or "")
        if len(candidates) > MAX_FILES:
            candidates = candidates[:MAX_FILES]

        logger.info(
            "github_ingest: %s/%s@%s — fetching %d files (prefix=%s)",
            owner,
            repo,
            branch,
            len(candidates),
            prefix or "/",
        )

        sem = __import__("asyncio").Semaphore(10)

        async def fetch_blob(path: str) -> str | None:
            raw = raw_github_file_url(owner, repo, branch, path)
            async with sem:
                try:
                    rr = await client.get(raw, headers={"User-Agent": "Briefed-Copilot-RAG/1.0"})
                    if not rr.is_success:
                        return None
                    text = rr.text
                    if len(text) > MAX_FILE_CHARS:
                        text = text[:MAX_FILE_CHARS] + "\n\n[…truncated…]"
                    return _clean_text(text)
                except Exception as e:
                    logger.warning("github_ingest fetch failed %s: %s", path, e)
                    return None

        import asyncio

        tasks = [fetch_blob(c["path"]) for c in candidates]
        contents = await asyncio.gather(*tasks)

        out: list[tuple[str, str]] = []
        total_chars = 0
        for item, body in zip(candidates, contents, strict=True):
            if not body or len(body) < 15:
                continue
            path = item["path"]
            display_url = f"https://github.com/{owner}/{repo}/blob/{branch}/{path}"
            header = f"[{owner}/{repo}: {path}]\n\n"
            combined = header + body
            if total_chars + len(combined) > MAX_TOTAL_CHARS:
                break
            total_chars += len(combined)
            for part in _chunk_text(combined):
                out.append((part, display_url))

        if not out:
            raise RuntimeError(
                "No text files matched filters after walking the repo. "
                "Try a /tree/branch/subfolder URL or add a GITHUB_TOKEN for private repos."
            )

        return out
