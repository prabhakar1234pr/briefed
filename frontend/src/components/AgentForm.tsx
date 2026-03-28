"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { createSupabaseDbBrowserClient } from "@/lib/supabase-browser";
import type { Agent, AgentMode } from "@/types/agents";
import {
  TTS_VOICES,
  DEFAULT_VOICE_ID,
  VOICE_CATEGORIES,
  type TTSVoice,
} from "@/lib/tts-voices";

type Props =
  | { mode: "create"; onCreateSuccess?: (agentId: string) => void }
  | { mode: "edit"; initialAgent: Agent };

/* ─── Inline sub-components ─────────────────────────────────────────────── */

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <label
        style={{
          fontSize: 13,
          fontWeight: 500,
          color: "var(--text-secondary)",
          letterSpacing: "0.01em",
        }}
      >
        {label}
      </label>
      {children}
      {hint && (
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 2 }}>
          {hint}
        </p>
      )}
    </div>
  );
}

function SectionHeader({ icon, title, desc }: { icon: string; title: string; desc: string }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        marginBottom: 20,
        paddingBottom: 16,
        borderBottom: "1px solid var(--border-subtle)",
      }}
    >
      <div
        style={{
          width: 36,
          height: 36,
          borderRadius: 10,
          background: "rgba(124,58,237,0.1)",
          border: "1px solid rgba(124,58,237,0.18)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 16,
          flexShrink: 0,
        }}
      >
        {icon}
      </div>
      <div>
        <p style={{ fontSize: 14, fontWeight: 500, color: "var(--text-primary)" }}>{title}</p>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>{desc}</p>
      </div>
    </div>
  );
}

function Toggle({
  checked,
  onChange,
  label,
  desc,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  desc: string;
}) {
  return (
    <label
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 12,
        cursor: "pointer",
        padding: "12px 16px",
        borderRadius: 10,
        border: "1px solid var(--border-subtle)",
        background: checked ? "rgba(124,58,237,0.06)" : "rgba(255,255,255,0.02)",
        transition: "background 0.15s, border-color 0.15s",
        borderColor: checked ? "rgba(124,58,237,0.22)" : "var(--border-subtle)",
      }}
    >
      <input
        type="checkbox"
        className="check"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        style={{ marginTop: 2 }}
      />
      <div>
        <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>{label}</p>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 2 }}>{desc}</p>
      </div>
    </label>
  );
}

/* ─── Custom dropdown ───────────────────────────────────────────────────── */

function CustomSelect<T extends string>({
  value,
  onChange,
  options,
  renderOption,
  renderSelected,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string; group?: string }[];
  renderOption?: (opt: { value: T; label: string }, isSelected: boolean) => React.ReactNode;
  renderSelected?: (opt: { value: T; label: string } | undefined) => React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);
  const [rect, setRect] = useState<DOMRect | null>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node) &&
          btnRef.current && !btnRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Update position when opening
  useEffect(() => {
    if (open && btnRef.current) {
      setRect(btnRef.current.getBoundingClientRect());
    }
  }, [open]);

  const selected = options.find((o) => o.value === value);
  const groups = [...new Set(options.map((o) => o.group).filter(Boolean))] as string[];

  return (
    <div style={{ position: "relative" }}>
      <button
        ref={btnRef}
        type="button"
        onClick={() => setOpen(!open)}
        style={{
          width: "100%",
          background: "rgba(255,255,255,0.04)",
          border: open ? "1px solid var(--accent)" : "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-md)",
          padding: "10px 14px",
          fontFamily: "var(--font-sans)",
          fontSize: 14,
          color: "var(--text-primary)",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          transition: "border-color 0.15s, background 0.15s, box-shadow 0.15s",
          boxShadow: open ? "0 0 0 3px rgba(124,58,237,0.1)" : "none",
          textAlign: "left",
        }}
      >
        {renderSelected ? renderSelected(selected) : <span>{selected?.label ?? "Select…"}</span>}
        <svg
          width="12" height="12" viewBox="0 0 12 12" fill="none"
          style={{ flexShrink: 0, transition: "transform 0.2s", transform: open ? "rotate(180deg)" : "rotate(0)" }}
        >
          <path d="M3 4.5L6 7.5L9 4.5" stroke="var(--text-tertiary)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && rect && createPortal(
        <div
          ref={ref}
          style={{
            position: "fixed",
            top: rect.bottom + 6,
            left: rect.left,
            width: rect.width,
            zIndex: 9999,
            background: "var(--bg-elevated)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-md)",
            boxShadow: "var(--shadow-lg)",
            maxHeight: 320,
            overflowY: "auto",
            padding: "6px",
          }}
        >
          {groups.length > 0
            ? groups.map((group) => (
                <div key={group}>
                  <div
                    style={{
                      fontSize: 11,
                      fontWeight: 600,
                      color: "var(--text-tertiary)",
                      padding: "8px 10px 4px",
                      letterSpacing: "0.04em",
                      textTransform: "uppercase",
                    }}
                  >
                    {group}
                  </div>
                  {options
                    .filter((o) => o.group === group)
                    .map((opt) => (
                      <DropdownItem
                        key={opt.value}
                        opt={opt}
                        isSelected={opt.value === value}
                        renderOption={renderOption}
                        onClick={() => { onChange(opt.value); setOpen(false); }}
                      />
                    ))}
                </div>
              ))
            : options.map((opt) => (
                <DropdownItem
                  key={opt.value}
                  opt={opt}
                  isSelected={opt.value === value}
                  renderOption={renderOption}
                  onClick={() => { onChange(opt.value); setOpen(false); }}
                />
              ))}
        </div>,
        document.body,
      )}
    </div>
  );
}

