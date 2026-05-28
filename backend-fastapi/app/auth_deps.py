"""Firebase + Supabase JWT validation.

Validates Firebase ID tokens issued to the frontend.
Falls back to Supabase JWKS for the WS bot-bridge path (signed by Supabase JWT secret).
"""

from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.config import get_settings
from app.logger import get_logger

log = get_logger(__name__)
security = HTTPBearer(auto_error=False)


# ─── Firebase Admin SDK (lazy init) ───────────────────────────────────────────
_firebase_app: Any = None


def _get_firebase_app() -> Any:
    """Initialize the Firebase Admin SDK once. Returns the default app."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app
    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError as e:
        raise RuntimeError(
            "firebase-admin not installed. Add it to pyproject.toml and `uv sync`."
        ) from e

    settings = get_settings()
    project_id = settings.get("firebase_project_id")
    client_email = settings.get("firebase_client_email")
    private_key = settings.get("firebase_private_key")
    if not (project_id and client_email and private_key):
        raise RuntimeError(
            "FIREBASE_PROJECT_ID, FIREBASE_CLIENT_EMAIL, FIREBASE_PRIVATE_KEY must be set."
        )

    try:
        _firebase_app = firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate({
            "type": "service_account",
            "project_id": project_id,
            "client_email": client_email,
            "private_key": private_key,
            "token_uri": "https://oauth2.googleapis.com/token",
        })
        _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


def _verify_firebase_id_token(token: str) -> dict[str, Any]:
    """Verify a Firebase ID token. Returns decoded claims with `sub` = Firebase UID."""
    from firebase_admin import auth as fb_auth
    _get_firebase_app()  # ensure init
    # check_revoked=False keeps this fast; rotate keys via Firebase if a token is compromised.
    decoded = fb_auth.verify_id_token(token, check_revoked=False)
    # Firebase puts the UID in both "uid" and "sub". Normalize to "sub".
    if "sub" not in decoded and "uid" in decoded:
        decoded["sub"] = decoded["uid"]
    return decoded


# ─── Supabase JWT fallback (for bot-bridge WebSocket) ─────────────────────────
@lru_cache(maxsize=8)
def _supabase_jwks_client(supabase_url: str) -> PyJWKClient:
    base = supabase_url.rstrip("/")
    return PyJWKClient(f"{base}/auth/v1/.well-known/jwks.json")


def _decode_supabase_fallback(token: str, supabase_url: str) -> dict:
    client = _supabase_jwks_client(supabase_url)
    signing_key = client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256", "RS256"],
        audience="authenticated",
        options={"verify_aud": True},
    )


# ─── FastAPI dependency ───────────────────────────────────────────────────────
def get_user_id(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> str:
    """
    Resolve the requesting user's ID from the Authorization: Bearer <token> header.

    Tries Firebase ID token first (the frontend's default), falls back to Supabase
    JWT (used by some legacy / WS paths). Returns the user's `sub` (Firebase UID
    or Supabase auth user UUID).
    """
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token")

    settings = get_settings()
    supabase_url = settings.get("supabase_url")
    token = creds.credentials
    payload: dict | None = None

    # Try Firebase first
    try:
        payload = _verify_firebase_id_token(token)
    except Exception as e:
        log.debug("firebase_verify_failed", error=str(e)[:160])
        payload = None

    # Fallback to Supabase-signed JWT
    if payload is None and supabase_url:
        try:
            payload = _decode_supabase_fallback(token, supabase_url)
        except jwt.PyJWTError as e:
            log.debug("supabase_verify_failed", error=str(e)[:160])
            payload = None

    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise HTTPException(status_code=401, detail="Invalid token subject")
    return sub


# Backwards-compatible alias
get_supabase_user_id = get_user_id
