import { NextResponse } from "next/server";
export async function GET() {
  return NextResponse.redirect(new URL("/auth", process.env.NEXT_PUBLIC_APP_URL ?? "https://briefed-mu.vercel.app"));
}
