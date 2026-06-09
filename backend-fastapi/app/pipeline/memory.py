"""
Unified memory layer — Supermemory primary, pgvector fallback.

Three memory kinds map to the "remote employee" model:
  - "doc":     uploaded knowledge base (PDFs, URLs, manual text)
  - "meeting": post-meeting summaries, decisions, action items (cross-meeting recall)
  - "code":    GitHub-ingested source files (kept fresh by GitHub webhook)

Each agent gets its own Supermemory namespace (container_tag = agent_id),
so Sam's memory is isolated from Riley's.
"""
from __future__ import annotations

from typing import Any, Literal

from app.config import get_settings
from app.logger import get_logger

log = get_logger(__name__)

MemoryKind = Literal["doc", "meeting", "code"]


# ─── Supermemory client (lazy init) ──────────────────────────────────────────
_supermemory_client: Any | None = None


def _get_client() -> Any | None:
    """Return Supermemory client, or None if not configured."""
    global _supermemory_client
    if _supermemory_client is not None:
        return _supermemory_client
    api_key = get_settings()["supermemory_api_key"]
    if not api_key:
        return None
    try:
        from supermemory import AsyncSupermemory
        _supermemory_client = AsyncSupermemory(api_key=api_key)
        return _supermemory_client
    except ImportError:
        log.warning("supermemory_sdk_missing")
        return None


# ─── Public API ──────────────────────────────────────────────────────────────


async def add_memory(
    agent_id: str,
    content: str,
    *,
    source_url: str,
    kind: MemoryKind,
    extra_metadata: dict[str, Any] | None = None,
) -> bool:
    """
    Persist a memory for an agent. Returns True on success.

    For the GitHub webhook path: call delete_by_source() first, then add_memory()
    with the new content under the same source_url.
    """
    client = _get_client()
    if client is None:
        return await _add_memory_pgvector_fallback(agent_id, content, source_url=source_url, kind=kind)

    metadata: dict[str, Any] = {"kind": kind, "source_url": source_url}
    if extra_metadata:
        metadata.update(extra_metadata)

    try:
        await client.memories.add(
            content=content,
            container_tag=f"agent:{agent_id}",
            metadata=metadata,
        )
        log.info("memory_added", agent_id=agent_id, kind=kind, source=source_url, chars=len(content))
        return True
    except Exception as e:
        log.error("memory_add_failed", agent_id=agent_id, error=str(e)[:200])
        return False


async def search_memory(
    agent_id: str,
    query: str,
    *,
    top_k: int = 6,
    kinds: list[MemoryKind] | None = None,
) -> list[dict[str, Any]]:
    """
    Recall memories relevant to a query. Returns list of {content, kind, source_url, score}.

    Pass kinds=["meeting"] to recall only prior-meeting context for "what did we decide last time?"
    Pass kinds=None to recall across everything.
    """
    client = _get_client()
    if client is None:
        return await _search_memory_pgvector_fallback(agent_id, query, top_k=top_k)

    filters: dict[str, Any] = {}
    if kinds:
        filters["kind"] = {"$in": list(kinds)}

    try:
        results = await client.search.execute(
            q=query,
            container_tags=[f"agent:{agent_id}"],
            limit=top_k,
            filters=filters or None,
        )
        out: list[dict[str, Any]] = []
        for r in (results.results or []):
            meta = r.metadata or {}
            out.append({
                "content": r.content or "",
                "kind": meta.get("kind", "doc"),
                "source_url": meta.get("source_url", ""),
                "score": getattr(r, "score", 0.0),
            })
        return out
    except Exception as e:
        log.error("memory_search_failed", agent_id=agent_id, error=str(e)[:200])
        return []


async def delete_by_source(agent_id: str, source_url: str) -> int:
    """
    Delete all memories with a given source_url for an agent.
    Used by the GitHub webhook to wipe stale chunks before re-ingest.
    Returns number of memories deleted.
    """
    client = _get_client()
    if client is None:
        return await _delete_pgvector_fallback(agent_id, source_url)

    try:
        # Supermemory: query by metadata.source_url, then delete by ID.
        results = await client.search.execute(
            q="",
            container_tags=[f"agent:{agent_id}"],
            limit=500,
            filters={"source_url": source_url},
        )
        deleted = 0
        for r in (results.results or []):
            mem_id = getattr(r, "id", None)
            if mem_id:
                await client.memories.delete(memory_id=mem_id)
                deleted += 1
        log.info("memory_deleted", agent_id=agent_id, source=source_url, count=deleted)
        return deleted
    except Exception as e:
        log.error("memory_delete_failed", agent_id=agent_id, error=str(e)[:200])
        return 0


# ─── pgvector fallback (transition period; lets v2 run without Supermemory) ──


async def _add_memory_pgvector_fallback(
    agent_id: str, content: str, *, source_url: str, kind: MemoryKind
) -> bool:
    """Fallback to existing context_chunks table when Supermemory not configured."""
    from app.context_pipeline import ingest_source
    try:
        await ingest_source(agent_id=agent_id, source_type="text", content=content, label=source_url)
        return True
    except Exception as e:
        log.error("memory_pgvector_add_failed", agent_id=agent_id, error=str(e)[:200])
        return False


async def _search_memory_pgvector_fallback(
    agent_id: str, query: str, *, top_k: int
) -> list[dict[str, Any]]:
    """Fallback search via pgvector — returns content but no kind/source metadata."""
    from app.context_pipeline import search_context
    chunks = await search_context(agent_id, query, top_k=top_k)
    return [{"content": c, "kind": "doc", "source_url": "", "score": 0.0} for c in chunks]


async def _delete_pgvector_fallback(agent_id: str, source_url: str) -> int:
    """Delete pgvector rows matching source_url."""
    from app import repo
    try:
        repo.delete_context_chunks(agent_id, source_url_eq=source_url)
        return 1
    except Exception as e:
        log.error("memory_pgvector_delete_failed", agent_id=agent_id, error=str(e)[:200])
        return 0
