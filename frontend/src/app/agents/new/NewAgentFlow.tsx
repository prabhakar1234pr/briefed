"use client";

import Link from "next/link";
import { useState } from "react";
import { AgentForm } from "@/components/AgentForm";
import { ContextBuilder } from "@/components/ContextBuilder";

export function NewAgentFlow() {
  const [createdAgentId, setCreatedAgentId] = useState<string | null>(null);

  return (
    <div style={{ maxWidth: 820, margin: "0 auto", padding: "48px 24px" }}>
      <div className="anim-0" style={{ marginBottom: 36 }}>
        <Link
          href="/agents"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            fontSize: 13,
            color: "var(--text-tertiary)",
            textDecoration: "none",
            marginBottom: 20,
            transition: "color 0.15s",
          }}
        >
          ← Agents
        </Link>
        <h1
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 30,
            fontWeight: 400,
            letterSpacing: "-0.02em",
            color: "var(--text-primary)",
            marginBottom: 6,
          }}
        >
          New agent
        </h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
          Configure identity and persona, then add knowledge sources on the right after you create the agent.
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 24,
          alignItems: "start",
        }}
      >
        <div className="anim-1">
          <AgentForm mode="create" onCreateSuccess={(id) => setCreatedAgentId(id)} />
        </div>
        <div className="anim-2">
          {createdAgentId ? (
            <>
              <p style={{ fontSize: 12, color: "var(--text-tertiary)", marginBottom: 12 }}>
                Knowledge base —{" "}
                <Link href={`/agents/${createdAgentId}/edit`} style={{ color: "var(--text-accent)" }}>
                  Open full edit
                </Link>
              </p>
              <ContextBuilder agentId={createdAgentId} />
            </>
          ) : (
            <div
              className="card"
              style={{
                padding: 24,
                borderStyle: "dashed",
                opacity: 0.85,
              }}
            >
              <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 8 }}>
                Knowledge base
              </p>
              <p style={{ fontSize: 12, color: "var(--text-tertiary)", lineHeight: 1.6 }}>
                Click <strong>Create agent</strong> on the left. You can add URLs and text here right away — no need to leave this page.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
