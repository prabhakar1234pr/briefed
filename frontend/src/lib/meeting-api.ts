const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

async function authHeaders(): Promise<Record<string, string>> {
  // Fetch access token from WorkOS AuthKit via server endpoint
  const r = await fetch("/api/auth/me");
  if (!r.ok) throw new Error("Not signed in");
  const data = await r.json();
  if (!data.authenticated) throw new Error("Not signed in");

  // WorkOS AuthKit stores session in httpOnly cookie — the middleware handles
  // injecting the access token. For API calls to the external backend, we use
  // a server action pattern. For now, we pass the session cookie implicitly
  // and let the /api proxy handle auth.
  //
  // Since our backend validates WorkOS JWTs directly, we need the access token.
  // We fetch it from a dedicated endpoint.
  const tokenResp = await fetch("/api/auth/token");
  if (tokenResp.ok) {
    const { accessToken } = await tokenResp.json();
    if (accessToken) {
      return {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      };
    }
  }

  // Fallback: try the /me endpoint's session
  throw new Error("Unable to get access token");
}

function errorDetail(payload: unknown): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const d = (payload as { detail: unknown }).detail;
    return typeof d === "string" ? d : JSON.stringify(d);
  }
  return "Request failed";
}

// ── Meetings ──────────────────────────────────────────────────────────────────

export type StartMeetingPayload = {
  agent_id: string;
  meeting_link: string;
  join_now: boolean;
  join_at?: string | null;
};

export type StartMeetingResult =
  | { ok: true; meeting_id: string; bot_id: string }
  | { ok: false; error: string };

export async function startMeeting(payload: StartMeetingPayload): Promise<StartMeetingResult> {
  try {
    const headers = await authHeaders();
    const r = await fetch(`${API_BASE_URL}/api/meetings/start`, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) return { ok: false, error: errorDetail(data) };
    const row = data as { meeting_id?: string; bot_id?: string };
    if (!row.meeting_id || !row.bot_id) return { ok: false, error: "Invalid response from server" };
    return { ok: true, meeting_id: row.meeting_id, bot_id: row.bot_id };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}

export type MeetingWithLines = {
  id: string;
  status: string;
  transcript_text: string | null;
  bot_id: string | null;
  summary?: string | null;
  action_items?: string | null;
  key_decisions?: string | null;
  transcript_lines: {
    id: string;
    speaker_name: string | null;
    content: string;
    spoken_at: string;
  }[];
};

export async function fetchMeeting(meetingId: string): Promise<MeetingWithLines> {
  const headers = await authHeaders();
  const r = await fetch(`${API_BASE_URL}/api/meetings/${encodeURIComponent(meetingId)}`, { headers });
  if (!r.ok) {
    const data = await r.json().catch(() => ({}));
    throw new Error(errorDetail(data));
  }
  return r.json();
}

export type Interaction = {
  id: string;
  interaction_type: string;
  trigger_text: string;
  response_text: string;
  spoken_at: string;
  created_at: string;
};

export async function fetchInteractions(meetingId: string): Promise<Interaction[]> {
  try {
    const headers = await authHeaders();
    const r = await fetch(`${API_BASE_URL}/api/meetings/${meetingId}/interactions`, { headers });
    if (!r.ok) return [];
    const data = await r.json();
    return data.interactions ?? [];
  } catch {
    return [];
  }
}

// ── Context ───────────────────────────────────────────────────────────────────

export type ContextSource = {
  source_url: string;
  chunk_count: number;
  last_added: string;
};

export async function fetchContext(agentId: string): Promise<{ sources: ContextSource[]; total_chunks: number }> {
  try {
    const headers = await authHeaders();
    const r = await fetch(`${API_BASE_URL}/api/agents/${agentId}/context`, { headers });
    if (!r.ok) return { sources: [], total_chunks: 0 };
    return r.json();
  } catch {
    return { sources: [], total_chunks: 0 };
  }
}

export type AddContextResult = { ok: true; chunks_added: number; source_url: string } | { ok: false; error: string };

export async function addContext(
  agentId: string,
  sourceType: "url" | "text",
  content: string,
  label?: string,
): Promise<AddContextResult> {
  try {
    const headers = await authHeaders();
    const r = await fetch(`${API_BASE_URL}/api/agents/${agentId}/context`, {
      method: "POST",
      headers,
      body: JSON.stringify({ source_type: sourceType, content, label }),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) return { ok: false, error: errorDetail(data) };
    return { ok: true, ...data };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}

export async function deleteContext(agentId: string, sourceUrl?: string): Promise<void> {
  const headers = await authHeaders();
  const url = new URL(`${API_BASE_URL}/api/agents/${agentId}/context`);
  if (sourceUrl) url.searchParams.set("source_url", sourceUrl);
  await fetch(url.toString(), { method: "DELETE", headers });
}

// ── Ask ───────────────────────────────────────────────────────────────────────

export async function askAgent(
  agentId: string,
  question: string,
  meetingId?: string,
): Promise<{ answer: string; context_chunks_used: number }> {
  const headers = await authHeaders();
  const r = await fetch(`${API_BASE_URL}/api/agents/${agentId}/ask`, {
    method: "POST",
    headers,
    body: JSON.stringify({ question, meeting_id: meetingId }),
  });
  if (!r.ok) throw new Error(errorDetail(await r.json().catch(() => ({}))));
  return r.json();
}
