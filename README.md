# Briefed — AI Meeting Intelligence Platform

> Your AI copilot for corporate meetings. Joins Zoom, Google Meet, or Microsoft Teams — answers questions live using your project's knowledge base, fact-checks statements in real-time, takes screenshots on command, and delivers post-meeting intelligence.

---

## What It Does

**During the meeting:**
- Say **"Hey Sam, what's the timeline for Phase 2?"** → Agent answers using your uploaded project docs
- Someone states incorrect project data → Agent **proactively corrects** with the right facts
- Say **"Take a screenshot"** → Captures and saves to your meeting dashboard
- All Q&A, corrections, and screenshots are logged for post-meeting review

**After the meeting:**
- AI-generated **summary, action items, and key decisions**
- Full searchable transcript with speaker attribution
- Optional email report sent automatically

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                  │
│  Next.js 16 · React 19 · Tailwind 4 · Supabase Auth             │
│  Deployed on Vercel                                               │
└──────────────────┬───────────────────────────────────────────────┘
                   │ REST API + WebSocket
┌──────────────────▼───────────────────────────────────────────────┐
│                         BACKEND                                   │
│  FastAPI · Python 3.12 · Deployed on Cloud Run (GCP)             │
│                                                                   │
│  ┌─────────────┐ ┌──────────────┐ ┌───────────────────────────┐  │
│  │ Gemini 2.5  │ │ Google Cloud │ │ Recall.ai API             │  │
│  │ Flash + Pro │ │ TTS Neural2  │ │ Bot joins · Transcript    │  │
│  │ (Vertex AI) │ │              │ │ Audio inject · Screenshot │  │
│  └─────────────┘ └──────────────┘ └───────────────────────────┘  │
└──────────────────┬───────────────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────────────┐
│                         DATABASE                                  │
│  Supabase (PostgreSQL + pgvector + Auth + Storage)               │
└──────────────────────────────────────────────────────────────────┘
```

### Key Technologies

| Layer | Stack |
|-------|-------|
| **Frontend** | Next.js 16, React 19, Tailwind 4, Supabase SSR |
| **Backend** | FastAPI, Python 3.12, uvicorn, httpx |
| **AI** | Vertex AI Gemini 2.5-flash (live Q&A), Gemini 2.5-pro (post-meeting) |
| **TTS** | Google Cloud Text-to-Speech (Neural2/Studio voices) |
| **Meeting Integration** | Recall.ai (bot joins Zoom/Meet/Teams, streams transcript, records) |
| **Database** | Supabase PostgreSQL + pgvector (768-dim embeddings) |
| **Vector Search** | Vertex AI text-embedding-004 + pgvector cosine similarity |
| **Bot UI** | Static HTML on GCS, runs in Recall's headless Chrome |
| **CI/CD** | GitHub Actions → Cloud Run; Vercel auto-deploy for frontend |

---

## Project Structure

```
meetstreamiq/
├── frontend/                    # Next.js 16 app
│   ├── src/
│   │   ├── app/                 # App Router pages
│   │   │   ├── agents/          # Create, list, edit agents
│   │   │   ├── meeting/         # Join meeting form
│   │   │   ├── meetings/        # Meeting list + details
│   │   │   └── auth/            # Sign in/up
│   │   ├── components/          # AgentForm, ContextBuilder, Shell
│   │   ├── lib/                 # API client, Supabase config, TTS voices
│   │   └── types/               # TypeScript interfaces
│   └── package.json
│
├── backend-fastapi/             # FastAPI backend
│   ├── app/
│   │   ├── main.py              # All routes, webhooks, copilot pipeline
│   │   ├── ai_client.py         # Gemini streaming, TTS, embeddings, fact-check
│   │   ├── context_pipeline.py  # RAG: URL fetch, chunking, embedding, search
│   │   ├── recall_client.py     # Recall.ai API (create bot, transcript, audio)
│   │   ├── output_media.py      # Audio injection + screenshot capture
│   │   ├── github_ingest.py     # GitHub repo RAG ingestion
│   │   ├── post_meeting_email.py# Post-meeting email via Resend
│   │   ├── auth_deps.py         # JWT validation
│   │   ├── config.py            # Environment config
│   │   └── db.py                # Supabase client
│   ├── tests/                   # ~1800 lines, pytest-asyncio
│   ├── Dockerfile
│   └── pyproject.toml
│
├── bot-page/                    # Runs inside Recall's headless Chrome
│   └── index.html               # Trigger detection, visual status display
│
├── .github/workflows/
│   └── deploy-backend-cloud-run.yml  # CI: test → deploy
│
├── SETUP.md                     # Complete setup guide with SQL migrations
└── README.md                    # This file
```

---

## How the Copilot Works

### Real-Time Q&A Flow

```
User speaks: "Hey Sam, what's the deadline for the API migration?"
                    │
                    ▼
         Recall.ai streams transcript
                    │
                    ▼
         Bot page detects trigger ("Sam" + question)
                    │
                    ▼
         WebSocket → Backend (/ws/copilot/{meeting_id})
                    │
           ┌────────┴────────┐
           ▼                 ▼
    pgvector search    Fetch recent
    (top 3 chunks)     transcript (20 lines)
           │                 │
           └────────┬────────┘
                    ▼
         Gemini 2.5-flash streams answer
         (grounded in knowledge base)
                    │
                    ▼
         Google Cloud TTS → MP3
                    │
                    ▼
         Recall inject_audio API → plays in meeting
                    │
                    ▼
         Saved to meeting_interactions table
