-- ============================================================================
-- Briefed — Cloud SQL (PostgreSQL 16) schema
-- ============================================================================
-- Exact replica of the former Supabase `public` schema, adapted for Cloud SQL.
--
-- Differences from Supabase (intentional):
--   * No Supabase `auth` schema / RLS policies. Access control is enforced in
--     the FastAPI backend (every query filters by user_id). The backend
--     connects as a single DB role, so RLS would be a no-op here anyway.
--   * uuid defaults use the built-in `gen_random_uuid()` (pgcrypto, ships with
--     PG16) instead of `extensions.uuid_generate_v4()`.
--   * pgvector is created via `CREATE EXTENSION vector` (Cloud SQL supports it).
--
-- Apply with: python db/apply_schema.py   (uses the Cloud SQL connector)
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ─── users ──────────────────────────────────────────────────────────────────
-- id is the Firebase UID (text), NOT a uuid.
CREATE TABLE IF NOT EXISTS public.users (
    id          text PRIMARY KEY,
    email       text NOT NULL UNIQUE,
    full_name   text,
    avatar_url  text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

-- ─── agents ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.agents (
    id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                  text NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    name                     text NOT NULL,
    description              text,
    mode                     text NOT NULL DEFAULT 'copilot'
                                 CHECK (mode = ANY (ARRAY['copilot'::text, 'proctor'::text])),
    persona_prompt           text,
    voice_id                 text,
    bot_image_url            text,
    proactive_fact_check     boolean NOT NULL DEFAULT true,
    screenshot_on_request    boolean NOT NULL DEFAULT true,
    send_post_meeting_email  boolean NOT NULL DEFAULT true,
    created_at               timestamptz NOT NULL DEFAULT now(),
    updated_at               timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS agents_user_id_idx ON public.agents USING btree (user_id);

-- ─── meetings ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.meetings (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         text NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    agent_id        uuid NOT NULL REFERENCES public.agents(id) ON DELETE CASCADE,
    meeting_link    text NOT NULL,
    bot_id          text,
    status          text NOT NULL DEFAULT 'scheduled'
                        CHECK (status = ANY (ARRAY['scheduled'::text, 'joining'::text,
                              'in_meeting'::text, 'processing'::text, 'completed'::text, 'failed'::text])),
    copilot_mode    text NOT NULL DEFAULT 'output_audio',
    transcript_text text,
    summary         text,
    action_items    text,
    key_decisions   text,
    audio_url       text,
    video_url       text,
    scheduled_at    timestamptz,
    joined_at       timestamptz,
    ended_at        timestamptz,
    email_sent      boolean NOT NULL DEFAULT false,
    email_sent_at   timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    bridge_token    text  -- v2 voice pipeline: per-meeting auth token for the bot-page WebSocket bridge.
);
CREATE INDEX IF NOT EXISTS meetings_user_id_idx  ON public.meetings USING btree (user_id);
CREATE INDEX IF NOT EXISTS meetings_agent_id_idx ON public.meetings USING btree (agent_id);
CREATE INDEX IF NOT EXISTS meetings_status_idx   ON public.meetings USING btree (status);

-- ─── transcript_lines ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.transcript_lines (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id   uuid NOT NULL REFERENCES public.meetings(id) ON DELETE CASCADE,
    speaker_name text,
    content      text NOT NULL,
    spoken_at    timestamptz NOT NULL DEFAULT now(),
    words        jsonb
);
CREATE INDEX IF NOT EXISTS transcript_lines_meeting_id_idx ON public.transcript_lines USING btree (meeting_id);

-- ─── context_chunks ─────────────────────────────────────────────────────────
-- embedding is pgvector dim 768 (Gemini text-embedding-004 size).
CREATE TABLE IF NOT EXISTS public.context_chunks (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id     uuid NOT NULL REFERENCES public.agents(id) ON DELETE CASCADE,
    source_url   text NOT NULL,
    content      text NOT NULL,
    content_hash text NOT NULL,
    embedding    vector(768),
    created_at   timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS context_chunks_agent_id_idx ON public.context_chunks USING btree (agent_id);
CREATE INDEX IF NOT EXISTS context_chunks_embedding_idx
    ON public.context_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ─── meeting_interactions ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.meeting_interactions (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id       uuid NOT NULL REFERENCES public.meetings(id) ON DELETE CASCADE,
    interaction_type text NOT NULL
                         CHECK (interaction_type = ANY (ARRAY['qa'::text, 'factcheck'::text, 'screenshot'::text])),
    trigger_text     text,
    response_text    text,
    screenshot_b64   text,
    screenshot_url   text,
    audio_url        text,
    spoken_at        timestamptz,
    created_at       timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS meeting_interactions_meeting_id_idx ON public.meeting_interactions USING btree (meeting_id);

-- ─── screenshots ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.screenshots (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id   uuid NOT NULL REFERENCES public.meetings(id) ON DELETE CASCADE,
    storage_path text NOT NULL,
    taken_at     timestamptz NOT NULL DEFAULT now(),
    triggered_by text
);
CREATE INDEX IF NOT EXISTS screenshots_meeting_id_idx ON public.screenshots USING btree (meeting_id);

-- ─── agent_github_sources ───────────────────────────────────────────────────
-- Phase 4b: GitHub repos connected to agents. Webhook keeps memory fresh on push.
CREATE TABLE IF NOT EXISTS public.agent_github_sources (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id         uuid NOT NULL REFERENCES public.agents(id) ON DELETE CASCADE,
    repo_full_name   text NOT NULL,
    branch           text NOT NULL DEFAULT 'main',
    installation_id  bigint,
    webhook_secret   text NOT NULL,
    last_synced_sha  text,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now(),
    UNIQUE (agent_id, repo_full_name, branch)
);
CREATE INDEX IF NOT EXISTS agent_github_sources_repo_branch_idx
    ON public.agent_github_sources USING btree (repo_full_name, branch);

-- ─── match_context_chunks (pgvector similarity search) ──────────────────────
-- Exact port of the former Supabase RPC. Used by app/context_pipeline.py.
CREATE OR REPLACE FUNCTION public.match_context_chunks(
    p_agent_id uuid,
    query_embedding vector,
    match_count integer DEFAULT 5
)
RETURNS TABLE(id uuid, content text, source_url text, similarity double precision)
LANGUAGE sql
STABLE
AS $function$
  SELECT
    id,
    content,
    source_url,
    1 - (embedding <=> query_embedding) AS similarity
  FROM public.context_chunks
  WHERE agent_id = p_agent_id
    AND embedding IS NOT NULL
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$function$;
