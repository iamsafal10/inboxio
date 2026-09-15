from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
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
    recipient_email: EmailStr
    role_specialization: str
    company: Optional[str] = None
    target_context: Optional[str] = None

class SendRequest(BaseModel):
    edited_body: Optional[str] = None
    edited_subject: Optional[str] = None
    acknowledge_flags: bool = False
    # Safety valve for testing: route the send to the user's own inbox
    # instead of the real recipient.
    send_to_self: bool = False

@router.get("/ui", response_class=HTMLResponse)
def get_cold_email_ui(request: Request):
    """Serve a basic HTML page for the cold email approval gate."""
    return templates.TemplateResponse(request=request, name="cold_email.html")

@router.post("/api/draft")
def api_draft_cold_email(
    req: DraftRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a draft, run critique, and save to DB."""
    if not req.role_specialization.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A role / specialization is required.",
        )

    try:
        result = draft_cold_email(
            user_id=current_user.id,
            role_specialization=req.role_specialization,
            recipient_email=str(req.recipient_email),
            company=req.company,
            target_context=req.target_context,
        )
        draft_body = result["draft_text"]
        chunks_used = result["used_chunks"]
        # self_critique throws RuntimeError if LLM fails, enforcing fail-closed
        flags = self_critique(
            draft=draft_body,
            profile_chunks_used=chunks_used
        )
        
        # 3. Store in DB
        draft_record = ColdEmailDraft(
            user_id=current_user.id,
            target_context=req.target_context or req.role_specialization,
            recipient_email=str(req.recipient_email),
            role_specialization=req.role_specialization,
            subject=result["subject"],
            original_body=draft_body,
            flags=flags,
            status="DRAFTED"
        )
        db.add(draft_record)
        db.commit()
        db.refresh(draft_record)
        
        return {
            "id": draft_record.id,
            "subject": result["subject"],
            "recipient_email": str(req.recipient_email),
            "body": draft_body,
            "flags": flags
        }
    except ValueError as e:
        # Missing profile content — the user can fix this, so it is a 400.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
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
    subject = req.edited_subject or draft_record.subject or (
        "Regarding " + (draft_record.role_specialization or draft_record.target_context[:40])
    )

    recipient = draft_record.recipient_email
    if req.send_to_self or not recipient:
        # Self-test path: never reaches the real contact.
        recipient = current_user.email

    # Precondition, not a send failure: leave the draft usable so the user can
    # grant the scope and retry instead of losing their work.
    if not current_user.gmail_send_scope_granted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Gmail send access has not been granted yet. Use 'Grant send "
                "access' on the Cold Email page, then send this draft again."
            ),
        )

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
        return {**result, "recipient": recipient, "subject": subject}
    except Exception as e:
        draft_record.status = "FAILED"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
