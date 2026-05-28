import "server-only";
import {
  initializeApp,
  getApps,
  getApp,
  cert,
  type App,
} from "firebase-admin/app";
import { getAuth as getAdminAuth, type DecodedIdToken } from "firebase-admin/auth";

/**
 * Server-side Firebase Admin SDK initialization (singleton).
 *
 * Reads FIREBASE_PROJECT_ID, FIREBASE_CLIENT_EMAIL, FIREBASE_PRIVATE_KEY.
 *
 * The private key is stored in env as a single line with literal `\n`
 * escapes (so it survives shell/Vercel env-var pasting); we expand those
 * back to real newlines before handing it to the cert loader.
 */

function getAdminConfig() {
  const projectId = process.env.FIREBASE_PROJECT_ID;
  const clientEmail = process.env.FIREBASE_CLIENT_EMAIL;
  const rawPrivateKey = process.env.FIREBASE_PRIVATE_KEY;

  if (!projectId || !clientEmail || !rawPrivateKey) {
    throw new Error(
      "Missing Firebase Admin env vars: FIREBASE_PROJECT_ID, FIREBASE_CLIENT_EMAIL, FIREBASE_PRIVATE_KEY",
    );
  }

  const privateKey = rawPrivateKey.replace(/\\n/g, "\n");
  return { projectId, clientEmail, privateKey };
}

export function getFirebaseAdmin(): App {
  if (getApps().length > 0) return getApp();
  const { projectId, clientEmail, privateKey } = getAdminConfig();
  return initializeApp({
    credential: cert({ projectId, clientEmail, privateKey }),
  });
}

/**
 * Verify a Firebase session cookie (set via `createSessionCookie`).
 *
 * Returns the decoded claims if valid, or `null` on any error
 * (expired, revoked, malformed, missing). Callers should treat
 * a `null` result as "not signed in".
 */
export async function verifySessionCookie(
  cookie: string | undefined,
): Promise<DecodedIdToken | null> {
  if (!cookie) return null;
  try {
    return await getAdminAuth(getFirebaseAdmin()).verifySessionCookie(
      cookie,
      true /* checkRevoked */,
    );
  } catch {
    return null;
  }
}

/**
 * Verify a raw Firebase ID token (the JWT clients get from `getIdToken()`).
 * Used by the session-exchange endpoint before minting the session cookie.
 */
export async function verifyIdToken(
  token: string,
): Promise<DecodedIdToken | null> {
  if (!token) return null;
  try {
    return await getAdminAuth(getFirebaseAdmin()).verifyIdToken(token);
  } catch {
    return null;
  }
}
