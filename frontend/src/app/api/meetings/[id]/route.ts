import { NextResponse } from "next/server";
import { serverApiDelete } from "@/lib/server-api";
import { getServerUser } from "@/lib/auth";

export const runtime = "nodejs";

export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const user = await getServerUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const res = await serverApiDelete(`/api/meetings/${encodeURIComponent(id)}`);
  if (!res.ok) {
    return NextResponse.json({ error: res.error ?? "Delete failed" }, { status: 400 });
  }
  return NextResponse.json({ ok: true });
}
