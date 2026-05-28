import os
from functools import lru_cache


@lru_cache
def get_settings() -> dict[str, str | None]:
    return {
        # Recall.ai
        "recall_api_key": os.getenv("RECALL_API_KEY", "").strip() or None,
        "recall_api_base": os.getenv("RECALL_API_BASE", "https://us-east-1.recall.ai").rstrip("/"),

        # Public URL for Recall.ai webhooks (ngrok locally, Cloud Run URL in prod)
        "public_api_base": os.getenv("PUBLIC_API_BASE", "").strip().rstrip("/") or None,

        # Supabase
        "supabase_url": os.getenv("SUPABASE_URL", "").strip().rstrip("/") or None,
        "supabase_service_role_key": os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip() or None,
        "supabase_jwt_secret": os.getenv("SUPABASE_JWT_SECRET", "").strip() or None,

        # Google Cloud (Vertex AI + TTS)
        "gcp_project": os.getenv("GCP_PROJECT", "").strip() or None,
        "gcp_location": os.getenv("GCP_LOCATION", "us-central1").strip(),
        "google_application_credentials": os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip() or None,

        # Gemini models
        # Post-meeting intelligence (summaries) — use Pro for quality
        "vertex_gemini_model": (
            os.getenv("VERTEX_GEMINI_MODEL", "gemini-2.5-pro").strip() or "gemini-2.5-pro"
        ),
        # Live Q&A model — gemini-2.5-flash for low latency first token.
        # gemini-2.5-pro available as fallback for higher quality if needed.
        "live_qa_model": (
            os.getenv("LIVE_QA_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
        ),

        # Optional: require Authorization: Bearer <secret> on Recall webhooks
        "webhook_secret": os.getenv("WEBHOOK_SECRET", "").strip() or None,

        # Optional post-meeting email (Resend)
        "resend_api_key": os.getenv("RESEND_API_KEY", "").strip() or None,
        "resend_from": os.getenv("RESEND_FROM", "").strip() or None,

        # Optional: higher rate limits & private repos for GitHub RAG ingest
        "github_token": os.getenv("GITHUB_TOKEN", "").strip() or None,

        # CORS (comma-separated origins)
        "cors_origins": os.getenv("CORS_ORIGINS", "").strip() or None,

        # Output Media bot page URL (GCS-hosted)
        "bot_page_url": (
            os.getenv("BOT_PAGE_URL", "https://storage.googleapis.com/briefed-bot-page/index.html").strip()
        ),

        # Unkey (rate limiting + API key management)
        "unkey_root_key": os.getenv("UNKEY_ROOT_KEY", "").strip() or None,
        "unkey_api_id": os.getenv("UNKEY_API_ID", "").strip() or None,

        # ── v2 voice pipeline ────────────────────────────────────────────────
        # Deepgram streaming STT (replaces Recall webhook STT)
        "deepgram_api_key": os.getenv("DEEPGRAM_API_KEY", "").strip() or None,
        "deepgram_model": os.getenv("DEEPGRAM_MODEL", "nova-3").strip() or "nova-3",

        # ElevenLabs streaming TTS (replaces Google Cloud TTS for live voice)
        "elevenlabs_api_key": os.getenv("ELEVENLABS_API_KEY", "").strip() or None,
        "elevenlabs_model": os.getenv("ELEVENLABS_MODEL", "eleven_flash_v2_5").strip() or "eleven_flash_v2_5",
        "elevenlabs_default_voice": os.getenv("ELEVENLABS_DEFAULT_VOICE", "21m00Tcm4TlvDq8ikWAM").strip() or "21m00Tcm4TlvDq8ikWAM",

        # ── v2 observability ─────────────────────────────────────────────────
        "langsmith_api_key": os.getenv("LANGSMITH_API_KEY", "").strip() or None,
        "langsmith_project": os.getenv("LANGSMITH_PROJECT", "briefed-dev").strip() or "briefed-dev",
        "langsmith_tracing": (os.getenv("LANGSMITH_TRACING", "").strip().lower() in {"1", "true", "yes"}),

        # ── v2 memory ────────────────────────────────────────────────────────
        # Supermemory replaces pgvector for unified doc + meeting + code memory
        "supermemory_api_key": os.getenv("SUPERMEMORY_API_KEY", "").strip() or None,

        # ── v2 auth (Firebase replaces Clerk) ────────────────────────────────
        "firebase_project_id": os.getenv("FIREBASE_PROJECT_ID", "").strip() or None,
        "firebase_client_email": os.getenv("FIREBASE_CLIENT_EMAIL", "").strip() or None,
        # Multi-line PEM — env stores literal "\n", we unescape here.
        "firebase_private_key": (
            os.getenv("FIREBASE_PRIVATE_KEY", "").strip().replace("\\n", "\n") or None
        ),

        # ── v2 GitHub App (live code memory) ─────────────────────────────────
        "github_app_id": os.getenv("GITHUB_APP_ID", "").strip() or None,
        "github_app_private_key": (
            os.getenv("GITHUB_APP_PRIVATE_KEY", "").strip().replace("\\n", "\n") or None
        ),
        "github_app_webhook_secret": os.getenv("GITHUB_APP_WEBHOOK_SECRET", "").strip() or None,
        # URL-safe name of your GitHub App (the slug in https://github.com/apps/<slug>)
        "github_app_slug": os.getenv("GITHUB_APP_SLUG", "briefed").strip() or "briefed",
    }
