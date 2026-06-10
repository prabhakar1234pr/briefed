"""Synthesize a ~10s reference clip via ElevenLabs at PCM 24kHz (what the backend
sends to the bot-page) → ref_24k.pcm. Run once."""
import os
from pathlib import Path
import httpx

HERE = Path(__file__).resolve().parent
ENV = HERE.parent.parent / ".env"
for raw in ENV.read_text(encoding="utf-8").splitlines():
    l = raw.strip()
    if l and not l.startswith("#") and "=" in l:
        k, v = l.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

VOICE = "21m00Tcm4TlvDq8ikWAM"
TEXT = ("The capital of France is Paris. The capital of India is New Delhi. "
        "The capital of Japan is Tokyo. Photosynthesis converts sunlight, water, "
        "and carbon dioxide into glucose and oxygen. This is a clarity test.")
r = httpx.post(
    f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}",
    params={"output_format": "pcm_24000"},
    headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "content-type": "application/json"},
    json={"text": TEXT, "model_id": "eleven_flash_v2_5"},
    timeout=60,
)
r.raise_for_status()
out = HERE / "ref_24k.pcm"
out.write_bytes(r.content)
print(f"wrote {out} ({len(r.content)} bytes, {len(r.content)/2/24000:.2f}s @24k)")
