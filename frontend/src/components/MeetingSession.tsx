"use client";

import { useEffect, useRef, useState } from "react";
import { fetchMeeting, startMeeting } from "@/lib/meeting-api";

type AgentOption = { id: string; name: string };
type LiveLine = { id: string; speaker: string; text: string; at: string };

function datetimeLocalToIsoUtc(value: string): string | null {
  const d = new Date(value);
  return isNaN(d.getTime()) ? null : d.toISOString();
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { dot: string; label: string; tagClass: string }> = {
    scheduled:  { dot: "dot dot-joining", label: "Scheduled",  tagClass: "tag tag-amber" },
    joining:    { dot: "dot dot-joining", label: "Joining…",   tagClass: "tag tag-amber" },
    in_meeting: { dot: "dot dot-live",    label: "Live",       tagClass: "tag tag-green" },
    processing: { dot: "dot dot-proc",   label: "Processing", tagClass: "tag tag-blue"  },
    completed:  { dot: "dot dot-done",   label: "Completed",  tagClass: "tag tag-gray"  },
    failed:     { dot: "dot dot-fail",   label: "Failed",     tagClass: "tag tag-red"   },
  };
  const s = map[status] ?? { dot: "dot dot-done", label: status, tagClass: "tag tag-gray" };
  return (
    <span className={s.tagClass} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
      <span className={s.dot} />
      {s.label}
    </span>
  );
}

