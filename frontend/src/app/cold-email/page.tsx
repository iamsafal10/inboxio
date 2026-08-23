"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

export default function ColdEmailPage() {
  const { token } = useAuth();
  const router = useRouter();
  
  const [targetContext, setTargetContext] = useState("");
  const [draft, setDraft] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [editedBody, setEditedBody] = useState("");
  const [acknowledgeFlags, setAcknowledgeFlags] = useState(false);

  useEffect(() => {
    if (!token) {
      router.push("/login");
    }
  }, [token, router]);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setDraft(null);

    try {
      const res = await fetch("/cold_email/api/draft", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}` 
        },
        body: JSON.stringify({ target_context: targetContext }),
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || "Draft generation failed");
      }
      
      setDraft(data);
      setEditedBody(data.draft_body);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async () => {
    if (!draft) return;
    
    setLoading(true);
    setError("");
    
    try {
      const res = await fetch(`/cold_email/api/send/${draft.draft_id}`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}` 
        },
        body: JSON.stringify({ 
          edited_body: editedBody,
          acknowledge_flags: acknowledgeFlags
        }),
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || "Failed to send email");
      }
      
      setSuccess("Email sent successfully!");
      setDraft(null);
      setTargetContext("");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!token) return null;

  return (
    <div className="container">
      <h2>Cold Email Drafter</h2>
      
      {error && <div className="alert alert-danger">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}
      
      {!draft ? (
        <form onSubmit={handleGenerate}>
          <div className="form-group">
            <label>Target Context</label>
            <p className="hint">Describe who you are emailing and why.</p>
            <textarea 
              className="input-field" 
              rows={4}
              value={targetContext}
              onChange={(e) => setTargetContext(e.target.value)}
              required
            />
          </div>
          <button type="submit" className="btn" disabled={loading}>
            {loading ? "Generating..." : "Generate Draft"}
          </button>
        </form>
      ) : (
        <div>
          <div className="form-group">
            <label>Draft Review</label>
            <textarea 
              className="input-field" 
              rows={8}
              value={editedBody}
              onChange={(e) => setEditedBody(e.target.value)}
            />
          </div>
          
          {draft.critique_flags && draft.critique_flags.length > 0 && (
            <div className="alert alert-warning">
              <label>Critique Flags</label>
              <ul style={{ margin: "10px 0", paddingLeft: "20px" }}>
                {draft.critique_flags.map((flag: string, i: number) => (
                  <li key={i}>{flag}</li>
                ))}
              </ul>
              <label style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "10px" }}>
                <input 
                  type="checkbox" 
                  checked={acknowledgeFlags} 
                  onChange={(e) => setAcknowledgeFlags(e.target.checked)} 
                />
                I acknowledge these issues
              </label>
            </div>
          )}
          
          <div style={{ display: "flex", gap: "10px" }}>
            <button 
              className="btn" 
              onClick={handleSend} 
              disabled={loading || (draft.critique_flags?.length > 0 && !acknowledgeFlags)}
            >
              {loading ? "Sending..." : "Send Email"}
            </button>
            <button 
              className="btn btn-danger" 
              onClick={() => { setDraft(null); setError(""); }}
              disabled={loading}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
