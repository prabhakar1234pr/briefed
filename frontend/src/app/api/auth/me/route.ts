import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { getAuth as getAdminAuth } from "firebase-admin/auth";
import { getFirebaseAdmin, verifySessionCookie } from "@/lib/firebase-admin";
import { getSupabaseAdminClient } from "@/lib/supabase-admin";

export const runtime = "nodejs";

const SESSION_COOKIE_NAME = "__session";

// /api/auth/me upserts the user row keyed on the Firebase UID. The row
// doesn't exist yet for new sign-ups, so the user-scoped RLS policies would
// reject the insert. We use the service-role admin client here on purpose —
// this endpoint is the trusted "user-provisioning" step.

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

  // Provision the users row. If something goes wrong (RLS, FK, unique-email
  // collision from a legacy account) we surface it instead of silently
  // returning a half-authenticated session — that was the bug behind a
  // notorious "agents_user_id_fkey violation" report.
  try {
    const supabase = getSupabaseAdminClient();
    const { error } = await supabase.from("users").upsert(
      {
        id: decoded.uid,
        email,
        full_name: fullName,
        avatar_url: avatarUrl,
        updated_at: new Date().toISOString(),
      },
      { onConflict: "id" },
    );
    if (error) {
      console.error("[/api/auth/me] users.upsert failed:", error);
      return NextResponse.json(
        {
          authenticated: false,
          user: null,
          error: `User provisioning failed: ${error.message}`,
          code: error.code,
        },
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
