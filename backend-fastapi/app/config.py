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

        # Cartesia TTS (for Output Media mode)
        "cartesia_api_key": (
            os.getenv("CARTESIA_API_KEY", "").strip()
            or os.getenv("Cartesia_API_key", "").strip()  # compat with .env naming
            or None
        ),

        # Output Media bot page URL (GCS-hosted)
        "bot_page_url": (
            os.getenv("BOT_PAGE_URL", "https://storage.googleapis.com/briefed-bot-page/index.html").strip()
        ),

        # Unkey (rate limiting + API key management)
        "unkey_root_key": os.getenv("UNKEY_ROOT_KEY", "").strip() or None,
        "unkey_api_id": os.getenv("UNKEY_API_ID", "").strip() or None,

        # WorkOS (authentication)
        "workos_api_key": (
            os.getenv("WORKOS_API_KEY", "").strip()
            or os.getenv("WorkOS_API_KEY", "").strip()  # compat with .env naming
            or None
        ),
        "workos_client_id": (
            os.getenv("WORKOS_CLIENT_ID", "").strip()
            or os.getenv("workOS_ClientID", "").strip()  # compat with .env naming
            or None
        ),
    }
