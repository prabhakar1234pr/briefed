"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  onAuthStateChanged,
  onIdTokenChanged,
  signOut as firebaseSignOut,
  type User,
} from "firebase/auth";
import { getFirebaseAuth } from "@/lib/firebase";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  signOut: () => Promise<void>;
  getIdToken: () => Promise<string | null>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

/**
 * Root client-side auth provider.
 *
 * - Subscribes to Firebase auth state on mount.
 * - On every new ID token (sign-in, refresh), POSTs to `/api/auth/session`
 *   so the server-side session cookie is in sync with the client.
 * - On sign-out, DELETEs `/api/auth/session` and clears Firebase client state.
 *
 * Wrap the app's root layout in `<AuthProvider>` and use `useAuth()` in
 * any client component that needs the current user.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  // Track the last ID token we synced to the server so we don't spam
  // /api/auth/session on every render or refresh tick.
  const lastSyncedToken = useRef<string | null>(null);

  useEffect(() => {
    const auth = getFirebaseAuth();

    const unsubAuth = onAuthStateChanged(auth, (u) => {
      setUser(u);
      setLoading(false);
    });

    // Fires on sign-in, token refresh (~ every 55min), and sign-out.
    const unsubToken = onIdTokenChanged(auth, async (u) => {
      if (!u) {
        // Don't auto-DELETE here — explicit signOut() handles cookie clearing,
        // and middleware will redirect on expired/missing cookies anyway.
        lastSyncedToken.current = null;
        return;
      }
      try {
        const token = await u.getIdToken();
        if (token === lastSyncedToken.current) return;
        lastSyncedToken.current = token;
        await fetch("/api/auth/session", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ idToken: token }),
        });
      } catch (e) {
        console.error("Failed to sync session cookie:", e);
      }
    });

    return () => {
      unsubAuth();
      unsubToken();
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      async signOut() {
        try {
          await fetch("/api/auth/session", { method: "DELETE" });
        } catch (e) {
          console.error("Failed to clear server session:", e);
        }
        await firebaseSignOut(getFirebaseAuth());
        lastSyncedToken.current = null;
      },
      async getIdToken() {
        const current = getFirebaseAuth().currentUser;
        if (!current) return null;
        try {
          return await current.getIdToken();
        } catch {
          return null;
        }
      },
    }),
    [user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}

/** Alias for clarity at call sites that just want the Firebase user. */
export function useFirebaseUser(): User | null {
  return useAuth().user;
}
