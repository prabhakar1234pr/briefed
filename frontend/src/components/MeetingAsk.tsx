"use client";

import { useState } from "react";
import { askAgent } from "@/lib/meeting-api";

export function MeetingAsk({
  agentId,
  agentName,
  meetingId,
}: {
  agentId: string;
  agentName: string;
  meetingId: string;
}) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAsk() {
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    setAnswer(null);
    try {
      const result = await askAgent(agentId, question.trim(), meetingId);
      setAnswer(result.answer);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="card"
      style={{ padding: 22, background: "rgba(59,130,246,0.04)", border: "1px solid rgba(59,130,246,0.12)" }}
    >
      <p style={{ fontSize: 11, fontWeight: 500, letterSpacing: "0.1em", color: "var(--text-tertiary)", textTransform: "uppercase", marginBottom: 4 }}>
        Ask {agentName}
      </p>
      <p style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 14, lineHeight: 1.6 }}>
        Ask anything about this meeting using the knowledge base for this agent.
      </p>

      <div style={{ display: "flex", gap: 8 }}>
        <input
          className="input-field"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="What was decided about…?"
          onKeyDown={(e) => { if (e.key === "Enter") void handleAsk(); }}
          style={{ flex: 1 }}
        />
        <button
          type="button"
          onClick={handleAsk}
          disabled={loading || !question.trim()}
          className="btn-primary"
          style={{ flexShrink: 0, padding: "10px 14px" }}
        >
          {loading ? (
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" style={{ animation: "spin 0.8s linear infinite" }}>
              <circle cx="6.5" cy="6.5" r="4.5" stroke="rgba(255,255,255,0.3)" strokeWidth="1.4" />
              <path d="M6.5 2a4.5 4.5 0 0 1 4.5 4.5" stroke="white" strokeWidth="1.4" strokeLinecap="round" />
            </svg>
          ) : "→"}
        </button>
      </div>

      {error && (
        <p style={{ fontSize: 12, color: "#fca5a5", marginTop: 10 }}>{error}</p>
      )}

      {answer && (
        <div style={{ marginTop: 14, padding: "12px 14px", borderRadius: 8, background: "rgba(255,255,255,0.04)", border: "1px solid var(--border-subtle)" }}>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 6, fontWeight: 500, letterSpacing: "0.05em", textTransform: "uppercase" }}>
            {agentName}
          </p>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.7 }}>{answer}</p>
        </div>
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
