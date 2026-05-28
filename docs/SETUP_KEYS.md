# Briefed v2 — Setup & Keys Guide

Everything you need to do **outside this repo** to get Briefed v2 running end-to-end, plus where every API key in `.env.example` comes from.

Read this once top-to-bottom before you start filling in `.env` files. Several pieces depend on each other (Supabase needs the Firebase project ID, Firebase Auth needs a Google project, the GitHub App needs `PUBLIC_API_BASE` to exist, etc.). The order below is the right order to do them in.

---

## Quick checklist

Use this as a smoke-test — every box has a corresponding section below.

- [ ] **1.** Google Cloud project created, Vertex AI + TTS APIs enabled, service account JSON downloaded
- [ ] **2.** Supabase project created, migrations applied, RLS policies present
- [ ] **3.** Firebase project created, Email/Password + Google providers enabled
- [ ] **4.** Firebase added as third-party JWT issuer in Supabase
- [ ] **5.** Recall.ai account, API key, region noted
- [ ] **6.** `PUBLIC_API_BASE` decided (ngrok for local, Cloud Run URL for prod)
- [ ] **7.** Deepgram API key generated
- [ ] **8.** ElevenLabs API key generated
- [ ] **9.** Supermemory API key generated
- [ ] **10.** LangSmith API key (optional but recommended)
- [ ] **11.** GitHub App created and webhook configured (for Phase 4b)
- [ ] **12.** `bot-page/index.html` uploaded to your GCS bucket
- [ ] **13.** `backend-fastapi/.env` and `frontend/.env.local` filled in
- [ ] **14.** `uv sync` on backend, `npm install` on frontend

---

## 1. Google Cloud Platform

**Used by:** Vertex AI (Gemini live + post-meeting), Cloud Text-to-Speech (post-meeting only — live TTS is ElevenLabs), Vertex Embeddings (only if you skip Supermemory and use the pgvector fallback).

### Steps

1. Create a project at **https://console.cloud.google.com** (or reuse one). Note the project ID.
2. Enable APIs at **APIs & Services → Library**:
   - `Vertex AI API`
   - `Cloud Text-to-Speech API`
3. Create a service account at **IAM & Admin → Service Accounts → Create service account**:
   - Name: `briefed-backend` (or anything)
   - Roles to grant: `Vertex AI User`, `Cloud Text-to-Speech User`, `Storage Object Viewer` (for the bot-page GCS bucket reads)
4. Create a JSON key for the service account (Keys tab → Add Key → JSON). It downloads as a `.json` file.
5. **Local dev:** save the JSON file somewhere safe and set `GOOGLE_APPLICATION_CREDENTIALS` to its absolute path.
   **Cloud Run:** skip the JSON file — attach the service account directly to your Cloud Run service.

### Fills in

```
GCP_PROJECT=<your-project-id>
GCP_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/key.json   # local dev only
```

---

## 2. Supabase (database)

**Used by:** Postgres (every table), pgvector (fallback embeddings storage), Auth (third-party JWT validation only, not as the user store).

### Steps

1. Create a project at **https://supabase.com/dashboard**. Region close to your backend deployment is faster.
2. Wait for it to provision (~2 min). Note the **project ref** (the alphanumeric ID in the URL).
3. Run the schema migrations. If you have the **Supabase MCP** loaded in Claude Code, ask Claude to apply them. Otherwise, paste the SQL in `SETUP.md` into Dashboard → SQL Editor.
4. Confirm the v2-specific migrations are applied: `meetings.bridge_token` column exists, the seven `allow_all` RLS policies are gone, and `agent_github_sources` table exists. Quick check in SQL Editor:
   ```sql
   select policyname from pg_policies where schemaname='public' order by tablename, policyname;
   ```
   You should see scoped policies like `users_select_own`, `agents_owner_all`, `meetings_owner_all`, `transcript_lines_via_meeting`, etc. — **not** `allow_all`.

### Where keys live

Dashboard → **Settings → API**:
- **Project URL** → `SUPABASE_URL` (backend) and `NEXT_PUBLIC_SUPABASE_URL` (frontend)
- **anon / public** key → `NEXT_PUBLIC_SUPABASE_ANON_KEY` (frontend, safe to expose)
- **service_role / secret** key → `SUPABASE_SERVICE_ROLE_KEY` (backend AND server-only on frontend). **Never** put this in a `NEXT_PUBLIC_*` var.
- **JWT Secret** (Dashboard → Settings → API → JWT Settings) → `SUPABASE_JWT_SECRET` (backend, only used by the legacy WS fallback)

