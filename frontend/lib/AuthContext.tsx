"use client";

import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from "react";
import { onAuthStateChanged, User } from "firebase/auth";
import { auth } from "@/lib/firebase";

/** sessionStorage key for the Google OAuth access token. */
const TOKEN_KEY = "gieventhub.googleAccessToken";

interface AuthContextValue {
  user: User | null;
  /** true while Firebase is still resolving the session (prevents flash) */
  loading: boolean;
  /**
   * The user's Google Workspace OAuth access token, captured at sign-in.
   * Needed by ai-service-backed endpoints (/api/scan, /api/adapt, /api/workspace/*).
   * Short-lived (~1h) — persisted in sessionStorage so it survives page
   * navigation/reload within the session.
   */
  googleAccessToken: string | null;
  setGoogleAccessToken: (token: string | null) => void;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  googleAccessToken: null,
  setGoogleAccessToken: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  // Lazy init from sessionStorage so a direct page load/reload keeps the token
  // without waiting on an effect (avoids a race with child-page fetches).
  const [googleAccessToken, setTokenState] = useState<string | null>(() =>
    typeof window !== "undefined" ? sessionStorage.getItem(TOKEN_KEY) : null,
  );

  const setGoogleAccessToken = useCallback((token: string | null) => {
    setTokenState(token);
    if (typeof window === "undefined") return;
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  }, []);

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, (u) => {
      setUser(u);
      setLoading(false);
      // Signed out — drop the Workspace token too.
      if (!u) setGoogleAccessToken(null);
    });
    return () => unsub();
  }, [setGoogleAccessToken]);

  return (
    <AuthContext.Provider value={{ user, loading, googleAccessToken, setGoogleAccessToken }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
