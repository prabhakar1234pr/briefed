import { NextResponse } from "next/server";
import { getSupabaseDbClient } from "@/lib/supabase";
import { withAuth } from "@workos-inc/authkit-nextjs";

export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const { user } = await withAuth();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const supabase = getSupabaseDbClient();

  const { error } = await supabase.from("meetings").delete().eq("id", id);
  if (error) {
    return NextResponse.json({ error: error.message }, { status: 400 });
  }
  return NextResponse.json({ ok: true });
}
