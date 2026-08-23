import base64
from email.message import EmailMessage
from typing import Dict, Any
import logging

from sqlalchemy.orm import Session
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials

from app.models.user import User
from app.models.email_send_log import EmailSendLog

logger = logging.getLogger(__name__)

def _get_user_credentials(user: User) -> Credentials:
    """Reconstructs Google OAuth credentials for a user."""
    from app.core.crypto import decrypt_token
    from app.core.config import settings

    if not user.gmail_access_token or not user.gmail_refresh_token:
        raise ValueError("User has not connected Gmail.")
    
    creds = Credentials(
        token=decrypt_token(user.gmail_access_token),
        refresh_token=decrypt_token(user.gmail_refresh_token),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )
    return creds

def send_email(user_id: str, recipient: str, subject: str, draft: str, db: Session) -> Dict[str, Any]:
    """
    Sends an email using the Gmail API. 
    Strictly enforces that the user has granted the send scope.
    Logs every attempt in the database.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found.")

    # 1. Fail loudly if send scope hasn't been explicitly granted
    if not user.gmail_send_scope_granted:
        raise RuntimeError(f"User {user_id} has not granted the Gmail send scope.")

    # 2. Create the MIME message
    message = EmailMessage()
    message.set_content(draft)
    message["To"] = recipient
    message["From"] = user.email
    message["Subject"] = subject
    
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    
    # 3. Create log entry
    send_log = EmailSendLog(
        user_id=user_id,
        recipient=recipient,
        draft_reference=draft,
    )
    
    # 4. Attempt sending
    try:
        creds = _get_user_credentials(user)
        service = build("gmail", "v1", credentials=creds)
        
        send_message = {"raw": encoded_message}
        result = (
            service.users()
            .messages()
            .send(userId="me", body=send_message)
            .execute()
        )
        
        send_log.status = "SUCCESS"
        db.add(send_log)
        db.commit()
        
        return {"status": "SUCCESS", "message_id": result.get("id")}
        
    except Exception as e:
        logger.error(f"Failed to send email for user {user_id}: {e}")
        send_log.status = "FAILED"
        send_log.error_message = str(e)
        db.add(send_log)
        db.commit()
        
        raise RuntimeError(f"Failed to send email: {e}") from e
