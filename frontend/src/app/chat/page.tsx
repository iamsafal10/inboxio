"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

export default function ChatPage() {
  const { token } = useAuth();
  const router = useRouter();
  
  const [messages, setMessages] = useState<{role: string, content: string}[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [gmailConnected, setGmailConnected] = useState<boolean | null>(null);

  useEffect(() => {
    if (!token) {
      router.push("/login");
    } else {
      // Fetch user profile to check gmail_connected
      fetch("/auth/me", {
        headers: { "Authorization": `Bearer ${token}` }
      })
      .then(res => res.json())
      .then(data => {
        if (data && data.gmail_connected !== undefined) {
          setGmailConnected(data.gmail_connected);
        }
      })
      .catch(err => console.error("Failed to fetch user data:", err));
    }
  }, [token, router]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = input;
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);
    setError("");

    try {
      const res = await fetch("/api/chat_backend", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}` 
        },
        body: JSON.stringify({ message: userMessage }),
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || "Chat failed");
      }
      
      setMessages(prev => [...prev, { role: "agent", content: data.response }]);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!token) return null;

  return (
    <div className="container" style={{ display: "flex", flexDirection: "column", height: "70vh" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h2 style={{ margin: 0 }}>Chat with Inboxio</h2>
        {gmailConnected !== null && (
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            {gmailConnected ? (
              <span style={{ color: "#16a34a", fontWeight: 500, fontSize: "0.9rem" }}>Gmail: Connected ✓</span>
            ) : (
              <>
                <span style={{ color: "#dc2626", fontWeight: 500, fontSize: "0.9rem" }}>Gmail: Not Connected</span>
                <a href="http://localhost:8000/gmail/oauth/connect" className="btn" style={{ textDecoration: "none", padding: "6px 12px", fontSize: "0.85rem" }}>
                  Connect
                </a>
              </>
            )}
          </div>
        )}
      </div>
      
      {error && <div className="alert alert-danger">{error}</div>}
      
      <div style={{ flex: 1, overflowY: "auto", marginBottom: "20px", border: "1px solid var(--border)", borderRadius: "8px", padding: "16px" }}>
        {messages.length === 0 ? (
          <p style={{ color: "var(--text-muted)", textAlign: "center", marginTop: "2rem" }}>
            Start a conversation with your agent...
          </p>
        ) : (
          messages.map((msg, i) => (
            <div key={i} style={{ 
              marginBottom: "12px", 
              textAlign: msg.role === "user" ? "right" : "left" 
            }}>
              <div style={{ 
                display: "inline-block", 
                padding: "8px 16px", 
                borderRadius: "16px",
                backgroundColor: msg.role === "user" ? "var(--primary)" : "#e5e7eb",
                color: msg.role === "user" ? "white" : "black"
              }}>
                {msg.content}
              </div>
            </div>
          ))
        )}
        {loading && <div style={{ textAlign: "left", color: "var(--text-muted)" }}>Agent is thinking...</div>}
      </div>
      
      <form onSubmit={handleSend} style={{ display: "flex", gap: "10px" }}>
        <input 
          type="text" 
          className="input-field" 
          style={{ marginBottom: 0, flex: 1 }}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          disabled={loading}
        />
        <button type="submit" className="btn" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
