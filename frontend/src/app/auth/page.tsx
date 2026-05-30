"use client";

import Link from "next/link";
import Image from "next/image";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import {
  GoogleAuthProvider,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signInWithPopup,
  updateProfile,
} from "firebase/auth";
import { getFirebaseAuth } from "@/lib/firebase";
import { useAuth } from "@/components/AuthProvider";

type Mode = "signin" | "signup";

export default function AuthPage() {
  return (
    <Suspense fallback={null}>
      <AuthPageInner />
    </Suspense>
  );
}

function AuthPageInner() {
  const router = useRouter();
  const search = useSearchParams();
  const next = search.get("next") || "/";
  const modeFromQuery = search.get("mode");
  const { user, loading } = useAuth();

  const [mode, setMode] = useState<Mode>(
    modeFromQuery === "signup" ? "signup" : "signin",
  );
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // If already signed in, bounce.
  useEffect(() => {
    if (!loading && user) router.replace(next);
  }, [loading, user, next, router]);

  useEffect(() => {
    if (modeFromQuery === "signup" || modeFromQuery === "signin") {
      setMode(modeFromQuery);
    }
  }, [modeFromQuery]);

  async function syncSession(forceRefresh = false) {
    const auth = getFirebaseAuth();
    const idToken = await auth.currentUser?.getIdToken(forceRefresh);
    if (!idToken) return;
    await fetch("/api/auth/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ idToken }),
    });
  }

  async function handleEmailSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const auth = getFirebaseAuth();
      if (mode === "signup") {
        const trimmedFirst = firstName.trim();
        const trimmedLast = lastName.trim();
        if (!trimmedFirst || !trimmedLast) {
          setError("First name and last name are required.");
          setSubmitting(false);
          return;
        }
        const credential = await createUserWithEmailAndPassword(auth, email, password);
        await updateProfile(credential.user, {
          displayName: `${trimmedFirst} ${trimmedLast}`,
        });
      } else {
        await signInWithEmailAndPassword(auth, email, password);
      }
      // AuthProvider's onIdTokenChanged will also sync, but await once here
      // so the server cookie is set before we navigate.
      await syncSession(mode === "signup");
      await fetch("/api/auth/me", { method: "GET" });
      router.replace(next);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Sign-in failed";
      setError(msg.replace(/^Firebase: /, ""));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleGoogle() {
    setError(null);
    setSubmitting(true);
    try {
      await signInWithPopup(getFirebaseAuth(), new GoogleAuthProvider());
      await syncSession();
      await fetch("/api/auth/me", { method: "GET" });
      router.replace(next);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Google sign-in failed";
      setError(msg.replace(/^Firebase: /, ""));
    } finally {
      setSubmitting(false);
    }
  }

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
          <span
            style={{
              position: "relative",
              width: 34,
              height: 34,
              flexShrink: 0,
              borderRadius: 12,
              overflow: "visible",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Image
              src="/assets/favicon.png"
              alt="Agent Bora icon"
              width={34}
              height={34}
              unoptimized
              style={{ borderRadius: 12, transform: "scale(3)", transformOrigin: "center" }}
            />
          </span>
          <span
            style={{
              fontFamily: "var(--font-display)",
              fontSize: 28,
              fontWeight: 700,
              color: "var(--text-primary)",
              letterSpacing: "-0.02em",
            }}
          >
            Agent <span style={{ color: "#ff8a00" }}>B</span>ora
          </span>
        </Link>

        <div
          className="card"
          style={{
            padding: 28,
            display: "flex",
            flexDirection: "column",
            gap: 16,
          }}
        >
          <div>
            <h1
              style={{
                fontFamily: "var(--font-display)",
                fontSize: 22,
                fontWeight: 700,
                color: "var(--text-primary)",
                marginBottom: 4,
                letterSpacing: "-0.01em",
              }}
            >
              {mode === "signin" ? "Sign in" : "Create your account"}
            </h1>
            <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
              {mode === "signin"
                ? "Welcome back to Agent Bora."
                : "Set up your first agent in minutes."}
            </p>
          </div>

          <button
            type="button"
            onClick={handleGoogle}
            disabled={submitting}
            className="btn-ghost"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 10,
              padding: "10px 14px",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-md)",
              background: "rgba(255,255,255,0.04)",
              cursor: submitting ? "wait" : "pointer",
            }}
          >
            <svg width="16" height="16" viewBox="0 0 18 18" aria-hidden>
              <path
                fill="#4285F4"
                d="M17.64 9.2c0-.64-.06-1.25-.17-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.71-1.57 2.68-3.88 2.68-6.62z"
              />
              <path
                fill="#34A853"
                d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.81.54-1.85.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A9 9 0 0 0 9 18z"
              />
              <path
                fill="#FBBC05"
                d="M3.97 10.71A5.4 5.4 0 0 1 3.68 9c0-.59.1-1.17.29-1.71V4.96H.96A9 9 0 0 0 0 9c0 1.45.35 2.83.96 4.04l3.01-2.33z"
              />
              <path
                fill="#EA4335"
                d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58A9 9 0 0 0 .96 4.96L3.97 7.3C4.68 5.16 6.66 3.58 9 3.58z"
              />
            </svg>
            <span style={{ fontSize: 13, color: "var(--text-primary)" }}>
              Continue with Google
            </span>
          </button>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              fontSize: 11,
              color: "var(--text-tertiary)",
              letterSpacing: "0.06em",
              textTransform: "uppercase",
            }}
          >
            <div style={{ flex: 1, height: 1, background: "var(--border-subtle)" }} />
            or
            <div style={{ flex: 1, height: 1, background: "var(--border-subtle)" }} />
          </div>

          <form
            onSubmit={handleEmailSubmit}
            style={{ display: "flex", flexDirection: "column", gap: 12 }}
          >
            {mode === "signup" && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <input
                  className="input-field"
                  type="text"
                  required
                  autoComplete="given-name"
                  placeholder="First name"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                />
                <input
                  className="input-field"
                  type="text"
                  required
                  autoComplete="family-name"
                  placeholder="Last name"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                />
              </div>
            )}
            <input
              className="input-field"
              type="email"
              required
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <input
              className="input-field"
              type="password"
              required
              autoComplete={mode === "signup" ? "new-password" : "current-password"}
              placeholder="Password"
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {error && (
              <div
                style={{
                  padding: "10px 12px",
                  borderRadius: 10,
                  background: "rgba(248,113,113,0.08)",
                  border: "1px solid rgba(248,113,113,0.2)",
                  color: "#fca5a5",
                  fontSize: 12,
                }}
              >
                {error}
              </div>
            )}
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting
                ? "Working…"
                : mode === "signin"
                  ? "Sign in"
                  : "Create account"}
            </button>
          </form>

          <button
            type="button"
            onClick={() => {
              setError(null);
              setMode(mode === "signin" ? "signup" : "signin");
            }}
            style={{
              background: "none",
              border: "none",
              fontSize: 12,
              color: "var(--text-tertiary)",
              cursor: "pointer",
              textAlign: "center",
            }}
          >
            {mode === "signin"
              ? "Don't have an account? Sign up"
              : "Already have an account? Sign in"}
          </button>
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
