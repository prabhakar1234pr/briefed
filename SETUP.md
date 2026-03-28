# Briefed — Copilot Mode Setup Guide

Everything you need to go from code to a live, working Copilot mode.

---

## 1. Supabase Setup

### 1.1 Run SQL migrations

Open **Supabase → SQL Editor** and run each block below.

#### Add columns to `meetings`
```sql
ALTER TABLE public.meetings
  ADD COLUMN IF NOT EXISTS summary         text,
  ADD COLUMN IF NOT EXISTS action_items    text,  -- stored as JSON array string
  ADD COLUMN IF NOT EXISTS key_decisions   text,  -- stored as JSON array string
  ADD COLUMN IF NOT EXISTS joined_at       timestamptz,
  ADD COLUMN IF NOT EXISTS ended_at        timestamptz,
  ADD COLUMN IF NOT EXISTS scheduled_at    timestamptz;
```

#### Create `context_chunks` table
```sql
-- Enable pgvector extension first
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS public.context_chunks (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id      uuid NOT NULL REFERENCES public.agents(id) ON DELETE CASCADE,
  source_url    text NOT NULL,
  content       text NOT NULL,
  content_hash  text NOT NULL,
  embedding     vector(768),       -- Vertex AI text-embedding-004 dimension
  created_at    timestamptz DEFAULT now()
);

-- Index for fast vector search
CREATE INDEX IF NOT EXISTS context_chunks_embedding_idx
  ON public.context_chunks
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- Index for agent lookups
CREATE INDEX IF NOT EXISTS context_chunks_agent_id_idx
  ON public.context_chunks (agent_id);

-- RLS
ALTER TABLE public.context_chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own agent chunks"
  ON public.context_chunks
  USING (
    agent_id IN (
      SELECT id FROM public.agents WHERE user_id = auth.uid()
    )
  );
```

#### Create `meeting_interactions` table
```sql
CREATE TABLE IF NOT EXISTS public.meeting_interactions (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  meeting_id        uuid NOT NULL REFERENCES public.meetings(id) ON DELETE CASCADE,
  interaction_type  text NOT NULL CHECK (interaction_type IN ('qa', 'factcheck', 'screenshot')),
  trigger_text      text,
  response_text     text,
  screenshot_b64    text,          -- base64 JPEG for screenshots
  spoken_at         timestamptz,
  created_at        timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS meeting_interactions_meeting_id_idx
  ON public.meeting_interactions (meeting_id);

ALTER TABLE public.meeting_interactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view own meeting interactions"
  ON public.meeting_interactions
  USING (
    meeting_id IN (
      SELECT id FROM public.meetings WHERE user_id = auth.uid()
    )
  );
```

#### Create semantic search RPC function
```sql
CREATE OR REPLACE FUNCTION match_context_chunks(
  p_agent_id      uuid,
  query_embedding vector(768),
  match_count     int DEFAULT 5
)
RETURNS TABLE (
  id          uuid,
  content     text,
  source_url  text,
  similarity  float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    id,
    content,
    source_url,
    1 - (embedding <=> query_embedding) AS similarity
  FROM public.context_chunks
  WHERE agent_id = p_agent_id
    AND embedding IS NOT NULL
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;
```

### 1.2 Verify agents table has required columns
```sql
-- Check and add if missing
ALTER TABLE public.agents
  ADD COLUMN IF NOT EXISTS persona_prompt        text,
  ADD COLUMN IF NOT EXISTS voice_id              text,
  ADD COLUMN IF NOT EXISTS bot_image_url         text,
  ADD COLUMN IF NOT EXISTS proactive_fact_check  boolean DEFAULT true,
  ADD COLUMN IF NOT EXISTS screenshot_on_request boolean DEFAULT true,
  ADD COLUMN IF NOT EXISTS send_post_meeting_email boolean DEFAULT true;
```

---

## 2. GCP Setup

### 2.1 Create a GCP project (or use existing)
```
https://console.cloud.google.com/projectcreate
```
Note your **Project ID** (e.g. `briefed-prod`).

### 2.2 Enable required APIs

Go to **APIs & Services → Enable APIs** and enable each of these:

