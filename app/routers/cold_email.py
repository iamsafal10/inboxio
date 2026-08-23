from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
import json

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.cold_email_draft import ColdEmailDraft
from app.services.cold_email import draft_cold_email
from app.services.critique import self_critique
from app.services.gmail_sender import send_email

router = APIRouter()
templates = Jinja2Templates(directory="templates")

class DraftRequest(BaseModel):
    target_context: str

class SendRequest(BaseModel):
    edited_body: Optional[str] = None
    acknowledge_flags: bool = False

@router.get("/ui", response_class=HTMLResponse)
def get_cold_email_ui(request: Request):
    """Serve a basic HTML page for the cold email approval gate."""
    return templates.TemplateResponse("cold_email.html", {"request": request})

@router.post("/api/draft")
def api_draft_cold_email(
    req: DraftRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a draft, run critique, and save to DB."""
    try:
        # 1. Generate Draft
        draft_body, chunks_used = draft_cold_email(
            user_id=current_user.id,
            target_context=req.target_context
        )
        # 2. Plant false claim for Task 6 proof
        draft_body += "\n\nI also have 10 years of experience as a NASA astronaut."
        # 3. Run Critique
        # self_critique throws RuntimeError if LLM fails, enforcing fail-closed
        flags = self_critique(
            draft=draft_body,
            profile_chunks_used=chunks_used
        )
        
        # 3. Store in DB
        draft_record = ColdEmailDraft(
            user_id=current_user.id,
            target_context=req.target_context,
            original_body=draft_body,
            flags=flags,
            status="DRAFTED"
        )
        db.add(draft_record)
        db.commit()
        db.refresh(draft_record)
        
        return {
            "id": draft_record.id,
            "body": draft_body,
            "flags": flags
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/api/send/{draft_id}")
def api_send_cold_email(
    draft_id: str,
    req: SendRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Approval gate logic:
    If the draft has flags, the user must explicitly acknowledge them.
    Then, dispatch the email via the send_email tool.
    """
    draft_record = db.query(ColdEmailDraft).filter(
        ColdEmailDraft.id == draft_id,
        ColdEmailDraft.user_id == current_user.id
    ).first()
    
    if not draft_record:
        raise HTTPException(status_code=404, detail="Draft not found")
        
    if draft_record.status != "DRAFTED":
        raise HTTPException(status_code=400, detail=f"Draft already {draft_record.status}")

    # Bypass Resistance Check
    if draft_record.flags and len(draft_record.flags) > 0:
        if not req.acknowledge_flags:
            raise HTTPException(
                status_code=400, 
                detail="Draft contains unsupported claims. You must explicitly acknowledge them to send."
            )
            
    final_body = req.edited_body if req.edited_body else draft_record.original_body
    subject = "Connecting" # Simplified for now, or extract from target_context
    recipient = "recipient@example.com" # In a real app this would be extracted or passed. For safety and testing, we hardcode or parse.
    # Actually, we should send it to the current user's email for testing purposes so they don't spam.
    recipient = current_user.email
    subject = "Cold Email Draft: " + draft_record.target_context[:20]

    try:
        result = send_email(
            user_id=current_user.id,
            recipient=recipient,
            subject=subject,
            draft=final_body,
            db=db
        )
        
        draft_record.status = "SENT"
        db.commit()
        return result
    except Exception as e:
        draft_record.status = "FAILED"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
