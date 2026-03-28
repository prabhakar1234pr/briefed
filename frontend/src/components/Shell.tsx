"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const navItems = [
  { href: "/", label: "Home" },
  { href: "/agents", label: "Agents" },
  { href: "/meeting", label: "Start" },
  { href: "/meetings", label: "Meetings" },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [signedIn, setSignedIn] = useState<boolean | null>(null);

  useEffect(() => {
    fetch("/api/auth/me")
      .then((r) => r.json())
      .then((data) => setSignedIn(data.authenticated === true))
      .catch(() => setSignedIn(false));
  }, [pathname]);

  if (pathname === "/auth") return <>{children}</>;

  return (
    <div className="min-h-screen flex flex-col relative z-10">
      {/* Nav */}
      <header
        style={{
          position: "sticky",
          top: 0,
          zIndex: 50,
          borderBottom: "1px solid rgba(255,255,255,0.06)",
          background: "rgba(8,10,15,0.8)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
        }}
      >
        <div
          style={{
            maxWidth: 1100,
            margin: "0 auto",
            padding: "0 24px",
            height: 56,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          {/* Logo */}
          <Link
            href="/"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              textDecoration: "none",
            }}
          >
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: 8,
                background: "linear-gradient(135deg, #3b82f6 0%, #2dd4bf 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 0 16px rgba(59,130,246,0.35)",
              }}
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
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
                fontFamily: "var(--font-sans)",
                fontSize: 16,
                fontWeight: 500,
                color: "var(--text-primary)",
                letterSpacing: "-0.01em",
              }}
            >
              Briefed
            </span>
          </Link>

          {/* Nav links */}
          <nav style={{ display: "flex", alignItems: "center", gap: 2 }}>
            {navItems.map((item) => {
              const active =
                item.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  style={{
                    padding: "5px 12px",
                    borderRadius: 8,
                    fontSize: 13,
                    fontWeight: active ? 500 : 400,
                    color: active ? "var(--text-primary)" : "var(--text-tertiary)",
                    background: active ? "rgba(255,255,255,0.07)" : "transparent",
                    textDecoration: "none",
                    transition: "color 0.15s, background 0.15s",
                  }}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          {/* Right side */}
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {signedIn ? (
              <>
                <Link
                  href="/meeting"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    background: "var(--accent)",
                    color: "#fff",
                    borderRadius: 8,
                    padding: "6px 14px",
                    fontSize: 13,
                    fontWeight: 500,
                    textDecoration: "none",
                    boxShadow: "0 0 16px rgba(59,130,246,0.25)",
                    transition: "background 0.15s",
                  }}
                >
                  <span style={{ fontSize: 11 }}>●</span>
                  New meeting
                </Link>
                <a
                  href="/api/auth/logout"
                  style={{
                    padding: "5px 12px",
                    borderRadius: 8,
                    fontSize: 13,
                    color: "var(--text-tertiary)",
                    textDecoration: "none",
                    transition: "color 0.15s",
                  }}
                >
                  Sign out
                </a>
              </>
            ) : (
              <Link
                href="/auth"
                className="btn-primary"
                style={{ fontSize: 13, padding: "8px 18px", textDecoration: "none" }}
              >
                Sign in
              </Link>
            )}
          </div>
        </div>
      </header>

      <main style={{ flex: 1, position: "relative", zIndex: 1 }}>
        {children}
      </main>
    </div>
  );
}
