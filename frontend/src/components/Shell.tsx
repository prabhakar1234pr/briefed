"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";

const navItems = [
  { href: "/home", label: "Home" },
  { href: "/agents", label: "Agents" },
  { href: "/meeting", label: "Start meeting" },
  { href: "/meetings", label: "Meetings" },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, signOut } = useAuth();
  const isSignedIn = !!user;

  const isPublicShellless =
    pathname === "/" || pathname === "/auth" || pathname.startsWith("/share/");
  if (isPublicShellless) return <>{children}</>;

  async function handleSignOut() {
    await signOut();
    router.replace("/");
    router.refresh();
  }

  return (
    <div
      className="min-h-screen relative z-10"
      style={{ display: "grid", gridTemplateColumns: "240px minmax(0, 1fr)" }}
    >
      <aside
        style={{
          borderRight: "1px solid var(--border-subtle)",
          background: "rgba(255,255,255,0.82)",
          backdropFilter: "blur(14px)",
          WebkitBackdropFilter: "blur(14px)",
          padding: "18px 14px",
          display: "flex",
          flexDirection: "column",
          gap: 18,
          position: "sticky",
          top: 0,
          height: "100vh",
        }}
      >
        <Link
          href={isSignedIn ? "/home" : "/"}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            textDecoration: "none",
            padding: "6px 8px",
          }}
        >
          <span
            style={{
              position: "relative",
              width: 34,
              height: 34,
              flexShrink: 0,
              borderRadius: 8,
              overflow: "visible",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Image
              src="/assets/favicon.png"
              alt="Agent Bora mark"
              width={34}
              height={34}
              unoptimized
              style={{ borderRadius: 8, transform: "scale(3)", transformOrigin: "center" }}
            />
          </span>
          <span
            style={{
              fontFamily: "var(--font-sans)",
              fontSize: 16,
              fontWeight: 700,
              color: "var(--text-primary)",
              letterSpacing: "-0.01em",
            }}
          >
            Agent <span style={{ color: "#ff8a00" }}>B</span>ora
          </span>
        </Link>

        <nav style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {navItems.map((item) => {
            const active =
              item.href === "/home"
                ? pathname === "/home"
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                style={{
                  padding: "9px 12px",
                  borderRadius: 10,
                  fontSize: 13,
                  fontWeight: active ? 600 : 500,
                  color: active ? "var(--text-primary)" : "var(--text-secondary)",
                  background: active ? "rgba(255,138,0,0.14)" : "transparent",
                  textDecoration: "none",
                  transition: "color 0.15s, background 0.15s",
                }}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: 10 }}>
          {isSignedIn ? (
            <>
              <div
                style={{
                  border: "1px solid var(--border-subtle)",
                  borderRadius: 10,
                  background: "rgba(255,255,255,0.74)",
                  padding: "10px 12px",
                }}
              >
                <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 3 }}>
                  Signed in as
                </p>
                <p style={{ fontSize: 13, color: "var(--text-primary)", fontWeight: 600 }}>
                  {user.displayName || user.email || "User"}
                </p>
              </div>
              <button
                type="button"
                onClick={handleSignOut}
                className="btn-secondary"
                style={{ justifyContent: "center" }}
              >
                Sign out
              </button>
            </>
          ) : (
            <Link
              href="/auth?mode=signin"
              className="btn-primary"
              style={{ fontSize: 13, textDecoration: "none", justifyContent: "center" }}
            >
              Sign in
            </Link>
          )}
        </div>
      </aside>

      <main style={{ position: "relative", zIndex: 1 }}>
        {children}
      </main>
    </div>
  );
}
