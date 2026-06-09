# Briefed / Agent Bora — project guide

AI meeting assistant: a bot ("Bora") joins Google Meet / Zoom / Teams via
**Recall.ai**, listens, answers questions out loud, fact-checks, takes
screenshots, and produces post-meeting briefs. Agents have a persona + a
knowledge base (docs + GitHub repos) used for grounded answers.

## Layout
- `frontend/` — Next.js 16 (Turbopack) app, deployed on **Vercel** (`briefed-mu.vercel.app`). Auth = Firebase. Talks to the backend over HTTP/WS. See `frontend/AGENTS.md` (Next 16 has breaking changes — read `node_modules/next/dist/docs/` before writing Next code).
- `backend-fastapi/` — FastAPI on **Cloud Run**. Live meeting pipeline (Recall + Pipecat voice), webhooks, context ingestion, post-meeting intelligence.
- `bot-page/index.html` — page Recall renders as the bot's camera (output media). Hosted in GCS.

## Infrastructure (GCP project `briefed-42540` is PRODUCTION)
- **Cloud SQL** `briefed-db` (Postgres 16), connection `briefed-42540:us-central1:briefed-db`, db `briefed`. Migrated off Supabase in June 2026.
- **Cloud Run** service `backend-fastapi` → `https://backend-fastapi-zl626x3wma-uc.a.run.app`.
- **GCS**: `briefed-42540-screenshots` (screenshots), `briefed-42540-bot-page` (bot page).
- **Secret Manager**: `briefed-db-password`, `firebase-private-key`, `github-app-private-key`.
- Firebase Auth lives in a **different** project (`briefed-492620`); both ends use it.
- Deploy: push to `main` touching `backend-fastapi/**` → `.github/workflows/deploy-backend-cloud-run.yml`. Vercel auto-deploys the frontend.
- ⚠️ Multiple stale GCP projects exist (`briefed-492620`, `meetstreamiq`, `briefed-app-prod`) — only `briefed-42540` is current.

## Database access (NO Supabase)
Backend: `app/sql.py` (SQLAlchemy engine via Cloud SQL connector) + `app/repo.py`
(typed queries; coerces UUID/datetime → JSON-friendly). Vector search via the
`match_context_chunks` SQL function (pgvector, `vector(768)`, Gemini
text-embedding-004). Frontend never touches the DB directly — server components
use `lib/server-api.ts` (mints a Firebase ID token from the session cookie),
client components use `lib/meeting-api.ts`. Both call backend endpoints.

## Recall.ai
The meeting bot + live audio is Recall.ai. **Use the `recall-ai` skill in
`.claude/skills/` for output-media, real-time audio, webhooks, and known
gotchas before touching that code.**

## RocketRide
For AI-pipeline / RAG / document-processing work, follow `.claude/rules/rocketride.md`.

## Known issues / gotchas
- **Voice: Bora doesn't hear the meeting.** The bot-page captures audio with
  `getUserMedia`, which Recall's output-media webpage does NOT feed meeting
  audio into. Needs rearchitecting to receive audio via a server-side Recall
  `realtime_endpoints` websocket (`audio_mixed_raw.data`). See the `recall-ai`
  skill. (Pre-existing; unrelated to the Cloud SQL migration.)
- Enabling a new GCP project means re-enabling APIs (`aiplatform`,
  `texttospeech`, `sqladmin`, `secretmanager`, `run`) and granting the runtime
  service account roles (`aiplatform.user`, `cloudsql.client`,
  `secretmanager.secretAccessor`, `storage.objectAdmin`).
- Backend tests mock the old Supabase client and are skipped via
  `collect_ignore_glob` in `tests/conftest.py` — pending rewrite against a
  `repo` fake. Pure tests (trigger detection, rate limit) run.
- `WEBHOOK_SECRET` must be UNSET for Recall webhooks to be accepted — the
  backend's check only understands `x-webhook-secret`/Bearer, not Recall's Svix
  signing.
