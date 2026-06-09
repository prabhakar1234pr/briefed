"""
FastAPI WebSocket endpoint that the bot-page connects to.

URL: wss://api.briefed.com/ws/bot-bridge/{meeting_id}?token=<bot_token>

Protocol (bidirectional, binary frames):
  - Bot-page → backend: PCM16 16kHz mono samples (from the meeting's audio track)
  - Backend → bot-page: PCM16 24kHz mono samples (TTS output, played into meeting)

JSON control messages (text frames):
  - {"type": "hello", "meeting_id": "..."}              (bot-page → backend on connect)
  - {"type": "bot_state", "speaking": true|false}        (backend → bot-page)

Token verification:
  - We mint a per-meeting bridge token when creating the bot.
  - Stored on the meetings row. Bot-page passes it as ?token=...
"""
from __future__ import annotations

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app import repo
from app.logger import get_logger
from app.pipeline.session import get_or_create

log = get_logger(__name__)

router = APIRouter()


@router.websocket("/ws/bot-bridge/{meeting_id}")
async def bot_bridge(
    websocket: WebSocket,
    meeting_id: str,
    token: str = Query(...),
):
    """
    Bot-page connects here on meeting start. We verify the bridge token,
    load the agent config, and spawn the Pipecat pipeline against this WS.
    """
    # ── Verify token & load meeting/agent ────────────────────────────────
    try:
        meeting = repo.get_meeting(meeting_id)
    except Exception as e:
        log.warning("bot_bridge_meeting_lookup_failed", meeting_id=meeting_id, error=str(e)[:160])
        await websocket.close(code=1008)
        return

    if not meeting or meeting.get("bridge_token") != token:
        log.warning("bot_bridge_token_mismatch", meeting_id=meeting_id)
        await websocket.close(code=1008)
        return

    agent_id = meeting["agent_id"]
    agent = repo.get_agent(agent_id)
    if not agent:
        log.warning("bot_bridge_agent_missing", meeting_id=meeting_id)
        await websocket.close(code=1008)
        return

    # ── Accept connection ────────────────────────────────────────────────
    await websocket.accept()
    log.info("bot_bridge_connected", meeting_id=meeting_id, agent=agent.get("name"))

    # ── Attach to the meeting session (output side) ──────────────────────
    # The session pairs this bot-page output socket with the Recall audio input
    # socket and starts the Pipecat pipeline once both are present. The bot-page
    # only carries OUTPUT (TTS bytes) + control messages now; meeting audio
    # arrives on the separate /ws/recall-audio endpoint.
    session = get_or_create(meeting_id, agent)
    await session.attach_bot_ws(websocket)

    # ── Hold the WS open so the bot-page stays connected ─────────────────
    # The bot-page sends no inbound frames we consume here; we just need to keep
    # the socket alive (and detect disconnect) while the pipeline writes to it.
    try:
        while True:
            msg = await websocket.receive()
            if msg.get("type") == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        log.info("bot_bridge_disconnected", meeting_id=meeting_id)
    except Exception as e:
        log.exception("bot_bridge_error", meeting_id=meeting_id, error=str(e)[:200])
    finally:
        await session.on_bot_ws_drop()
