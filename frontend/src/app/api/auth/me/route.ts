import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { getAuth as getAdminAuth } from "firebase-admin/auth";
import { getFirebaseAdmin, verifySessionCookie } from "@/lib/firebase-admin";
import { serverApiPost } from "@/lib/server-api";

export const runtime = "nodejs";

const SESSION_COOKIE_NAME = "__session";

// /api/auth/me provisions the user row keyed on the Firebase UID by calling the
// backend's /api/users/provision (which upserts into Cloud SQL). The row may not
// exist yet for new sign-ups, so this is the trusted "user-provisioning" step.

export async function GET() {
  const cookieStore = await cookies();
  const cookie = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  const decoded = await verifySessionCookie(cookie);

  if (!decoded) {
    return NextResponse.json({ authenticated: false, user: null });
  }

  // Pull the freshest profile info from Firebase Auth — session cookie
  // claims can be stale if the user updated their display name/photo.
  let email = typeof decoded.email === "string" ? decoded.email : "";
  let fullName = typeof decoded.name === "string" ? decoded.name : null;
  let avatarUrl: string | null =
    typeof decoded.picture === "string" ? decoded.picture : null;

  try {
    const record = await getAdminAuth(getFirebaseAdmin()).getUser(decoded.uid);
    email = record.email ?? email;
    fullName = record.displayName ?? fullName;
    avatarUrl = record.photoURL ?? avatarUrl;
  } catch (e) {
    console.error("Failed to fetch Firebase user record:", e);
  }

  // Provision the users row via the backend (Cloud SQL upsert). Surface
  // failures instead of returning a half-authenticated session.
  try {
    const res = await serverApiPost("/api/users/provision", {
      email,
      full_name: fullName,
      avatar_url: avatarUrl,
    });
    if (!res.ok) {
      console.error("[/api/auth/me] provision failed:", res.error);
      return NextResponse.json(
        { authenticated: false, user: null, error: `User provisioning failed: ${res.error}` },
        { status: 500 },
      );
    }
  } catch (e) {
    console.error("[/api/auth/me] unexpected error:", e);
    return NextResponse.json(
      { authenticated: false, user: null, error: "User provisioning crashed" },
      { status: 500 },
    );
  }

  return NextResponse.json({
    authenticated: true,
    user: {
      sub: decoded.uid,
      email: email || null,
      name: fullName,
    },
  });
}
