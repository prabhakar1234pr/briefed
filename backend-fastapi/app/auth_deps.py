"""Firebase ID-token validation.

Validates Firebase ID tokens issued to the frontend. (The legacy Supabase JWT
fallback was removed with the Cloud SQL migration — Firebase is the only issuer.)
"""

from typing import Annotated, Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

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


# ─── FastAPI dependency ───────────────────────────────────────────────────────
def get_user_id(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> str:
    """
    Resolve the requesting user's ID from the Authorization: Bearer <token> header.

    Validates the Firebase ID token and returns the user's `sub` (Firebase UID).
    """
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token")

    try:
        payload = _verify_firebase_id_token(creds.credentials)
    except Exception as e:
        log.debug("firebase_verify_failed", error=str(e)[:160])
        raise HTTPException(status_code=401, detail="Invalid token") from e

    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise HTTPException(status_code=401, detail="Invalid token subject")
    return sub
