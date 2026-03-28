import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";

export async function GET() {
  const { getToken } = await auth();
  const token = await getToken();
  if (!token) {
    return NextResponse.json({ accessToken: null }, { status: 401 });
  }
  return NextResponse.json({ accessToken: token });
}
