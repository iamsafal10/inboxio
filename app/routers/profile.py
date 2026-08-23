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
<html>
<head>
    <title>Inboxio Profile</title>
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        textarea { width: 100%; height: 100px; }
        .success { color: green; }
        .error { color: red; }
    </style>
</head>
<body>
    <h1>Your Inboxio Profile</h1>
    <div id="auth-section">
        <h3>Authenticate to view/edit</h3>
        <input type="text" id="jwt-token" placeholder="Paste JWT token here" style="width: 100%;"><br><br>
        <button onclick="loadProfile()">Load Profile</button>
    </div>

    <div id="profile-section" style="display: none; margin-top: 20px;">
        <div class="form-group">
            <label>Resume Text</label>
            <textarea id="resume_text" placeholder="Paste your resume..."></textarea>
        </div>
        <div class="form-group">
            <label>Career Info & Goals</label>
            <textarea id="career_info" placeholder="What are your target roles?"></textarea>
        </div>
        <div class="form-group">
            <label>Writing Style Samples</label>
            <textarea id="writing_style_samples" placeholder="Paste some past emails you've written..."></textarea>
        </div>
        <button onclick="saveProfile()">Save & Embed Profile</button>
        <p id="status-msg"></p>
    </div>

    <script>
        let token = "";

        async function loadProfile() {
            token = document.getElementById("jwt-token").value;
            if(!token) return;
            
            const res = await fetch("/api/profile", {
                headers: { "Authorization": "Bearer " + token }
            });
            
            if(res.ok) {
                const data = await res.json();
                document.getElementById("auth-section").style.display = "none";
                document.getElementById("profile-section").style.display = "block";
                
                document.getElementById("resume_text").value = data.resume_text || "";
                document.getElementById("career_info").value = data.career_info || "";
                document.getElementById("writing_style_samples").value = data.writing_style_samples || "";
            } else {
                alert("Failed to load profile. Check token.");
            }
        }

        async function saveProfile() {
            const data = {
                resume_text: document.getElementById("resume_text").value,
                career_info: document.getElementById("career_info").value,
                writing_style_samples: document.getElementById("writing_style_samples").value
            };
            
            document.getElementById("status-msg").innerText = "Saving and embedding...";
            document.getElementById("status-msg").className = "";
            
            const res = await fetch("/api/profile", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + token
                },
                body: JSON.stringify(data)
            });
            
            if(res.ok) {
                document.getElementById("status-msg").innerText = "Profile saved and embedded successfully!";
                document.getElementById("status-msg").className = "success";
            } else {
                document.getElementById("status-msg").innerText = "Failed to save profile.";
                document.getElementById("status-msg").className = "error";
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
    
    return {"status": "success"}
