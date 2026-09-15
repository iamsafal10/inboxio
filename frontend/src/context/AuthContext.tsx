"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useSyncExternalStore,
} from "react";
import { useRouter } from "next/navigation";

const TOKEN_KEY = "inboxio_token";

/**
 * Minimal external store over localStorage. Using useSyncExternalStore rather
 * than an effect keeps the server and client snapshots explicit (the server
 * has no token) and picks up logouts from other tabs via the storage event.
 */
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

function readToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function writeToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* private mode / blocked storage — the session just won't persist */
  }
  emit();
}

interface AuthContextType {
  token: string | null;
  setToken: (token: string | null) => void;
  logout: () => void;
  /**
   * fetch() with the Bearer token attached. On a 401 the stored token is
   * cleared and the user is sent to /login, so an expired token can never
   * leave a page silently failing.
   */
  authFetch: (input: string, init?: RequestInit) => Promise<Response>;
}

const AuthContext = createContext<AuthContextType>({
  token: null,
  setToken: () => {},
  logout: () => {},
  authFetch: () => Promise.reject(new Error("AuthProvider missing")),
});

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const router = useRouter();

  const token = useSyncExternalStore(
    subscribe,
    readToken,
    () => null // server snapshot: never authenticated during SSR
  );

  const setToken = useCallback((newToken: string | null) => {
    writeToken(newToken);
  }, []);

  const logout = useCallback(() => {
    writeToken(null);
    router.push("/");
  }, [router]);

  const authFetch = useCallback(
    async (input: string, init: RequestInit = {}) => {
      const headers = new Headers(init.headers);
      const current = readToken();

      if (current) headers.set("Authorization", `Bearer ${current}`);
      if (init.body && !headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
      }

      const res = await fetch(input, { ...init, headers });

      if (res.status === 401) {
        writeToken(null);
        router.push("/login");
      }

      return res;
    },
    [router]
  );

  const value = useMemo(
    () => ({ token, setToken, logout, authFetch }),
    [token, setToken, logout, authFetch]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => useContext(AuthContext);
