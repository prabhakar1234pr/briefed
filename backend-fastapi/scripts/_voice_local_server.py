"""
Local voice-pipeline server for end-to-end testing WITHOUT a real meeting / DB.

Loads backend-fastapi/.env (real Deepgram / ElevenLabs / Vertex creds), stubs the
two DB lookups the WebSocket handlers need (get_meeting / get_agent) with an
in-memory fake meeting + agent, then runs the real FastAPI app on :8000.

The actual audio pipeline (RecallAudioInputTransport → VAD → Deepgram STT →
TurnGate → Gemini → ElevenLabs TTS → BotPageOutputTransport) runs completely
untouched — only the persistence lookups are faked. Drive it with
scripts/voice_e2e_test.py.

    cd backend-fastapi && .venv/Scripts/python.exe scripts/_voice_local_server.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # backend-fastapi/
sys.path.insert(0, str(ROOT))  # so `import app...` resolves when run from scripts/
os.chdir(ROOT)  # GOOGLE_APPLICATION_CREDENTIALS=./gcp-sa-key.json is relative

# ── Load .env into the environment (config.py reads os.getenv directly) ───────
envf = ROOT / ".env"
for raw in envf.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    v = v.strip().strip('"').strip("'")
    os.environ.setdefault(k.strip(), v)

# Make sure we NEVER accidentally hit a real DB from this process.
for db_var in ("CLOUD_SQL_CONNECTION_NAME", "DB_HOST", "DB_PASS"):
    os.environ.pop(db_var, None)
os.environ.setdefault("LOG_LEVEL", "DEBUG")

# Test identifiers shared with the client.
MEETING_ID = os.environ.get("TEST_MEETING_ID", "e2e-test-meeting")
TOKEN = os.environ.get("TEST_TOKEN", "e2e-test-token")
AGENT_ID = "e2e-test-agent"
AGENT_NAME = os.environ.get("TEST_AGENT_NAME", "Bora")

# ── Stub the persistence layer the WS handlers call ───────────────────────────
import app.repo as repo  # noqa: E402


def _fake_get_meeting(meeting_id, user_id=None):
    return {
        "id": meeting_id,
        "agent_id": AGENT_ID,
        "bridge_token": TOKEN,
        "bot_id": "test-bot-id",
        "copilot_mode": "v2",
        "status": "in_call",
    }


def _fake_get_agent(agent_id, user_id=None):
    return {
        "id": AGENT_ID,
        "name": AGENT_NAME,
        # Short, factual persona so answers are easy to sanity-check.
        "persona": "You are a concise, friendly meeting assistant.",
        "voice_id": None,  # → falls back to settings.elevenlabs_default_voice
    }


repo.get_meeting = _fake_get_meeting
repo.get_agent = _fake_get_agent

# Intercept Recall audio injection → save the mp3 ElevenLabs produced so the test
# can verify it's clean (instead of POSTing to a real bot). tts_to_mp3 still runs
# for real, so this exercises the full native-output path end to end.
import tempfile, time  # noqa: E402
import app.pipeline.recall_output as _ro  # noqa: E402

_INJECT_DIR = Path(tempfile.gettempdir())


async def _fake_inject_audio(bot_id, mp3_bytes):
    p = _INJECT_DIR / f"native_inject_{int(time.time() * 1000)}.mp3"
    p.write_bytes(mp3_bytes)
    print(f"[native-inject] bot={bot_id} saved {p} ({len(mp3_bytes)} bytes)")
    return True


_ro.inject_audio = _fake_inject_audio


def _warm_imports() -> None:
    """Pre-import the heavy pipeline deps so the FIRST pipeline build isn't a
    ~10s cold start (lazy imports + model load). In a real meeting that cost is
    paid during the bot's join phase before anyone talks; in the test the client
    starts streaming immediately, so we eliminate it here."""
    try:
        import time as _t
        t0 = _t.time()
        from pipecat.audio.vad.silero import SileroVADAnalyzer  # noqa: F401
        from pipecat.pipeline.pipeline import Pipeline  # noqa: F401
        from pipecat.pipeline.runner import PipelineRunner  # noqa: F401
        from pipecat.pipeline.task import PipelineTask  # noqa: F401
        from pipecat.services.deepgram.stt import DeepgramSTTService  # noqa: F401
        from pipecat.services.elevenlabs.tts import ElevenLabsTTSService  # noqa: F401
        from pipecat.services.google.vertex.llm import GoogleVertexLLMService  # noqa: F401
        # Touch the VAD model load too (the slow part of build).
        SileroVADAnalyzer()
        print(f"[local-server] warmed pipeline imports in {_t.time()-t0:.1f}s")
    except Exception as e:  # pragma: no cover - warmup is best-effort
        print(f"[local-server] warmup skipped: {e}")


if __name__ == "__main__":
    _warm_imports()
    import uvicorn

    print(f"[local-server] meeting_id={MEETING_ID} token={TOKEN} agent={AGENT_NAME}")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, log_level="info")
