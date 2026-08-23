"""Service for fetching emails from the Gmail API with pagination and rate-limit handling."""

import base64
import html
import re
import time
import email.utils
from typing import Optional, List, Dict, Any
import logging

from sqlalchemy.orm import Session
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials

from app.core.config import settings
from app.core.crypto import decrypt_token
from app.models.user import User
from app.models.email_indexed import EmailIndexed
from app.services.gmail_oauth import refresh_credentials
from app.services.domain_filter import is_career_related

logger = logging.getLogger(__name__)

def _get_user_credentials(user: User) -> Credentials:
    """Reconstructs and refreshes Google OAuth credentials for a user."""
    if not user.gmail_access_token or not user.gmail_refresh_token:
        raise ValueError("User has not connected Gmail.")
    
    creds = Credentials(
        token=decrypt_token(user.gmail_access_token),
        refresh_token=decrypt_token(user.gmail_refresh_token),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )
    return refresh_credentials(creds)

def with_exponential_backoff(max_retries: int = 4, base_delay: float = 1.0):
    """Decorator for retrying functions on 429 and 403 HttpErrors."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = base_delay
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except HttpError as e:
                    if e.resp.status in [403, 429] and attempt < max_retries:
                        logger.warning(f"Rate limited (status {e.resp.status}). Retrying in {delay}s...")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        raise
        return wrapper
    return decorator

@with_exponential_backoff(max_retries=4, base_delay=1.0)
def execute_request(request: Any) -> Any:
    """Executes a Google API request with exponential backoff for rate limits."""
    return request.execute()

def strip_html(html_content: str) -> str:
    """Basic HTML stripper if only HTML is provided."""
    text = re.sub(r'<[^>]+>', ' ', html_content)
    text = re.sub(r'\s+', ' ', text)
    return html.unescape(text).strip()

def parse_message_payload(msg_payload: dict) -> dict:
    """Extracts subject, sender, recipient, date, and body from the payload."""
    payload = msg_payload.get('payload', {})
    headers_list = payload.get('headers', [])
    headers = {h['name'].lower(): h['value'] for h in headers_list}
    
    subject = headers.get('subject', '')
    sender = headers.get('from', '')
    recipient = headers.get('to', '')
    date_str = headers.get('date', '')
    
    sent_at = None
    if date_str:
        try:
            sent_at = email.utils.parsedate_to_datetime(date_str)
        except Exception:
            pass

    body = ""
    
    def extract_body(parts: List[dict]) -> bool:
        nonlocal body
        for part in parts:
            mime_type = part.get('mimeType', '')
            data = part.get('body', {}).get('data', '')
            
            if mime_type == 'text/plain' and data:
                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                return True
            elif mime_type == 'text/html' and data and not body:
                html_data = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                body = strip_html(html_data)
            elif 'parts' in part:
                if extract_body(part['parts']):
                    return True
        return False

    if payload.get('mimeType') == 'text/plain':
        data = payload.get('body', {}).get('data', '')
        if data:
            body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    elif payload.get('mimeType') == 'text/html':
        data = payload.get('body', {}).get('data', '')
        if data:
            body = strip_html(base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore'))
    else:
        extract_body(payload.get('parts', []))
        
    return {
        "subject": subject,
        "sender": sender,
        "recipient": recipient,
        "sent_at": sent_at,
        "body": body
    }

def fetch_recent_emails(user: User, db: Session, max_emails: Optional[int] = None) -> int:
    """
    Fetches emails from Gmail API with pagination, parsing, and storing into the DB.
    Returns the number of emails fetched and stored.
    """
    if max_emails is None:
        max_emails = settings.MAX_EMAILS

    creds = _get_user_credentials(user)
    service = build('gmail', 'v1', credentials=creds)
    
    fetched_count = 0
    next_page_token = None

    while fetched_count < max_emails:
        # Fetch list of messages
        request = service.users().messages().list(
            userId='me',
            pageToken=next_page_token,
            maxResults=min(100, max_emails - fetched_count)
        )
        response = execute_request(request)
        
        messages = response.get('messages', [])
        if not messages:
            break
            
        for msg_ref in messages:
            if fetched_count >= max_emails:
                break
                
            msg_id = msg_ref['id']
            
            # Skip if already exists
            existing = db.query(EmailIndexed).filter(EmailIndexed.gmail_message_id == msg_id).first()
            if existing:
                continue

            # Fetch full message
            msg_request = service.users().messages().get(userId='me', id=msg_id, format='full')
            msg_payload = execute_request(msg_request)
            
            thread_id = msg_payload.get('threadId', '')
            parsed = parse_message_payload(msg_payload)
            
            if parsed['sent_at'] is None:
                fetched_count += 1
                continue # Skip if we can't parse the date properly for now

            # Filter non-career emails
            if not is_career_related(parsed['subject'], parsed['sender'], parsed['body']):
                fetched_count += 1
                continue

            email_idx = EmailIndexed(
                user_id=user.id,
                gmail_message_id=msg_id,
                gmail_thread_id=thread_id,
                sender=parsed['sender'][:255],
                recipient=parsed['recipient'][:255],
                subject=parsed['subject'],
                sent_at=parsed['sent_at'],
                body=parsed['body'],
                status="fetched",
                embedded=False
            )
            db.add(email_idx)
            fetched_count += 1
            
        db.commit()
        
        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break
            
    return fetched_count
