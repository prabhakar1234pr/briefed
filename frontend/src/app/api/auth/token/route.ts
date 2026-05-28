import { NextResponse } from "next/server";
import { getServerUser } from "@/lib/auth";

export const runtime = "nodejs";

/**
 * Returns the current user's Firebase UID, or 401 if not signed in.
 *
 * The Clerk-era variant of this route returned a JWT; with Firebase that's
 * no longer needed (the session cookie is the canonical credential, and
 * client code reads the live ID token via `useAuth().getIdToken()`).
 */
export async function GET() {
  const user = await getServerUser();
  if (!user) {
    return NextResponse.json({ uid: null }, { status: 401 });
  }
  return NextResponse.json({ uid: user.uid });
}