```

### Proactive Fact-Checking

When someone makes a declarative statement (8+ words, not a question), the system automatically checks it against the knowledge base:

1. Gemini evaluates: does the statement contradict verified project docs?
2. If yes → speaks a diplomatic correction: *"Actually, the correct figure is..."*
3. If no contradiction → stays silent (no false positives)
4. Rate-limited: 28s cooldown, max 12 checks/hour

### Screenshot Capture

Say "take a screenshot" → Recall API captures the meeting view → uploaded to Supabase Storage → visible in meeting dashboard.

### Post-Meeting Intelligence

When the meeting ends:
1. Full transcript downloaded from Recall.ai
2. Gemini 2.5-pro generates: summary, action items, key decisions
3. Optionally emailed via Resend

---

## Quick Start

### Prerequisites

- Node.js 18+, Python 3.12+
- GCP project with Vertex AI + Cloud TTS enabled
- Supabase project
- Recall.ai account
- ngrok (for local webhook tunneling)

### 1. Clone and install

```bash
git clone https://github.com/prabhakar1234pr/meetstreamIQ.git
cd meetstreamIQ

# Backend
cd backend-fastapi
pip install uv && uv sync
cd ..

# Frontend
cd frontend
npm install
cd ..
```

### 2. Set up Supabase

Run the SQL migrations from [SETUP.md](./SETUP.md#1-supabase-setup) in your Supabase SQL editor. This creates the required tables: `context_chunks`, `meeting_interactions`, and adds columns to `agents` and `meetings`.

### 3. Set up GCP

```bash
# Enable required APIs
gcloud services enable \
  aiplatform.googleapis.com \
  texttospeech.googleapis.com \
  run.googleapis.com \
  --project YOUR_PROJECT_ID

# Create service account
gcloud iam service-accounts create briefed-backend
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:briefed-backend@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:briefed-backend@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudtexttospeech.user"

# Download key for local dev
gcloud iam service-accounts keys create gcp-sa-key.json \
  --iam-account briefed-backend@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

### 4. Configure environment

**Backend** (`backend-fastapi/.env`):
```env
RECALL_API_KEY=your_recall_api_key
PUBLIC_API_BASE=https://YOUR-DOMAIN.ngrok-free.app
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_JWT_SECRET=your_jwt_secret
GCP_PROJECT=your-project-id
GCP_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/gcp-sa-key.json
CORS_ORIGINS=http://localhost:3000
```

**Frontend** (`frontend/.env`):
```env
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### 5. Start ngrok + dev servers

```bash
# Terminal 1 — ngrok (required for Recall.ai webhooks)
ngrok http --domain=YOUR-DOMAIN.ngrok-free.app 8000

# Terminal 2 — Backend
cd backend-fastapi
uv run uvicorn app.main:app --reload --port 8000

# Terminal 3 — Frontend
cd frontend
npm run dev
```

### 6. Configure Recall.ai webhooks

In the [Recall.ai dashboard](https://app.recall.ai):
1. **Webhooks → Add Endpoint**
2. URL: `https://YOUR-DOMAIN.ngrok-free.app/api/webhooks/recall/bot-status`
3. Select all `bot.*` events

