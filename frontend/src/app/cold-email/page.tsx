"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { errorMessage } from "@/lib/errors";

type CritiqueFlag = { claim?: string; truth?: string };

type Draft = {
  id: string;
  subject: string;
  recipient_email: string;
  body: string;
  flags: CritiqueFlag[];
};

export default function ColdEmailPage() {
  const { token, authFetch } = useAuth();
  const router = useRouter();

  const [recipientEmail, setRecipientEmail] = useState("");
  const [roleSpecialization, setRoleSpecialization] = useState("");
  const [company, setCompany] = useState("");
  const [targetContext, setTargetContext] = useState("");
  const [draft, setDraft] = useState<Draft | null>(null);
  const [editedSubject, setEditedSubject] = useState("");
  const [sendToSelf, setSendToSelf] = useState(false);
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
    authFetch("/auth/me")
      .then((res) => res.json())
      .then((data) => {
        if (data && data.gmail_send_scope_granted !== undefined) {
          setSendScopeGranted(!!data.gmail_send_scope_granted);
        }
      })
      .catch(() => {});
  }, [token, router, authFetch]);

  const connectSendScope = async () => {
    setError("");
    try {
      const res = await authFetch("/gmail/oauth/connect/send");
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to start send-scope OAuth");
      window.location.href = data.authorization_url;
    } catch (err: unknown) {
      setError(errorMessage(err));
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
      const res = await authFetch("/cold_email/api/draft", {
        method: "POST",
        body: JSON.stringify({
          recipient_email: recipientEmail,
          role_specialization: roleSpecialization,
          company: company || null,
          target_context: targetContext || null,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : "Draft generation failed");
      }

      setDraft(data);
      setEditedBody(data.body || "");
      setEditedSubject(data.subject || "");
    } catch (err: unknown) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async () => {
    if (!draft) return;

    setLoading(true);
    setError("");

    try {
      const res = await authFetch(`/cold_email/api/send/${draft.id}`, {
        method: "POST",
        body: JSON.stringify({
          edited_body: editedBody,
          edited_subject: editedSubject,
          acknowledge_flags: acknowledgeFlags,
          send_to_self: sendToSelf,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : "Failed to send email");
      }

      setSuccess(`Email sent successfully to ${data.recipient}.`);
      setDraft(null);
      setTargetContext("");
      setRecipientEmail("");
      setRoleSpecialization("");
      setCompany("");
    } catch (err: unknown) {
      setError(errorMessage(err));
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
      <p className="hint">
        Enter the HR or recruiter address and the role you want, and the draft is
        written from your saved profile. Review it before anything is sent.
      </p>

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
            <label>HR / Recruiter Email</label>
            <input
              type="email"
              className="input-field"
              value={recipientEmail}
              onChange={(e) => setRecipientEmail(e.target.value)}
              placeholder="hr@company.com"
              required
            />
          </div>
          <div className="form-group">
            <label>Role / Specialization</label>
            <input
              type="text"
              className="input-field"
              value={roleSpecialization}
              onChange={(e) => setRoleSpecialization(e.target.value)}
              placeholder="Backend Engineering Intern"
              required
            />
          </div>
          <div className="form-group">
            <label>Company (optional)</label>
            <input
              type="text"
              className="input-field"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="Acme Corp"
            />
          </div>
          <div className="form-group">
            <label>Extra Context (optional)</label>
            <p className="hint">Anything else worth mentioning. Save your profile first for better drafts.</p>
            <textarea
              className="input-field"
              rows={4}
              value={targetContext}
              onChange={(e) => setTargetContext(e.target.value)}
            />
          </div>
          <button type="submit" className="btn" disabled={loading}>
            {loading ? "Generating..." : "Generate Draft"}
          </button>
        </form>
      ) : (
        <div>
          <p className="hint">
            To: <strong>{draft.recipient_email}</strong>
          </p>
          <div className="form-group">
            <label>Subject</label>
            <input
              type="text"
              className="input-field"
              value={editedSubject}
              onChange={(e) => setEditedSubject(e.target.value)}
            />
          </div>
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

          <label style={{ display: "flex", alignItems: "center", gap: "8px", margin: "10px 0" }}>
            <input
              type="checkbox"
              checked={sendToSelf}
              onChange={(e) => setSendToSelf(e.target.checked)}
            />
            Send to my own address instead (test run)
          </label>

          <div style={{ display: "flex", gap: "10px" }}>
            <button
              className="btn"
              onClick={handleSend}
              disabled={loading || (hasFlags && !acknowledgeFlags)}
            >
              {loading ? "Sending..." : sendToSelf ? "Send Test to Myself" : `Send to ${draft.recipient_email}`}
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
