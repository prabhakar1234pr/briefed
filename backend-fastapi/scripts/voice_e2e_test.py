"""
End-to-end voice-pipeline test (no real meeting needed).

Talks to the locally-running pipeline (scripts/_voice_local_server.py) over the
exact two WebSockets Recall uses:

  • OUTPUT  ws://127.0.0.1:8000/ws/bot-bridge/<mid>?token=...   (receive TTS PCM16 24k)
  • INPUT   ws://127.0.0.1:8000/ws/recall-audio/<mid>/?token=... (send meeting PCM16 16k)

It synthesizes a real spoken question (ElevenLabs, cached), streams it in 200ms
chunks at real time exactly like Recall's audio_mixed_raw, then captures the
bot's TTS reply and measures what actually matters:

  • onset latency  — question end → first TTS byte (perceived "thinking" time)
  • delivery ratio — wall-clock to deliver the reply ÷ the reply's audio length.
                     ~1.0 = real time (good). ~1.8 = the old pacing bug (audio is
                     sent at ~0.55× real time → the meeting hears choppy/static).
  • underruns      — replays the bot-page jitter-buffer scheduler over the real
                     arrival times and counts mid-reply starvation gaps.

Writes the reply to scripts/_out_24k.wav for listening / inspection.

    cd backend-fastapi && .venv/Scripts/python.exe scripts/voice_e2e_test.py
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import sys
import time
import wave
from pathlib import Path

import httpx
import websockets

try:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows cp1252 chokes on non-ASCII
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def _load_env() -> None:
    envf = ROOT / ".env"
    for raw in envf.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()

# Unique per run so each test gets a FRESH pipeline (the stub repo accepts any
# meeting_id with the shared token). Avoids reusing a half-torn-down session.
MID = os.environ.get("TEST_MEETING_ID") or f"e2e-{int(time.time())}"
TOKEN = os.environ.get("TEST_TOKEN", "e2e-test-token")
HOST = os.environ.get("TEST_HOST", "127.0.0.1:8000")
QUESTION = os.environ.get("TEST_QUESTION", "Bora, what is the capital of France?")
EL_VOICE = os.environ.get("TEST_VOICE", "21m00Tcm4TlvDq8ikWAM")  # ElevenLabs Rachel
IN_RATE = 16000
OUT_RATE = 24000
CHUNK_MS = 200
CHUNK_BYTES = IN_RATE * 2 * CHUNK_MS // 1000  # 6400 bytes = 200ms @16k mono S16

OUT_WAV = SCRIPTS / "_out_24k.wav"


# ─── 1. Synthesize the spoken question (cached) ───────────────────────────────
def synth_question_pcm() -> bytes:
    key = hashlib.sha1(f"{QUESTION}|{EL_VOICE}".encode()).hexdigest()[:10]
    cache = SCRIPTS / f"_q_{key}_16k.pcm"
    if cache.exists():
        return cache.read_bytes()
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        sys.exit("ELEVENLABS_API_KEY not in .env — cannot synthesize question")
    print(f"[synth] generating question audio: {QUESTION!r}")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{EL_VOICE}"
    r = httpx.post(
        url,
        params={"output_format": "pcm_16000"},
        headers={"xi-api-key": api_key, "content-type": "application/json"},
        json={"text": QUESTION, "model_id": "eleven_flash_v2_5"},
        timeout=60,
    )
    r.raise_for_status()
    pcm = r.content
    cache.write_bytes(pcm)
    print(f"[synth] {len(pcm)} bytes ({len(pcm)/2/IN_RATE:.2f}s) cached → {cache.name}")
    return pcm


# ─── 2. Drive the pipeline ────────────────────────────────────────────────────
async def run() -> dict:
    pcm = synth_question_pcm()
    out_url = f"ws://{HOST}/ws/bot-bridge/{MID}?token={TOKEN}"
    in_url = f"ws://{HOST}/ws/recall-audio/{MID}/?token={TOKEN}"

    recv_frames: list[tuple[float, bytes]] = []
    controls: list[tuple[float, str]] = []
    state = {"q_end": None, "done": asyncio.Event(), "first_audio": None}

    out_ws = await websockets.connect(out_url, max_size=None, ping_interval=None)
    in_ws = await websockets.connect(in_url, max_size=None, ping_interval=None)
    print(f"[ws] connected. streaming question ({len(pcm)/2/IN_RATE:.2f}s)…")

    async def recv_out():
        while True:
            try:
                msg = await asyncio.wait_for(out_ws.recv(), timeout=2.5)
            except asyncio.TimeoutError:
                if recv_frames:  # got the reply, then 2.5s of quiet → done
                    break
                continue
            except websockets.ConnectionClosed:
                break
            t = time.monotonic()
            if isinstance(msg, (bytes, bytearray)):
                if state["first_audio"] is None:
                    state["first_audio"] = t
                recv_frames.append((t, bytes(msg)))
            else:
                controls.append((t, msg))
                print(f"[ctrl] {msg}")

    async def send_in():
        # Lead silence so the pipeline (VAD/STT/LLM/TTS build) is fully ready
        # before the question — otherwise the opening words land mid cold-start.
        warmup_s = float(os.environ.get("TEST_WARMUP_S", "10.0"))
        silence0 = b"\x00" * CHUNK_BYTES
        for _ in range(int(warmup_s * 1000 / CHUNK_MS)):
            await in_ws.send(silence0)
            await asyncio.sleep(CHUNK_MS / 1000)
        # question at real time, exactly like Recall's 200ms audio_mixed_raw
        for i in range(0, len(pcm), CHUNK_BYTES):
            chunk = pcm[i:i + CHUNK_BYTES]
            if len(chunk) < CHUNK_BYTES:
                chunk = chunk + b"\x00" * (CHUNK_BYTES - len(chunk))
            await in_ws.send(chunk)
            await asyncio.sleep(CHUNK_MS / 1000)
        state["q_end"] = time.monotonic()
        print("[in] question sent; streaming trailing silence…")
        silence = b"\x00" * CHUNK_BYTES
        for _ in range(200):  # up to 40s of keep-alive silence
            if state["done"].is_set():
                break
            try:
                await in_ws.send(silence)
            except websockets.ConnectionClosed:
                break
            await asyncio.sleep(CHUNK_MS / 1000)

    recv_task = asyncio.create_task(recv_out())
    send_task = asyncio.create_task(send_in())
    # Cap must exceed the lead-silence (warmup) + question + response.
    warmup_s = float(os.environ.get("TEST_WARMUP_S", "10.0"))
    overall_timeout = warmup_s + 60
    try:
        await asyncio.wait_for(recv_task, timeout=overall_timeout)
    except asyncio.TimeoutError:
        recv_task.cancel()
    state["done"].set()
    send_task.cancel()
    for ws in (in_ws, out_ws):
        try:
            await ws.close()
        except Exception:
            pass

    return _report(recv_frames, controls, state)


# ─── 3. Metrics + report ──────────────────────────────────────────────────────
def _simulate_playback_underruns(frames: list[tuple[float, bytes]]) -> int:
    """Replay the bot-page scheduler (index.html playPcm16) over real arrivals."""
    JITTER_LEAD = 0.20
    if not frames:
        return 0
    ctx0 = frames[0][0]
    next_play = 0.0
    underruns = 0
    for t, b in frames:
        now = t - ctx0
        dur = (len(b) / 2) / OUT_RATE
        if next_play < now:
            if next_play > 0.0:  # fell behind mid-reply → audible gap
                underruns += 1
            start_at = now + JITTER_LEAD
        else:
            start_at = next_play
        next_play = start_at + dur
    return underruns


def _report(recv_frames, controls, state) -> dict:
    total_bytes = sum(len(b) for _, b in recv_frames)
    audio_secs = total_bytes / 2 / OUT_RATE
    res: dict = {
        "got_audio": bool(recv_frames),
        "frames": len(recv_frames),
        "audio_secs": round(audio_secs, 3),
        "controls": [c for _, c in controls],
    }
    if recv_frames:
        first_t = recv_frames[0][0]
        last_t = recv_frames[-1][0]
        delivery = last_t - first_t
        res["onset_latency_s"] = (
            round(first_t - state["q_end"], 3) if state["q_end"] else None
        )
        res["delivery_wallclock_s"] = round(delivery, 3)
        res["delivery_ratio"] = round(delivery / audio_secs, 3) if audio_secs else None
        gaps = [recv_frames[i][0] - recv_frames[i - 1][0] for i in range(1, len(recv_frames))]
        res["max_interframe_gap_s"] = round(max(gaps), 3) if gaps else 0.0
        res["mean_interframe_gap_ms"] = round(1000 * sum(gaps) / len(gaps), 1) if gaps else 0.0
        res["sim_playback_underruns"] = _simulate_playback_underruns(recv_frames)
        # write WAV
        with wave.open(str(OUT_WAV), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(OUT_RATE)
            w.writeframes(b"".join(b for _, b in recv_frames))
        res["wav"] = str(OUT_WAV)
    return res


def _verdict(r: dict) -> str:
    if not r["got_audio"]:
        return "FAIL: no TTS audio came back (turn gate didn't fire or STT/LLM/TTS broke)"
    issues = []
    if r.get("delivery_ratio") and r["delivery_ratio"] > 1.15:
        issues.append(
            f"delivery_ratio={r['delivery_ratio']} (>1.15 → sent slower than real time; "
            "meeting will hear choppy/stretched audio)"
        )
    if r.get("onset_latency_s") and r["onset_latency_s"] > 4.0:
        issues.append(f"onset_latency={r['onset_latency_s']}s (>4s feels laggy)")
    if r.get("sim_playback_underruns", 0) > 0:
        issues.append(f"{r['sim_playback_underruns']} simulated playback underruns (audible gaps)")
    if r.get("max_interframe_gap_s", 0) > 1.0:
        issues.append(f"max interframe gap {r['max_interframe_gap_s']}s")
    return "PASS: smooth + responsive" if not issues else "ISSUES:\n  - " + "\n  - ".join(issues)


if __name__ == "__main__":
    r = asyncio.run(run())
    print("\n==================== E2E VOICE REPORT ====================")
    for k, v in r.items():
        print(f"  {k}: {v}")
    print("----------------------------------------------------------")
    print(_verdict(r))
    print("==========================================================")
