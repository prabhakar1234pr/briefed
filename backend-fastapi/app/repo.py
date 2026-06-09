"""Data-access layer over Cloud SQL (replaces the Supabase client).

All DB reads/writes the backend performs go through these functions. They use
SQLAlchemy Core with parameterized SQL against the shared engine in app.sql.

Conventions:
  * Rows are returned as plain dicts (RowMapping -> dict) to match the shape the
    old Supabase `.data` returned, minimizing downstream changes.
  * Mutations that "upsert dynamic columns" (e.g. meeting updates with a varying
    set of fields) accept a dict and build the SET clause dynamically with bound
    params — never string-interpolating values.
"""
from __future__ import annotations

import json
import uuid as _uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import text

from app.sql import get_engine

# Columns we allow to be updated on `meetings` via update_meeting(). Guards
# against accidental/injected column names in the dynamic SET builder.
_MEETING_UPDATABLE = {
    "bot_id", "status", "copilot_mode", "transcript_text", "summary",
    "action_items", "key_decisions", "audio_url", "video_url", "scheduled_at",
    "joined_at", "ended_at", "email_sent", "email_sent_at", "updated_at",
    "bridge_token", "meeting_link",
}

_AGENT_UPDATABLE = {
    "name", "description", "mode", "persona_prompt", "voice_id", "bot_image_url",
    "proactive_fact_check", "screenshot_on_request", "send_post_meeting_email",
    "updated_at",
}


