import Link from "next/link";
import { requireServerUser } from "@/lib/auth";
import { getSupabaseDbClient } from "@/lib/supabase";

export default async function HomePage() {
  const user = await requireServerUser("/home");
  const supabase = await getSupabaseDbClient();

  const { data: profile } = await supabase
    .from("users")
    .select("full_name")
    .eq("id", user.uid)
    .maybeSingle();

  const fullName =
    profile?.full_name?.trim() ||
    user.name?.trim() ||
    "there";

  return (
    <div style={{ maxWidth: 960, margin: "0 auto", padding: "48px 28px" }}>
      <div className="anim-0" style={{ marginBottom: 30 }}>
        <p
          style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: "var(--text-tertiary)",
            marginBottom: 8,
          }}
        >
          Home
        </p>
        <h1
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 34,
            fontWeight: 700,
            color: "var(--text-primary)",
            letterSpacing: "-0.02em",
            marginBottom: 8,
          }}
        >
          Hello, {fullName}
        </h1>
        <p style={{ fontSize: 14, color: "var(--text-secondary)" }}>
          Welcome back to Agent Bora.
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 14,
        }}
      >
        <Link href="/meeting" className="card card-hover anim-1" style={{ padding: 22, textDecoration: "none" }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 6 }}>
            Start meeting
          </p>
          <p style={{ fontSize: 12, color: "var(--text-secondary)" }}>
            Send your agent into a live call.
          </p>
        </Link>

        <Link href="/agents" className="card card-hover anim-2" style={{ padding: 22, textDecoration: "none" }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 6 }}>
            Manage agents
          </p>
          <p style={{ fontSize: 12, color: "var(--text-secondary)" }}>
            Create and edit your agent profiles.
          </p>
        </Link>

        <Link href="/meetings" className="card card-hover anim-3" style={{ padding: 22, textDecoration: "none" }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 6 }}>
            Open meeting history
          </p>
          <p style={{ fontSize: 12, color: "var(--text-secondary)" }}>
            Review transcripts, summaries, and recordings.
          </p>
        </Link>
      </div>
    </div>
  );
}
