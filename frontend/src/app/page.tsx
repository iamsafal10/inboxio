"use client";

import Link from "next/link";
import { useAuth } from "@/context/AuthContext";

export default function Home() {
  const { token } = useAuth();

  return (
    <div className="container" style={{ textAlign: "center", padding: "4rem 2rem" }}>
      <h1>Welcome to Inboxio</h1>
      <p style={{ color: "var(--text-muted)", marginBottom: "2rem" }}>
        Your Personal Gmail Intelligence Agent. Search, draft, and analyze emails efficiently.
      </p>
      
      {token ? (
        <Link href="/chat" className="btn">
          Go to Dashboard
        </Link>
      ) : (
        <div style={{ display: "flex", gap: "1rem", justifyContent: "center" }}>
          <Link href="/login" className="btn">
            Login
          </Link>
          <Link href="/signup" className="btn" style={{ backgroundColor: "transparent", color: "var(--primary)", border: "1px solid var(--primary)" }}>
            Sign Up
          </Link>
        </div>
      )}
    </div>
  );
}