### Fills in

```
# backend
SUPABASE_URL=https://aubjnmkvfewzepezvqzr.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOi...
SUPABASE_JWT_SECRET=...

# frontend
NEXT_PUBLIC_SUPABASE_URL=https://aubjnmkvfewzepezvqzr.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOi...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOi...   # same value as backend, server-side only
```

---

## 3. Firebase (auth)

**Used by:** signing users in (replaces Clerk), issuing JWTs that Supabase validates.

### Steps

1. Create a project at **https://console.firebase.google.com**. You can reuse the same GCP project from step 1 (Firebase will detect it). The Firebase **project ID** is the same as your GCP project ID.
2. Enable sign-in providers at **Authentication → Sign-in method**:
   - **Email/Password** — toggle on
   - **Google** — toggle on, pick your support email
3. **Authentication → Settings → Authorized domains** — add the domains your frontend will run on:
   - `localhost` (already there by default)
   - your Vercel preview/prod domain (e.g. `briefed.vercel.app`)
4. **Project Settings → General → Your apps → Web app**:
   - If no web app exists, click "Add app" → Web (`</>`) icon → name it (e.g. `briefed-web`) → Register.
   - Copy the `firebaseConfig` object. You need `apiKey`, `authDomain`, `projectId`, `appId`.
