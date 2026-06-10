"""
Inbound meeting-audio websocket — the endpoint Recall connects to.

Recall connects (as a CLIENT) to this server endpoint and streams the mixed
meeting audio in real time. We decode each message to raw PCM16 (16 kHz mono
S16LE) and feed it into the meeting's Pipecat pipeline via the session's input
transport.

URL (registered in start_meeting): wss://<backend>/ws/recall-audio/{meeting_id}/?token=<bridge_token>
  - Trailing slash BEFORE the query params is required by Recall (else HTTP 400).
  - `token` is the per-meeting bridge_token, the same one the bot-page uses.

⚠️ Payload shape is the #1 unknown: the recall-ai skill documents
`audio_mixed_raw.data` as BINARY S16LE frames; other Recall docs show a JSON
envelope carrying a base64 buffer. `decode_recall_audio` handles BOTH and logs
`recall_audio_unknown_shape` once if neither matches, so we can pin the real
shape from a live run without a redeploy.
"""
from __future__ import annotations

import base64
import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from pipecat.transports.base_transport import TransportParams

from app import repo
from app.logger import get_logger
from app.pipeline.session import get_or_create
from app.pipeline.transports import RecallAudioInputTransport

log = get_logger(__name__)

router = APIRouter()

# Log the unknown-shape diagnostic at most once per process to avoid log spam.
_warned_unknown_shape = False


def decode_recall_audio(message: bytes | str) -> list[bytes]:
    """Decode a Recall realtime message into zero or more raw PCM16 buffers."""
    global _warned_unknown_shape

    # Binary frame → already raw PCM16 16k mono.
    if isinstance(message, (bytes, bytearray)):
        return [bytes(message)] if message else []

    # Text frame → JSON envelope.
    try:
        body = json.loads(message)
    except (ValueError, TypeError):
        return []
    if not isinstance(body, dict):
        return []

    # Skip the v1.10-style handshake message (no event, just protocol metadata).
    event = body.get("event")
    if not event and ("protocol_version" in body or "bot_id" in body):
        return []

    if event not in ("audio_mixed_raw.data", "audio_separate_raw.data"):
        # Not an audio event we handle (participant events, transcripts, etc.).
        if event is None:
            _maybe_warn_unknown(body)
        return []

    # Find the base64 buffer across the known nesting variants.
    data = body.get("data") or {}
    inner = data.get("data") if isinstance(data.get("data"), dict) else {}
    b64 = (
        inner.get("buffer")
        or data.get("buffer")
        or inner.get("b64_data")
        or data.get("b64_data")
    )
    if not isinstance(b64, str) or not b64:
        _maybe_warn_unknown(body)
        return []
    try:
        return [base64.b64decode(b64)]
    except Exception:
        return []


def _maybe_warn_unknown(body: dict) -> None:
    global _warned_unknown_shape
    if _warned_unknown_shape:
        return
    _warned_unknown_shape = True
    keys = sorted(body.keys())
    data_keys = sorted(body["data"].keys()) if isinstance(body.get("data"), dict) else None
    log.warning("recall_audio_unknown_shape", top_level_keys=keys, data_keys=data_keys)


@router.websocket("/ws/recall-audio/{meeting_id}/")
async def recall_audio(
    websocket: WebSocket,
    meeting_id: str,
    token: str = Query(...),
):
    # ── Verify token & load meeting/agent (same pattern as bot_bridge) ──────
    try:
        meeting = repo.get_meeting(meeting_id)
    except Exception as e:
        log.warning("recall_audio_meeting_lookup_failed", meeting_id=meeting_id, error=str(e)[:160])
        await websocket.close(code=1008)
        return
    if not meeting or meeting.get("bridge_token") != token:
        log.warning("recall_audio_token_mismatch", meeting_id=meeting_id)
        await websocket.close(code=1008)
        return
    agent = repo.get_agent(meeting["agent_id"])
    if not agent:
        log.warning("recall_audio_agent_missing", meeting_id=meeting_id)
        await websocket.close(code=1008)
        return

    await websocket.accept()
    log.info("recall_audio_connected", meeting_id=meeting_id)

    session = get_or_create(meeting_id, agent, bot_id=meeting.get("bot_id"))
    # Build the input transport standalone so meeting audio can start flowing
    # even before the bot-page (output socket) has connected. The session pairs
    # it with the bot-page output transport when both are present.
    input_transport = RecallAudioInputTransport(
        TransportParams(audio_in_enabled=True, audio_in_sample_rate=16000, audio_in_passthrough=True)
    )
    await session.attach_recall_input(input_transport)

    frames = 0
    try:
        async for message in _iter_ws(websocket):
            for pcm in decode_recall_audio(message):
                if not pcm:
                    continue
                await input_transport.feed_pcm(pcm)
                frames += 1
                if frames % 250 == 0:  # ~5s of 20ms frames
                    log.debug("recall_audio_frame", meeting_id=meeting_id, n=frames, last_bytes=len(pcm))
    except WebSocketDisconnect:
        log.info("recall_audio_disconnected", meeting_id=meeting_id, frames=frames)
    except Exception as e:
        log.warning("recall_audio_error", meeting_id=meeting_id, error=str(e)[:200])
    finally:
        await session.on_recall_drop()


async def _iter_ws(websocket: WebSocket):
    """Yield each inbound message as bytes or str until the socket disconnects."""
    while True:
        msg = await websocket.receive()
        if msg.get("type") == "websocket.disconnect":
            raise WebSocketDisconnect()
        if msg.get("bytes") is not None:
            yield msg["bytes"]
        elif msg.get("text") is not None:
            yield msg["text"]
