import { NextResponse } from "next/server";
import { getSupabaseDbClient } from "@/lib/supabase";
import { auth } from "@clerk/nextjs/server";

export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const supabase = getSupabaseDbClient();

  // Meetings reference agent_id with ON DELETE SET NULL but column is NOT NULL — remove meetings first.
  const { error: meetingsErr } = await supabase
    .from("meetings")
    .delete()
    .eq("agent_id", id);
  if (meetingsErr) {
    return NextResponse.json({ error: meetingsErr.message }, { status: 400 });
  }

  const { error } = await supabase.from("agents").delete().eq("id", id);
  if (error) {
    return NextResponse.json({ error: error.message }, { status: 400 });
  }
  return NextResponse.json({ ok: true });
}
