import { handleAuth } from "@workos-inc/authkit-nextjs";
import { NextResponse } from "next/server";

export const GET = handleAuth({
  returnPathname: "/",
  onError: ({ error }) => {
    // Show the real error for debugging
    return NextResponse.json(
      {
        debug: true,
        error: String(error),
        message: (error as Error)?.message,
        stack: (error as Error)?.stack?.split("\n").slice(0, 5),
        env: {
          hasApiKey: !!process.env.WORKOS_API_KEY,
          hasClientId: !!process.env.WORKOS_CLIENT_ID,
          hasCookiePassword: !!process.env.WORKOS_COOKIE_PASSWORD,
          redirectUri: process.env.NEXT_PUBLIC_WORKOS_REDIRECT_URI,
        },
      },
      { status: 500 },
    );
  },
});
