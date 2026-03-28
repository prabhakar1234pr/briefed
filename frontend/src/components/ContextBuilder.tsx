"use client";

import { useCallback, useEffect, useState } from "react";
import {
  addContext,
  deleteContext,
  fetchContext,
  type ContextSource,
} from "@/lib/meeting-api";

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 2) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function shortUrl(url: string) {
  if (url === "manual") return "Manual text";
  try {
    const u = new URL(url);
    return u.hostname.replace("www.", "") + u.pathname.slice(0, 30);
  } catch {
    return url.slice(0, 40);
  }
}

export function ContextBuilder({ agentId }: { agentId: string }) {
  const [sources, setSources] = useState<ContextSource[]>([]);
  const [totalChunks, setTotalChunks] = useState(0);
  const [loading, setLoading] = useState(true);

  const [tab, setTab] = useState<"url" | "text">("url");
  const [urlInput, setUrlInput] = useState("");
  const [textInput, setTextInput] = useState("");
  const [textLabel, setTextLabel] = useState("");
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const [addSuccess, setAddSuccess] = useState<string | null>(null);
  const [deletingUrl, setDeletingUrl] = useState<string | null>(null);

  const loadContext = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchContext(agentId);
      setSources(data.sources);
      setTotalChunks(data.total_chunks);
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchContext(agentId)
      .then((data) => {
        if (cancelled) return;
        setSources(data.sources);
        setTotalChunks(data.total_chunks);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [agentId]);

  async function handleAdd() {
    setAddError(null);
    setAddSuccess(null);
    const content = tab === "url" ? urlInput.trim() : textInput.trim();
    if (!content) { setAddError("Content is required."); return; }
    if (tab === "url" && !content.startsWith("http")) { setAddError("Enter a valid URL starting with https://"); return; }

    setAdding(true);
    const result = await addContext(agentId, tab, content, textLabel.trim() || undefined);
    setAdding(false);

    if (!result.ok) {
      setAddError(result.error);
      return;
    }

    setAddSuccess(`✓ Added ${result.chunks_added} chunks from ${shortUrl(result.source_url)}`);
    if (tab === "url") setUrlInput("");
    else { setTextInput(""); setTextLabel(""); }
    await loadContext();
    setTimeout(() => setAddSuccess(null), 4000);
  }

  async function handleDelete(sourceUrl: string) {
    setDeletingUrl(sourceUrl);
    await deleteContext(agentId, sourceUrl);
    setDeletingUrl(null);
    await loadContext();
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Add source card */}
      <div className="card" style={{ padding: 24 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
          <div>
            <p style={{ fontSize: 11, fontWeight: 500, letterSpacing: "0.1em", color: "var(--text-tertiary)", textTransform: "uppercase", marginBottom: 4 }}>
              Knowledge base
            </p>
            <p style={{ fontSize: 14, fontWeight: 500, color: "var(--text-primary)" }}>
              Add context sources
            </p>
          </div>
          {totalChunks > 0 && (
            <span className="tag tag-teal">
              {totalChunks} chunks indexed
            </span>
          )}
        </div>

        {/* Tab switcher */}
        <div style={{ display: "flex", gap: 4, marginBottom: 16, background: "rgba(255,255,255,0.04)", borderRadius: 10, padding: 4 }}>
          {(["url", "text"] as const).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              style={{
                flex: 1,
                padding: "7px 12px",
                borderRadius: 7,
                border: "none",
                fontSize: 13,
                fontWeight: tab === t ? 500 : 400,
                color: tab === t ? "var(--text-primary)" : "var(--text-tertiary)",
                background: tab === t ? "rgba(255,255,255,0.1)" : "transparent",
                cursor: "pointer",
                transition: "background 0.15s, color 0.15s",
                fontFamily: "var(--font-sans)",
              }}
            >
              {t === "url" ? "URL / GitHub" : "Raw text"}
            </button>
          ))}
        </div>

        {tab === "url" ? (
          <div style={{ display: "flex", gap: 10 }}>
            <input
              className="input-field"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              placeholder="https://github.com/org/repo  or  https://docs.example.com/page"
              onKeyDown={(e) => { if (e.key === "Enter") void handleAdd(); }}
            />
            <button
              type="button"
              onClick={handleAdd}
              disabled={adding}
              className="btn-primary"
              style={{ flexShrink: 0 }}
            >
              {adding ? (
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" style={{ animation: "spin 0.8s linear infinite" }}>
                  <circle cx="7" cy="7" r="5" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" />
                  <path d="M7 2a5 5 0 0 1 5 5" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              ) : "Add"}
            </button>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <input
              className="input-field"
              value={textLabel}
              onChange={(e) => setTextLabel(e.target.value)}
              placeholder="Label (e.g. 'Product spec', 'Meeting notes')"
            />
            <textarea
              className="input-field"
              rows={5}
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="Paste any text — docs, specs, notes, context…"
              style={{ resize: "vertical", minHeight: 100 }}
            />
            <button
              type="button"
              onClick={handleAdd}
              disabled={adding}
              className="btn-primary"
              style={{ alignSelf: "flex-start" }}
            >
              {adding ? "Indexing…" : "Add text"}
            </button>
          </div>
        )}

        {addError && (
          <p style={{ fontSize: 13, color: "#fca5a5", marginTop: 10 }}>{addError}</p>
        )}
        {addSuccess && (
          <p style={{ fontSize: 13, color: "var(--green)", marginTop: 10 }}>{addSuccess}</p>
        )}

        <p style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 12, lineHeight: 1.6 }}>
          Supported: GitHub repo URLs (fetches README), any public webpage, raw text.
          Content is chunked and embedded — the agent uses this to answer questions during meetings.
        </p>
      </div>

      {/* Sources list */}
      {loading ? (
        <div style={{ padding: "20px 0", textAlign: "center" }}>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Loading context…</p>
        </div>
      ) : sources.length === 0 ? (
        <div
          style={{
            padding: "32px 24px",
            borderRadius: "var(--radius-xl)",
            border: "1px dashed var(--border-subtle)",
            textAlign: "center",
          }}
        >
          <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
            No sources yet. Add a URL or paste text above.
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {sources.map((src) => (
            <div
              key={src.source_url}
              className="card"
              style={{
                padding: "14px 18px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 12,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0 }}>
                <div
                  style={{
                    width: 32, height: 32, borderRadius: 8,
                    background: "rgba(45,212,191,0.1)",
                    border: "1px solid rgba(45,212,191,0.15)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 14, color: "#5eead4", flexShrink: 0,
                  }}
                >
                  ◈
                </div>
                <div style={{ minWidth: 0 }}>
                  <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {shortUrl(src.source_url)}
                  </p>
                  <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 1 }}>
                    {src.chunk_count} chunks · {timeAgo(src.last_added)}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => void handleDelete(src.source_url)}
                disabled={deletingUrl === src.source_url}
                style={{
                  background: "none", border: "none",
                  color: "var(--text-tertiary)", cursor: "pointer",
                  fontSize: 18, lineHeight: 1, padding: "4px 8px",
                  borderRadius: 6,
                  transition: "color 0.15s, background 0.15s",
                  flexShrink: 0,
                  fontFamily: "var(--font-sans)",
                }}
              >
                {deletingUrl === src.source_url ? "…" : "×"}
              </button>
            </div>
          ))}
        </div>
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
