"""
Briefed FastAPI backend — main application.

Real-time copilot pipeline (per transcript trigger):
  1. ACK injected immediately (<500ms) — agent says "On it." before Gemini starts
  2. asyncio.gather: embed question + fetch transcript in parallel
  3. Gemini 2.5-pro streams answer — no token limit, answers fully
  4. Each complete sentence → TTS → inject_audio immediately
  → Users hear a natural, complete, flowing response starting ~2s after trigger.
"""
from __future__ import annotations

import asyncio
import base64
import json
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import os as _os
from pathlib import Path as _Path
try:
    from dotenv import load_dotenv as _load_dotenv
    _env_file = _Path(__file__).resolve().parent.parent / ".env"
    if _env_file.exists():
        _load_dotenv(_env_file, override=False)
except ImportError:
    pass

# Clear config cache so it re-reads the now-loaded env vars
from app.config import get_settings as _gs; _gs.cache_clear()

from app.auth_deps import get_user_id
from app.config import get_settings
from app.db import get_supabase_service
from app.logger import get_logger, log_timing, setup_logging
from app.output_media import copilot_bootstrap_mp3_b64
from app import recall_client as recall

log = get_logger(__name__)


# ─── In-memory caches ─────────────────────────────────────────────────────────
_agent_cache: dict[str, tuple[dict[str, Any], float]] = {}
_AGENT_CACHE_TTL = 300.0

_trigger_active: dict[str, bool] = {}

MIN_CHARS_FACT    = 42


def _get_cached_agent(agent_id: str) -> dict[str, Any] | None:
    entry = _agent_cache.get(agent_id)
    if entry and (time.monotonic() - entry[1]) < _AGENT_CACHE_TTL:
        return entry[0]
    return None


def _set_cached_agent(agent_id: str, agent: dict[str, Any]) -> None:
    _agent_cache[agent_id] = (agent, time.monotonic())


# ─── App lifespan ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()  # defaults to INFO; override with LOG_LEVEL env var
    log.info("briefed_startup",
             model=get_settings().get("live_qa_model", "gemini-2.5-pro"),
             project=get_settings().get("gcp_project"),
             recall_base=get_settings().get("recall_api_base"))
    yield
    log.info("briefed_shutdown")


app = FastAPI(title="Briefed API", lifespan=lifespan)

