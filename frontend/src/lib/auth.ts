import "server-only";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { verifySessionCookie } from "@/lib/firebase-admin";

export type ServerUser = {
  uid: string;
  email?: string;
  name?: string;
};

const SESSION_COOKIE_NAME = "__session";

/**
 * Read & verify the Firebase session cookie. Returns the canonical user
 * shape used by server components and route handlers, or `null` if not
 * signed in (cookie missing / expired / revoked / invalid).
 */
export async function getServerUser(): Promise<ServerUser | null> {
  const cookieStore = await cookies();
  const cookie = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  const decoded = await verifySessionCookie(cookie);
  if (!decoded) return null;
  return {
    uid: decoded.uid,
    email: typeof decoded.email === "string" ? decoded.email : undefined,
    name: typeof decoded.name === "string" ? decoded.name : undefined,
  };
}

/**
 * Same as `getServerUser` but redirects to `/auth?next=...` when the user
 * is not signed in. Use inside server components/pages.
 *
 * @param nextPath  Path to send the user back to after sign-in. Defaults
 *                  to the current page via the middleware-provided redirect,
 *                  but pages may pass an explicit value if needed.
 */
export async function requireServerUser(nextPath?: string): Promise<ServerUser> {
  const user = await getServerUser();
  if (!user) {
    const qs = nextPath ? `?next=${encodeURIComponent(nextPath)}` : "";
    redirect(`/auth${qs}`);
  }
  return user;
}
