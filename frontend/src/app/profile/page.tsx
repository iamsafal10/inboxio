"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

export default function ProfilePage() {
  const { token } = useAuth();
  const router = useRouter();
  
  const [resumeText, setResumeText] = useState("");
  const [careerInfo, setCareerInfo] = useState("");
  const [writingSamples, setWritingSamples] = useState("");
  const [message, setMessage] = useState({ text: "", type: "" });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) {
      router.push("/login");
      return;
    }

    // Load profile
    const fetchProfile = async () => {
      try {
        const res = await fetch("/api/profile", {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setResumeText(data.resume_text || "");
          setCareerInfo(data.career_info || "");
          setWritingSamples(data.writing_style_samples || "");
        }
      } catch (err) {
        console.error("Failed to load profile", err);
      }
    };
    
    fetchProfile();
  }, [token, router]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage({ text: "", type: "" });
    setLoading(true);

    try {
      const res = await fetch("/api/profile", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}` 
        },
        body: JSON.stringify({
          resume_text: resumeText,
          career_info: careerInfo,
          writing_style_samples: writingSamples
        }),
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || "Failed to save profile");
      }
      
      router.push("/cold-email");
    } catch (err: any) {
      setMessage({ text: err.message, type: "danger" });
    } finally {
      setLoading(false);
    }
  };

  if (!token) return null;

  return (
    <div className="container">
      <h2>Profile Settings</h2>
      <p className="hint">Configure your professional profile to power the AI.</p>
      
      {message.text && (
        <div className={`alert alert-${message.type}`}>
          {message.text}
        </div>
      )}
      
      <form onSubmit={handleSave}>
        <div className="form-group">
          <label>Resume (Text)</label>
          <span className="hint">Placeholder for PDF upload later</span>
          <textarea 
            className="input-field" 
            rows={5}
            value={resumeText}
            onChange={(e) => setResumeText(e.target.value)}
          />
        </div>
        
        <div className="form-group">
          <label>Career Info & Goals</label>
          <textarea 
            className="input-field" 
            rows={4}
            value={careerInfo}
            onChange={(e) => setCareerInfo(e.target.value)}
          />
        </div>
        
        <div className="form-group">
          <label>Writing Samples</label>
          <textarea 
            className="input-field" 
            rows={4}
            value={writingSamples}
            onChange={(e) => setWritingSamples(e.target.value)}
          />
        </div>
        
        <button type="submit" className="btn" disabled={loading}>
          {loading ? "Saving..." : "Save Profile"}
        </button>
      </form>
    </div>
  );
}
