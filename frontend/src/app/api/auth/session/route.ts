import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { getAuth as getAdminAuth } from "firebase-admin/auth";
import { getFirebaseAdmin, verifyIdToken } from "@/lib/firebase-admin";

export const runtime = "nodejs";

const SESSION_COOKIE_NAME = "__session";
// 14 days in milliseconds — matches the lifetime Firebase Admin allows for
// session cookies (max is 14 days; we use the full duration).
const SESSION_DURATION_MS = 14 * 24 * 60 * 60 * 1000;

/**
 * POST /api/auth/session
 *
 * Body: { idToken: string }
 *
 * Validates the Firebase ID token, exchanges it for a session cookie via
 * Admin SDK, and sets the cookie as `__session` (httpOnly, sameSite=lax,
 * secure in production). Used by the client after `signInWithPopup` or
 * `signInWithEmailAndPassword` to establish the server-side session.
 */
export async function POST(req: Request) {
  let body: { idToken?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const idToken = body.idToken?.trim();
  if (!idToken) {
    return NextResponse.json({ error: "Missing idToken" }, { status: 400 });
  }

  const decoded = await verifyIdToken(idToken);
  if (!decoded) {
    return NextResponse.json({ error: "Invalid idToken" }, { status: 401 });
  }

  let sessionCookie: string;
  try {
    sessionCookie = await getAdminAuth(getFirebaseAdmin()).createSessionCookie(
      idToken,
      { expiresIn: SESSION_DURATION_MS },
    );
  } catch (e) {
    console.error("createSessionCookie failed:", e);
    return NextResponse.json(
      { error: "Failed to create session" },
      { status: 500 },
    );
  }

  const cookieStore = await cookies();
  cookieStore.set(SESSION_COOKIE_NAME, sessionCookie, {
    maxAge: SESSION_DURATION_MS / 1000,
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
  });

  return NextResponse.json({ ok: true, uid: decoded.uid });
}

/**
 * DELETE /api/auth/session
 *
 * Clears the `__session` cookie. The client should also call
 * `signOut(auth)` from `firebase/auth` to clear the Firebase client state.
 */
export async function DELETE() {
  const cookieStore = await cookies();
  cookieStore.set(SESSION_COOKIE_NAME, "", {
    maxAge: 0,
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
  });
  return NextResponse.json({ ok: true });
}
