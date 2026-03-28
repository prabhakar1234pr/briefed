# backend-fastapi

## Run (local)

Copy `.env.example` to `.env` and set at least:

- `RECALL_API_KEY` — from [Recall.ai](https://www.recall.ai/) (use `RECALL_API_BASE` for your region, e.g. `https://us-east-1.recall.ai`)
- `PUBLIC_API_BASE` — public URL of this API (use [ngrok](https://ngrok.com/) or similar so Recall.ai can POST realtime webhooks)
- In the Recall dashboard, add a **bot status** webhook URL: `{PUBLIC_API_BASE}/api/webhooks/recall/bot-status`
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET` (Dashboard → Settings → API)

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

## Cloud Run (gcloud)

Requires **billing enabled** on the GCP project.

```bash
gcloud config set project meetstreamiq
gcloud run deploy backend-fastapi --source=./backend-fastapi --region=us-central1 --allow-unauthenticated
```

Set CORS for your Vercel frontend URL (comma-separated):

```bash
gcloud run services update backend-fastapi --region=us-central1 --set-env-vars="CORS_ORIGINS=https://YOUR-APP.vercel.app"
```

## GitHub Actions CI/CD

Workflow: `.github/workflows/deploy-backend-cloud-run.yml` (runs only when `backend-fastapi/` changes).