### 7. Test it

1. Open `http://localhost:3000` → Sign in with Google
2. Create an agent → add knowledge sources (URLs, GitHub repos, or text)
3. Start a meeting → paste a Google Meet/Zoom/Teams link
4. Say "Hey [AgentName], what is this project about?"
5. Hear the answer spoken in the meeting

---

## Deployment

### Backend → Cloud Run (via GitHub Actions)

Every push to `main` that changes `backend-fastapi/` triggers:
1. Run pytest
2. Build Docker image
3. Deploy to Cloud Run

Required GitHub secrets:
- `GCP_SA_KEY` — Service account JSON (base64 encoded)

Environment variables are set on Cloud Run via the workflow.

### Frontend → Vercel

Auto-deploys on push. Set these env vars in Vercel:
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_API_BASE_URL` (Cloud Run URL)

### Bot Page → GCS

```bash
gcloud storage cp bot-page/index.html \
  gs://briefed-bot-page/index.html \
  --cache-control="no-cache, no-store, max-age=0" \
  --content-type="text/html"
```

---

## API Endpoints

### REST

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/meetings/start` | Start meeting (creates Recall bot) |
| `GET` | `/api/meetings/{id}` | Get meeting details + transcript |
| `GET` | `/api/meetings/{id}/interactions` | Get Q&A, fact-checks, screenshots |
| `POST` | `/api/agents/{id}/context` | Add knowledge source (URL/text/GitHub) |
| `GET` | `/api/agents/{id}/context` | List agent's knowledge sources |
| `DELETE` | `/api/agents/{id}/context` | Remove knowledge source |
| `POST` | `/api/agents/{id}/ask` | Ask agent a question (non-streaming) |
| `POST` | `/api/webhooks/recall/bot-status` | Recall.ai bot lifecycle events |
| `POST` | `/api/webhooks/recall/realtime` | Recall.ai real-time transcript |

### WebSocket

| Path | Description |
|------|-------------|
| `/ws/copilot/{meeting_id}` | Real-time copilot: trigger → Gemini stream → TTS → inject |

---

## Database Schema

| Table | Purpose |
|-------|---------|
| `agents` | Agent config: name, persona, voice, capabilities |
| `meetings` | Meeting records: status, transcript, summary, action items |
| `transcript_lines` | Raw transcript segments with speaker + timestamp |
| `context_chunks` | Chunked documents with 768-dim pgvector embeddings |
| `meeting_interactions` | Logged Q&A, fact-checks, screenshots |
| `screenshots` | Screenshot metadata + Supabase Storage paths |

---

## Environment Variables

### Backend

| Variable | Required | Description |
|----------|----------|-------------|
| `RECALL_API_KEY` | Yes | Recall.ai API key |
| `PUBLIC_API_BASE` | Yes | Backend's public URL (ngrok or Cloud Run) |
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Supabase service role key |
| `SUPABASE_JWT_SECRET` | Yes | Supabase JWT secret |
| `GCP_PROJECT` | Yes | GCP project ID |
| `GCP_LOCATION` | No | Default: `us-central1` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Local only | Path to SA key JSON |
| `CORS_ORIGINS` | Production | Comma-separated allowed origins |
| `VERTEX_GEMINI_MODEL` | No | Default: `gemini-2.5-pro` |
| `LIVE_QA_MODEL` | No | Default: `gemini-2.5-flash` |
| `WEBHOOK_SECRET` | No | Recall webhook signing secret |
| `RESEND_API_KEY` | No | For post-meeting emails |
| `CARTESIA_API_KEY` | No | For Output Media TTS (legacy) |
| `BOT_PAGE_URL` | No | Default: GCS-hosted HTML |

### Frontend

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Supabase anonymous key |
| `NEXT_PUBLIC_API_BASE_URL` | Yes | Backend URL |

---

## Testing

```bash
cd backend-fastapi
uv sync --extra dev
uv run pytest tests/ -v
```

Tests use an in-memory `FakeSupabase` mock — no real database needed. Covers: trigger detection, copilot pipeline, WebSocket handler, screenshot flow, auth, webhooks, and context ingestion.

---

## License

Proprietary. All rights reserved.
