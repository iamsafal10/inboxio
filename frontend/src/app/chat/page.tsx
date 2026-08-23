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

  useEffect(() => {
    if (!token) {
      router.push("/login");
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
      const res = await fetch("/chat", {
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
      <h2>Chat with Inboxio</h2>
      
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
