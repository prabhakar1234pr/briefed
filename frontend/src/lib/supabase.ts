import "server-only";
import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { getAuth as getAdminAuth } from "firebase-admin/auth";
import { getFirebaseAdmin } from "@/lib/firebase-admin";
import { getServerUser } from "@/lib/auth";

export const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";

function getSupabaseConfig() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error(
      "Missing Supabase env vars: NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY",
    );
  }

  return { supabaseUrl, supabaseAnonKey };
}

/* ─── Firebase ID-token minting for server-side Supabase requests ─────────
 *
 * Server components don't see the user's Firebase ID token directly — they
 * only have the long-lived session cookie. To talk to Supabase as the user
 * (so RLS applies), we:
 *   1. Verify the session cookie → get the UID.
 *   2. Mint a Firebase *custom token* for that UID via Admin SDK.
 *   3. Exchange the custom token for an ID token via Firebase's REST API
 *      (`accounts:signInWithCustomToken`).
 *   4. Pass the ID token as a Bearer to Supabase.
 *
 * Firebase ID tokens live 60 minutes. We cache per UID for 50 minutes to
 * give a comfortable refresh buffer without round-tripping on every page.
 */

type CachedToken = { idToken: string; expiresAt: number };
const tokenCache = new Map<string, CachedToken>();
const TOKEN_TTL_MS = 50 * 60 * 1000;

async function mintIdTokenForUid(uid: string): Promise<string> {
  const cached = tokenCache.get(uid);
  if (cached && cached.expiresAt > Date.now()) {
    return cached.idToken;
  }

  const apiKey = process.env.NEXT_PUBLIC_FIREBASE_API_KEY;
  if (!apiKey) {
    throw new Error(
      "Missing NEXT_PUBLIC_FIREBASE_API_KEY (required for custom-token exchange)",
    );
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
    const text = await resp.text();
    throw new Error(`signInWithCustomToken failed (${resp.status}): ${text}`);
  }

  const data = (await resp.json()) as { idToken?: string };
  if (!data.idToken) {
    throw new Error("signInWithCustomToken returned no idToken");
  }

  tokenCache.set(uid, {
    idToken: data.idToken,
    expiresAt: Date.now() + TOKEN_TTL_MS,
  });
  return data.idToken;
}

/**
 * DB Supabase client for server components and API routes.
 *
 * Verifies the Firebase session cookie, mints a fresh ID token for the
 * verified UID, and attaches it as a Bearer token. Supabase (configured
 * with Firebase as a third-party JWT issuer) sees `auth.jwt() ->> 'sub'`
 * equal to the Firebase UID — which matches the `user_id` column on every
 * RLS-protected table.
 *
 * If the caller is unauthenticated, returns a client with no bearer token;
 * RLS will return zero rows. Pages should `await requireServerUser()`
 * first to short-circuit that case.
 */
export async function getSupabaseDbClient(): Promise<SupabaseClient> {
  const { supabaseUrl, supabaseAnonKey } = getSupabaseConfig();
  const user = await getServerUser();

  let idToken: string | null = null;
  if (user) {
    try {
      idToken = await mintIdTokenForUid(user.uid);
    } catch (e) {
      console.error("Failed to mint Firebase ID token:", e);
    }
  }

  return createClient(supabaseUrl, supabaseAnonKey, {
    global: idToken ? { headers: { Authorization: `Bearer ${idToken}` } } : {},
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

/**
 * Public read client — no JWT, no auth. Used only for routes that intentionally
 * serve content without sign-in (e.g., a shared-meeting page where the URL is
 * the authorization token).
 *
 * After the v2 RLS lockdown this will return zero rows from any table that
 * requires `auth.jwt() ->> 'sub'`. Public-share pages must either:
 *   - Use a dedicated `public_shares` table with a `share_token`-based policy, or
 *   - Use `getSupabaseAdminClient()` (server-only) and validate the share token
 *     in the route handler.
 */
export function getSupabasePublicClient() {
  const { supabaseUrl, supabaseAnonKey } = getSupabaseConfig();
  return createClient(supabaseUrl, supabaseAnonKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}
