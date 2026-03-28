import { NextResponse } from "next/server";
import { currentUser } from "@clerk/nextjs/server";
import { getSupabaseDbClient } from "@/lib/supabase";

export async function GET() {
  const user = await currentUser();
  if (!user) {
    return NextResponse.json({ authenticated: false, user: null });
  }

  const fullName = [user.firstName, user.lastName].filter(Boolean).join(" ") || null;

  try {
    const supabase = getSupabaseDbClient();
    await supabase.from("users").upsert(
      {
        id: user.id,
        email: user.primaryEmailAddress?.emailAddress ?? "",
        full_name: fullName,
        avatar_url: user.imageUrl ?? null,
        updated_at: new Date().toISOString(),
      },
      { onConflict: "id" },
    );
  } catch (e) {
    console.error("Failed to upsert user:", e);
  }

  return NextResponse.json({
    authenticated: true,
    user: {
      sub: user.id,
      email: user.primaryEmailAddress?.emailAddress ?? null,
      name: fullName,
    },
  });
}
