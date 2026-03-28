import { NextResponse } from "next/server";
import { withAuth } from "@workos-inc/authkit-nextjs";
import { getSupabaseDbClient } from "@/lib/supabase";

export async function GET() {
  const session = await withAuth();

  if (!session.user) {
    return NextResponse.json({ authenticated: false, user: null });
  }

  const user = session.user;
  const fullName = `${user.firstName ?? ""} ${user.lastName ?? ""}`.trim() || null;

  // Upsert user into Supabase on every auth check (creates on first sign-in)
  try {
    const supabase = getSupabaseDbClient();
    await supabase.from("users").upsert(
      {
        id: user.id,
        email: user.email ?? "",
        full_name: fullName,
        avatar_url: user.profilePictureUrl ?? null,
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
      email: user.email ?? null,
      name: fullName,
    },
  });
}