function DropdownItem<T extends string>({
  opt,
  isSelected,
  renderOption,
  onClick,
}: {
  opt: { value: T; label: string };
  isSelected: boolean;
  renderOption?: (opt: { value: T; label: string }, isSelected: boolean) => React.ReactNode;
  onClick: () => void;
}) {
  const [hovered, setHovered] = useState(false);
  return (
    <button
      type="button"
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        width: "100%",
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "8px 10px",
        border: "none",
        borderRadius: 8,
        background: isSelected
          ? "rgba(124,58,237,0.12)"
          : hovered
          ? "rgba(255,255,255,0.06)"
          : "transparent",
        color: isSelected ? "var(--text-accent)" : "var(--text-primary)",
        fontSize: 13,
        fontFamily: "var(--font-sans)",
        cursor: "pointer",
        textAlign: "left",
        transition: "background 0.1s",
      }}
    >
      {renderOption ? renderOption(opt, isSelected) : opt.label}
    </button>
  );
}

/* ─── Main form ─────────────────────────────────────────────────────────── */

export function AgentForm(props: Props) {
  const router = useRouter();
  const init = props.mode === "edit" ? props.initialAgent : null;

  const [name, setName] = useState(init?.name ?? "");
  const [agentMode, setAgentMode] = useState<AgentMode>(init?.mode ?? "copilot");
  const [description, setDescription] = useState(init?.description ?? "");
  const [personaPrompt, setPersonaPrompt] = useState(init?.persona_prompt ?? "");

  // Voice: migrate old Cartesia UUIDs to default Google TTS voice
  const rawVoice = init?.voice_id?.trim() ?? "";
  const isCartesiaUuid = rawVoice && !rawVoice.startsWith("en-");
  const [voiceId, setVoiceId] = useState(
    isCartesiaUuid ? DEFAULT_VOICE_ID : rawVoice || DEFAULT_VOICE_ID,
  );

  const [botImageUrl, setBotImageUrl] = useState(init?.bot_image_url ?? "");
  const [proactiveFactCheck, setProactiveFactCheck] = useState(init?.proactive_fact_check ?? true);
  const [screenshotOnRequest, setScreenshotOnRequest] = useState(init?.screenshot_on_request ?? true);
  const [sendPostMeetingEmail, setSendPostMeetingEmail] = useState(init?.send_post_meeting_email ?? true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const voiceDropdownOptions = useMemo(() => {
    return TTS_VOICES.map((v) => {
      const cat = VOICE_CATEGORIES.find((c) => c.key === v.category);
      return {
        value: v.id,
        label: `${v.gender === "female" ? "♀" : "♂"} ${v.label}`,
        group: cat?.label ?? "Other",
      };
    });
  }, []);

  const modeOptions = [
    { value: "copilot" as const, label: "Copilot — Live Q&A + context" },
    { value: "proctor" as const, label: "Proctor — Integrity signals only" },
  ];

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaved(false);
    const trimmed = name.trim();
    if (!trimmed) { setError("Agent name is required."); return; }

    setSaving(true);
    const supabase = createSupabaseDbBrowserClient();
    // Get user ID from WorkOS session
    const meResp = await fetch("/api/auth/me");
    const meData = await meResp.json();
    if (!meData.authenticated || !meData.user?.sub) { setError("Not signed in."); setSaving(false); return; }
    const userId = meData.user.sub;

    const row = {
      name: trimmed,
      mode: agentMode,
      description: description.trim() || null,
      persona_prompt: personaPrompt.trim() || null,
      voice_id: voiceId.trim() || DEFAULT_VOICE_ID,
      bot_image_url: botImageUrl.trim() || null,
      proactive_fact_check: proactiveFactCheck,
      screenshot_on_request: screenshotOnRequest,
      send_post_meeting_email: sendPostMeetingEmail,
    };

    if (props.mode === "create") {
      const { data, error: insertError } = await supabase
        .from("agents")
        .insert({ ...row, user_id: userId })
        .select("id")
        .single();
      if (insertError) { setError(insertError.message); setSaving(false); return; }
      if (props.onCreateSuccess) {
        props.onCreateSuccess(data.id);
        setSaving(false);
        router.refresh();
        return;
      }
      router.push(`/agents/${data.id}/edit`);
      router.refresh();
      return;
    }

    const { error: updateError } = await supabase
      .from("agents")
      .update(row)
      .eq("id", props.initialAgent.id);
    if (updateError) { setError(updateError.message); setSaving(false); return; }
    setSaved(true);
    setSaving(false);
    setTimeout(() => setSaved(false), 3000);
    router.refresh();
  }

  const selectedVoice = TTS_VOICES.find((v) => v.id === voiceId);

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* ── Identity ─────────────────────────────────────────────────── */}
      <div className="card anim-1" style={{ padding: 24 }}>
        <SectionHeader icon="◎" title="Identity" desc="How the agent presents itself in meetings" />
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Field label="Mode" hint="Copilot: live Q&A and context. Proctor: integrity signals only.">
            <CustomSelect
              value={agentMode}
              onChange={(v) => setAgentMode(v as AgentMode)}
              options={modeOptions}
            />
          </Field>
          <Field label="Name *" hint="This name is used as the trigger phrase (e.g. 'Hey Briefed')">
            <input
              className="input-field"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Briefed, Scribe, Assistant…"
            />
          </Field>
          <Field label="Description">
            <input
              className="input-field"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What does this agent specialise in?"
            />
          </Field>
          <Field label="Bot avatar URL">
            <input
              className="input-field"
              type="url"
              value={botImageUrl}
              onChange={(e) => setBotImageUrl(e.target.value)}
              placeholder="https://… (optional, shown in the call)"
            />
          </Field>
        </div>
      </div>

      {/* ── Persona ──────────────────────────────────────────────────── */}
      <div className="card anim-2" style={{ padding: 24 }}>
        <SectionHeader icon="◈" title="Persona & Voice" desc="How the agent thinks, responds, and sounds" />
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Field
            label="System prompt"
            hint="Define the agent's personality, focus area, and behaviour during meetings."
          >
            <textarea
              className="input-field"
              rows={5}
              value={personaPrompt}
              onChange={(e) => setPersonaPrompt(e.target.value)}
              placeholder="You are a precise technical assistant. When answering questions, cite specific lines from the codebase…"
              style={{ resize: "vertical", minHeight: 120 }}
            />
          </Field>
          <Field label="Voice" hint="Google Cloud Neural2/Studio voices — clean, low-latency English TTS.">
            <CustomSelect
              value={voiceId}
              onChange={setVoiceId}
              options={voiceDropdownOptions}
              renderSelected={(opt) => {
                const v = TTS_VOICES.find((tv) => tv.id === voiceId);
                return (
                  <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span
                      style={{
                        width: 6, height: 6, borderRadius: "50%",
                        background: v?.gender === "female" ? "#f472b6" : "#a78bfa",
                        flexShrink: 0,
                      }}
                    />
                    {opt?.label ?? "Select voice…"}
                  </span>
                );
              }}
              renderOption={(opt, isSelected) => {
                const v = TTS_VOICES.find((tv) => tv.id === opt.value);
                return (
                  <span style={{ display: "flex", flexDirection: "column", gap: 1 }}>
                    <span style={{ fontSize: 13, fontWeight: isSelected ? 500 : 400 }}>
                      {opt.label}
                    </span>
                    {v?.description && (
                      <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                        {v.description}
                      </span>
                    )}
                  </span>
                );
              }}
            />
            {selectedVoice && (
              <p style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 4 }}>
                {selectedVoice.description}
              </p>
            )}
          </Field>
        </div>
      </div>

      {/* ── Capabilities ─────────────────────────────────────────────── */}
      <div className="card anim-3" style={{ padding: 24 }}>
        <SectionHeader icon="◉" title="Capabilities" desc="What the agent is allowed to do during meetings" />
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <Toggle
            checked={proactiveFactCheck}
            onChange={setProactiveFactCheck}
            label="Proactive fact-checking"
            desc="Automatically detect and correct factual errors spoken during the meeting."
          />
          <Toggle
            checked={screenshotOnRequest}
            onChange={setScreenshotOnRequest}
            label="Screenshots on request"
            desc="Listen for 'take a screenshot' and capture the meeting screen."
          />
          <Toggle
            checked={sendPostMeetingEmail}
            onChange={setSendPostMeetingEmail}
            label="Post-meeting email"
            desc="Send a summary email with action items when the meeting ends."
          />
        </div>
      </div>

      {/* ── Error / Actions ──────────────────────────────────────────── */}
      {error && (
        <div
          style={{
            padding: "12px 16px",
            borderRadius: 10,
            background: "rgba(248,113,113,0.08)",
            border: "1px solid rgba(248,113,113,0.2)",
            color: "#fca5a5",
            fontSize: 13,
          }}
        >
          {error}
        </div>
      )}

      <div className="anim-4" style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <button type="submit" disabled={saving} className="btn-primary">
          {saving ? (
            <>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" style={{ animation: "spin 0.8s linear infinite" }}>
                <circle cx="7" cy="7" r="5" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" />
                <path d="M7 2a5 5 0 0 1 5 5" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
              Saving…
            </>
          ) : (
            props.mode === "create" ? "Create agent" : "Save changes"
          )}
        </button>
        {saved && (
          <span style={{ fontSize: 13, color: "var(--green)", display: "flex", alignItems: "center", gap: 6 }}>
            ✓ Saved
          </span>
        )}
        <Link href="/agents" className="btn-ghost">
          Cancel
        </Link>
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </form>
  );
}