5. **Project Settings → Service Accounts → Generate new private key**:
   - Downloads a JSON file. Three fields matter: `project_id`, `client_email`, `private_key`.
   - The `private_key` contains literal `\n` newlines — when pasting into `.env`, keep the `\n` as-is (don't replace with real newlines) and wrap the whole value in double-quotes.

### Fills in

```
# frontend (client SDK — browser-safe)
NEXT_PUBLIC_FIREBASE_API_KEY=AIza...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=briefed-xyz.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=briefed-xyz
NEXT_PUBLIC_FIREBASE_APP_ID=1:1234567890:web:abc123

# frontend (Admin SDK — server-side only, used by /api/auth/session and /api/auth/me)
FIREBASE_PROJECT_ID=briefed-xyz
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxx@briefed-xyz.iam.gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIIEv...==\n-----END PRIVATE KEY-----\n"

# backend (Admin SDK — used by app/auth_deps.py to verify Firebase ID tokens)
FIREBASE_PROJECT_ID=briefed-xyz
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxx@briefed-xyz.iam.gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIIEv...==\n-----END PRIVATE KEY-----\n"
```

---

## 4. Connect Firebase to Supabase (third-party JWT auth)

**This is the step most people miss.** Without it, Supabase rejects Firebase ID tokens and every authenticated frontend query returns zero rows.

### Steps

1. In Supabase dashboard, go to **Authentication → Sign In / Up → Third-Party Auth**.
2. Click **Add provider → Firebase**.
3. Paste your Firebase **project ID** (same as `FIREBASE_PROJECT_ID`).
4. Save.

Now when a request hits Supabase with `Authorization: Bearer <firebase-id-token>`, Supabase validates the token against Firebase's public keys, and RLS policies see `auth.jwt() ->> 'sub'` equal to the Firebase UID.

### Verify

Sign in via your `/auth` page, then in the Supabase SQL Editor run:
```sql
select auth.jwt();
```
While you're signed in via your frontend, this should return your Firebase UID under the `sub` claim. (Run it from your app code; the SQL editor itself uses a different auth path.)

---

## 5. Recall.ai (meeting joiner)

**Used by:** putting a bot into Zoom / Google Meet / Microsoft Teams meetings.

### Steps

1. Sign up at **https://www.recall.ai**.
2. Note your **region** — it's part of the dashboard URL. Use the matching API base URL:
   - US East 1 → `https://us-east-1.recall.ai`
   - EU Central 1 → `https://eu-central-1.recall.ai`
   - AP Northeast 1 → `https://ap-northeast-1.recall.ai`
3. Dashboard → **API Keys → Create new key**. Copy the value.
4. **Bot status webhooks** (optional but recommended for failure debugging): Dashboard → Webhooks → New webhook
   - URL: `{PUBLIC_API_BASE}/api/webhooks/recall/bot-status`
   - Header (if you set `WEBHOOK_SECRET`): `Authorization: Bearer <your-secret>` or `X-Webhook-Secret: <your-secret>`
   - Events: all bot lifecycle events

### Output Media feature

The v2 voice pipeline requires Recall's **Output Media** feature (the bot renders your webpage in headless Chrome). This is enabled by default on Pro tier+. If you get errors about `output_media` being unavailable, contact Recall support.

### Fills in

```
RECALL_API_KEY=<from dashboard>
RECALL_API_BASE=https://us-east-1.recall.ai
WEBHOOK_SECRET=<a strong random string of your choosing>   # optional
```

---

## 6. `PUBLIC_API_BASE` (your backend's public URL)

**This is what Recall and GitHub call back into.** Must be a real URL on the public internet — not `localhost`.

### Local dev

Use **ngrok**:
```bash
ngrok http 8000
```
Copy the `https://xxxx.ngrok-free.app` URL → `PUBLIC_API_BASE`. Restart `ngrok` and update this if it changes.

### Production

Your Cloud Run service URL (or whatever you deploy to). Looks like `https://briefed-api-abc123-uc.a.run.app`.

### Fills in

```
PUBLIC_API_BASE=https://abc123.ngrok-free.app
```

---

## 7. Deepgram (streaming STT)

**Used by:** the v2 voice pipeline — transcribing meeting audio in real-time.

### Steps

1. Sign up at **https://console.deepgram.com**. Free tier includes $200 credit.
2. Dashboard → **API Keys → Create Key**.
   - Name: `briefed-backend`
   - Scope: `Member` (or higher)
3. Copy the key immediately — it's shown once.

### Fills in

```
DEEPGRAM_API_KEY=<from console>
# DEEPGRAM_MODEL=nova-3   # optional, default is fine
```

### Cost

Roughly $0.0043/min for streaming Nova-3. For a 60-min meeting that's ~$0.26.

---

## 8. ElevenLabs (streaming TTS)

**Used by:** the v2 voice pipeline — generating the bot's spoken responses.

### Steps

1. Sign up at **https://elevenlabs.io**.
2. Dashboard → **Settings → API Keys → Create API Key**.
3. Pick a voice. Default in the code is Rachel (`21m00Tcm4TlvDq8ikWAM`), but you can browse **Voice Library** for others.

### Fills in

```
ELEVENLABS_API_KEY=<from settings>
# ELEVENLABS_MODEL=eleven_flash_v2_5   # optional
# ELEVENLABS_DEFAULT_VOICE=21m00Tcm4TlvDq8ikWAM   # optional
```

### Cost

Flash v2.5 is ~$0.05 per 1000 characters. A typical 30-word bot response is ~150 chars → ~$0.0075. Cheap.

---

## 9. Supermemory (long-term memory)

**Used by:** unified knowledge base + cross-meeting recall + GitHub code memory.

### Steps

1. Sign up at **https://supermemory.ai**.
2. Dashboard → **Settings → API Keys → Generate**.

That's it — Supermemory handles chunking, embedding, and storage server-side. Each Briefed agent gets its own namespace via `container_tag = "agent:<agent_id>"`.

### Fills in

```
SUPERMEMORY_API_KEY=<from dashboard>
```

### If you skip this

`pipeline/memory.py` falls back to the legacy `context_chunks` table (pgvector + Vertex embeddings). Functional but lacks cross-meeting recall — Sam won't remember the previous meeting.

---

## 10. LangSmith (LLM tracing — optional)

**Used by:** Phase 3 — viewing every Gemini call, classifier decision, and fact-check evaluation in a dashboard.

### Steps

1. Sign up at **https://smith.langchain.com**.
2. Settings → **API Keys → Create API Key**.
3. Create a project (e.g. `briefed-prod`, `briefed-dev`) — or LangSmith creates one with the name you put in `LANGSMITH_PROJECT`.

### Fills in

```
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=briefed-prod
LANGSMITH_TRACING=true
```

### If you skip this

The `@traced` decorator no-ops cleanly. Zero performance impact, you just lose visibility.

---

## 11. GitHub App (Phase 4b — live code memory)

**Used by:** the webhook that re-ingests changed code files into agent memory on every push.

### Two options

**Option A: Personal Access Token (PAT)** — fastest, fine for solo use.
1. https://github.com/settings/tokens → Generate new token (classic)
2. Scope: `repo` (private repos) or `public_repo` (public only)
3. Put it in `GITHUB_TOKEN`. **Done.** Skip the GitHub App steps below.
4. Manually register a webhook on each repo: Settings → Webhooks → Add webhook
   - Payload URL: `{PUBLIC_API_BASE}/api/webhooks/github`
   - Content type: `application/json`
   - Secret: the value returned from `POST /api/agents/{id}/github`
   - Events: just "Pushes"

**Option B: GitHub App** — better for multi-user / production.
1. https://github.com/settings/apps → **New GitHub App**
2. Settings:
   - GitHub App name: `Briefed` (or whatever)
   - Homepage URL: your frontend URL
   - Webhook → Active: **yes**
   - Webhook URL: `{PUBLIC_API_BASE}/api/webhooks/github`
   - Webhook secret: generate a strong random value — save it now, you'll paste into both env vars and GitHub
   - Permissions:
     - Repository → Contents: **Read-only**
     - Repository → Metadata: **Read-only**
   - Subscribe to events: **Push**
   - Where can this GitHub App be installed?: **Any account**
3. After creating: scroll down, click **Generate a private key** → downloads a `.pem` file.
4. Note the App ID at the top of the settings page.
5. Install the app on the repos you want connected (top-right "Install App").

### Fills in

```
# Option A (PAT):
GITHUB_TOKEN=ghp_...

# Option B (GitHub App):
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nMIIEow...==\n-----END RSA PRIVATE KEY-----\n"
GITHUB_APP_WEBHOOK_SECRET=<same secret you put in the App settings>
```

### Per-repo registration (both options)

After your agent exists and the backend is reachable at `PUBLIC_API_BASE`:

```bash
curl -X POST "$PUBLIC_API_BASE/api/agents/$AGENT_ID/github" \
  -H "Authorization: Bearer $FIREBASE_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"repo_full_name": "owner/repo", "branch": "main"}'
```

Response: `{ "webhook_url": "...", "webhook_secret": "...", "events": ["push"], ... }`. Use that secret when registering the webhook on GitHub (Option A only; Option B uses your App-wide secret).

---

## 12. Bot-page deployment

**Used by:** Recall loads `bot-page/index.html` inside the bot's headless Chrome via Output Media.

### Steps

1. Create a public GCS bucket (or any CDN). Public-read on the file is fine — no secrets in there.
2. Upload `bot-page/index.html`. Note the URL.
3. Set `BOT_PAGE_URL` to that URL. Default in code is `https://storage.googleapis.com/briefed-bot-page/index.html`.

### When you edit `bot-page/index.html`

Re-upload to GCS, and bump the cache by adding/changing the `_v=...` query param in `start_meeting` (already auto-done with `int(time.time())`).

### Local dev tip

If you want to iterate on the bot-page without re-uploading, point `BOT_PAGE_URL` at an ngrok tunnel to a local file server. Recall fetches the URL from inside its container, so it must be publicly reachable.

---

## 13. Final env-file checklist

Backend (`backend-fastapi/.env`):
- [ ] `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`
- [ ] `RECALL_API_KEY`, `RECALL_API_BASE`
- [ ] `PUBLIC_API_BASE`
- [ ] `GCP_PROJECT`, `GCP_LOCATION`, `GOOGLE_APPLICATION_CREDENTIALS` (local) or attach SA (Cloud Run)
- [ ] `BOT_PAGE_URL`
- [ ] `DEEPGRAM_API_KEY`
- [ ] `ELEVENLABS_API_KEY`
- [ ] `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY`
- [ ] `SUPERMEMORY_API_KEY`
- [ ] `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`, `LANGSMITH_TRACING=true` (optional)
- [ ] `GITHUB_TOKEN` **or** `GITHUB_APP_ID` + `GITHUB_APP_PRIVATE_KEY` + `GITHUB_APP_WEBHOOK_SECRET`
- [ ] `WEBHOOK_SECRET` (optional)
- [ ] `RESEND_API_KEY`, `RESEND_FROM` (optional, for post-meeting email)

Frontend (`frontend/.env.local`):
- [ ] `NEXT_PUBLIC_APP_URL`
- [ ] `NEXT_PUBLIC_API_BASE_URL`
- [ ] `NEXT_PUBLIC_SUPABASE_URL`
- [ ] `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- [ ] `SUPABASE_SERVICE_ROLE_KEY` (same value as backend, server-only)
- [ ] `NEXT_PUBLIC_FIREBASE_API_KEY`
- [ ] `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN`
- [ ] `NEXT_PUBLIC_FIREBASE_PROJECT_ID`
- [ ] `NEXT_PUBLIC_FIREBASE_APP_ID`
- [ ] `FIREBASE_PROJECT_ID`
- [ ] `FIREBASE_CLIENT_EMAIL`
- [ ] `FIREBASE_PRIVATE_KEY`

---

## 14. Install and run

### Backend
```bash
cd backend-fastapi
uv sync                          # installs new deps: pipecat, deepgram, elevenlabs, firebase-admin, supermemory, langsmith
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install                      # removes @clerk/*, adds firebase + firebase-admin
npm run dev
```

### Smoke test sequence

1. Visit `http://localhost:3000/auth` → sign in with Google → row appears in Supabase `users` table with your Firebase UID as `id`.
2. Visit `/agents/new` → create an agent.
3. Visit `/meeting`, paste a Google Meet link you control, click Start. Bot should join within ~10s.
4. Speak: "Hey Sam, what time is it?" — bot should respond. Confirm latency from end-of-speech to start-of-audio is under ~1.5s.
5. Without using the name, speak: "what was the deadline we discussed?" — bot should respond via the addressed-classifier path.
6. While the bot is speaking, start talking. Bot should stop within ~300ms (real barge-in).
7. End the meeting. Check backend logs for `meeting_memory_persisted` (Phase 4a). In the Supermemory dashboard, look for a `kind=meeting` entry under `agent:<your-agent-id>`.
8. Start a new meeting with the same agent. Ask: "what did we discuss last time?" — should reference the previous meeting's summary.
9. If LangSmith is configured: visit your project, you should see traces with nested spans for `decide_turn`, `classify_addressed`, `answer_question_streaming`, `fact_check`.
10. Connect a GitHub repo via the API (step 11 above), push a commit to it, check backend logs for `github_sync_done`.

---

## Common failure modes

| Symptom | Likely cause |
|---|---|
| `/agents` shows "0 agents" even though they exist | Firebase third-party JWT not configured in Supabase, or you forgot to add `SUPABASE_SERVICE_ROLE_KEY` to the frontend env |
| Sign-in works but `/api/auth/me` returns `authenticated: false` | `FIREBASE_PRIVATE_KEY` has literal newlines instead of `\n`. Re-paste from the JSON, wrap in double quotes |
| Bot joins meeting but says nothing | Likely the v2 path didn't activate — check backend logs for `v2_pipeline_configured`. If absent, `DEEPGRAM_API_KEY` or `ELEVENLABS_API_KEY` is missing |
| Bot speaks but the audio is chipmunked or stuttery | Sample-rate mismatch. Confirm Pipecat's `audio_in_sample_rate=16000` and `audio_out_sample_rate=24000` match the bot-page's downsampler |
| `bridge_token` shows up as `null` in `meetings` | v2 didn't activate — same as above |
| Recall webhook arrives but signature fails | `WEBHOOK_SECRET` env value doesn't match the header you configured in Recall |
| GitHub webhook returns 401 | Per-source webhook secret doesn't match. Re-mint via `POST /api/agents/{id}/github`, re-register on GitHub |
| LangSmith dashboard empty | `LANGSMITH_TRACING=true` is missing (the env var needs that literal value) |

---

## Production deployment (Cloud Run + Vercel)

Backend (Cloud Run):
- Use Secret Manager for all the API keys (don't put them in `gcloud run deploy --set-env-vars`).
- Attach a service account with `Vertex AI User` + `Cloud TTS User` roles to the Cloud Run service — then drop `GOOGLE_APPLICATION_CREDENTIALS` from env.
- Set min instances ≥ 1 to avoid cold-start latency on the voice pipeline.
- The Pipecat pipeline holds long-lived WebSocket connections — make sure Cloud Run's request timeout is set high (3600s max).

Frontend (Vercel):
- Add all env vars in Vercel project settings → Environment Variables. Public vars need to be added for all environments; secrets only for `Production`.
- Don't forget to add your Vercel domain to **Firebase Authorized Domains** and **Supabase CORS allowed origins**.
