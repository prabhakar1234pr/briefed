import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { withAuth } from "@workos-inc/authkit-nextjs";
import { getSupabaseDbClient } from "@/lib/supabase";
import type { MeetingStatus } from "@/types/agents";
import { MeetingChat } from "@/components/MeetingChat";

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

export default async function MeetingDetailPage({ params }: Props) {
  const { id } = await params;
  await withAuth({ ensureSignedIn: true });
  const supabase = getSupabaseDbClient();

  const { data: meeting, error } = await supabase
    .from("meetings")
    .select("id, meeting_link, status, bot_id, transcript_text, audio_url, video_url, created_at, agent_id, summary, action_items, key_decisions")
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
    .select("id, interaction_type, trigger_text, response_text, spoken_at, screenshot_url")
    .eq("meeting_id", id)
    .order("spoken_at");

  // Get agent info for ask
  const { data: agent } = meeting.agent_id
    ? await supabase.from("agents").select("id, name").eq("id", meeting.agent_id).maybeSingle()
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
    catch { return meeting.meeting_link; }
  })();

  const interactionTypeIcon: Record<string, string> = {
    qa: "◎",
    factcheck: "◈",
    screenshot: "⊡",
  };

  return (
    <div style={{ maxWidth: 1020, margin: "0 auto", padding: "48px 24px" }}>
      {/* Header */}
      <div className="anim-0" style={{ marginBottom: 36 }}>
        <Link href="/meetings" style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 13, color: "var(--text-tertiary)", textDecoration: "none", marginBottom: 20 }}>
          ← Meetings
        </Link>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16 }}>
          <div>
            <h1 style={{ fontFamily: "var(--font-display)", fontSize: 28, fontWeight: 400, letterSpacing: "-0.02em", color: "var(--text-primary)", marginBottom: 6 }}>
              {domain}
            </h1>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span className={s.tagClass} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                <span className={s.dot} />{s.label}
              </span>
              <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>{formatDate(meeting.created_at)}</span>
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
            {meeting.video_url && <a href={meeting.video_url} target="_blank" rel="noopener noreferrer" className="btn-secondary">↓ Video</a>}
            {meeting.audio_url && <a href={meeting.audio_url} target="_blank" rel="noopener noreferrer" className="btn-secondary">↓ Audio</a>}
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 16, alignItems: "start" }}>
        {/* Left */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

          {/* Summary */}
          {meeting.summary ? (
            <div className="card anim-1" style={{ padding: 28 }}>
              <SL>AI Summary</SL>
              <p style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.75 }}>{meeting.summary}</p>
            </div>
          ) : meeting.status === "completed" ? (
            <div className="card anim-1" style={{ padding: 28, background: "rgba(59,130,246,0.04)", border: "1px solid rgba(59,130,246,0.1)" }}>
              <SL>AI Summary</SL>
              <p style={{ fontSize: 13, color: "var(--text-tertiary)", fontStyle: "italic" }}>
                Summary not generated yet. Make sure GCP_PROJECT is set and Vertex AI is enabled.
              </p>
            </div>
          ) : null}

          {/* Action items */}
          {actionItems.length > 0 && (
            <div className="card anim-2" style={{ padding: 28 }}>
              <SL>Action items</SL>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {actionItems.map((item, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 12, padding: "10px 14px", borderRadius: 8, border: "1px solid var(--border-subtle)", background: "rgba(255,255,255,0.02)" }}>
                    <div style={{ width: 18, height: 18, borderRadius: 5, border: "1.5px solid var(--border-default)", flexShrink: 0, marginTop: 2 }} />
                    <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>{item}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Copilot interactions */}
          {interactions && interactions.length > 0 && (
            <div className="card anim-2" style={{ padding: 28 }}>
              <SL>Copilot interactions ({interactions.length})</SL>
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {interactions.map((ix) => (
                  <div key={ix.id} style={{ padding: "14px 16px", borderRadius: 10, border: "1px solid var(--border-subtle)", background: "rgba(59,130,246,0.03)" }}>
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
                      <q style={{ quotes: "auto" }}>{ix.trigger_text}</q>
                    </p>
                    <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                      {ix.response_text}
                    </p>
                    {(ix as { screenshot_url?: string | null }).screenshot_url ? (
                      <Image
                        src={(ix as { screenshot_url: string }).screenshot_url}
                        alt="Copilot screenshot"
                        width={640}
                        height={360}
                        unoptimized
                        style={{
                          width: "100%",
                          maxWidth: 320,
                          height: "auto",
                          marginTop: 10,
                          borderRadius: 8,
                          border: "1px solid var(--border-subtle)",
                        }}
                      />
                    ) : null}
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
                    <div style={{ width: 26, height: 26, borderRadius: "50%", background: "rgba(59,130,246,0.12)", border: "1px solid rgba(59,130,246,0.18)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 9, fontWeight: 600, color: "#93c5fd", flexShrink: 0, marginTop: 1 }}>
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
              <p style={{ fontSize: 13, color: "var(--text-tertiary)", fontStyle: "italic" }}>
                {meeting.status === "completed" ? "No transcript stored." : "Transcript will appear when the meeting finishes."}
              </p>
            )}
          </div>

          {/* Video / audio (show MP3 whenever Recall provides audio_url, even if video exists) */}
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
              <SL>Audio (mixed MP3)</SL>
              <audio controls preload="metadata" style={{ width: "100%", borderRadius: 8 }} src={meeting.audio_url}>
                <track kind="captions" />
              </audio>
            </div>
          )}
        </div>

        {/* Right */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

          {/* Key decisions */}
          {keyDecisions.length > 0 && (
            <div className="card anim-1" style={{ padding: 22 }}>
              <SL>Key decisions</SL>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {keyDecisions.map((d, i) => <span key={i} className="tag tag-gray">{d}</span>)}
              </div>
            </div>
          )}

          {/* Ask Briefed — assistant-ui powered chat */}
          {agent && (
            <MeetingChat agentId={agent.id} agentName={agent.name} meetingId={id} meetingStatus={meeting.status} />
          )}

          {/* Details */}
          <div className="card anim-2" style={{ padding: 22 }}>
            <SL>Details</SL>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {[
                { label: "Status", value: <span className={s.tagClass} style={{ display: "inline-flex", alignItems: "center", gap: 5 }}><span className={s.dot} />{s.label}</span> },
                { label: "Date", value: formatDate(meeting.created_at) },
                { label: "Link", value: <a href={meeting.meeting_link} target="_blank" rel="noopener noreferrer" style={{ color: "var(--text-accent)", fontSize: 12, wordBreak: "break-all" }}>{meeting.meeting_link.slice(0, 38)}{meeting.meeting_link.length > 38 ? "…" : ""}</a> },
              ].map(({ label, value }) => (
                <div key={label} style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                  <p style={{ fontSize: 10, color: "var(--text-tertiary)", fontWeight: 500, letterSpacing: "0.06em", textTransform: "uppercase" }}>{label}</p>
                  <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>{value}</div>
                </div>
              ))}
            </div>
          </div>

          {/* IDs */}
          <div className="anim-3" style={{ padding: "14px 18px", borderRadius: 10, border: "1px solid var(--border-subtle)", background: "rgba(255,255,255,0.01)" }}>
            <p style={{ fontSize: 10, color: "var(--text-tertiary)", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 6 }}>Meeting ID</p>
            <code style={{ fontSize: 11, color: "var(--text-tertiary)", fontFamily: "monospace", wordBreak: "break-all" }}>{meeting.id}</code>
            {meeting.bot_id && (
              <>
                <p style={{ fontSize: 10, color: "var(--text-tertiary)", letterSpacing: "0.06em", textTransform: "uppercase", margin: "10px 0 4px" }}>Bot ID</p>
                <code style={{ fontSize: 11, color: "var(--text-tertiary)", fontFamily: "monospace" }}>{meeting.bot_id.slice(0, 22)}…</code>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
