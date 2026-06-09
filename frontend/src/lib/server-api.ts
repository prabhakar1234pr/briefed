import "server-only";
import { getAuth as getAdminAuth } from "firebase-admin/auth";
import { getFirebaseAdmin, verifySessionCookie } from "@/lib/firebase-admin";
import { cookies } from "next/headers";

/**
 * Server-side client for the FastAPI backend.
 *
 * Server components only have the long-lived Firebase session cookie, not an ID
 * token. To call the backend (which validates Firebase ID tokens), we:
 *   1. Verify the session cookie → get the UID.
 *   2. Mint a Firebase custom token for that UID (Admin SDK).
 *   3. Exchange it for an ID token via Firebase's REST API.
 *   4. Send it as `Authorization: Bearer` to the backend.
 *
 * ID tokens live 60 min; we cache per UID for 50 min.
 *
 * (This replaces the old getSupabaseDbClient(), which did the same token dance
 * to talk to Supabase. Now it talks to our backend instead.)
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const SESSION_COOKIE_NAME = "__session";

type CachedToken = { idToken: string; expiresAt: number };
const tokenCache = new Map<string, CachedToken>();
const TOKEN_TTL_MS = 50 * 60 * 1000;

async function mintIdTokenForUid(uid: string): Promise<string> {
  const cached = tokenCache.get(uid);
  if (cached && cached.expiresAt > Date.now()) return cached.idToken;

  const apiKey = process.env.NEXT_PUBLIC_FIREBASE_API_KEY;
  if (!apiKey) {
    throw new Error("Missing NEXT_PUBLIC_FIREBASE_API_KEY (custom-token exchange)");
  }
  const customToken = await getAdminAuth(getFirebaseAdmin()).createCustomToken(uid);
  const resp = await fetch(
    `https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key=${apiKey}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: customToken, returnSecureToken: true }),
    },
  );
  if (!resp.ok) {
    throw new Error(`signInWithCustomToken failed (${resp.status}): ${await resp.text()}`);
  }
  const data = (await resp.json()) as { idToken?: string };
  if (!data.idToken) throw new Error("signInWithCustomToken returned no idToken");

  tokenCache.set(uid, { idToken: data.idToken, expiresAt: Date.now() + TOKEN_TTL_MS });
  return data.idToken;
}

/** Get a Bearer token for the currently signed-in user, or null if unauthenticated. */
async function bearerForCurrentUser(): Promise<string | null> {
  const cookieStore = await cookies();
  const cookie = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  const decoded = await verifySessionCookie(cookie);
  if (!decoded) return null;
  try {
    return await mintIdTokenForUid(decoded.uid);
  } catch (e) {
    console.error("[server-api] failed to mint ID token:", e);
    return null;
  }
}

/** GET a backend endpoint as the current user. Returns parsed JSON. Throws on non-OK. */
export async function serverApiGet<T = unknown>(path: string): Promise<T> {
  const token = await bearerForCurrentUser();
  const r = await fetch(`${API_BASE_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });
  if (!r.ok) {
    const body = await r.text().catch(() => "");
    throw new Error(`Backend ${r.status} on ${path}: ${body.slice(0, 200)}`);
  }
  return r.json() as Promise<T>;
}

/** POST a backend endpoint as the current user. Returns ok flag + parsed data/error. */
export async function serverApiPost<T = unknown>(
  path: string,
  body: unknown,
): Promise<{ ok: true; data: T } | { ok: false; error: string }> {
  const token = await bearerForCurrentUser();
  const r = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const detail = (data as { detail?: unknown }).detail;
    return { ok: false, error: typeof detail === "string" ? detail : `Backend ${r.status}` };
  }
  return { ok: true, data: data as T };
}

/** Public (no-auth) GET — for the share page. */
export async function publicApiGet<T = unknown>(path: string): Promise<T | null> {
  const r = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`Backend ${r.status} on ${path}`);
  return r.json() as Promise<T>;
}

/** DELETE a backend endpoint as the current user. Returns ok flag + optional error. */
export async function serverApiDelete(path: string): Promise<{ ok: boolean; error?: string }> {
  const token = await bearerForCurrentUser();
  const r = await fetch(`${API_BASE_URL}${path}`, {
    method: "DELETE",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });
  if (!r.ok) {
    const body = await r.text().catch(() => "");
    return { ok: false, error: body.slice(0, 200) || `Backend ${r.status}` };
  }
  return { ok: true };
}
