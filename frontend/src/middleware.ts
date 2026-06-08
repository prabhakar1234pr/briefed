import { NextResponse, type NextRequest } from "next/server";

const SESSION_COOKIE_NAME = "__session";

// Public paths that should never be auth-gated. Everything else under the
// middleware matcher is treated as protected.
//
// We DO NOT verify the session cookie here — Firebase Admin SDK relies on
// Node APIs and won't run on Next's edge runtime. The cookie's mere presence
// gets the user past the gate; server components/route handlers do the real
// verification via `getServerUser()`.
const PUBLIC_PREFIXES = [
  "/auth",
  "/share",
  "/docs",
  "/api/auth/session",
  "/api/auth/me",
];

function isPublic(pathname: string) {
  if (pathname === "/") return true;
  return PUBLIC_PREFIXES.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`),
  );
}

export default function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  if (isPublic(pathname)) return NextResponse.next();

  const cookie = req.cookies.get(SESSION_COOKIE_NAME)?.value;
  if (cookie) return NextResponse.next();

  const url = req.nextUrl.clone();
  url.pathname = "/auth";
  url.search = `?next=${encodeURIComponent(pathname)}`;
  return NextResponse.redirect(url);
}

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
