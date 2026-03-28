"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

type MeResponse = {
  authenticated: boolean;
  user: {
    sub: string | null;
    email: string | null;
    name: string | null;
  } | null;
};

export default function AuthPage() {
  const router = useRouter();
  const authError =
    typeof window !== "undefined"
      ? new URLSearchParams(window.location.search).get("authError") ?? ""
      : "";

  useEffect(() => {
    const loadMe = async () => {
      const response = await fetch("/api/auth/me");
      if (!response.ok) {
        return;
      }
      const data: MeResponse = await response.json();
      if (data.authenticated) {
        router.replace("/");
      }
    };

    loadMe();
  }, [router]);

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
              background: "linear-gradient(135deg, #3b82f6 0%, #2dd4bf 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 24px rgba(59,130,246,0.4)",
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
          className="card"
          style={{
            padding: "40px 36px",
            borderRadius: "var(--radius-xl)",
            textAlign: "center",
          }}
        >
          <p
            style={{
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              color: "var(--text-tertiary)",
              marginBottom: 12,
            }}
          >
            Welcome
          </p>
          <h1
            style={{
              fontFamily: "var(--font-display)",
              fontSize: 26,
              fontWeight: 400,
              color: "var(--text-primary)",
              lineHeight: 1.25,
              marginBottom: 12,
            }}
          >
            Sign in to your workspace
          </h1>
          <p
            style={{
              fontSize: 14,
              color: "var(--text-secondary)",
              lineHeight: 1.6,
              marginBottom: 28,
            }}
          >
            Use your email to create an account or access agents, live meetings,
            and transcripts powered by Recall.ai.
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <a href="/api/auth/signup" className="btn-primary" style={{ justifyContent: "center", width: "100%" }}>
              Create account
            </a>
            <a
              href="/api/auth/login"
              className="btn-secondary"
              style={{ justifyContent: "center", width: "100%" }}
            >
              Log in
            </a>
          </div>

          {authError ? (
            <p
              role="alert"
              style={{
                marginTop: 20,
                fontSize: 13,
                color: "var(--red)",
                lineHeight: 1.5,
                padding: "12px 14px",
                borderRadius: 10,
                background: "rgba(248,113,113,0.08)",
                border: "1px solid rgba(248,113,113,0.2)",
              }}
            >
              {authError}
            </p>
          ) : null}

          <p
            style={{
              marginTop: 28,
              fontSize: 12,
              color: "var(--text-tertiary)",
              lineHeight: 1.5,
            }}
          >
            By continuing you agree to Briefed&apos;s use of authentication
            services from WorkOS.
          </p>
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
