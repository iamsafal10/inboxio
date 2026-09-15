from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.profile import Profile
from app.services.profile_embedder import embed_profile_content

router = APIRouter(tags=["profile"])

class ProfileRequest(BaseModel):
    resume_text: Optional[str] = None
    career_info: Optional[str] = None
    writing_style_samples: Optional[str] = None

PROFILE_UI_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Inboxio | Profile Settings</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #f3f4f6;
            --card-bg: #ffffff;
            --primary: #2563eb;
            --primary-hover: #1d4ed8;
            --text-main: #1f2937;
            --text-muted: #6b7280;
            --border: #e5e7eb;
        }
        * { box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            background: var(--card-bg);
            width: 100%;
            max-width: 800px;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.05);
            overflow: hidden;
        }
        .header {
            padding: 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 { margin: 0; font-size: 1.25rem; font-weight: 600; }
        .nav-link { font-size: 0.875rem; color: var(--primary); text-decoration: none; font-weight: 500;}
        .nav-link:hover { text-decoration: underline; }
        
        .content { padding: 30px; }
        
        /* Auth Screen */
        #auth-section {
            padding: 40px;
            text-align: center;
        }
        .input-field {
            width: 100%;
            padding: 10px 12px;
            margin-bottom: 12px;
            border: 1px solid var(--border);
            border-radius: 6px;
            font-size: 0.95rem;
            font-family: inherit;
        }
        .btn {
            background-color: var(--primary);
            color: white;
            border: none;
            padding: 10px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.95rem;
            font-weight: 500;
            transition: background 0.2s;
        }
        .btn:hover { background-color: var(--primary-hover); }
        .btn:disabled { opacity: 0.7; cursor: not-allowed; }
        
        /* Form elements */
        .form-group { margin-bottom: 20px; text-align: left; }
        label { display: block; margin-bottom: 8px; font-weight: 500; font-size: 0.95rem; color: var(--text-main); }
        .hint { display: block; font-size: 0.8rem; color: var(--text-muted); margin-bottom: 8px; }
        textarea.input-field { height: 120px; resize: vertical; }
        
        .success { color: #16a34a; font-size: 0.9rem; margin-top: 15px; display: none; background: #dcfce7; padding: 10px; border-radius: 6px;}
        .error { color: #dc2626; font-size: 0.9rem; margin-top: 15px; display: none; background: #fee2e2; padding: 10px; border-radius: 6px;}
        
        #profile-section { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Inboxio Profile</h1>
            <a href="/chat-ui" class="nav-link">← Back to Chat</a>
        </div>
        
        <div class="content">
            <!-- AUTH SECTION -->
            <div id="auth-section">
                <h2 style="margin-top:0;">Sign in to continue</h2>
                <p style="color: var(--text-muted); margin-bottom: 24px;">Please login with your agent account.</p>
                <div style="max-width: 300px; margin: 0 auto;">
                    <input type="email" id="email" class="input-field" placeholder="Email address">
                    <input type="password" id="password" class="input-field" placeholder="Password">
                    <button class="btn" style="width: 100%;" onclick="handleLogin()">Login</button>
                    <div id="auth-error" class="error"></div>
                </div>
            </div>

            <!-- PROFILE SECTION -->
            <div id="profile-section">
                <p style="color: var(--text-muted); margin-top: 0; margin-bottom: 24px;">
                    This information is embedded securely in your personal vector database and used by the agent to draft highly personalized emails.
                </p>
                
                <div class="form-group">
                    <label>Resume & Background</label>
                    <span class="hint">Paste your resume text, current job title, and core skills.</span>
                    <textarea id="resume_text" class="input-field" placeholder="Software Engineer at Acme Corp. 5 years experience..."></textarea>
                </div>
                
                <div class="form-group">
                    <label>Career Goals & Current Context</label>
                    <span class="hint">What are you trying to achieve? (e.g., "Looking for a backend role at a Series A startup")</span>
                    <textarea id="career_info" class="input-field" placeholder="I am currently looking for..."></textarea>
                </div>
                
                <div class="form-group">
                    <label>Writing Style Samples</label>
                    <span class="hint">Paste 1-2 examples of emails you've written so the agent can mimic your voice.</span>
                    <textarea id="writing_style_samples" class="input-field" placeholder="Hi [Name], I'm reaching out because..."></textarea>
                </div>
                
                <button id="save-btn" class="btn" onclick="saveProfile()">Save & Embed Profile</button>
                
                <div id="status-success" class="success">Profile saved and successfully embedded!</div>
                <div id="status-error" class="error">Failed to save profile.</div>
            </div>
        </div>
    </div>

    <script>
        let token = "";

        async function handleLogin() {
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            
            try {
                const res = await fetch('/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || 'Authentication failed');
                
                token = data.access_token;
                document.getElementById('auth-error').style.display = 'none';
                
                loadProfile();
            } catch (err) {
                const errDiv = document.getElementById('auth-error');
                errDiv.innerText = err.message;
                errDiv.style.display = 'block';
            }
        }

        async function loadProfile() {
            const res = await fetch("/api/profile", { headers: { "Authorization": "Bearer " + token } });
            
            if(res.ok) {
                const data = await res.json();
                document.getElementById("auth-section").style.display = "none";
                document.getElementById("profile-section").style.display = "block";
                
                document.getElementById("resume_text").value = data.resume_text || "";
                document.getElementById("career_info").value = data.career_info || "";
                document.getElementById("writing_style_samples").value = data.writing_style_samples || "";
            } else {
                alert("Failed to load profile context.");
            }
        }

        async function saveProfile() {
            const btn = document.getElementById('save-btn');
            btn.innerText = "Saving & Embedding...";
            btn.disabled = true;
            
            document.getElementById("status-success").style.display = "none";
            document.getElementById("status-error").style.display = "none";
            
            const data = {
                resume_text: document.getElementById("resume_text").value,
                career_info: document.getElementById("career_info").value,
                writing_style_samples: document.getElementById("writing_style_samples").value
            };
            
            try {
                const res = await fetch("/api/profile", {
                    method: "POST",
                    headers: { "Content-Type": "application/json", "Authorization": "Bearer " + token },
                    body: JSON.stringify(data)
                });
                
                if(res.ok) {
                    document.getElementById("status-success").style.display = "block";
                } else {
                    document.getElementById("status-error").style.display = "block";
                }
            } catch (err) {
                document.getElementById("status-error").style.display = "block";
            } finally {
                btn.innerText = "Save & Embed Profile";
                btn.disabled = false;
            }
        }
    </script>
</body>
</html>
"""

@router.get("/profile/ui", response_class=HTMLResponse)
def get_profile_ui():
    """Serves the minimal Profile UI."""
    return PROFILE_UI_HTML

@router.get("/api/profile")
def get_profile(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        return {"resume_text": "", "career_info": "", "writing_style_samples": ""}
    return {
        "resume_text": profile.resume_text,
        "career_info": profile.career_info,
        "writing_style_samples": profile.writing_style_samples
    }

@router.post("/api/profile")
def save_profile(
    req: ProfileRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        profile = Profile(user_id=user.id)
        db.add(profile)
        
    profile.resume_text = req.resume_text
    profile.career_info = req.career_info
    profile.writing_style_samples = req.writing_style_samples
    
    db.commit()
    db.refresh(profile)
    
    # Trigger chunking and embedding
    embed_profile_content(user.id, profile)

    return {"status": "success", "message": "Profile saved and embedded"}