# ─── CORS ─────────────────────────────────────────────────────────────────────
_default_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
_extra = __import__("os").getenv("CORS_ORIGINS", "")
if _extra.strip():
    _default_origins = [o.strip() for o in _extra.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request models ───────────────────────────────────────────────────────────

class StartMeetingBody(BaseModel):
    agent_id: str
    meeting_link: str = Field(min_length=8)
    join_now: bool = True
    join_at: str | None = None


class IngestContextBody(BaseModel):
    source_type: str = Field(pattern="^(url|text)$")
    content: str = Field(min_length=3, max_length=200_000)
    label: str | None = None


class AskBody(BaseModel):
    question: str = Field(min_length=3, max_length=10_000)
    meeting_id: str | None = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

import re

def _public_base() -> str:
    base = get_settings()["public_api_base"]
    if not base:
        raise HTTPException(
            status_code=503,
            detail="Set PUBLIC_API_BASE to your public URL so Recall.ai can reach webhooks.",
        )
    return base


def _bot_message_from_agent(agent: dict[str, Any]) -> str:
    name = (agent.get("name") or "Briefed").strip()
    return (
        f"Hi, I'm {name} — your AI assistant. "
        f'Say "{name}" followed by any question to ask me something.'
    )[:500]


def _format_transcript_download(raw: Any) -> str:
    if isinstance(raw, list):
        lines: list[str] = []
        for seg in raw:
            if not isinstance(seg, dict):
                continue
            pname = (seg.get("participant") or {}).get("name") or "Unknown"
            words = seg.get("words") or []
            texts = [str(w["text"]) for w in words if isinstance(w, dict) and w.get("text")]
            line = " ".join(texts).strip()
            if line:
                lines.append(f"{pname}: {line}")
        return "\n".join(lines)
    if isinstance(raw, dict):
        return json.dumps(raw, indent=2)
    return str(raw)


def _artifact_download_url(bot: dict[str, Any], shortcut: str) -> str | None:
    for rec in bot.get("recordings") or []:
        ms = rec.get("media_shortcuts") or {}
        art = ms.get(shortcut) or {}
        url = (art.get("data") or {}).get("download_url")
        if isinstance(url, str) and url.strip():
            return url.strip()
    return None


def _detect_trigger(
    text: str, agent_name: str, *, screenshot_on: bool
) -> tuple[str | None, str | None]:
    t = text.lower().strip()
    name = agent_name.lower()
    if screenshot_on and any(p in t for p in [
        "take a screenshot", "screenshot please", "grab a screenshot", "capture screen"
    ]):
        return "screenshot", text
    m = re.search(
        rf"(?:hey\s+|ok\s+|okay\s+|@)?(?<![a-z]){re.escape(name)}(?![a-z])\s*[,:]?\s*(.+)", t
    )
    if m:
        question = (m.group(1) or "").strip() or "What would you like to know?"
        return "qa", question
    return None, None


async def _should_run_factcheck(meeting_id: str, text: str, agent: dict[str, Any]) -> bool:
    from app.rate_limit import check_fact_cooldown, check_fact_hourly_cap

    if agent.get("mode") == "proctor":
        return False
    if not agent.get("proactive_fact_check"):
        return False
    t = text.strip()
    if len(t) < MIN_CHARS_FACT or t.endswith("?") or len(t.split()) < 8:
        return False
    if not await check_fact_cooldown(meeting_id):
        return False
    return await check_fact_hourly_cap(meeting_id)


def _webhook_secret_ok(request: Request) -> bool:
    secret = get_settings().get("webhook_secret")
    if not secret:
        return True
    return (request.headers.get("x-webhook-secret") == secret or
            request.headers.get("authorization") == f"Bearer {secret}")


# ─── Background: refresh media URLs ──────────────────────────────────────────

async def refresh_recall_media_urls(bot_id: str) -> None:
    try:
        db = get_supabase_service()
    except RuntimeError as e:
        log.warning("refresh_media_urls_skip", error=str(e))
        return
    res = db.table("meetings").select("id").eq("bot_id", bot_id).limit(1).execute()
    if not res.data:
        return
    meeting_id = res.data[0]["id"]
    try:
        bot = await recall.retrieve_bot(bot_id)
    except Exception as e:
        log.exception("refresh_media_retrieve_failed", bot_id=bot_id, error=str(e))
        return
    video_u = _artifact_download_url(bot, "video_mixed")
    audio_u = _artifact_download_url(bot, "audio_mixed")
    if not audio_u:
        try:
            audio_u = await recall.fetch_audio_mixed_download_url(bot)
        except Exception as e:
            log.warning("refresh_audio_fetch_failed", bot_id=bot_id, error=str(e))
    update: dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if video_u:
        update["video_url"] = video_u
    if audio_u:
        update["audio_url"] = audio_u
    if len(update) > 1:
        db.table("meetings").update(update).eq("id", meeting_id).execute()
        log.info("media_urls_refreshed", meeting_id=meeting_id,
                 has_video=bool(video_u), has_audio=bool(audio_u))


# ─── Background: finalize meeting ────────────────────────────────────────────

async def finalize_meeting(bot_id: str) -> None:
    from app.ai_client import generate_meeting_intelligence
    from app.post_meeting_email import try_send_post_meeting_brief

    log.info("finalize_meeting_start", bot_id=bot_id)
    try:
        db = get_supabase_service()
    except RuntimeError as e:
        log.warning("finalize_meeting_skip", error=str(e))
        return

    res = db.table("meetings").select("id, status, agent_id, user_id").eq("bot_id", bot_id).limit(1).execute()
    if not res.data:
        return
    meeting = res.data[0]
    if meeting.get("status") == "completed":
        return
    meeting_id = meeting["id"]
    agent_id   = meeting.get("agent_id")
    user_id    = meeting.get("user_id")

    full_text: str | None = None
    video_u: str | None = None
    audio_u: str | None = None

    try:
        bot = await recall.retrieve_bot(bot_id)
        dl = _artifact_download_url(bot, "transcript")
        if dl:
            raw = await recall.fetch_transcript_json(dl)
            full_text = _format_transcript_download(raw)
            log.info("transcript_downloaded", meeting_id=meeting_id,
                     chars=len(full_text) if full_text else 0)
        video_u = _artifact_download_url(bot, "video_mixed")
        audio_u = _artifact_download_url(bot, "audio_mixed")
        if not audio_u:
            try:
                audio_u = await recall.fetch_audio_mixed_download_url(bot)
            except Exception as ae:
                log.warning("audio_mixed_fetch_failed", error=str(ae))
    except Exception as e:
        log.exception("finalize_recall_fetch_failed", meeting_id=meeting_id, error=str(e))

    if not full_text:
        lines_res = (
            db.table("transcript_lines")
            .select("speaker_name, content")
            .eq("meeting_id", meeting_id)
            .order("spoken_at")
            .execute()
        )
        parts = [
            f"{r.get('speaker_name','Unknown')}: {r['content']}"
            for r in (lines_res.data or []) if r.get("content")
        ]
        full_text = "\n".join(parts) if parts else None
        log.info("transcript_from_db", meeting_id=meeting_id, lines=len(parts))

    now = datetime.now(timezone.utc).isoformat()
    update: dict[str, Any] = {"status": "completed", "ended_at": now, "updated_at": now}
    if full_text:
        update["transcript_text"] = full_text
    if video_u:
        update["video_url"] = video_u
    if audio_u:
        update["audio_url"] = audio_u

    intel: dict[str, Any] | None = None
    if full_text and len(full_text.strip()) > 40:
        try:
            agent_name = "Briefed"
            if agent_id:
                ag_res = db.table("agents").select("name").eq("id", agent_id).limit(1).execute()
                if ag_res.data:
                    agent_name = ag_res.data[0].get("name") or "Briefed"
            with log_timing(log, "generate_intelligence", meeting_id=meeting_id):
                intel = await generate_meeting_intelligence(full_text, agent_name)
            if intel.get("summary"):
                update["summary"] = intel["summary"]
            if intel.get("action_items"):
                update["action_items"] = json.dumps(intel["action_items"])
            if intel.get("key_decisions"):
                update["key_decisions"] = json.dumps(intel["key_decisions"])
        except Exception as e:
            log.exception("intelligence_failed", meeting_id=meeting_id, error=str(e))

    db.table("meetings").update(update).eq("id", meeting_id).execute()
    log.info("finalize_meeting_done", meeting_id=meeting_id,
             has_intel=bool(intel), has_video=bool(video_u), has_audio=bool(audio_u))

    if user_id and intel:
        await try_send_post_meeting_brief(
            db, meeting_id=str(meeting_id), user_id=str(user_id),
            agent_id=str(agent_id) if agent_id else None, intel=intel,
        )


# ─── Core: streaming copilot trigger ─────────────────────────────────────────

async def process_copilot_trigger(
    meeting_id: str,
    bot_id: str,
    trigger_type: str,
    content: str,
    agent: dict[str, Any],
    spoken_at: str,
) -> None:
    from app.ai_client import (
        answer_question_streaming, fact_check,
        text_to_speech_mp3, thinking_acknowledgement,
    )
    from app.context_pipeline import search_context
    from app.output_media import inject_audio, take_screenshot

    if agent.get("mode") == "proctor":
        return

    db = get_supabase_service()
    agent_id   = str(agent.get("id") or "")
    agent_name = str(agent.get("name") or "Briefed")
    voice_id   = str(agent.get("voice_id") or "en-US-Neural2-J")
    persona    = agent.get("persona_prompt")

    log.info("copilot_trigger",
             meeting_id=meeting_id, trigger=trigger_type,
             agent=agent_name, content_preview=content[:80])

    response_parts: list[str] = []

    try:
        # ── Screenshot ────────────────────────────────────────────────────
        if trigger_type == "screenshot":
            log.info("screenshot_requested", meeting_id=meeting_id)
            b64 = await take_screenshot(bot_id)
            screenshot_url: str | None = None
            if b64:
                try:
                    mres = db.table("meetings").select("user_id").eq("id", meeting_id).limit(1).execute()
                    uid = mres.data[0]["user_id"] if mres.data else None
                    if uid:
                        raw = base64.b64decode(b64)
                        path = f"{uid}/{meeting_id}/{uuid.uuid4().hex}.jpg"
                        db.storage.from_("meeting-screenshots").upload(
                            path, raw, file_options={"content-type": "image/jpeg"}
                        )
                        base = (get_settings().get("supabase_url") or "").rstrip("/")
                        screenshot_url = f"{base}/storage/v1/object/public/meeting-screenshots/{path}"
                        db.table("screenshots").insert({
                            "meeting_id": meeting_id, "storage_path": path,
                            "taken_at": spoken_at, "triggered_by": "voice",
                        }).execute()
                        log.info("screenshot_saved", meeting_id=meeting_id, path=path)
                except Exception as e:
                    log.exception("screenshot_upload_failed", meeting_id=meeting_id, error=str(e))
            reply = "Screenshot saved." if b64 else "Screenshot unavailable."
            mp3 = await text_to_speech_mp3(reply, voice_id)
            await inject_audio(bot_id, mp3)
            db.table("meeting_interactions").insert({
                "meeting_id": meeting_id, "interaction_type": "screenshot",
                "trigger_text": content, "response_text": reply,
                "screenshot_b64": None if screenshot_url else b64,
                "screenshot_url": screenshot_url, "spoken_at": spoken_at,
            }).execute()
            return

        # ── Q&A: full streaming pipeline ─────────────────────────────────
        if trigger_type == "qa":
            # Step 1: ACK + context fetch + transcript fetch — ALL in parallel
            log.debug("gather_start", meeting_id=meeting_id)
            t0 = time.perf_counter()
            ack_mp3, context_chunks, recent_transcript = await asyncio.gather(
                thinking_acknowledgement(voice_id),
                search_context(agent_id, content, top_k=3),
                _fetch_recent_transcript(db, meeting_id, limit=20),
            )
            log.info("gather_done",
                     meeting_id=meeting_id,
                     context_chunks=len(context_chunks),
                     elapsed_ms=int((time.perf_counter() - t0) * 1000))

            # Inject ACK audio (fast — cached + pooled connection)
            await inject_audio(bot_id, ack_mp3)

            # Step 2: stream Gemini → TTS → inject with playback gap
            # Key: Recall plays audio immediately on inject — no queue.
            # We must wait for the previous sentence to finish playing
            # before injecting the next one, or they overlap.
            sentence_n = 0
            last_inject_at: float = 0.0       # monotonic time when last inject returned
            last_audio_duration: float = 0.0   # estimated playback time of last sentence

            async for sentence in answer_question_streaming(
                question=content,
                context_chunks=context_chunks,
                transcript=recent_transcript,
                agent_name=agent_name,
                persona=persona,
                meeting_id=meeting_id,
            ):
                if not sentence.strip():
                    continue
                sentence_n += 1

                # TTS: convert sentence to MP3
                t_tts = time.perf_counter()
                mp3 = await text_to_speech_mp3(sentence, voice_id)
                tts_ms = int((time.perf_counter() - t_tts) * 1000)

                # Wait for previous sentence to finish PLAYING (not just injecting)
                # MP3 at 128kbps: duration ≈ bytes / 16000. Add 0.3s buffer.
                if last_inject_at > 0:
                    elapsed_since_inject = time.perf_counter() - last_inject_at
                    remaining_playback = last_audio_duration - elapsed_since_inject
                    if remaining_playback > 0:
                        log.debug("playback_wait",
                                  meeting_id=meeting_id, n=sentence_n,
                                  wait_s=round(remaining_playback, 2))
                        await asyncio.sleep(remaining_playback)

                # Inject audio
                t_inject = time.perf_counter()
                await inject_audio(bot_id, mp3)
                inject_ms = int((time.perf_counter() - t_inject) * 1000)

                # Track timing for next sentence's playback wait
                last_inject_at = time.perf_counter()
                last_audio_duration = len(mp3) / 16000.0 + 0.3  # MP3 128kbps estimate + buffer

                log.info("sentence_spoken",
                         meeting_id=meeting_id, n=sentence_n,
                         tts_ms=tts_ms, inject_ms=inject_ms,
                         audio_est_s=round(last_audio_duration, 1),
                         sentence_preview=sentence[:60])
                response_parts.append(sentence)

        # ── Fact-check ────────────────────────────────────────────────────
        elif trigger_type == "factcheck":
            if not agent.get("proactive_fact_check"):
                return
            context_chunks = await search_context(agent_id, content, top_k=4)
            result = await fact_check(content, context_chunks, agent_name)
            if not result.get("contradicts"):
                log.debug("factcheck_no_contradiction", meeting_id=meeting_id)
                return
            correction = result.get("correction") or "Actually, that doesn't seem right."
            log.info("factcheck_contradiction", meeting_id=meeting_id,
                     correction_preview=correction[:60])
            mp3 = await text_to_speech_mp3(correction, voice_id)
            await inject_audio(bot_id, mp3)
            response_parts = [correction]

        if response_parts:
            full = " ".join(response_parts)
            db.table("meeting_interactions").insert({
                "meeting_id": meeting_id,
                "interaction_type": trigger_type,
                "trigger_text": content,
                "response_text": full,
                "spoken_at": spoken_at,
            }).execute()
            log.info("interaction_saved",
                     meeting_id=meeting_id, trigger=trigger_type,
                     response_chars=len(full), sentences=len(response_parts))

    except Exception as e:
        log.exception("copilot_trigger_failed",
                      meeting_id=meeting_id, trigger=trigger_type, error=str(e))
    finally:
        _trigger_active.pop(meeting_id, None)


async def _inject_and_log(
    bot_id: str, mp3: bytes, meeting_id: str,
    sentence_n: int, sentence: str, t_start: float,
) -> None:
    """Inject audio and log timing. Used as a background task for pipelining."""
    from app.output_media import inject_audio
    try:
        await inject_audio(bot_id, mp3)
        inject_ms = int((time.perf_counter() - t_start) * 1000)
        log.info("sentence_injected",
                 meeting_id=meeting_id, n=sentence_n,
                 inject_ms=inject_ms,
                 sentence_preview=sentence[:60])
    except Exception as e:
        log.warning("sentence_inject_failed",
                    meeting_id=meeting_id, n=sentence_n, error=str(e))


async def _fetch_recent_transcript(
    db: Any, meeting_id: str, limit: int = 20
) -> str:
    lines_res = (
        db.table("transcript_lines")
        .select("speaker_name, content")
        .eq("meeting_id", meeting_id)
        .order("spoken_at", desc=True)
        .limit(limit)
        .execute()
    )
    return "\n".join(
        f"{r.get('speaker_name','?')}: {r['content']}"
        for r in reversed(lines_res.data or [])
    )


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict[str, object]:
    return {"ok": True, "service": "briefed-backend",
            "model": get_settings().get("live_qa_model", "gemini-2.5-pro")}


# ── Context management ────────────────────────────────────────────────────────

def _context_list_group_key(source_url: str) -> str:
    m = re.match(r"(https://github\.com/[^/]+/[^/]+)/blob/", source_url, re.IGNORECASE)
    return m.group(1) if m else source_url


@app.post("/api/agents/{agent_id}/context")
async def add_context(
    agent_id: str,
    body: IngestContextBody,
    user_id: Annotated[str, Depends(get_user_id)],
) -> dict[str, Any]:
    from app.context_pipeline import ingest_source
    db = get_supabase_service()
    ag = db.table("agents").select("id").eq("id", agent_id).eq("user_id", user_id).limit(1).execute()
    if not ag.data:
        raise HTTPException(status_code=404, detail="Agent not found")
    log.info("context_ingest_start", agent_id=agent_id,
             source_type=body.source_type, content_preview=body.content[:80])
    try:
        with log_timing(log, "ingest_source", agent_id=agent_id):
            result = await ingest_source(agent_id, body.source_type, body.content, body.label)
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    _agent_cache.pop(agent_id, None)
    log.info("context_ingest_done", agent_id=agent_id,
             chunks_added=result.get("chunks_added"))
    return result


@app.get("/api/agents/{agent_id}/context")
def list_context(
    agent_id: str,
    user_id: Annotated[str, Depends(get_user_id)],
) -> dict[str, Any]:
    db = get_supabase_service()
    ag = db.table("agents").select("id").eq("id", agent_id).eq("user_id", user_id).limit(1).execute()
    if not ag.data:
        raise HTTPException(status_code=404, detail="Agent not found")
    res = (
        db.table("context_chunks").select("id, source_url, content, created_at")
        .eq("agent_id", agent_id).order("created_at", desc=True).execute()
    )
    sources: dict[str, dict] = {}
    for row in res.data or []:
        url = row["source_url"]
        key = _context_list_group_key(url)
        if key not in sources:
            sources[key] = {"source_url": key, "chunk_count": 0, "last_added": row["created_at"]}
        entry = sources[key]
        entry["chunk_count"] += 1
        if row["created_at"] > entry["last_added"]:
            entry["last_added"] = row["created_at"]
    return {"sources": list(sources.values()), "total_chunks": len(res.data or [])}


@app.delete("/api/agents/{agent_id}/context")
def clear_context(
    agent_id: str,
    source_url: str | None = Query(None),
    user_id: Annotated[str, Depends(get_user_id)] = None,
) -> dict[str, Any]:
    db = get_supabase_service()
    ag = db.table("agents").select("id").eq("id", agent_id).eq("user_id", user_id).limit(1).execute()
    if not ag.data:
        raise HTTPException(status_code=404, detail="Agent not found")
    q = db.table("context_chunks").delete().eq("agent_id", agent_id)
    if source_url:
        from app.github_ingest import parse_github_repo_url
        su = source_url.strip()
        ref = parse_github_repo_url(su)
        if ref:
            prefix = f"https://github.com/{ref.owner}/{ref.repo}/blob/"
            q = q.like("source_url", f"{prefix}%")
        else:
            blob_m = re.match(r"https://github\.com/([^/]+)/([^/]+)/blob/", su, re.IGNORECASE)
            if blob_m:
                q = q.like("source_url", f"https://github.com/{blob_m.group(1)}/{blob_m.group(2)}/blob/%")
            else:
                q = q.eq("source_url", su)
    q.execute()
    _agent_cache.pop(agent_id, None)
    log.info("context_cleared", agent_id=agent_id, source_url=source_url)
    return {"deleted": True}


# ── Meetings ──────────────────────────────────────────────────────────────────

@app.post("/api/meetings/start")
async def start_meeting(
    body: StartMeetingBody,
    user_id: Annotated[str, Depends(get_user_id)],
) -> dict[str, str]:
    if not body.join_now and not body.join_at:
        raise HTTPException(status_code=400, detail="join_at required when join_now is false")
    db = get_supabase_service()
    ag_res = (
        db.table("agents").select("*")
        .eq("id", body.agent_id).eq("user_id", user_id).limit(1).execute()
    )
    if not ag_res.data:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent = ag_res.data[0]
    meeting_row_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    s = get_settings()
    use_output_media = bool(s.get("cartesia_api_key") and s.get("bot_page_url"))
    copilot_mode = "output_media" if use_output_media else "output_audio"

    db.table("meetings").insert({
        "id": meeting_row_id, "user_id": user_id, "agent_id": body.agent_id,
        "meeting_link": body.meeting_link.strip(), "bot_id": None,
        "status": "scheduled", "copilot_mode": copilot_mode,
        "scheduled_at": body.join_at if not body.join_now else None,
        "updated_at": now,
    }).execute()
    public = _public_base()
    realtime_url = f"{public}/api/webhooks/recall/realtime?meeting_id={meeting_row_id}"
    bot_name = (agent.get("name") or "Briefed").strip()[:100]
    voice_id = str(agent.get("voice_id") or "f786b574-daa5-4673-aa0c-cbe3e8534c02")
    log.info("start_meeting", meeting_id=meeting_row_id,
             agent=bot_name, link=body.meeting_link[:60],
             copilot_mode=copilot_mode)
    payload: dict[str, Any] = {
        "meeting_url": body.meeting_link.strip(),
        "bot_name": bot_name,
        "metadata": {"meeting_id": meeting_row_id},
        "recording_config": {
            "transcript": {"provider": {"recallai_streaming": {
                "language_code": "en", "mode": "prioritize_low_latency"
            }}},
            "video_mixed_mp4": {}, "audio_mixed_mp3": {},
            "realtime_endpoints": [
                {"type": "webhook", "url": realtime_url, "events": ["transcript.data"]}
            ],
        },
        "automatic_leave": {
            "waiting_room_timeout": 600,
            "everyone_left_timeout": {"timeout": 120},
            "in_call_recording_timeout": 14400,
            "recording_permission_denied_timeout": 60,
        },
        "chat": {"on_bot_join": {
            "send_to": "everyone", "message": _bot_message_from_agent(agent)
        }},
    }
    if use_output_media:
        # Output Media: bot renders a webpage that handles TTS client-side
        backend_ws = public.replace("https://", "wss://").replace("http://", "ws://")
        from urllib.parse import urlencode
        import time as _time
        page_params = urlencode({
            "meeting_id": meeting_row_id,
            "agent_id": body.agent_id,
            "backend_ws": backend_ws,
            "cartesia_key": s["cartesia_api_key"],
            "agent_name": bot_name,
            "voice_id": voice_id,
            "_v": str(int(_time.time())),  # cache-bust
        })
        payload["bot_variant"] = "web_4_core"
        payload["output_media"] = {
            "camera": {
                "kind": "webpage",
                "config": {"url": f"{s['bot_page_url']}?{page_params}"},
            }
        }
        log.info("output_media_configured", meeting_id=meeting_row_id,
                 bot_page=s["bot_page_url"])
    else:
        # Legacy: output_audio with bootstrap MP3
        payload["automatic_audio_output"] = {
            "in_call_recording": {"data": {"kind": "mp3", "b64_data": copilot_bootstrap_mp3_b64()}}
        }
        img = agent.get("bot_image_url")
        if isinstance(img, str) and img.strip():
            try:
                b64 = await recall.fetch_image_b64_for_video(img.strip())
                if b64:
                    payload["automatic_video_output"] = {
                        "in_call_recording": {"kind": "jpeg", "b64_data": b64}
                    }
            except Exception:
                log.warning("bot_image_fetch_failed", agent_id=body.agent_id)

    if not body.join_now and body.join_at:
        payload["join_at"] = body.join_at
    try:
        with log_timing(log, "recall_create_bot", meeting_id=meeting_row_id):
            out = await recall.create_bot(payload)
    except Exception as e:
        log.exception("recall_create_bot_failed", meeting_id=meeting_row_id, error=str(e))
        db.table("meetings").update({"status": "failed", "updated_at": now}).eq("id", meeting_row_id).execute()
        raise HTTPException(status_code=502, detail=f"Recall.ai error: {e!s}") from e
    bot_id = out.get("id")
    if not bot_id:
        db.table("meetings").update({"status": "failed", "updated_at": now}).eq("id", meeting_row_id).execute()
        raise HTTPException(status_code=502, detail="Recall.ai did not return bot id")
    db.table("meetings").update({
        "bot_id": str(bot_id), "status": "joining",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", meeting_row_id).execute()
    log.info("meeting_started", meeting_id=meeting_row_id, bot_id=bot_id)
    return {"meeting_id": meeting_row_id, "bot_id": str(bot_id)}


@app.get("/api/meetings/{meeting_id}")
def get_meeting(
    meeting_id: str,
    user_id: Annotated[str, Depends(get_user_id)],
) -> dict[str, Any]:
    db = get_supabase_service()
    m_res = (
        db.table("meetings").select("*")
        .eq("id", meeting_id).eq("user_id", user_id).limit(1).execute()
    )
    if not m_res.data:
        raise HTTPException(status_code=404, detail="Meeting not found")
    meeting = m_res.data[0]
    lines_res = (
        db.table("transcript_lines").select("*")
        .eq("meeting_id", meeting_id).order("spoken_at").execute()
    )
    meeting["transcript_lines"] = lines_res.data or []
    return meeting


@app.get("/api/meetings/{meeting_id}/interactions")
def get_interactions(
    meeting_id: str,
    user_id: Annotated[str, Depends(get_user_id)],
) -> dict[str, Any]:
    db = get_supabase_service()
    m = db.table("meetings").select("id").eq("id", meeting_id).eq("user_id", user_id).limit(1).execute()
    if not m.data:
        raise HTTPException(status_code=404, detail="Meeting not found")
    res = (
        db.table("meeting_interactions")
        .select("id, interaction_type, trigger_text, response_text, spoken_at, created_at, screenshot_url, audio_url")
        .eq("meeting_id", meeting_id).order("spoken_at").execute()
    )
    return {"interactions": res.data or []}


@app.post("/api/agents/{agent_id}/ask")
async def ask_agent(
    agent_id: str,
    body: AskBody,
    user_id: Annotated[str, Depends(get_user_id)],
) -> dict[str, Any]:
    from app.ai_client import answer_question
    from app.context_pipeline import search_context
    db = get_supabase_service()
    ag = db.table("agents").select("*").eq("id", agent_id).eq("user_id", user_id).limit(1).execute()
    if not ag.data:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent = ag.data[0]
    transcript = None
    if body.meeting_id:
        lines = (
            db.table("transcript_lines").select("speaker_name, content")
            .eq("meeting_id", body.meeting_id).order("spoken_at").execute()
        )
        transcript = "\n".join(
            f"{r.get('speaker_name','?')}: {r['content']}" for r in (lines.data or [])
        )
    log.info("ask_agent", agent_id=agent_id, question=body.question[:80])
    with log_timing(log, "ask_agent_full", agent_id=agent_id):
        context_chunks = await search_context(agent_id, body.question, top_k=6)
        answer = await answer_question(
            question=body.question,
            context_chunks=context_chunks,
            transcript=transcript,
            agent_name=agent.get("name") or "Briefed",
            persona=agent.get("persona_prompt"),
        )
    return {"answer": answer, "context_chunks_used": len(context_chunks)}


# ─── WebSocket: copilot streaming for Output Media ──────────────────────────

@app.websocket("/ws/copilot/{meeting_id}")
async def ws_copilot(websocket: WebSocket, meeting_id: str) -> None:
    """
    WebSocket endpoint for the Output Media bot page.
    Bot page handles trigger detection + visuals; backend does TTS + audio
    injection via Recall API (bypasses Chrome audio capture = no static).
    Protocol:
      → {"type":"trigger", "question":"...", "agent_id":"..."}
      ← {"type":"token", "text":"..."} per sentence (for visual display)
      ← {"type":"done"}
      → {"type":"interrupt"} to cancel mid-stream
    """
    from app.ai_client import answer_question_streaming, text_to_speech_mp3
    from app.context_pipeline import search_context
    from app.output_media import inject_audio

    await websocket.accept()
    db = get_supabase_service()

    # Validate meeting and get bot_id for audio injection
    m_res = (
        db.table("meetings")
        .select("status, agent_id, bot_id")
        .eq("id", meeting_id).limit(1).execute()
    )
    if not m_res.data or m_res.data[0].get("status") not in ("in_meeting", "joining"):
        await websocket.close(code=4004, reason="Meeting not found or not active")
        return

    bot_id = m_res.data[0].get("bot_id") or ""

    interrupted = False

    try:
        while True:
            raw = await websocket.receive_json()
            msg_type = raw.get("type")

            if msg_type == "interrupt":
                interrupted = True
                continue

            if msg_type != "trigger":
                continue

            question = str(raw.get("question", "")).strip()
            agent_id = str(raw.get("agent_id", "")).strip()
            if not question or not agent_id:
                await websocket.send_json({"type": "error", "message": "Missing question or agent_id"})
                continue

            # Load agent
            agent = _get_cached_agent(agent_id)
            if agent is None:
                ag_res = db.table("agents").select("*").eq("id", agent_id).limit(1).execute()
                if not ag_res.data:
                    await websocket.send_json({"type": "error", "message": "Agent not found"})
                    continue
                agent = ag_res.data[0]
                _set_cached_agent(agent_id, agent)

            agent_name = str(agent.get("name") or "Briefed")
            persona = agent.get("persona_prompt")
            raw_voice = str(agent.get("voice_id") or "")
            # Google Cloud TTS voices look like "en-US-Neural2-J";
            # Cartesia UUIDs look like "f786b574-...". Detect and fallback.
            if raw_voice and "-" in raw_voice and not raw_voice.startswith("en-"):
                voice_id = "en-US-Neural2-J"  # default Google TTS voice
            else:
                voice_id = raw_voice or "en-US-Neural2-J"
            interrupted = False

            # Parallel: context search + recent transcript
            t0 = time.perf_counter()
            context_chunks, recent_transcript = await asyncio.gather(
                search_context(agent_id, question, top_k=3),
                _fetch_recent_transcript(db, meeting_id, limit=20),
            )
            log.info("ws_gather_done",
                     meeting_id=meeting_id,
                     context_chunks=len(context_chunks),
                     elapsed_ms=int((time.perf_counter() - t0) * 1000))

            # Stream Gemini → collect all sentences → single TTS + inject
            # Per-sentence injection caused overlap because MP3 duration
            # estimation is unreliable. One TTS call = one continuous
            # audio block = zero overlap, guaranteed.
            response_parts: list[str] = []

            async for sentence in answer_question_streaming(
                question=question,
                context_chunks=context_chunks,
                transcript=recent_transcript,
                agent_name=agent_name,
                persona=persona,
                meeting_id=meeting_id,
            ):
                if interrupted:
                    log.info("ws_interrupted", meeting_id=meeting_id)
                    break
                if not sentence.strip():
                    continue

                # Send text to bot page for visual display (streams live)
                await websocket.send_json({"type": "token", "text": sentence})
                response_parts.append(sentence)

            # TTS the full response as one block → inject once
            if response_parts and not interrupted and bot_id:
                full_text = " ".join(response_parts)
                try:
                    mp3 = await text_to_speech_mp3(full_text, voice_id)
                    await inject_audio(bot_id, mp3)
                    log.info("ws_audio_injected",
                             meeting_id=meeting_id,
                             chars=len(full_text),
                             mp3_kb=round(len(mp3) / 1024, 1))
                except Exception as tts_err:
                    log.warning("ws_tts_error", meeting_id=meeting_id,
                                error=str(tts_err)[:100])

            await websocket.send_json({"type": "done"})

            # Save interaction
            if response_parts:
                full = " ".join(response_parts)
                db.table("meeting_interactions").insert({
                    "meeting_id": meeting_id,
                    "interaction_type": "qa",
                    "trigger_text": question,
                    "response_text": full,
                    "spoken_at": datetime.now(timezone.utc).isoformat(),
                }).execute()
                log.info("ws_interaction_saved",
                         meeting_id=meeting_id,
                         response_chars=len(full),
                         sentences=len(response_parts))

    except WebSocketDisconnect:
        log.info("ws_copilot_disconnected", meeting_id=meeting_id)
    except Exception as e:
        log.exception("ws_copilot_error", meeting_id=meeting_id, error=str(e))


# ─── Bot page debug log receiver ─────────────────────────────────────────────

@app.post("/api/bot-debug")
async def bot_debug(request: Request) -> dict[str, str]:
    """Receives debug logs from the bot page running inside Recall's headless Chrome."""
    try:
        # Try JSON first, fall back to parsing raw text body (no-cors sends text/plain)
        try:
            body = await request.json()
        except Exception:
            raw = (await request.body()).decode("utf-8", errors="replace")
            try:
                body = json.loads(raw)
            except Exception:
                body = {"msg": raw[:500], "meeting_id": "?"}
        msg = body.get("msg", "")
        meeting_id = body.get("meeting_id", "?")
        log.info("BOT_PAGE", meeting_id=meeting_id, msg=str(msg)[:500])
    except Exception:
        pass
    return {"ok": "true"}


# ─── Webhooks ─────────────────────────────────────────────────────────────────

def _parse_recall_bot_webhook(body: dict[str, Any]) -> tuple[str | None, str | None]:
    b = body
    if b.get("type") == "message" and isinstance(b.get("data"), dict):
        inner = b["data"]
        if inner.get("event"):
            b = inner
    event = b.get("event")
    d = b.get("data")
    bot_id = None
    if isinstance(d, dict):
        bot_id = (d.get("bot") or {}).get("id")
    return (str(event) if event else None, str(bot_id) if bot_id else None)


def _extract_realtime_transcript(
    body: dict[str, Any],
) -> tuple[str | None, str, str, list[Any] | None]:
    d = body.get("data")
    if not isinstance(d, dict):
        return None, "", "Unknown", None
    bot_id = (d.get("bot") or {}).get("id")
    inner = d.get("data")
    if not isinstance(inner, dict):
        return (str(bot_id) if bot_id else None), "", "Unknown", None
    words = inner.get("words") or []
    texts = [str(w["text"]) for w in words if isinstance(w, dict) and w.get("text")]
    text = " ".join(texts).strip()
    speaker = (inner.get("participant") or {}).get("name") or "Unknown"
    return (
        str(bot_id) if bot_id else None, text,
        str(speaker)[:500], words if isinstance(words, list) else None,
    )


@app.post("/api/webhooks/recall/bot-status")
async def recall_bot_status(
    request: Request, body: dict[str, Any], background_tasks: BackgroundTasks,
) -> dict[str, str]:
    if not _webhook_secret_ok(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    event, bot_id = _parse_recall_bot_webhook(body)
    if not bot_id:
        return {"ok": "true"}
    try:
        db = get_supabase_service()
    except RuntimeError:
        return {"ok": "true"}
    res = db.table("meetings").select("id").eq("bot_id", bot_id).limit(1).execute()
    if not res.data:
        log.warning("bot_status_unknown_bot", bot_id=bot_id, event=event)
        return {"ok": "true"}
    meeting_id = res.data[0]["id"]
    now = datetime.now(timezone.utc).isoformat()
    status_map = {
        "bot.joining_call":          {"status": "joining",    "updated_at": now},
        "bot.in_waiting_room":       {"status": "joining",    "updated_at": now},
        "bot.in_call_not_recording": {"status": "joining",    "updated_at": now},
        "bot.in_call_recording":     {"status": "in_meeting", "joined_at": now, "updated_at": now},
        "bot.call_ended":            {"status": "processing", "ended_at": now,  "updated_at": now},
        "bot.fatal":                 {"status": "failed",     "updated_at": now},
    }
    if event in status_map:
        db.table("meetings").update(status_map[event]).eq("id", meeting_id).execute()
        log.info("bot_status_updated", meeting_id=meeting_id, event=event)
    if event == "bot.done":
        db.table("meetings").update({"status": "processing", "updated_at": now}).eq("id", meeting_id).execute()
        background_tasks.add_task(finalize_meeting, bot_id)
    elif event in ("recording.done", "video_mixed.done", "audio_mixed.done"):
        background_tasks.add_task(refresh_recall_media_urls, bot_id)
    return {"ok": "true"}


@app.post("/api/webhooks/recall/realtime")
@app.post("/api/webhooks/recall/realtime/")
async def recall_realtime(
    request: Request, background_tasks: BackgroundTasks,
    meeting_id: str | None = Query(None),
) -> dict[str, str]:
    if not _webhook_secret_ok(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    if body.get("event") != "transcript.data":
        return {"ok": "true"}
    background_tasks.add_task(_handle_realtime_transcript, body, meeting_id)
    return {"ok": "true"}


async def _handle_realtime_transcript(body: dict[str, Any], meeting_id: str | None) -> None:
    try:
        db = get_supabase_service()
    except RuntimeError:
        return
    bot_id, text, speaker, words_payload = _extract_realtime_transcript(body)
    resolved_id: str | None = meeting_id
    if not resolved_id and bot_id:
        res = db.table("meetings").select("id").eq("bot_id", bot_id).limit(1).execute()
        if res.data:
            resolved_id = res.data[0]["id"]
    if not resolved_id or not text:
        return

    # Parse timestamp
    inner = (body.get("data") or {}).get("data") if isinstance(body.get("data"), dict) else {}
    ts_str = None
    if isinstance(inner, dict):
        w0 = (inner.get("words") or [None])[0]
        if isinstance(w0, dict):
            st = w0.get("start_timestamp") or {}
            if isinstance(st, dict):
                ts_str = st.get("absolute")
    try:
        spoken_at = (
            datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
            if isinstance(ts_str, str) and ts_str
            else datetime.now(timezone.utc)
        )
    except Exception:
        spoken_at = datetime.now(timezone.utc)

    # Store transcript line
    db.table("transcript_lines").insert({
        "meeting_id": resolved_id, "speaker_name": speaker,
        "content": str(text), "spoken_at": spoken_at.isoformat(),
        "words": words_payload,
    }).execute()
    log.debug("transcript_line_stored",
              meeting_id=resolved_id, speaker=speaker, text_preview=text[:60])

    # Check meeting status
    m_res = db.table("meetings").select("status, agent_id, bot_id, copilot_mode").eq("id", resolved_id).limit(1).execute()
    if not m_res.data or m_res.data[0].get("status") != "in_meeting":
        return
    meeting_row = m_res.data[0]

    # Output Media: Q&A triggers are handled client-side by the bot page.
    # But screenshot and fact-check still need webhook-side detection.
    is_output_media = meeting_row.get("copilot_mode") == "output_media"

    agent_id = meeting_row.get("agent_id")
    if not agent_id:
        return

    # Agent from cache
    agent = _get_cached_agent(agent_id)
    if agent is None:
        ag_res = db.table("agents").select("*").eq("id", agent_id).limit(1).execute()
        if not ag_res.data:
            return
        agent = ag_res.data[0]
        _set_cached_agent(agent_id, agent)

    agent_name = str(agent.get("name") or "Briefed")
    if agent.get("mode") == "proctor" or speaker.lower() == agent_name.lower():
        return

    screenshot_on = bool(agent.get("screenshot_on_request", True))
    trigger_type, trigger_content = _detect_trigger(text, agent_name, screenshot_on=screenshot_on)

    # In output_media mode, Q&A is handled client-side by the bot page.
    # Only allow screenshot and factcheck triggers through the webhook.
    if is_output_media and trigger_type == "qa":
        trigger_type = None
        trigger_content = None

    if not trigger_type or not trigger_content:
        if await _should_run_factcheck(resolved_id, text, agent):
            trigger_type = "factcheck"
            trigger_content = text
        else:
            return

    if trigger_type == "qa":
        from app.rate_limit import check_qa_cooldown
        if not await check_qa_cooldown(resolved_id):
            log.debug("qa_cooldown_skip", meeting_id=resolved_id)
            return
        if _trigger_active.get(resolved_id):
            log.debug("trigger_inflight_skip", meeting_id=resolved_id)
            return
        _trigger_active[resolved_id] = True
        log.info("trigger_detected",
                 meeting_id=resolved_id, trigger=trigger_type,
                 speaker=speaker, content=str(trigger_content)[:80])

    actual_bot_id = meeting_row.get("bot_id") or bot_id or ""
    # IMPORTANT: await directly — do NOT use asyncio.create_task().
    # Cloud Run kills instances when no requests are active. Since
    # _handle_realtime_transcript runs via FastAPI BackgroundTasks,
    # awaiting here keeps the request lifecycle alive until completion.
    await process_copilot_trigger(
        meeting_id=resolved_id,
        bot_id=str(actual_bot_id),
        trigger_type=trigger_type,
        content=str(trigger_content),
        agent=agent,
        spoken_at=spoken_at.isoformat(),
    )
