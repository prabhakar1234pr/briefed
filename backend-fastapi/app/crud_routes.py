"""CRUD + read endpoints the frontend used to hit Supabase directly for.

After the Cloud SQL migration the frontend no longer talks to a database; it
calls these backend endpoints (with the Firebase ID token as a Bearer). Auth is
enforced here via get_user_id + owner-scoped repo queries.

  Agents:
    GET    /api/agents               list current user's agents
    POST   /api/agents               create an agent
    GET    /api/agents/{id}          get one (owner-scoped)
    PATCH  /api/agents/{id}          update one
    DELETE /api/agents/{id}          delete one (cascades to meetings/chunks)

  Meetings:
    GET    /api/meetings             list current user's meetings
    DELETE /api/meetings/{id}        delete one

  Users:
    POST   /api/users/provision      upsert the current user's row (sign-in)

  Public:
    GET    /api/share/{meeting_id}   public meeting brief (UUID = share token)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import repo
from app.auth_deps import get_user_id
from app.logger import get_logger

log = get_logger(__name__)
router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Agents ───────────────────────────────────────────────────────────────────

class AgentUpsertBody(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    mode: str = Field(default="copilot", pattern="^(copilot|proctor)$")
    persona_prompt: str | None = None
    voice_id: str | None = None
    bot_image_url: str | None = None
    proactive_fact_check: bool = True
    screenshot_on_request: bool = True
    send_post_meeting_email: bool = True


class AgentPatchBody(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    mode: str | None = Field(default=None, pattern="^(copilot|proctor)$")
    persona_prompt: str | None = None
    voice_id: str | None = None
    bot_image_url: str | None = None
    proactive_fact_check: bool | None = None
    screenshot_on_request: bool | None = None
    send_post_meeting_email: bool | None = None


@router.get("/api/agents")
def list_agents(user_id: Annotated[str, Depends(get_user_id)]) -> dict[str, Any]:
    return {"agents": repo.list_agents(user_id)}


@router.post("/api/agents")
def create_agent(
    body: AgentUpsertBody,
    user_id: Annotated[str, Depends(get_user_id)],
) -> dict[str, Any]:
    agent = repo.insert_agent(user_id=user_id, fields=body.model_dump())
    log.info("agent_created", agent_id=agent.get("id"), user_id=user_id)
    return agent


@router.get("/api/agents/{agent_id}")
def get_agent(
    agent_id: str,
    user_id: Annotated[str, Depends(get_user_id)],
) -> dict[str, Any]:
    agent = repo.get_agent(agent_id, user_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/api/agents/{agent_id}")
def update_agent(
    agent_id: str,
    body: AgentPatchBody,
    user_id: Annotated[str, Depends(get_user_id)],
) -> dict[str, Any]:
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    fields["updated_at"] = _now()
    if not repo.update_agent(agent_id, user_id, fields):
        raise HTTPException(status_code=404, detail="Agent not found")
    return repo.get_agent(agent_id, user_id) or {}


@router.delete("/api/agents/{agent_id}")
def delete_agent(
    agent_id: str,
    user_id: Annotated[str, Depends(get_user_id)],
) -> dict[str, bool]:
    if not repo.get_agent(agent_id, user_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    repo.delete_agent(agent_id, user_id)  # FK cascade handles meetings/chunks
    log.info("agent_deleted", agent_id=agent_id, user_id=user_id)
    return {"ok": True}


# ─── Meetings ─────────────────────────────────────────────────────────────────

@router.get("/api/meetings")
def list_meetings(user_id: Annotated[str, Depends(get_user_id)]) -> dict[str, Any]:
    return {"meetings": repo.list_meetings(user_id, limit=50)}


@router.delete("/api/meetings/{meeting_id}")
def delete_meeting(
    meeting_id: str,
    user_id: Annotated[str, Depends(get_user_id)],
) -> dict[str, bool]:
    if not repo.get_meeting(meeting_id, user_id):
        raise HTTPException(status_code=404, detail="Meeting not found")
    repo.delete_meeting(meeting_id, user_id)
    return {"ok": True}


# ─── Users ────────────────────────────────────────────────────────────────────

class UserProvisionBody(BaseModel):
    email: str
    full_name: str | None = None
    avatar_url: str | None = None


@router.post("/api/users/provision")
def provision_user(
    body: UserProvisionBody,
    user_id: Annotated[str, Depends(get_user_id)],
) -> dict[str, Any]:
    """Upsert the authenticated user's row (called on sign-in)."""
    repo.upsert_user(
        id=user_id, email=body.email, full_name=body.full_name,
        avatar_url=body.avatar_url, updated_at=_now(),
    )
    return {"ok": True, "user": {"sub": user_id, "email": body.email, "name": body.full_name}}


# ─── Public share ─────────────────────────────────────────────────────────────

@router.get("/api/share/{meeting_id}")
def public_meeting_brief(meeting_id: str) -> dict[str, Any]:
    """Public meeting brief — no auth. The meeting UUID is the share token.

    Mirrors the data the old service-role share page assembled.
    """
    meeting = repo.get_meeting(meeting_id)  # no user scope: public
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    agent_name = None
    if meeting.get("agent_id"):
        ag = repo.get_agent(meeting["agent_id"])
        agent_name = ag.get("name") if ag else None

    # Only expose the fields the share page renders.
    public_meeting = {
        k: meeting.get(k) for k in (
            "id", "meeting_link", "status", "transcript_text", "audio_url",
            "video_url", "created_at", "agent_id", "summary", "action_items",
            "key_decisions",
        )
    }
    return {
        "meeting": public_meeting,
        "agent_name": agent_name,
        "transcript_lines": repo.list_transcript_lines(
            meeting_id, columns="id, speaker_name, content, spoken_at"
        ),
        "interactions": repo.list_interactions(meeting_id),
    }
