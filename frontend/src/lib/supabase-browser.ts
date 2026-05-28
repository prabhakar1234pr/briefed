"use client";
import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { useMemo } from "react";
import { useAuth } from "@/components/AuthProvider";

function getSupabaseConfig() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error(
      "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY",
    );
  }
  return { supabaseUrl, supabaseAnonKey };
}

/**
 * React hook returning a Supabase client that injects a fresh Firebase ID
 * token on every request.
 *
 * Use this inside client components. The hook re-memoizes when `getIdToken`
 * changes (sign-in / sign-out), so the client always has the right token
 * without manual reconnection. Supabase RLS sees `auth.jwt() ->> 'sub'`
 * equal to the Firebase UID.
 *
 * For server components / API routes use `getSupabaseDbClient()` from
 * `@/lib/supabase` instead.
 */
export function useSupabaseDbClient(): SupabaseClient {
  const { getIdToken } = useAuth();
  return useMemo(() => {
    const { supabaseUrl, supabaseAnonKey } = getSupabaseConfig();
    return createClient(supabaseUrl, supabaseAnonKey, {
      global: {
        fetch: async (input, init) => {
          const token = await getIdToken();
          const headers = new Headers(init?.headers);
          if (token) headers.set("Authorization", `Bearer ${token}`);
          return fetch(input, { ...init, headers });
        },
      },
      auth: { persistSession: false, autoRefreshToken: false },
    });
  }, [getIdToken]);
}
