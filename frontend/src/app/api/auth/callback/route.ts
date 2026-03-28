import { handleAuth } from "@workos-inc/authkit-nextjs";
import { NextResponse } from "next/server";

export const GET = handleAuth({
  returnPathname: "/",
  onError: ({ error }) => {
    return NextResponse.json(
      {
        error: String(error),
        message: (error as Error)?.message,
      },
      { status: 500 },
    );
  },
});
