"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

type Props = {
  apiPath: string;
  confirmMessage: string;
  label?: string;
};

export function DeleteRowButton({
  apiPath,
  confirmMessage,
  label = "Delete",
}: Props) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function handleClick(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm(confirmMessage)) return;
    setBusy(true);
    try {
      const res = await fetch(apiPath, { method: "DELETE" });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        alert(typeof body.error === "string" ? body.error : "Delete failed");
        return;
      }
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={busy}
      className="btn-ghost"
      style={{
        fontSize: 12,
        color: "#f87171",
        flexShrink: 0,
        padding: "0 12px",
        minHeight: 36,
      }}
    >
      {busy ? "…" : label}
    </button>
  );
}
