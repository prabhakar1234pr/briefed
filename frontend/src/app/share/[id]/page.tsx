import { notFound } from "next/navigation";
import Link from "next/link";
import { getSupabaseDbClient } from "@/lib/supabase";
import type { MeetingStatus } from "@/types/agents";

type Props = { params: Promise<{ id: string }> };
export const dynamic = "force-dynamic";

const statusConfig: Record<MeetingStatus, { dot: string; label: string; tagClass: string }> = {
  scheduled:  { dot: "dot dot-joining", label: "Scheduled",  tagClass: "tag tag-amber" },
  joining:    { dot: "dot dot-joining", label: "Joining…",   tagClass: "tag tag-amber" },
  in_meeting: { dot: "dot dot-live",    label: "Live",       tagClass: "tag tag-green" },
  processing: { dot: "dot dot-proc",    label: "Processing", tagClass: "tag tag-blue"  },
  completed:  { dot: "dot dot-done",    label: "Completed",  tagClass: "tag tag-gray"  },
  failed:     { dot: "dot dot-fail",    label: "Failed",     tagClass: "tag tag-red"   },
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    weekday: "short", month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function SL({ children }: { children: React.ReactNode }) {
  return (
    <p style={{ fontSize: 11, fontWeight: 500, letterSpacing: "0.1em", color: "var(--text-tertiary)", textTransform: "uppercase", marginBottom: 14 }}>
      {children}
    </p>
  );
}

export default async function SharedMeetingPage({ params }: Props) {
  const { id } = await params;
  const supabase = getSupabaseDbClient();

  const { data: meeting, error } = await supabase
    .from("meetings")
    .select("id, meeting_link, status, transcript_text, audio_url, video_url, created_at, agent_id, summary, action_items, key_decisions")
    .eq("id", id)
    .maybeSingle();

  if (error || !meeting) notFound();

  const { data: transcriptLines } = await supabase
    .from("transcript_lines")
    .select("id, speaker_name, content, spoken_at")
    .eq("meeting_id", id)
    .order("spoken_at");

  const { data: interactions } = await supabase
    .from("meeting_interactions")
    .select("id, interaction_type, trigger_text, response_text, spoken_at")
    .eq("meeting_id", id)
    .order("spoken_at");

  const { data: agent } = meeting.agent_id
    ? await supabase.from("agents").select("name").eq("id", meeting.agent_id).maybeSingle()
    : { data: null };

  const s = statusConfig[meeting.status as MeetingStatus] ?? statusConfig.completed;

  let actionItems: string[] = [];
  try {
    if (meeting.action_items) {
      actionItems = typeof meeting.action_items === "string"
        ? JSON.parse(meeting.action_items) : meeting.action_items;
    }
  } catch { actionItems = []; }

  let keyDecisions: string[] = [];
  try {
    if (meeting.key_decisions) {
      keyDecisions = typeof meeting.key_decisions === "string"
        ? JSON.parse(meeting.key_decisions) : meeting.key_decisions;
    }
  } catch { keyDecisions = []; }

  const domain = (() => {
    try { return new URL(meeting.meeting_link).hostname.replace("www.", ""); }
    catch { return "Meeting"; }
  })();

  const interactionTypeIcon: Record<string, string> = { qa: "◎", factcheck: "◈", screenshot: "⊡" };

  return (
    <div style={{ maxWidth: 860, margin: "0 auto", padding: "48px 24px" }}>
      {/* Header */}
      <div className="anim-0" style={{ marginBottom: 36, textAlign: "center" }}>
        <div style={{ display: "inline-flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
          <div style={{ width: 28, height: 28, borderRadius: 8, background: "linear-gradient(135deg, #7c3aed 0%, #6366f1 100%)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="2.5" fill="white" /><path d="M7 1.5C7 1.5 10.5 3.5 10.5 7C10.5 10.5 7 12.5 7 12.5" stroke="white" strokeWidth="1.2" strokeLinecap="round" opacity="0.6" /><path d="M7 1.5C7 1.5 3.5 3.5 3.5 7C3.5 10.5 7 12.5 7 12.5" stroke="white" strokeWidth="1.2" strokeLinecap="round" opacity="0.6" /></svg>
          </div>
          <span style={{ fontSize: 14, fontWeight: 500, color: "var(--text-tertiary)" }}>Briefed</span>
        </div>
        <h1 style={{ fontFamily: "var(--font-display)", fontSize: 28, fontWeight: 400, color: "var(--text-primary)", marginBottom: 8 }}>
          Meeting Brief — {domain}
        </h1>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 12 }}>
          <span className={s.tagClass} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            <span className={s.dot} />{s.label}
          </span>
          <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>{formatDate(meeting.created_at)}</span>
          {agent && <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Agent: {agent.name}</span>}
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Summary */}
        {meeting.summary && (
          <div className="card anim-1" style={{ padding: 28 }}>
            <SL>AI Summary</SL>
            <p style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.75 }}>{meeting.summary}</p>
          </div>
        )}

        {/* Action Items + Key Decisions side by side */}
        {(actionItems.length > 0 || keyDecisions.length > 0) && (
          <div style={{ display: "grid", gridTemplateColumns: actionItems.length > 0 && keyDecisions.length > 0 ? "1fr 1fr" : "1fr", gap: 16 }}>
            {actionItems.length > 0 && (
              <div className="card anim-2" style={{ padding: 28 }}>
                <SL>Action Items</SL>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {actionItems.map((item, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border-subtle)", background: "rgba(255,255,255,0.02)" }}>
                      <div style={{ width: 16, height: 16, borderRadius: 4, border: "1.5px solid var(--border-default)", flexShrink: 0, marginTop: 2 }} />
                      <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>{item}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {keyDecisions.length > 0 && (
              <div className="card anim-2" style={{ padding: 28 }}>
                <SL>Key Decisions</SL>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {keyDecisions.map((d, i) => <span key={i} className="tag tag-gray">{d}</span>)}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Copilot Interactions */}
        {interactions && interactions.length > 0 && (
          <div className="card anim-2" style={{ padding: 28 }}>
            <SL>Copilot Interactions ({interactions.length})</SL>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {interactions.map((ix) => (
                <div key={ix.id} style={{ padding: "14px 16px", borderRadius: 10, border: "1px solid var(--border-subtle)", background: "rgba(124,58,237,0.03)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                    <span style={{ fontSize: 14, color: "var(--text-accent)" }}>
                      {interactionTypeIcon[ix.interaction_type] ?? "◎"}
                    </span>
                    <span className={`tag ${ix.interaction_type === "factcheck" ? "tag-amber" : ix.interaction_type === "screenshot" ? "tag-teal" : "tag-blue"}`}>
                      {ix.interaction_type === "qa" ? "Q&A" : ix.interaction_type === "factcheck" ? "Fact check" : "Screenshot"}
                    </span>
                    <span style={{ fontSize: 11, color: "var(--text-tertiary)", marginLeft: "auto" }}>
                      {new Date(ix.spoken_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </div>
                  <p style={{ fontSize: 12, color: "var(--text-tertiary)", marginBottom: 6, fontStyle: "italic" }}>
                    &ldquo;{ix.trigger_text}&rdquo;
                  </p>
                  <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                    {ix.response_text}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Transcript */}
        <div className="card anim-3" style={{ padding: 28 }}>
          <SL>Transcript</SL>
          {transcriptLines && transcriptLines.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 12, maxHeight: 480, overflowY: "auto", background: "rgba(0,0,0,0.15)", borderRadius: 10, border: "1px solid var(--border-subtle)", padding: "16px 18px" }}>
              {transcriptLines.map((line) => (
                <div key={line.id} style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                  <div style={{ width: 26, height: 26, borderRadius: "50%", background: "rgba(124,58,237,0.12)", border: "1px solid rgba(124,58,237,0.18)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 9, fontWeight: 600, color: "#a78bfa", flexShrink: 0, marginTop: 1 }}>
                    {(line.speaker_name ?? "?").slice(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <span style={{ fontSize: 11, fontWeight: 500, color: "var(--text-tertiary)", marginRight: 8 }}>{line.speaker_name ?? "Unknown"}</span>
                    <span style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.65 }}>{line.content}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : meeting.transcript_text ? (
            <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", fontFamily: "var(--font-sans)", fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.75, background: "rgba(0,0,0,0.15)", border: "1px solid var(--border-subtle)", borderRadius: 10, padding: "16px 18px", maxHeight: 400, overflowY: "auto" }}>
              {meeting.transcript_text}
            </pre>
          ) : (
            <p style={{ fontSize: 13, color: "var(--text-tertiary)", fontStyle: "italic" }}>No transcript available.</p>
          )}
        </div>

        {/* Media */}
        {meeting.video_url && (
          <div className="card anim-4" style={{ padding: 28 }}>
            <SL>Recording</SL>
            <video controls playsInline preload="metadata" style={{ width: "100%", maxHeight: 480, borderRadius: 10, background: "#000" }} src={meeting.video_url}>
              <track kind="captions" />
            </video>
          </div>
        )}
        {meeting.audio_url && (
          <div className="card anim-4" style={{ padding: 28 }}>
            <SL>Audio</SL>
            <audio controls preload="metadata" style={{ width: "100%", borderRadius: 8 }} src={meeting.audio_url}>
              <track kind="captions" />
            </audio>
          </div>
        )}
      </div>

      {/* Footer */}
      <div style={{ textAlign: "center", marginTop: 48, paddingTop: 24, borderTop: "1px solid var(--border-subtle)" }}>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
          Powered by <Link href="/" style={{ color: "var(--text-accent)", textDecoration: "none" }}>Briefed</Link> — AI Meeting Intelligence
        </p>
      </div>
    </div>
  );
}
