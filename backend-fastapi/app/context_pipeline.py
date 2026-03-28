"""
Context ingestion pipeline:
  - Fetch URL content (GitHub, docs, raw text)
  - Chunk into ~512-token segments
  - Embed via Vertex AI
  - Store in Supabase context_chunks table (with pgvector)
  - Semantic search for Q&A
"""
import asyncio
import hashlib
import logging
import re
from typing import Any

import httpx

from app.db import get_supabase_service

logger = logging.getLogger(__name__)

# ~512 tokens ≈ 2000 chars, 50-token overlap ≈ 200 chars
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200
EMBED_BATCH = 10  # Vertex AI allows up to 250 but stay conservative


def _chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks. Returns non-empty chunks only."""
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


def _clean_text(raw: str) -> str:
    """Remove excessive whitespace and null bytes."""
    raw = raw.replace("\x00", "")
    raw = re.sub(r"\n{4,}", "\n\n\n", raw)
    raw = re.sub(r" {4,}", "   ", raw)
    return raw.strip()


async def _fetch_url_text(url: str) -> str:
    """
    Fetch a URL and return text content.
    GitHub repository root /tree URLs are handled in ingest_source (full RAG walk).
    """
    # GitHub raw file
    if "raw.githubusercontent.com" in url or url.endswith((".md", ".txt", ".py", ".ts", ".js", ".go", ".rs", ".java")):
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as c:
            r = await c.get(url, headers={"User-Agent": "BriefedBot/1.0"})
            r.raise_for_status()
            return _clean_text(r.text)

    # Generic webpage: strip HTML tags
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as c:
        r = await c.get(url, headers={"User-Agent": "BriefedBot/1.0"})
        r.raise_for_status()
        text = r.text
        # Strip HTML
        text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"&[a-z]+;", " ", text)
        return _clean_text(text)


async def ingest_source(
    agent_id: str,
    source_type: str,  # "url" | "text"
    content: str,      # URL string or raw text
    label: str | None = None,
) -> dict[str, Any]:
    """
    Main ingestion entry point.
    Returns { chunks_added: int, source_url: str } — source_url is the ingest root (repo URL or manual).
    """
    from app.ai_client import embed_text
    from app.github_ingest import ingest_github_repo_to_chunks, parse_github_repo_url

    db = get_supabase_service()
    primary_source_url = content.strip() if source_type == "url" else (label or "manual")

    chunk_pairs: list[tuple[str, str]] = []

    if source_type == "url":
        source_url = content.strip()
        if parse_github_repo_url(source_url):
            try:
                chunk_pairs = await ingest_github_repo_to_chunks(source_url)
            except Exception as e:
                raise RuntimeError(f"GitHub ingest failed: {e}") from e
        else:
            try:
                text = await _fetch_url_text(source_url)
            except Exception as e:
                raise RuntimeError(f"Failed to fetch {source_url}: {e}") from e
            if not text or len(text) < 20:
                raise RuntimeError("Content is too short or empty")
            for c in _chunk_text(text):
                chunk_pairs.append((c, source_url))
    else:
        source_url = label or "manual"
        primary_source_url = source_url
        text = content
        if not text or len(text) < 20:
            raise RuntimeError("Content is too short or empty")
        for c in _chunk_text(text):
            chunk_pairs.append((c, source_url))

    if not chunk_pairs:
        raise RuntimeError("No chunks generated from content")

    existing_res = (
        db.table("context_chunks")
        .select("content_hash")
        .eq("agent_id", agent_id)
        .execute()
    )
    existing_hashes = {r["content_hash"] for r in (existing_res.data or [])}

    new_rows: list[tuple[str, str, str]] = []
    for chunk, src_url in chunk_pairs:
        h = hashlib.sha256(chunk.encode()).hexdigest()
        if h not in existing_hashes:
            new_rows.append((chunk, h, src_url))
            existing_hashes.add(h)

    if not new_rows:
        return {"chunks_added": 0, "source_url": primary_source_url}

    inserted = 0
    for i in range(0, len(new_rows), EMBED_BATCH):
        # Throttle: 1.5s between batches to stay under RPM quota
        if i > 0:
            await asyncio.sleep(1.5)

        batch = new_rows[i : i + EMBED_BATCH]
        texts = [c for c, _, __ in batch]

        try:
            vectors = await embed_text(texts)
        except Exception as e:
            logger.exception("embed_text batch %d failed: %s", i, e)
            continue

        rows = [
            {
                "agent_id": agent_id,
                "source_url": batch[j][2],
                "content": texts[j],
                "content_hash": batch[j][1],
                "embedding": vectors[j],
            }
            for j in range(len(batch))
        ]
        db.table("context_chunks").insert(rows).execute()
        inserted += len(rows)

    return {"chunks_added": inserted, "source_url": primary_source_url}


async def search_context(agent_id: str, query: str, top_k: int = 5) -> list[str]:
    """
    Semantic search over an agent's context chunks.
    Returns list of chunk content strings, most relevant first.
    """
    from app.ai_client import embed_text

    try:
        vectors = await embed_text([query])
        query_vec = vectors[0]
    except Exception as e:
        logger.exception("search_context embed failed: %s", e)
        return []

    db = get_supabase_service()

    try:
        # Use pgvector cosine similarity via Supabase RPC
        res = db.rpc(
            "match_context_chunks",
            {
                "p_agent_id": agent_id,
                "query_embedding": query_vec,
                "match_count": top_k,
            },
        ).execute()
        return [r["content"] for r in (res.data or [])]
    except Exception as e:
        logger.exception("search_context rpc failed: %s", e)
        # Fallback: return most recent chunks
        fallback = (
            db.table("context_chunks")
            .select("content")
            .eq("agent_id", agent_id)
            .limit(top_k)
            .execute()
        )
        return [r["content"] for r in (fallback.data or [])]