export function MeetingSession({ agents }: { agents: AgentOption[] }) {
  const [agentId, setAgentId] = useState(agents[0]?.id ?? "");
  const [meetingLink, setMeetingLink] = useState("");
  const [joinNow, setJoinNow] = useState(true);
  const [joinAtLocal, setJoinAtLocal] = useState("");
  const [phase, setPhase] = useState<"idle" | "starting" | "live" | "ended">("idle");
  const [error, setError] = useState<string | null>(null);
  const [liveLines, setLiveLines] = useState<LiveLine[]>([]);
  const [meetingId, setMeetingId] = useState<string | null>(null);
  const [finalTranscript, setFinalTranscript] = useState<string | null>(null);
  const [meetingStatus, setMeetingStatus] = useState<string>("joining");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const transcriptRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [liveLines]);

  useEffect(() => {
    if (!meetingId || phase === "idle" || phase === "ended") return;
    const tick = async () => {
      try {
        const m = await fetchMeeting(meetingId);
        setMeetingStatus(m.status);
        setFinalTranscript(m.transcript_text ?? null);
        setLiveLines(
          (m.transcript_lines ?? []).map((row) => ({
            id: row.id,
            speaker: row.speaker_name ?? "Speaker",
            text: row.content,
            at: row.spoken_at,
          }))
        );
        if (m.status === "completed" || m.status === "failed") {
          if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
          setPhase("ended");
        }
      } catch { /* ignore transient */ }
    };
    void tick();
    pollRef.current = setInterval(() => { void tick(); }, 2500);
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  }, [meetingId, phase]);

  async function handleStart() {
    setError(null);
    const link = meetingLink.trim();
    if (!link) { setError("Paste a meeting link."); return; }
    if (!agentId) { setError("Select an agent."); return; }
    let joinAtIso: string | null = null;
    if (!joinNow) {
      if (!joinAtLocal.trim()) { setError("Choose a join time or enable Join now."); return; }
      joinAtIso = datetimeLocalToIsoUtc(joinAtLocal);
      if (!joinAtIso) { setError("Invalid join time."); return; }
    }
    setPhase("starting");
    const result = await startMeeting({ agent_id: agentId, meeting_link: link, join_now: joinNow, join_at: joinNow ? null : joinAtIso });
    if (!result.ok) { setError(result.error); setPhase("idle"); return; }
    setMeetingId(result.meeting_id);
    setPhase("live");
    setLiveLines([]);
  }

  const isActive = phase === "live" || phase === "starting";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Setup card */}
      <div className="card anim-1" style={{ padding: 28 }}>
        <p
          style={{
            fontSize: 11,
            fontWeight: 500,
            letterSpacing: "0.1em",
            color: "var(--text-tertiary)",
            textTransform: "uppercase",
            marginBottom: 20,
          }}
        >
          Configuration
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Agent select */}
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{ fontSize: 13, fontWeight: 500, color: "var(--text-secondary)" }}>
              Agent
            </label>
            <select
              className="input-field"
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              disabled={isActive}
              style={{ cursor: "pointer" }}
            >
              {agents.map((a) => (
                <option key={a.id} value={a.id} style={{ background: "#161b24" }}>
                  {a.name}
                </option>
              ))}
            </select>
          </div>

          {/* Meeting link */}
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{ fontSize: 13, fontWeight: 500, color: "var(--text-secondary)" }}>
              Meeting link
            </label>
            <input
              className="input-field"
              type="url"
              value={meetingLink}
              onChange={(e) => setMeetingLink(e.target.value)}
              placeholder="https://meet.google.com/… or https://zoom.us/j/…"
              disabled={isActive}
            />
          </div>

          {/* Join timing */}
          <div
            style={{
              padding: "14px 16px",
              borderRadius: 10,
              border: "1px solid var(--border-subtle)",
              background: "rgba(255,255,255,0.02)",
            }}
          >
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                cursor: "pointer",
              }}
            >
              <input
                type="checkbox"
                className="check"
                checked={joinNow}
                onChange={(e) => setJoinNow(e.target.checked)}
                disabled={isActive}
              />
              <div>
                <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>
                  Join immediately
                </p>
                <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                  Agent joins the moment you click Start
                </p>
              </div>
            </label>

            {!joinNow && (
              <div style={{ marginTop: 14, paddingTop: 14, borderTop: "1px solid var(--border-subtle)" }}>
                <label style={{ fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 8 }}>
                  Schedule for
                </label>
                <input
                  type="datetime-local"
                  className="input-field"
                  style={{ maxWidth: 280 }}
                  value={joinAtLocal}
                  onChange={(e) => setJoinAtLocal(e.target.value)}
                  disabled={isActive}
                />
              </div>
            )}
          </div>

          {/* Error */}
          {error && (
            <div
              style={{
                padding: "10px 14px",
                borderRadius: 8,
                background: "rgba(248,113,113,0.08)",
                border: "1px solid rgba(248,113,113,0.2)",
                color: "#fca5a5",
                fontSize: 13,
              }}
            >
              {error}
            </div>
          )}

          {/* Actions */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, paddingTop: 4 }}>
            <button
              type="button"
              onClick={handleStart}
              disabled={isActive}
              className="btn-primary"
            >
              {phase === "starting" ? (
                <>
                  <svg width="13" height="13" viewBox="0 0 13 13" fill="none" style={{ animation: "spin 0.8s linear infinite" }}>
                    <circle cx="6.5" cy="6.5" r="4.5" stroke="rgba(255,255,255,0.3)" strokeWidth="1.4" />
                    <path d="M6.5 2a4.5 4.5 0 0 1 4.5 4.5" stroke="white" strokeWidth="1.4" strokeLinecap="round" />
                  </svg>
                  Sending agent…
                </>
              ) : (
                <>
                  <span style={{ fontSize: 11 }}>●</span>
                  Start meeting
                </>
              )}
            </button>

            {phase === "live" && (
              <button
                type="button"
                onClick={() => {
                  if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
                  setPhase("ended");
                }}
                className="btn-secondary"
              >
                Stop watching
              </button>
            )}

            {phase === "live" && (
              <StatusBadge status={meetingStatus} />
            )}
          </div>
        </div>
      </div>

      {/* Live transcript */}
      {(phase === "live" || phase === "ended") && (
        <div className="card anim-2" style={{ padding: 28 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: 20,
            }}
          >
            <div>
              <p
                style={{
                  fontSize: 11,
                  fontWeight: 500,
                  letterSpacing: "0.1em",
                  color: "var(--text-tertiary)",
                  textTransform: "uppercase",
                  marginBottom: 4,
                }}
              >
                Live transcript
              </p>
              <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                {phase === "live"
                  ? "Transcript updates in real time as the meeting progresses."
                  : "Meeting ended — full transcript below."}
              </p>
            </div>
            {phase === "live" && <StatusBadge status={meetingStatus} />}
          </div>

          <div
            ref={transcriptRef}
            style={{
              minHeight: 220,
              maxHeight: 380,
              overflowY: "auto",
              borderRadius: 10,
              border: "1px solid var(--border-subtle)",
              background: "rgba(0,0,0,0.2)",
              padding: "16px 18px",
              display: "flex",
              flexDirection: "column",
              gap: 12,
            }}
          >
            {liveLines.length === 0 ? (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  minHeight: 160,
                  gap: 10,
                  color: "var(--text-tertiary)",
                }}
              >
                {phase === "live" ? (
                  <>
                    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" style={{ opacity: 0.4 }}>
                      <circle cx="10" cy="10" r="8" stroke="currentColor" strokeWidth="1.5" />
                      <path d="M7 10h6M10 7v6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                    </svg>
                    <p style={{ fontSize: 13 }}>Waiting for transcript…</p>
                  </>
                ) : (
                  <p style={{ fontSize: 13 }}>No lines recorded.</p>
                )}
              </div>
            ) : (
              liveLines.map((line) => (
                <div
                  key={line.id}
                  className="transcript-line"
                  style={{ display: "flex", gap: 10, alignItems: "flex-start" }}
                >
                  {/* Speaker avatar */}
                  <div
                    style={{
                      width: 24,
                      height: 24,
                      borderRadius: "50%",
                      background: "rgba(59,130,246,0.15)",
                      border: "1px solid rgba(59,130,246,0.2)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 9,
                      fontWeight: 600,
                      color: "#93c5fd",
                      flexShrink: 0,
                      marginTop: 1,
                    }}
                  >
                    {line.speaker.slice(0, 2).toUpperCase()}
                  </div>
                  <div style={{ flex: 1 }}>
                    <span style={{ fontSize: 11, fontWeight: 500, color: "var(--text-tertiary)", marginRight: 6 }}>
                      {line.speaker}
                    </span>
                    <span style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                      {line.text}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Full transcript (post-meeting) */}
          {phase === "ended" && finalTranscript && (
            <div style={{ marginTop: 20 }}>
              <p
                style={{
                  fontSize: 11,
                  fontWeight: 500,
                  letterSpacing: "0.1em",
                  color: "var(--text-tertiary)",
                  textTransform: "uppercase",
                  marginBottom: 12,
                }}
              >
                Full transcript
              </p>
              <pre
                style={{
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                  fontFamily: "var(--font-sans)",
                  fontSize: 13,
                  color: "var(--text-secondary)",
                  lineHeight: 1.75,
                  background: "rgba(0,0,0,0.2)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: 10,
                  padding: "16px 18px",
                  maxHeight: 320,
                  overflowY: "auto",
                }}
              >
                {finalTranscript}
              </pre>
            </div>
          )}
        </div>
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
