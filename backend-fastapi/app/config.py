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

        # Cloud SQL (PostgreSQL) — replaces Supabase
        # On Cloud Run set CLOUD_SQL_CONNECTION_NAME (project:region:instance);
        # locally set DB_HOST to the instance public IP. See app/sql.py.
        "cloud_sql_connection_name": os.getenv("CLOUD_SQL_CONNECTION_NAME", "").strip() or None,
        "db_host": os.getenv("DB_HOST", "").strip() or None,
        "db_name": os.getenv("DB_NAME", "briefed").strip() or "briefed",
        "db_user": os.getenv("DB_USER", "postgres").strip() or "postgres",
        "db_pass": os.getenv("DB_PASS", "").strip() or None,
        # GCS bucket for meeting screenshots (replaces Supabase Storage)
        "screenshots_bucket": os.getenv("SCREENSHOTS_BUCKET", "").strip() or None,

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
            os.getenv("BOT_PAGE_URL", "https://storage.googleapis.com/briefed-42540-bot-page/index.html").strip()
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

        # ── Nebius (always-on turn-taking gate) ───────────────────────────────
        # OpenAI-compatible. Cheap Qwen MoE decides if the bot has something worth
        # saying; on a confident YES the bot raises its hand (it never auto-speaks).
        "nebius_api_key": os.getenv("NEBIUS_API_KEY", "").strip() or None,
        "nebius_api_base": (
            os.getenv("NEBIUS_API_BASE", "https://api.tokenfactory.nebius.com/v1").strip()
            or "https://api.tokenfactory.nebius.com/v1"
        ),
        "nebius_trigger_model": (
            os.getenv("NEBIUS_TRIGGER_MODEL", "Qwen/Qwen3-30B-A3B-Instruct-2507").strip()
            or "Qwen/Qwen3-30B-A3B-Instruct-2507"
        ),
        # Confidence above which Bora raises its hand. Parsed to float by the gate.
        "nebius_speak_threshold": os.getenv("NEBIUS_SPEAK_THRESHOLD", "0.7").strip() or "0.7",
        # Seconds to keep the hand raised waiting for permission before lowering it.
        "nebius_hand_timeout": os.getenv("NEBIUS_HAND_TIMEOUT", "20").strip() or "20",

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
