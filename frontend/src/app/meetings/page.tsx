import Link from "next/link";
import { DeleteRowButton } from "@/components/DeleteRowButton";
import { getSupabaseDbClient } from "@/lib/supabase";
import { withAuth } from "@workos-inc/authkit-nextjs";
import type { MeetingStatus } from "@/types/agents";

const statusConfig: Record<MeetingStatus, { dot: string; label: string; tagClass: string }> = {
  scheduled:  { dot: "dot dot-joining", label: "Scheduled",  tagClass: "tag tag-amber" },
  joining:    { dot: "dot dot-joining", label: "Joining",    tagClass: "tag tag-amber" },
  in_meeting: { dot: "dot dot-live",    label: "Live",       tagClass: "tag tag-green" },
  processing: { dot: "dot dot-proc",    label: "Processing", tagClass: "tag tag-blue"  },
  completed:  { dot: "dot dot-done",    label: "Completed",  tagClass: "tag tag-gray"  },
  failed:     { dot: "dot dot-fail",    label: "Failed",     tagClass: "tag tag-red"   },
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function extractDomain(url: string) {
  try { return new URL(url).hostname.replace("www.", ""); }
  catch { return url.slice(0, 40); }
}

export default async function MeetingsPage() {
  await withAuth({ ensureSignedIn: true });
  const supabase = getSupabaseDbClient();
  const { data: meetings, error } = await supabase
    .from("meetings")
    .select("id, meeting_link, status, created_at, bot_id")
    .order("created_at", { ascending: false })
    .limit(50);

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "48px 24px" }}>
      {/* Header */}
      <div
        className="anim-0"
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 16,
          marginBottom: 40,
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
              marginBottom: 8,
            }}
          >
            History
          </p>
          <h1
            style={{
              fontFamily: "var(--font-display)",
              fontSize: 32,
              fontWeight: 400,
              letterSpacing: "-0.02em",
              color: "var(--text-primary)",
              lineHeight: 1.2,
            }}
          >
            Past meetings
          </h1>
          <p style={{ fontSize: 14, color: "var(--text-secondary)", marginTop: 6 }}>
            Transcripts, summaries, and recordings from your agent sessions.
          </p>
        </div>
        <Link href="/meeting" className="btn-primary" style={{ flexShrink: 0, marginTop: 4 }}>
          <span style={{ fontSize: 11 }}>●</span>
          New meeting
        </Link>
      </div>

      {/* Content */}
      {error ? (
        <div
          style={{
            padding: "16px 20px",
            borderRadius: 10,
            background: "rgba(248,113,113,0.08)",
            border: "1px solid rgba(248,113,113,0.2)",
            color: "#fca5a5",
            fontSize: 14,
          }}
        >
          {error.message}
        </div>
      ) : !meetings?.length ? (
        <div className="card anim-1" style={{ padding: 60, textAlign: "center" }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 16,
              background: "rgba(59,130,246,0.1)",
              border: "1px solid rgba(59,130,246,0.15)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 20px",
              fontSize: 22,
            }}
          >
            ◉
          </div>
          <p style={{ fontSize: 16, fontWeight: 500, color: "var(--text-primary)", marginBottom: 8 }}>
            No meetings yet
          </p>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 24 }}>
            Start your first meeting to see recordings and transcripts here.
          </p>
          <Link href="/meeting" className="btn-primary">
            Start meeting
          </Link>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {meetings.map((m, i) => {
            const s = statusConfig[m.status as MeetingStatus] ?? statusConfig.completed;
            return (
              <div
                key={m.id}
                className={`card anim-${Math.min(i + 1, 4)}`}
                style={{
                  padding: "10px 10px 10px 18px",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <Link
                  href={`/meetings/${m.id}`}
                  className="card-hover"
                  style={{
                    flex: 1,
                    minWidth: 0,
                    padding: "8px 8px 8px 0",
                    textDecoration: "none",
                    display: "flex",
                    alignItems: "center",
                    gap: 16,
                    borderRadius: 8,
                  }}
                >
                  {/* Icon */}
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: 12,
                      background: "rgba(255,255,255,0.04)",
                      border: "1px solid var(--border-subtle)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 15,
                      flexShrink: 0,
                      color: "var(--text-tertiary)",
                    }}
                  >
                    ◎
                  </div>

                  {/* Info */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p
                      style={{
                        fontSize: 14,
                        fontWeight: 500,
                        color: "var(--text-primary)",
                        marginBottom: 3,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {extractDomain(m.meeting_link)}
                    </p>
                    <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                      {formatDate(m.created_at)}
                      {m.bot_id ? ` · bot ${m.bot_id.slice(0, 8)}…` : ""}
                    </p>
                  </div>

                  {/* Status */}
                  <span
                    className={s.tagClass}
                    style={{ display: "inline-flex", alignItems: "center", gap: 6, flexShrink: 0 }}
                  >
                    <span className={s.dot} />
                    {s.label}
                  </span>

                  <span style={{ fontSize: 12, color: "var(--text-tertiary)", flexShrink: 0 }}>
                    →
                  </span>
                </Link>
                <DeleteRowButton
                  apiPath={`/api/meetings/${m.id}`}
                  confirmMessage="Delete this meeting? This cannot be undone."
                />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