def _coerce(v: Any) -> Any:
    """Normalize DB types to JSON-friendly values matching the old Supabase
    client output: UUID -> str, datetime/date -> ISO str, Decimal -> float."""
    if isinstance(v, _uuid.UUID):
        return str(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


def _dict(m) -> dict[str, Any]:
    return {k: _coerce(v) for k, v in m.items()}


def _rows(result) -> list[dict[str, Any]]:
    return [_dict(r) for r in result.mappings().all()]


def _row(result) -> dict[str, Any] | None:
    m = result.mappings().first()
    return _dict(m) if m else None


# ─── users ────────────────────────────────────────────────────────────────────

def upsert_user(*, id: str, email: str, full_name: str | None,
                avatar_url: str | None, updated_at: str) -> None:
    with get_engine().begin() as c:
        c.execute(
            text("""
                INSERT INTO users (id, email, full_name, avatar_url, updated_at)
                VALUES (:id, :email, :full_name, :avatar_url, :updated_at)
                ON CONFLICT (id) DO UPDATE SET
                  email = EXCLUDED.email,
                  full_name = EXCLUDED.full_name,
                  avatar_url = EXCLUDED.avatar_url,
                  updated_at = EXCLUDED.updated_at
            """),
            {"id": id, "email": email, "full_name": full_name,
             "avatar_url": avatar_url, "updated_at": updated_at},
        )


def get_user(user_id: str) -> dict[str, Any] | None:
    with get_engine().connect() as c:
        return _row(c.execute(
            text("SELECT id, email, full_name, avatar_url, created_at, updated_at "
                 "FROM users WHERE id = :id"),
            {"id": user_id},
        ))


# ─── agents ───────────────────────────────────────────────────────────────────

def get_agent(agent_id: str, user_id: str | None = None) -> dict[str, Any] | None:
    """Fetch one agent. If user_id is given, scope to that owner (auth)."""
    sql = "SELECT * FROM agents WHERE id = :id"
    params: dict[str, Any] = {"id": agent_id}
    if user_id is not None:
        sql += " AND user_id = :uid"
        params["uid"] = user_id
    with get_engine().connect() as c:
        return _row(c.execute(text(sql), params))


def insert_agent(*, user_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    """Insert an agent owned by user_id. Returns the new row (incl. generated id)."""
    cols = {k: v for k, v in fields.items() if k in _AGENT_UPDATABLE and k != "updated_at"}
    cols["user_id"] = user_id
    col_names = ", ".join(cols)
    placeholders = ", ".join(f":{k}" for k in cols)
    with get_engine().begin() as c:
        res = c.execute(
            text(f"INSERT INTO agents ({col_names}) VALUES ({placeholders}) RETURNING *"),
            cols,
        )
        return _row(res)  # type: ignore[return-value]


def list_agents(user_id: str) -> list[dict[str, Any]]:
    with get_engine().connect() as c:
        return _rows(c.execute(
            text("""SELECT id, name, description, updated_at,
                           proactive_fact_check, screenshot_on_request
                    FROM agents WHERE user_id = :uid
                    ORDER BY updated_at DESC"""),
            {"uid": user_id},
        ))


def update_agent(agent_id: str, user_id: str, fields: dict[str, Any]) -> bool:
    cols = {k: v for k, v in fields.items() if k in _AGENT_UPDATABLE}
    if not cols:
        return False
    set_clause = ", ".join(f"{k} = :{k}" for k in cols)
    params = {**cols, "id": agent_id, "uid": user_id}
    with get_engine().begin() as c:
        res = c.execute(
            text(f"UPDATE agents SET {set_clause} WHERE id = :id AND user_id = :uid"),
            params,
        )
        return res.rowcount > 0


def delete_agent(agent_id: str, user_id: str) -> None:
    # FK ON DELETE CASCADE handles meetings/context_chunks/etc.
    with get_engine().begin() as c:
        c.execute(text("DELETE FROM agents WHERE id = :id AND user_id = :uid"),
                  {"id": agent_id, "uid": user_id})


# ─── meetings ─────────────────────────────────────────────────────────────────

def insert_meeting(row: dict[str, Any]) -> None:
    with get_engine().begin() as c:
        c.execute(
            text("""
                INSERT INTO meetings
                  (id, user_id, agent_id, meeting_link, bot_id, status,
                   copilot_mode, bridge_token, scheduled_at, updated_at)
                VALUES
                  (:id, :user_id, :agent_id, :meeting_link, :bot_id, :status,
                   :copilot_mode, :bridge_token, :scheduled_at, :updated_at)
            """),
            {
                "id": row["id"], "user_id": row["user_id"], "agent_id": row["agent_id"],
                "meeting_link": row["meeting_link"], "bot_id": row.get("bot_id"),
                "status": row.get("status", "scheduled"),
                "copilot_mode": row.get("copilot_mode", "output_audio"),
                "bridge_token": row.get("bridge_token"),
                "scheduled_at": row.get("scheduled_at"),
                "updated_at": row["updated_at"],
            },
        )


def update_meeting(meeting_id: str, fields: dict[str, Any]) -> None:
    cols = {k: v for k, v in fields.items() if k in _MEETING_UPDATABLE}
    if not cols:
        return
    set_clause = ", ".join(f"{k} = :{k}" for k in cols)
    with get_engine().begin() as c:
        c.execute(text(f"UPDATE meetings SET {set_clause} WHERE id = :id"),
                  {**cols, "id": meeting_id})


def get_meeting(meeting_id: str, user_id: str | None = None) -> dict[str, Any] | None:
    sql = "SELECT * FROM meetings WHERE id = :id"
    params: dict[str, Any] = {"id": meeting_id}
    if user_id is not None:
        sql += " AND user_id = :uid"
        params["uid"] = user_id
    with get_engine().connect() as c:
        return _row(c.execute(text(sql), params))


def get_meeting_by_bot(bot_id: str, columns: str = "*") -> dict[str, Any] | None:
    with get_engine().connect() as c:
        return _row(c.execute(
            text(f"SELECT {columns} FROM meetings WHERE bot_id = :bot LIMIT 1"),
            {"bot": bot_id},
        ))


def list_meetings(user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    with get_engine().connect() as c:
        return _rows(c.execute(
            text("""SELECT id, meeting_link, status, created_at, bot_id
                    FROM meetings WHERE user_id = :uid
                    ORDER BY created_at DESC LIMIT :lim"""),
            {"uid": user_id, "lim": limit},
        ))


def delete_meetings_for_agent(agent_id: str) -> None:
    with get_engine().begin() as c:
        c.execute(text("DELETE FROM meetings WHERE agent_id = :aid"), {"aid": agent_id})


def delete_meeting(meeting_id: str, user_id: str) -> None:
    with get_engine().begin() as c:
        c.execute(text("DELETE FROM meetings WHERE id = :id AND user_id = :uid"),
                  {"id": meeting_id, "uid": user_id})


# ─── transcript_lines ─────────────────────────────────────────────────────────

def insert_transcript_line(*, meeting_id: str, speaker_name: str | None,
                           content: str, spoken_at: str,
                           words: Any | None) -> None:
    with get_engine().begin() as c:
        c.execute(
            text("""INSERT INTO transcript_lines
                      (meeting_id, speaker_name, content, spoken_at, words)
                    VALUES (:mid, :sp, :content, :spoken_at, :words)"""),
            {"mid": meeting_id, "sp": speaker_name, "content": content,
             "spoken_at": spoken_at,
             "words": json.dumps(words) if words is not None else None},
        )


def list_transcript_lines(meeting_id: str, *, columns: str = "*",
                          desc: bool = False, limit: int | None = None) -> list[dict[str, Any]]:
    order = "DESC" if desc else "ASC"
    sql = (f"SELECT {columns} FROM transcript_lines WHERE meeting_id = :mid "
           f"ORDER BY spoken_at {order}")
    params: dict[str, Any] = {"mid": meeting_id}
    if limit is not None:
        sql += " LIMIT :lim"
        params["lim"] = limit
    with get_engine().connect() as c:
        return _rows(c.execute(text(sql), params))


# ─── meeting_interactions ─────────────────────────────────────────────────────

def insert_interaction(row: dict[str, Any]) -> None:
    with get_engine().begin() as c:
        c.execute(
            text("""INSERT INTO meeting_interactions
                      (meeting_id, interaction_type, trigger_text, response_text,
                       screenshot_b64, screenshot_url, audio_url, spoken_at)
                    VALUES (:mid, :itype, :trig, :resp, :ss_b64, :ss_url, :audio, :spoken_at)"""),
            {
                "mid": row["meeting_id"], "itype": row["interaction_type"],
                "trig": row.get("trigger_text"), "resp": row.get("response_text"),
                "ss_b64": row.get("screenshot_b64"), "ss_url": row.get("screenshot_url"),
                "audio": row.get("audio_url"), "spoken_at": row.get("spoken_at"),
            },
        )


def list_interactions(meeting_id: str) -> list[dict[str, Any]]:
    with get_engine().connect() as c:
        return _rows(c.execute(
            text("""SELECT id, interaction_type, trigger_text, response_text,
                           spoken_at, created_at, screenshot_url, audio_url
                    FROM meeting_interactions WHERE meeting_id = :mid
                    ORDER BY spoken_at ASC"""),
            {"mid": meeting_id},
        ))


# ─── screenshots ──────────────────────────────────────────────────────────────

def insert_screenshot(*, meeting_id: str, storage_path: str,
                      taken_at: str, triggered_by: str | None) -> None:
    with get_engine().begin() as c:
        c.execute(
            text("""INSERT INTO screenshots (meeting_id, storage_path, taken_at, triggered_by)
                    VALUES (:mid, :path, :taken_at, :trig)"""),
            {"mid": meeting_id, "path": storage_path, "taken_at": taken_at,
             "trig": triggered_by},
        )


# ─── context_chunks ───────────────────────────────────────────────────────────

def existing_content_hashes(agent_id: str) -> set[str]:
    with get_engine().connect() as c:
        rows = c.execute(
            text("SELECT content_hash FROM context_chunks WHERE agent_id = :aid"),
            {"aid": agent_id},
        ).scalars().all()
    return set(rows)


def insert_context_chunks(rows: Iterable[dict[str, Any]]) -> int:
    rows = list(rows)
    if not rows:
        return 0
    # pgvector via pg8000: pass the embedding as a string literal "[1,2,3]".
    payload = [
        {
            "agent_id": r["agent_id"],
            "source_url": r["source_url"],
            "content": r["content"],
            "content_hash": r["content_hash"],
            "embedding": _vec_literal(r["embedding"]),
        }
        for r in rows
    ]
    with get_engine().begin() as c:
        c.execute(
            text("""INSERT INTO context_chunks
                      (agent_id, source_url, content, content_hash, embedding)
                    VALUES (:agent_id, :source_url, :content, :content_hash,
                            CAST(:embedding AS vector))"""),
            payload,
        )
    return len(payload)


def list_context_chunks(agent_id: str, *, columns: str = "*",
                        desc: bool = False, limit: int | None = None) -> list[dict[str, Any]]:
    order = "ORDER BY created_at DESC" if desc else ""
    sql = f"SELECT {columns} FROM context_chunks WHERE agent_id = :aid {order}"
    params: dict[str, Any] = {"aid": agent_id}
    if limit is not None:
        sql += " LIMIT :lim"
        params["lim"] = limit
    with get_engine().connect() as c:
        return _rows(c.execute(text(sql), params))


def delete_context_chunks(agent_id: str, *, source_url_eq: str | None = None,
                          source_url_like: str | None = None) -> None:
    sql = "DELETE FROM context_chunks WHERE agent_id = :aid"
    params: dict[str, Any] = {"aid": agent_id}
    if source_url_eq is not None:
        sql += " AND source_url = :su"
        params["su"] = source_url_eq
    elif source_url_like is not None:
        sql += " AND source_url LIKE :su"
        params["su"] = source_url_like
    with get_engine().begin() as c:
        c.execute(text(sql), params)


def match_context_chunks(agent_id: str, query_embedding: list[float],
                         match_count: int = 5) -> list[dict[str, Any]]:
    """pgvector similarity search via the match_context_chunks SQL function."""
    with get_engine().connect() as c:
        return _rows(c.execute(
            text("""SELECT id, content, source_url, similarity
                    FROM match_context_chunks(:aid, CAST(:emb AS vector), :k)"""),
            {"aid": agent_id, "emb": _vec_literal(query_embedding), "k": match_count},
        ))


def _vec_literal(vec: Any) -> str:
    """Format a float list as a pgvector text literal: [0.1,0.2,...]."""
    if isinstance(vec, str):
        return vec
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


# ─── agent_github_sources ─────────────────────────────────────────────────────

def upsert_github_source(*, agent_id: str, repo_full_name: str, branch: str,
                         installation_id: int | None, webhook_secret: str,
                         updated_at: str) -> None:
    with get_engine().begin() as c:
        c.execute(
            text("""
                INSERT INTO agent_github_sources
                  (agent_id, repo_full_name, branch, installation_id, webhook_secret, updated_at)
                VALUES (:aid, :repo, :branch, :inst, :secret, :updated_at)
                ON CONFLICT (agent_id, repo_full_name, branch) DO UPDATE SET
                  installation_id = EXCLUDED.installation_id,
                  webhook_secret = EXCLUDED.webhook_secret,
                  updated_at = EXCLUDED.updated_at
            """),
            {"aid": agent_id, "repo": repo_full_name, "branch": branch,
             "inst": installation_id, "secret": webhook_secret, "updated_at": updated_at},
        )


def list_github_sources(*, repo_full_name: str, branch: str) -> list[dict[str, Any]]:
    with get_engine().connect() as c:
        return _rows(c.execute(
            text("""SELECT * FROM agent_github_sources
                    WHERE repo_full_name = :repo AND branch = :branch"""),
            {"repo": repo_full_name, "branch": branch},
        ))


def update_github_source_sha(source_id: str, *, last_synced_sha: str, updated_at: str) -> None:
    with get_engine().begin() as c:
        c.execute(
            text("""UPDATE agent_github_sources
                    SET last_synced_sha = :sha, updated_at = :updated_at
                    WHERE id = :id"""),
            {"sha": last_synced_sha, "updated_at": updated_at, "id": source_id},
        )


def delete_github_sources_by_installation(installation_id: int) -> int:
    with get_engine().begin() as c:
        res = c.execute(
            text("DELETE FROM agent_github_sources WHERE installation_id = :inst"),
            {"inst": installation_id},
        )
        return res.rowcount
