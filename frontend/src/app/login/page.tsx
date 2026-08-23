"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

export default function LoginPage() {
  const router = useRouter();
  const { setToken } = useAuth();
  
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    try {
      const res = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || "Login failed");
      }
      
      setToken(data.access_token);
      router.push("/chat");
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="container" style={{ maxWidth: "400px" }}>
      <h2 style={{ textAlign: "center" }}>Welcome Back</h2>
      
      {error && <div className="alert alert-danger">{error}</div>}
      
      <form onSubmit={handleLogin}>
        <div className="form-group">
          <label>Email</label>
          <input 
            type="email" 
            className="input-field" 
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div className="form-group">
          <label>Password</label>
          <input 
            type="password" 
            className="input-field" 
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <button type="submit" className="btn" style={{ width: "100%" }}>
          Login
        </button>
      </form>
    </div>
  );
}
