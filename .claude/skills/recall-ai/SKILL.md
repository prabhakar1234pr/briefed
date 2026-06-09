---
name: recall-ai
description: Use when working with Recall.ai in Briefed — sending meeting bots (create_bot), output media (bot-page as camera/audio), receiving real-time meeting audio or transcripts, bot-status/lifecycle webhooks, or debugging "the bot doesn't hear/respond" and "meeting stuck on Joining". Covers the v1.11 API, exact config shapes, and Briefed-specific gotchas.
---

# Recall.ai integration (Briefed)

Recall.ai joins meeting bots to Google Meet / Zoom / Teams. Briefed uses it for
the live voice agent ("Bora"), recordings, transcripts, and screenshots.
Account region: **`us-west-2`** (`https://us-west-2.recall.ai`), workspace
"Northeastern University". **Use the v1.11 API** (v1.10 field names like
`real_time_media`, `real_time_transcription` are NOT valid here).

Backend code: `backend-fastapi/app/main.py` (`start_meeting` builds the
`create_bot` payload; `recall_bot_status` / `recall_realtime` handle webhooks),
`app/recall_client.py`, `app/pipeline/` (Pipecat voice), `bot-page/index.html`.

Authoritative docs index: https://docs.recall.ai/llms.txt

## create_bot essentials (v1.11)
All recording/transcript/realtime config goes under `recording_config`:
```json
{
  "meeting_url": "...",
  "bot_name": "...",
  "recording_config": {
    "transcript": { "provider": { "recallai_streaming": { "mode": "prioritize_low_latency", "language_code": "en" } } },
    "video_mixed_mp4": {}, "audio_mixed_mp3": {},
    "realtime_endpoints": [ { "type": "websocket", "url": "wss://...", "events": ["..."] } ]
  }
}
```
- `prioritize_low_latency` REQUIRES `language_code: "en"` and supports no other transcript options.
- Region-specific host: `https://us-west-2.recall.ai/api/v1/bot`.

## Output Media (bot speaks/shows into the meeting)
Render a webpage as the bot's camera; its audio+video stream into the meeting:
```json
"bot_variant": "web_4_core",
"output_media": { "camera": { "kind": "webpage", "config": { "url": "<bot-page>?<params>" } } }
```
- Output media ALWAYS shows the webpage as the bot's video; you can't do audio-only or turn the camera off while output media is on.
- The Output Video/Output Audio endpoints can't be used while output media is active.
- The bot-page can PLAY audio (TTS) back into the meeting — this direction works.

## ⚠️ Receiving meeting audio — the big gotcha
**An output-media webpage CANNOT capture meeting audio via `getUserMedia`.**
Recall does not pipe meeting audio into the webpage's mic; `getUserMedia` returns
silence. Briefed's `bot-page/index.html` does exactly this, which is why **Bora
never hears anyone** (the `/ws/bot-bridge` WS opens but zero inbound audio frames
arrive — confirmed via backend DEBUG logs showing only outbound keepalives).

**Correct mechanism — server-side websocket** for real-time audio:
```json
"recording_config": {
  "realtime_endpoints": [ { "type": "websocket", "url": "wss://<backend>/<audio-ws>", "events": ["audio_mixed_raw.data"] } ],
  "audio_mixed_raw": {}
}
```
- `audio_mixed_raw.data`: binary frames, **S16LE / 16000 Hz / mono**. Empty packets sent during silence.
- `audio_separate_raw.data` (per-participant): JSON with base64 buffer (`data.data.buffer`, S16LE 16kHz mono) + timestamp + participant. Compute-heavy → use 4-core bots.
- This CAN run alongside `output_media` (input via websocket, output via the webpage).

**To fix Bora's audio:** add a backend WS endpoint that consumes `audio_mixed_raw.data`, register it in `realtime_endpoints` from `start_meeting`, and feed those frames into the Pipecat transport's input (keep the bot-page for OUTPUT only). The Pipecat pipeline (`app/pipeline/runner.py`: Deepgram STT → Vertex Gemini → ElevenLabs TTS) is already correct — it just has no audio input today.

## Real-time transcription (alternative to raw audio)
Both fields are mandatory or you get nothing (and may not even get a failure event):
```json
"recording_config": {
  "transcript": { "provider": { "recallai_streaming": { "mode": "prioritize_low_latency", "language_code": "en" } } },
  "realtime_endpoints": [ { "type": "webhook", "url": "<your-endpoint>", "events": ["transcript.data"] } ]
}
```
Add `transcript.partial_data` to events for interim results. Briefed's v1 path
used a `transcript.data` webhook → `/api/webhooks/recall/realtime`.

## Webhooks (bot lifecycle / status)
Status events (`bot.joining_call`, `bot.in_waiting_room`,
`bot.in_call_not_recording`, `bot.in_call_recording`, `bot.call_ended`,
`bot.done`, `bot.fatal`, `recording.done`, `audio_mixed.done`,
`video_mixed.done`) drive the meeting status in `recall_bot_status`.

- Configure the endpoint in the **Recall dashboard → Webhooks → Endpoints**
  (Svix-based), NOT only in `create_bot`. Briefed's endpoint:
  `https://backend-fastapi-zl626x3wma-uc.a.run.app/api/webhooks/recall/bot-status`.
- **Symptom "meeting stuck on Joining…"** = status webhooks aren't reaching the
  backend. Check the dashboard endpoints point at the CURRENT backend URL (stale
  ones from old GCP projects are a common cause after a migration).
- **`WEBHOOK_SECRET` must be UNSET** on the backend. Recall signs webhooks with
  **Svix** (`svix-signature` header); Briefed's `_webhook_secret_ok` only checks
  `x-webhook-secret`/`Authorization: Bearer`, so a set secret → 401 rejections.
  (If you need verification, implement Svix signature checks instead.)
- Retry policy: 30 attempts, 3s apart, then endpoint marked failed.

## Debugging
- **Remote DevTools:** Recall dashboard → the live bot → CPU Metrics → "Open
  Remote DevTools" opens a Chrome inspector INTO the bot's browser — use it to
  see the bot-page's `[v2]` console logs (getUserMedia success, frames, errors).
- Backend: set `LOG_LEVEL=DEBUG` on Cloud Run to see Pipecat audio-frame / VAD /
  Deepgram activity; absence of inbound audio frames = capture problem upstream.
- The bot-page only logs to the browser console (`dbg()` writes DOM + console),
  so backend logs won't show its internals unless you re-add a debug POST.

Related memory: [[v2-voice-audio-input-broken]], [[briefed-deploy-and-projects]].
