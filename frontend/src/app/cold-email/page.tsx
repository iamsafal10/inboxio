"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

type CritiqueFlag = { claim?: string; truth?: string };

export default function ColdEmailPage() {
  const { token } = useAuth();
  const router = useRouter();

  const [targetContext, setTargetContext] = useState("");
  const [draft, setDraft] = useState<{ id: string; body: string; flags: CritiqueFlag[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [editedBody, setEditedBody] = useState("");
  const [acknowledgeFlags, setAcknowledgeFlags] = useState(false);
  const [sendScopeGranted, setSendScopeGranted] = useState<boolean | null>(null);

  useEffect(() => {
    if (!token) {
      router.push("/login");
      return;
    }
    fetch("/auth/me", { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => res.json())
      .then((data) => {
        if (data && data.gmail_send_scope_granted !== undefined) {
          setSendScopeGranted(!!data.gmail_send_scope_granted);
        }
      })
      .catch(() => {});
  }, [token, router]);

  const connectSendScope = async () => {
    setError("");
    try {
      const res = await fetch("/gmail/oauth/connect/send", {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to start send-scope OAuth");
      window.location.href = data.authorization_url;
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setSuccess("");
    setDraft(null);
    setAcknowledgeFlags(false);

    try {
      const res = await fetch("/cold_email/api/draft", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ target_context: targetContext }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : "Draft generation failed");
      }

      setDraft(data);
      setEditedBody(data.body || "");
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
      const res = await fetch(`/cold_email/api/send/${draft.id}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          edited_body: editedBody,
          acknowledge_flags: acknowledgeFlags,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : "Failed to send email");
      }

      setSuccess("Email sent successfully (to your account email).");
      setDraft(null);
      setTargetContext("");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!token) return null;

  const flags = draft?.flags || [];
  const hasFlags = flags.length > 0;

  return (
    <div className="container">
      <h2>Cold Email Drafter</h2>
      <p className="hint">Outbound mail goes to your own account email (self-test).</p>

      {sendScopeGranted === false && (
        <div className="alert alert-warning" style={{ marginBottom: "1rem" }}>
          Gmail send scope not granted.{" "}
          <button type="button" className="btn" style={{ padding: "4px 10px", fontSize: "0.85rem" }} onClick={connectSendScope}>
            Grant send access
          </button>
        </div>
      )}
      {sendScopeGranted && (
        <p style={{ color: "#16a34a", fontSize: "0.9rem" }}>Gmail send scope: granted ✓</p>
      )}

      {error && <div className="alert alert-danger">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {!draft ? (
        <form onSubmit={handleGenerate}>
          <div className="form-group">
            <label>Target Context</label>
            <p className="hint">Describe who you are emailing and why. Save your profile first for better drafts.</p>
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

          {hasFlags && (
            <div className="alert alert-warning">
              <label>Critique Flags</label>
              <ul style={{ margin: "10px 0", paddingLeft: "20px" }}>
                {flags.map((flag, i) => (
                  <li key={i}>
                    <strong>{flag.claim || "Unsupported claim"}</strong>
                    {flag.truth ? (
                      <>
                        <br />
                        <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>Truth: {flag.truth}</span>
                      </>
                    ) : null}
                  </li>
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
              disabled={loading || (hasFlags && !acknowledgeFlags)}
            >
              {loading ? "Sending..." : "Send Email"}
            </button>
            <button
              className="btn btn-danger"
              onClick={() => {
                setDraft(null);
                setError("");
              }}
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
