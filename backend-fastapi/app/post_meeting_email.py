"""
Optional post-meeting brief email via Resend (https://resend.com).
Requires RESEND_API_KEY; otherwise skipped with an info log.
"""
import html
from typing import Any

import httpx

from app.config import get_settings
from app.logger import get_logger

log = get_logger(__name__)


def _get_user_email(db: Any, user_id: str) -> str | None:
    """
    Fetch user email. Tries two approaches:
    1. Supabase Auth Admin API (auth.users — where Supabase stores emails)
    2. Fallback: public.users table (if synced via DB trigger)
    """
    # Approach 1: Supabase Auth Admin API
    try:
        user = db.auth.admin.get_user_by_id(user_id)
        if user and hasattr(user, "user") and user.user:
            email = getattr(user.user, "email", None)
            if email:
                log.debug("user_email_from_auth", user_id=user_id, email=email)
                return email
    except Exception as e:
        log.debug("auth_admin_lookup_failed", user_id=user_id, error=str(e))

    # Approach 2: public.users table fallback
    try:
        u_res = db.table("users").select("email").eq("id", user_id).limit(1).execute()
        email = (u_res.data or [{}])[0].get("email")
        if email:
            log.debug("user_email_from_table", user_id=user_id, email=email)
            return email
    except Exception as e:
        log.debug("users_table_lookup_failed", user_id=user_id, error=str(e))

    return None


async def try_send_post_meeting_brief(
    db: Any,
    *,
    meeting_id: str,
    user_id: str,
    agent_id: str | None,
    intel: dict[str, Any] | None,
) -> None:
    if not intel or not intel.get("summary"):
        log.info("email_skip_no_intel", meeting_id=meeting_id)
        return

    if not agent_id:
        log.info("email_skip_no_agent", meeting_id=meeting_id)
        return

    ag_res = (
        db.table("agents")
        .select("send_post_meeting_email, name")
        .eq("id", agent_id)
        .limit(1)
        .execute()
    )
    if not ag_res.data:
        log.warning("email_skip_agent_not_found", meeting_id=meeting_id, agent_id=agent_id)
        return

    email_enabled = ag_res.data[0].get("send_post_meeting_email")
    if not email_enabled:
        log.info("email_skip_disabled_on_agent",
                 meeting_id=meeting_id, agent_id=agent_id,
                 field_value=email_enabled)
        return

    to_email = _get_user_email(db, user_id)
    if not to_email:
        log.warning("email_skip_no_user_email",
                     meeting_id=meeting_id, user_id=user_id,
                     hint="User email not found. Supabase Auth emails live in auth.users — "
                          "ensure the service role key has auth admin access, or sync emails "
                          "to a public.users table via a DB trigger.")
        return

    s = get_settings()
    api_key = s.get("resend_api_key")
    if not api_key:
        log.warning("email_skip_no_resend_key",
                     meeting_id=meeting_id,
                     hint="Set RESEND_API_KEY env var to enable post-meeting emails.")
        return

    from_addr = s.get("resend_from") or "Briefed <onboarding@resend.dev>"
    agent_name = ag_res.data[0].get("name") or "Briefed"

    summary = str(intel.get("summary") or "")
    items = intel.get("action_items") or []
    decs = intel.get("key_decisions") or []
    if not isinstance(items, list):
        items = []
    if not isinstance(decs, list):
        decs = []

    def esc(x: str) -> str:
        return html.escape(x, quote=True)

    li_items = "".join(f"<li>{esc(str(x))}</li>" for x in items[:30])
    li_decs = "".join(f"<li>{esc(str(x))}</li>" for x in decs[:30])

    body = f"""<h2>Meeting brief</h2>
<p><strong>{esc(agent_name)}</strong> · meeting <code>{esc(meeting_id[:8])}…</code></p>
<h3>Summary</h3>
<p>{esc(summary)}</p>
<h3>Action items</h3>
<ul>{li_items or "<li>—</li>"}</ul>
<h3>Key decisions</h3>
<ul>{li_decs or "<li>—</li>"}</ul>
"""

    payload = {
        "from": from_addr,
        "to": [to_email],
        "subject": f"Meeting brief — {agent_name}",
        "html": body,
    }

    log.info("email_sending",
             meeting_id=meeting_id, to=to_email, agent=agent_name)

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(
                "https://api.resend.com/emails",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if r.is_success:
                log.info("email_sent", meeting_id=meeting_id, to=to_email)
            else:
                log.error("email_resend_error",
                          meeting_id=meeting_id,
                          status=r.status_code,
                          response=r.text[:300])
    except Exception as e:
        log.exception("email_send_failed", meeting_id=meeting_id, error=str(e))
