import Link from "next/link";
import { DeleteRowButton } from "@/components/DeleteRowButton";
import { getSupabaseDbClient } from "@/lib/supabase";
import { auth } from "@clerk/nextjs/server";

export default async function AgentsListPage() {
  await auth.protect();
  const supabase = getSupabaseDbClient();
  const { data: agents, error } = await supabase
    .from("agents")
    .select("id, name, description, updated_at, proactive_fact_check, screenshot_on_request")
    .order("updated_at", { ascending: false });

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
            Agents
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
            Your AI agents
          </h1>
          <p style={{ fontSize: 14, color: "var(--text-secondary)", marginTop: 6 }}>
            Each agent joins meetings with its own persona, context, and capabilities.
          </p>
        </div>
        <Link
          href="/agents/new"
          className="btn-primary"
          style={{ flexShrink: 0, marginTop: 4 }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 2v10M2 7h10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
          New agent
        </Link>
      </div>

      {/* Content */}
      {error ? (
        <div
          style={{
            padding: "16px 20px",
            borderRadius: "var(--radius-md)",
            background: "rgba(248,113,113,0.08)",
            border: "1px solid rgba(248,113,113,0.2)",
            color: "#fca5a5",
            fontSize: 14,
          }}
        >
          {error.message}
        </div>
      ) : !agents?.length ? (
        <div
          className="card anim-1"
          style={{
            padding: 60,
            textAlign: "center",
          }}
        >
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
            Create your first agent to start joining meetings.
          </p>
          <Link href="/agents/new" className="btn-primary">
            Create agent
          </Link>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {agents.map((a, i) => (
            <div
              key={a.id}
              className={`card anim-${Math.min(i + 1, 4)}`}
              style={{
                padding: "12px 12px 12px 20px",
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <Link
                href={`/agents/${a.id}/edit`}
                className="card-hover"
                style={{
                  flex: 1,
                  minWidth: 0,
                  padding: "8px 8px 8px 0",
                  textDecoration: "none",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 16,
                  borderRadius: 8,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                  {/* Avatar */}
                  <div
                    style={{
                      width: 42,
                      height: 42,
                      borderRadius: 12,
                      background: "linear-gradient(135deg, rgba(59,130,246,0.2) 0%, rgba(45,212,191,0.15) 100%)",
                      border: "1px solid rgba(59,130,246,0.15)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 16,
                      color: "#60a5fa",
                      flexShrink: 0,
                    }}
                  >
                    ◎
                  </div>
                  <div>
                    <p
                      style={{
                        fontSize: 15,
                        fontWeight: 500,
                        color: "var(--text-primary)",
                        marginBottom: 3,
                      }}
                    >
                      {a.name}
                    </p>
                    {a.description ? (
                      <p
                        style={{
                          fontSize: 12,
                          color: "var(--text-tertiary)",
                          maxWidth: 480,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {a.description}
                      </p>
                    ) : null}
                  </div>
                </div>

                {/* Right side */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    flexShrink: 0,
                  }}
                >
                  {a.proactive_fact_check && (
                    <span className="tag tag-blue">Fact-check</span>
                  )}
                  {a.screenshot_on_request && (
                    <span className="tag tag-teal">Screenshots</span>
                  )}
                  <span
                    style={{
                      fontSize: 12,
                      color: "var(--text-tertiary)",
                      marginLeft: 4,
                    }}
                  >
                    Edit →
                  </span>
                </div>
              </Link>
              <DeleteRowButton
                apiPath={`/api/agents/${a.id}`}
                confirmMessage="Delete this agent and all meetings linked to it? This cannot be undone."
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
