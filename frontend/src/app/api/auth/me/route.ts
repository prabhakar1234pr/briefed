import { NextResponse } from "next/server";
import { withAuth } from "@workos-inc/authkit-nextjs";

export async function GET() {
  const session = await withAuth();

  if (!session.user) {
    return NextResponse.json({ authenticated: false, user: null });
  }

  return NextResponse.json({
    authenticated: true,
    user: {
      sub: session.user.id,
      email: session.user.email ?? null,
      name: `${session.user.firstName ?? ""} ${session.user.lastName ?? ""}`.trim() || null,
    },
  });
}