| API | Console name |
|-----|-------------|
| Vertex AI | `Vertex AI API` |
| Cloud Text-to-Speech | `Cloud Text-to-Speech API` |
| Cloud Run | `Cloud Run Admin API` |
| Artifact Registry | `Artifact Registry API` |
| IAM | Already enabled |

Or run via gcloud:
```bash
gcloud services enable \
  aiplatform.googleapis.com \
  texttospeech.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  --project YOUR_PROJECT_ID
```

### 2.3 Create a Service Account

1. Go to **IAM & Admin → Service Accounts → Create Service Account**
2. Name: `briefed-backend`
3. Grant these roles:
   - `Vertex AI User`
   - `Cloud Text-to-Speech API User`
4. Click **Done**
5. Click the service account → **Keys → Add Key → JSON**
6. Download the JSON file → save as `gcp-sa-key.json` in `backend-fastapi/`

> ⚠️ Never commit this file. It's in `.gitignore` already.

### 2.4 Local development: set credentials

In your backend `.env`:
```env
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/backend-fastapi/gcp-sa-key.json
GCP_PROJECT=your-project-id
GCP_LOCATION=us-central1
```

### 2.5 Cloud Run: attach service account

When deploying, attach the service account so it can call Vertex AI without a key file:
```bash
gcloud run deploy briefed-backend \
  --service-account briefed-backend@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --region us-central1 \
  ...
```
(See Section 4 for full deploy command.)

---

## 3. Local Development Setup

### 3.1 Backend `.env`
```env
# Recall.ai
RECALL_API_KEY=your_recall_api_key

# Your public URL (ngrok for local dev)
PUBLIC_API_BASE=https://YOUR-STATIC-DOMAIN.ngrok-free.app

# Supabase
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_JWT_SECRET=your_jwt_secret

# GCP
GCP_PROJECT=your-project-id
GCP_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/gcp-sa-key.json

# CORS (add your Vercel URL when deployed)
CORS_ORIGINS=http://localhost:3000
```

### 3.2 Frontend `.env`
```env
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### 3.3 Install dependencies

**Backend:**
```bash
cd backend-fastapi
pip install fastapi "uvicorn[standard]" httpx PyJWT cryptography supabase \
  "google-cloud-aiplatform>=1.60.0" "google-cloud-texttospeech>=2.16.0" vertexai
```

**Frontend:**
```bash
cd frontend
npm install
```

### 3.4 Start ngrok (REQUIRED for Recall.ai webhooks locally)
```bash
# Claim a free static domain first at ngrok.com/dashboard
ngrok http --domain=YOUR-STATIC-DOMAIN.ngrok-free.app 8000
```
Then set `PUBLIC_API_BASE=https://YOUR-STATIC-DOMAIN.ngrok-free.app` in backend `.env`.

### 3.5 Configure Recall.ai webhooks

