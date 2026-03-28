"""Rich seed records mimicking production-shaped Supabase rows."""

USER_ID = "user-e2e-9f3c"
USER_EMAIL = "testuser@briefed-e2e.test"

AGENT_COPILOT = {
    "id": "agent-copilot-aa11",
    "user_id": USER_ID,
    "name": "Pal",
    "mode": "copilot",
    "persona_prompt": "You are a concise engineering copilot. Prefer actionable answers.",
    "voice_id": "en-US-Neural2-J",
    "proactive_fact_check": False,
    "screenshot_on_request": True,
    "send_post_meeting_email": True,
    "bot_image_url": None,
}

AGENT_FACTCHECK = {
    "id": "agent-factcheck-ff33",
    "user_id": USER_ID,
    "name": "FactBot",
    "mode": "copilot",
    "persona_prompt": "You are a meticulous fact-checker.",
    "voice_id": "en-US-Neural2-D",
    "proactive_fact_check": True,
    "screenshot_on_request": False,
    "send_post_meeting_email": False,
    "bot_image_url": None,
}

AGENT_PROCTOR = {
    "id": "agent-proctor-bb22",
    "user_id": USER_ID,
    "name": "Proctor-AI",
    "mode": "proctor",
    "persona_prompt": "Interview integrity assistant.",
    "voice_id": "en-US-Neural2-D",
    "proactive_fact_check": False,
    "screenshot_on_request": False,
    "send_post_meeting_email": False,
    "bot_image_url": None,
}

AGENT_NO_EMAIL = {
    "id": "agent-noemail-ee44",
    "user_id": USER_ID,
    "name": "NoMailBot",
    "mode": "copilot",
    "persona_prompt": None,
    "voice_id": "en-US-Neural2-J",
    "proactive_fact_check": False,
    "screenshot_on_request": True,
    "send_post_meeting_email": False,
    "bot_image_url": None,
}

MEETING_LIVE = {
    "id": "meet-live-cc33",
    "user_id": USER_ID,
    "agent_id": AGENT_COPILOT["id"],
    "meeting_link": "https://meet.google.com/abc-defg-hij",
    "bot_id": "recall-bot-dd44",
    "status": "in_meeting",
    "transcript_text": None,
    "summary": None,
    "action_items": None,
    "key_decisions": None,
    "video_url": None,
    "audio_url": None,
    "created_at": "2025-03-24T18:00:00+00:00",
    "updated_at": "2025-03-24T18:05:00+00:00",
    "scheduled_at": None,
    "joined_at": "2025-03-24T18:01:00+00:00",
    "ended_at": None,
}

MEETING_DONE = {
    "id": "meet-done-ff55",
    "user_id": USER_ID,
    "agent_id": AGENT_COPILOT["id"],
    "meeting_link": "https://meet.google.com/done-meeting",
    "bot_id": "recall-bot-done-66",
    "status": "processing",
    "transcript_text": None,
    "summary": None,
    "action_items": None,
    "key_decisions": None,
    "video_url": None,
    "audio_url": None,
    "created_at": "2025-03-24T17:00:00+00:00",
    "updated_at": "2025-03-24T18:00:00+00:00",
    "scheduled_at": None,
    "joined_at": "2025-03-24T17:01:00+00:00",
    "ended_at": "2025-03-24T18:00:00+00:00",
}

TRANSCRIPT_LINES = [
    {
        "id": "tl-001",
        "meeting_id": MEETING_LIVE["id"],
        "speaker_name": "Alex Rivera",
        "content": "Let's walk through the Q2 roadmap milestones.",
        "spoken_at": "2025-03-24T18:02:00+00:00",
        "words": None,
    },
    {
        "id": "tl-002",
        "meeting_id": MEETING_LIVE["id"],
        "speaker_name": "Jordan Lee",
        "content": "Pal, what did we decide last week about the API rate limits?",
        "spoken_at": "2025-03-24T18:03:00+00:00",
        "words": None,
    },
]

CONTEXT_CHUNKS = [
    {
        "id": "cc-001",
        "agent_id": AGENT_COPILOT["id"],
        "source_url": "https://github.com/acme/platform/blob/main/README.md",
        "content": "[acme/platform: README] Rate limits: 1000 req/min per workspace for REST; burst 120.",
        "created_at": "2025-03-20T12:00:00+00:00",
    },
    {
        "id": "cc-002",
        "agent_id": AGENT_COPILOT["id"],
        "source_url": "https://github.com/acme/platform/blob/main/README.md",
        "content": "[acme/platform: README] Authentication uses JWT with RS256.",
        "created_at": "2025-03-20T12:01:00+00:00",
    },
    {
        "id": "cc-003",
        "agent_id": AGENT_COPILOT["id"],
        "source_url": "manual",
        "content": "Release freeze starts April 1; only P0 fixes merge.",
        "created_at": "2025-03-21T09:00:00+00:00",
    },
]

MEETING_INTERACTION = {
    "id": "mi-001",
    "meeting_id": MEETING_LIVE["id"],
    "interaction_type": "qa",
    "trigger_text": "Pal, what did we decide last week about the API rate limits?",
    "response_text": "Last week we locked 1000 requests per minute per workspace.",
    "spoken_at": "2025-03-24T18:03:15+00:00",
    "created_at": "2025-03-24T18:03:16+00:00",
    "screenshot_url": None,
    "audio_url": None,
}


# ─── Auth users (Supabase auth.users equivalent) ─────────────────────────────

AUTH_USERS = {
    USER_ID: USER_EMAIL,
}


def seed_tables() -> dict[str, list[dict]]:
    return {
        "agents": [
            {**AGENT_COPILOT},
            {**AGENT_PROCTOR},
            {**AGENT_FACTCHECK},
            {**AGENT_NO_EMAIL},
        ],
        "meetings": [{**MEETING_LIVE}, {**MEETING_DONE}],
        "transcript_lines": [{**r} for r in TRANSCRIPT_LINES],
        "context_chunks": [{**r} for r in CONTEXT_CHUNKS],
        "meeting_interactions": [{**MEETING_INTERACTION}],
        "screenshots": [],
        "users": [],  # empty — email should come from auth.admin
    }
