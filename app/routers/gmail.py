"""Router for Gmail OAuth connect, callback, and connection status endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import encrypt_token
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.gmail_oauth import (
    decode_oauth_state,
    exchange_code_for_tokens,
    get_authorization_url,
)
from app.services.gmail_fetcher import fetch_recent_emails
from app.services.email_chunker import process_email_chunks

router = APIRouter(prefix="/gmail", tags=["gmail"])


@router.get("/oauth/connect")
def connect_gmail(current_user: User = Depends(get_current_user)) -> dict:
    """Generate and return the Google OAuth consent URL for the authenticated user."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth credentials are not configured in environment (.env)",
        )

    auth_url = get_authorization_url(user_id=current_user.id)
    return {
        "authorization_url": auth_url,
    }


@router.get("/oauth/callback")
def oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Handle Google OAuth redirect, exchange code for tokens via PKCE, and store encrypted tokens."""
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth authorization error: {error}",
        )

    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required code or state parameter in OAuth callback",
        )

    user_id, code_verifier = decode_oauth_state(state)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User associated with this OAuth state was not found",
        )

    try:
        credentials = exchange_code_for_tokens(
            code=code,
            state=state,
            code_verifier=code_verifier,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to exchange authorization code for tokens: {str(exc)}",
        )

    # Store encrypted tokens
    if credentials.token:
        user.gmail_access_token = encrypt_token(credentials.token)
    if credentials.refresh_token:
        user.gmail_refresh_token = encrypt_token(credentials.refresh_token)
    if credentials.expiry:
        user.gmail_token_expiry = credentials.expiry

    user.gmail_connected = True
    db.commit()
    db.refresh(user)

    return RedirectResponse(url="/gmail/connected")


@router.get("/connected")
def gmail_connected() -> dict:
    """Placeholder confirmation endpoint after successful Gmail connection."""
    return {
        "status": "success",
        "message": "Gmail account connected successfully",
    }

@router.post("/sync")
def sync_gmail_emails(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Triggers an on-demand sync of recent emails from Gmail API."""
    if not current_user.gmail_connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail account is not connected",
        )
    try:
        fetched_count = fetch_recent_emails(user=current_user, db=db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync emails: {str(e)}",
        )
        
    return {
        "status": "success",
        "message": f"Successfully synced {fetched_count} emails.",
        "fetched_count": fetched_count
    }

@router.post("/chunk")
def chunk_synced_emails(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Triggers an on-demand chunking of fetched, unchunked emails."""
    try:
        total_chunks = process_email_chunks(user_id=current_user.id, db=db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to chunk emails: {str(e)}",
        )
        
    return {
        "status": "success",
        "message": f"Successfully created {total_chunks} chunks.",
        "total_chunks": total_chunks
    }
