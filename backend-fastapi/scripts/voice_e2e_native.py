"""Native-output E2E: stream a question to the recall-audio input WS only (no
bot-page). The server (native mode) synthesizes the reply and calls inject_audio,
which the launcher stubs to save the mp3 to %TEMP%/native_inject_*.mp3."""
import asyncio
import sys
from pathlib import Path

import websockets

sys.path.insert(0, str(Path(__file__).resolve().parent))
import voice_e2e_test as base  # reuse synth + constants


async def main():
    pcm = base.synth_question_pcm()
    in_url = f"ws://{base.HOST}/ws/recall-audio/{base.MID}/?token={base.TOKEN}"
    ws = await websockets.connect(in_url, max_size=None, ping_interval=None)
    print(f"[native-test] streaming question ({len(pcm)/2/16000:.2f}s)")
    sil = b"\x00" * base.CHUNK_BYTES

    async def stream(buf):
        for i in range(0, len(buf), base.CHUNK_BYTES):
            c = buf[i:i + base.CHUNK_BYTES]
            if len(c) < base.CHUNK_BYTES:
                c = c + b"\x00" * (base.CHUNK_BYTES - len(c))
            await ws.send(c)
            await asyncio.sleep(base.CHUNK_MS / 1000)

    # warmup (let pipeline build), then question, then trailing silence to let
    # VAD/Deepgram finalize + the LLM+TTS+inject happen.
    for _ in range(int(10 * 1000 / base.CHUNK_MS)):
        await ws.send(sil); await asyncio.sleep(base.CHUNK_MS / 1000)
    await stream(pcm)
    print("[native-test] question sent; waiting for synth+inject...")
    for _ in range(int(15 * 1000 / base.CHUNK_MS)):
        await ws.send(sil); await asyncio.sleep(base.CHUNK_MS / 1000)
    await ws.close()
    print("[native-test] done")


if __name__ == "__main__":
    asyncio.run(main())
