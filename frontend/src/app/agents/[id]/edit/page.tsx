import Link from "next/link";
import { notFound } from "next/navigation";
import { serverApiGet } from "@/lib/server-api";
import { requireServerUser } from "@/lib/auth";
import { AgentForm } from "@/components/AgentForm";
import { ContextBuilder } from "@/components/ContextBuilder";
import type { Agent } from "@/types/agents";

type Props = { params: Promise<{ id: string }> };

export default async function EditAgentPage({ params }: Props) {
  const { id } = await params;
  await requireServerUser(`/agents/${id}/edit`);
  let agent: Agent | null = null;
  try {
    agent = await serverApiGet<Agent>(`/api/agents/${id}`);
  } catch {
    notFound();
  }
  if (!agent) notFound();

  return (
    <div style={{ maxWidth: 820, margin: "0 auto", padding: "48px 24px" }}>
      <div className="anim-0" style={{ marginBottom: 36 }}>
        <Link
          href="/agents"
          style={{
            display: "inline-flex", alignItems: "center", gap: 6,
            fontSize: 13, color: "var(--text-tertiary)",
            textDecoration: "none", marginBottom: 20,
          }}
        >
          ← Agents
        </Link>
        <h1
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 30, fontWeight: 400,
            letterSpacing: "-0.02em",
            color: "var(--text-primary)", marginBottom: 6,
          }}
        >
          {agent.name}
        </h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
          Configure identity, persona, capabilities, and knowledge base.
        </p>
      </div>

      {/* Two column: settings left, context right */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, alignItems: "start" }}>
        <div className="anim-1">
          <AgentForm mode="edit" initialAgent={agent} />
        </div>
        <div className="anim-2">
          <ContextBuilder agentId={id} />
        </div>
      </div>
    </div>
  );
}
