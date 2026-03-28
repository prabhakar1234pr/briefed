import Link from "next/link";
import { getSupabaseDbClient } from "@/lib/supabase";
import { auth } from "@clerk/nextjs/server";
import { MeetingSession } from "@/components/MeetingSession";

export default async function MeetingPage() {
  await auth.protect();
  const supabase = getSupabaseDbClient();
  const { data: agents } = await supabase
    .from("agents")
    .select("id, name")
    .order("name");

  return (
    <div style={{ maxWidth: 780, margin: "0 auto", padding: "48px 24px" }}>
      <div className="anim-0" style={{ marginBottom: 36 }}>
        <Link
          href="/"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            fontSize: 13,
            color: "var(--text-tertiary)",
            textDecoration: "none",
            marginBottom: 20,
          }}
        >
          ← Home
        </Link>
        <h1
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 32,
            fontWeight: 400,
            letterSpacing: "-0.02em",
            color: "var(--text-primary)",
            marginBottom: 6,
          }}
        >
          Start a meeting
        </h1>
        <p style={{ fontSize: 14, color: "var(--text-secondary)" }}>
          Send your agent into any Zoom, Google Meet, or Teams call.
        </p>
      </div>

      {!agents?.length ? (
        <div
          className="card anim-1"
          style={{ padding: 60, textAlign: "center" }}
        >
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 16,
              background: "rgba(124,58,237,0.1)",
              border: "1px solid rgba(124,58,237,0.18)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 20px",
              fontSize: 22,
            }}
          >
            ◎
          </div>
          <p
            style={{
              fontSize: 16,
              fontWeight: 500,
              color: "var(--text-primary)",
              marginBottom: 8,
            }}
          >
            No agents yet
          </p>
          <p
            style={{
              fontSize: 13,
              color: "var(--text-secondary)",
              marginBottom: 24,
            }}
          >
            Create an agent before starting a meeting.
          </p>
          <Link href="/agents/new" className="btn-primary">
            Create agent
          </Link>
        </div>
      ) : (
        <MeetingSession agents={agents} />
      )}
    </div>
  );
}
