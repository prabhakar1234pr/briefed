import { NextResponse } from "next/server";
import { withAuth } from "@workos-inc/authkit-nextjs";

export async function GET() {
  const session = await withAuth();

  if (!session.accessToken) {
    return NextResponse.json({ accessToken: null }, { status: 401 });
  }

  return NextResponse.json({ accessToken: session.accessToken });
}