1. Log into [recall.ai dashboard](https://app.recall.ai)
2. Go to **Webhooks → Add Endpoint**
3. URL: `https://YOUR-STATIC-DOMAIN.ngrok-free.app/api/webhooks/recall/bot-status`
4. Select all `bot.*` events
5. Copy the signing secret (optional but recommended for production)

### 3.6 Start everything
```bash
# Terminal 1 - Backend
cd backend-fastapi
uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

---

## 4. Deploy to Production

### 4.1 Deploy backend to Cloud Run

```bash
# Set your project
export PROJECT_ID=your-project-id
export REGION=us-central1

# Build and push
gcloud builds submit \
  --tag gcr.io/$PROJECT_ID/briefed-backend \
  ./backend-fastapi

# Deploy
gcloud run deploy briefed-backend \
  --image gcr.io/$PROJECT_ID/briefed-backend \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --service-account briefed-backend@$PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars "RECALL_API_KEY=xxx,SUPABASE_URL=xxx,SUPABASE_SERVICE_ROLE_KEY=xxx,SUPABASE_JWT_SECRET=xxx,GCP_PROJECT=$PROJECT_ID,GCP_LOCATION=$REGION,CORS_ORIGINS=https://your-vercel-app.vercel.app" \
  --memory 512Mi \
  --min-instances 0 \
  --max-instances 10
```

After deploy, copy the Cloud Run URL (e.g. `https://briefed-backend-xxxx-uc.a.run.app`).

Then redeploy with `PUBLIC_API_BASE` set to the Cloud Run URL:
```bash
gcloud run services update briefed-backend \
  --update-env-vars PUBLIC_API_BASE=https://briefed-backend-xxxx-uc.a.run.app \
  --region $REGION
```

### 4.2 Deploy frontend to Vercel

1. Push repo to GitHub
2. Import project at [vercel.com/new](https://vercel.com/new)
3. Set environment variables:
   ```
   NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
   NEXT_PUBLIC_API_BASE_URL=https://briefed-backend-xxxx-uc.a.run.app
   ```
4. Deploy

### 4.3 Update Recall.ai webhook URL

In the Recall.ai dashboard, update your webhook endpoint to:
```
https://briefed-backend-xxxx-uc.a.run.app/api/webhooks/recall/bot-status
```

---

## 5. Quick Verification Checklist

After setup, verify each layer:

| Check | How |
|-------|-----|
| Backend running | `GET /health` → `{"ok": true}` |
| Supabase auth | Sign in to frontend, check Supabase Auth dashboard |
| pgvector working | Create agent, add a URL — check `context_chunks` table has rows |
| Vertex AI working | Add context source and see chunks indexed (requires GCP_PROJECT set) |
| Recall.ai bot | Start meeting, check Recall.ai dashboard for bot appearing |
| Webhooks firing | Check backend logs for POST to `/api/webhooks/recall/realtime` |
| TTS working | Join meeting, say agent name + question, listen for response |
| Post-meeting AI | After meeting ends, check `meetings` table for `summary` column populated |

---

## 6. How Copilot Mode Works End-to-End

```
1. User creates agent → sets name, persona, voice
2. User adds context sources (GitHub, docs, text)
   → Backend fetches → chunks → embeds via Vertex AI → stores in pgvector

3. User starts meeting → Recall.ai bot joins call
4. Recall.ai streams transcript chunks → POST /api/webhooks/recall/realtime

5. For each chunk:
   a. Stored in transcript_lines
   b. Checked for trigger:
      - "Hey [AgentName], question?" → Q&A trigger
      - "take a screenshot"          → Screenshot trigger
      - (any statement)              → Fact-check (if enabled)

6. On Q&A trigger:
   → pgvector search (top 5 chunks)
   → Gemini: question + context + recent transcript → answer
   → Google TTS: answer text → MP3
   → Recall.ai Output Media: MP3 injected into live call
   → Stored in meeting_interactions

7. On meeting end (bot.done webhook):
   → Download full transcript from Recall.ai
   → Gemini: transcript → summary + action_items + key_decisions
   → Saved to meetings table
   → Frontend shows post-meeting brief
```

---

## 7. Environment Variables Reference

### Backend (Cloud Run / `.env`)
| Variable | Required | Description |
|----------|----------|-------------|
| `RECALL_API_KEY` | ✅ | From recall.ai dashboard |
| `RECALL_API_BASE` | optional | Default: `https://us-east-1.recall.ai` |
| `PUBLIC_API_BASE` | ✅ | Your backend's public URL (ngrok or Cloud Run) |
| `SUPABASE_URL` | ✅ | From Supabase project settings |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | From Supabase project settings → API |
| `SUPABASE_JWT_SECRET` | ✅ | From Supabase project settings → API |
| `GCP_PROJECT` | ✅ | Your GCP project ID |
| `GCP_LOCATION` | optional | Default: `us-central1` |
| `GOOGLE_APPLICATION_CREDENTIALS` | local only | Path to service account JSON (not needed on Cloud Run with SA attached) |
| `CORS_ORIGINS` | ✅ prod | Comma-separated allowed origins |

### Frontend (Vercel / `.env`)
| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | ✅ | From Supabase project settings |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ✅ | From Supabase project settings → API |
| `NEXT_PUBLIC_API_BASE_URL` | ✅ | Backend URL (localhost:8000 or Cloud Run) |
