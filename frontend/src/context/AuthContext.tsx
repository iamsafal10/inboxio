"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

const TOKEN_KEY = "inboxio_token";

interface AuthContextType {
  token: string | null;
  setToken: (token: string | null) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  token: null,
  setToken: () => {},
  logout: () => {},
});

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [token, setTokenState] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      setTokenState(localStorage.getItem(TOKEN_KEY));
    } catch {
      /* ignore */
    }
    setReady(true);
  }, []);

  const setToken = (newToken: string | null) => {
    setTokenState(newToken);
    try {
      if (newToken) localStorage.setItem(TOKEN_KEY, newToken);
      else localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* ignore */
    }
  };

  const logout = () => {
    setToken(null);
    window.location.href = "/";
  };

  if (!ready) return null;

  return (
    <AuthContext.Provider value={{ token, setToken, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
