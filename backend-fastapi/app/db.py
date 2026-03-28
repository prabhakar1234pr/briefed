from supabase import Client, create_client

from app.config import get_settings


def get_supabase_service() -> Client:
    s = get_settings()
    url = s["supabase_url"]
    key = s["supabase_service_role_key"]
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    return create_client(url, key)
