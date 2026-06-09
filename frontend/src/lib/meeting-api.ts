import { getFirebaseAuth } from "@/lib/firebase";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

/**
 * Build the auth headers for a call to the FastAPI backend.
 *
 * The backend validates the Firebase ID token (set up separately). We grab
 * a fresh ID token directly from the Firebase client SDK — `getIdToken()`
 * auto-refreshes if the current one is near expiry, so call sites don't
 * need to worry about staleness.
 */
async function authHeaders(): Promise<Record<string, string>> {
  const user = getFirebaseAuth().currentUser;
  if (!user) throw new Error("Not signed in");
  const token = await user.getIdToken();
  if (!token) throw new Error("Unable to get access token");
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
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

// ── Agents (client-side CRUD) ───────────────────────────────────────────────

export type AgentUpsertFields = {
  name: string;
  description?: string | null;
  mode?: string;
  persona_prompt?: string | null;
  voice_id?: string | null;
  bot_image_url?: string | null;
  proactive_fact_check?: boolean;
  screenshot_on_request?: boolean;
  send_post_meeting_email?: boolean;
};

export async function createAgent(
  fields: AgentUpsertFields,
): Promise<{ ok: true; id: string } | { ok: false; error: string }> {
  try {
    const headers = await authHeaders();
    const r = await fetch(`${API_BASE_URL}/api/agents`, {
      method: "POST",
      headers,
      body: JSON.stringify(fields),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) return { ok: false, error: errorDetail(data) };
    return { ok: true, id: (data as { id: string }).id };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}

export async function updateAgent(
  agentId: string,
  fields: Partial<AgentUpsertFields>,
): Promise<{ ok: true } | { ok: false; error: string }> {
  try {
    const headers = await authHeaders();
    const r = await fetch(`${API_BASE_URL}/api/agents/${agentId}`, {
      method: "PATCH",
      headers,
      body: JSON.stringify(fields),
    });
    if (!r.ok) return { ok: false, error: errorDetail(await r.json().catch(() => ({}))) };
    return { ok: true };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}

export async function deleteAgent(agentId: string): Promise<void> {
  const headers = await authHeaders();
  await fetch(`${API_BASE_URL}/api/agents/${agentId}`, { method: "DELETE", headers });
}

export async function deleteMeeting(meetingId: string): Promise<void> {
  const headers = await authHeaders();
  await fetch(`${API_BASE_URL}/api/meetings/${meetingId}`, { method: "DELETE", headers });
}
