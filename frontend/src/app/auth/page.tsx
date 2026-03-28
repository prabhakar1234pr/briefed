"use client";

import Link from "next/link";
import { SignIn } from "@clerk/nextjs";

export default function AuthPage() {
  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center px-6 py-16 relative z-10"
      style={{ fontFamily: "var(--font-sans)" }}
    >
      <div style={{ width: "100%", maxWidth: 420 }} className="anim-0">
        {/* Logo */}
        <Link
          href="/"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 12,
            textDecoration: "none",
            marginBottom: 40,
          }}
        >
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              background: "linear-gradient(135deg, #7c3aed 0%, #6366f1 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 24px rgba(124,58,237,0.45)",
            }}
          >
            <svg width="20" height="20" viewBox="0 0 14 14" fill="none" aria-hidden>
              <circle cx="7" cy="7" r="2.5" fill="white" />
              <path
                d="M7 1.5C7 1.5 10.5 3.5 10.5 7C10.5 10.5 7 12.5 7 12.5"
                stroke="white"
                strokeWidth="1.2"
                strokeLinecap="round"
                opacity="0.6"
              />
              <path
                d="M7 1.5C7 1.5 3.5 3.5 3.5 7C3.5 10.5 7 12.5 7 12.5"
                stroke="white"
                strokeWidth="1.2"
                strokeLinecap="round"
                opacity="0.6"
              />
            </svg>
          </div>
          <span
            style={{
              fontFamily: "var(--font-display)",
              fontSize: 28,
              fontWeight: 400,
              color: "var(--text-primary)",
              letterSpacing: "-0.02em",
            }}
          >
            Briefed
          </span>
        </Link>

        <div
          style={{
            display: "flex",
            justifyContent: "center",
          }}
        >
          <SignIn routing="hash" />
        </div>

        <p style={{ textAlign: "center", marginTop: 28 }} className="anim-1">
          <Link href="/" className="btn-ghost" style={{ fontSize: 14 }}>
            &larr; Back to home
          </Link>
        </p>
      </div>
    </div>
  );
}
