"""Service for chunking email bodies into semantic blocks."""

import logging
from typing import List
from sqlalchemy.orm import Session

from app.models.email_indexed import EmailIndexed
from app.models.chunk import Chunk
from app.core.config import settings

logger = logging.getLogger(__name__)

def split_text_into_chunks(text: str, max_length: int) -> List[str]:
    """Splits long text by paragraphs or hard lengths."""
    if not text:
        return []
    
    # Try splitting by double newline first (paragraphs)
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    chunks = []
    current_chunk = ""
    
    for p in paragraphs:
        if not current_chunk:
            if len(p) <= max_length:
                current_chunk = p
            else:
                # A single paragraph is too long, hard split it
                for i in range(0, len(p), max_length):
                    chunks.append(p[i:i+max_length])
        else:
            # Check if adding this paragraph exceeds limit (adding 2 for \n\n)
            if len(current_chunk) + len(p) + 2 <= max_length:
                current_chunk += "\n\n" + p
            else:
                chunks.append(current_chunk)
                if len(p) <= max_length:
                    current_chunk = p
                else:
                    for i in range(0, len(p), max_length):
                        chunks.append(p[i:i+max_length])
                    current_chunk = ""
                    
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks

def process_email_chunks(user_id: str, db: Session) -> int:
    """
    Finds fetched emails, chunks them, and updates statuses.
    Returns the number of new chunks created.
    """
    emails = db.query(EmailIndexed).filter(
        EmailIndexed.user_id == user_id,
        EmailIndexed.status == "fetched"
    ).all()
    
    total_chunks = 0
    max_length = settings.MAX_CHUNK_CHARS
    
    for email in emails:
        text = email.body or ""
        text_chunks = split_text_into_chunks(text, max_length)
        
        # If empty body, create one empty chunk just so it's searchable by subject/metadata
        if not text_chunks:
            text_chunks = [""]
            
        for idx, chunk_text in enumerate(text_chunks):
            new_chunk = Chunk(
                email_id=email.id,
                gmail_message_id=email.gmail_message_id,
                gmail_thread_id=email.gmail_thread_id,
                sender=email.sender,
                subject=email.subject,
                sent_at=email.sent_at,
                chunk_index=idx,
                text=chunk_text,
                status="chunked"
            )
            db.add(new_chunk)
            total_chunks += 1
            
        email.status = "chunked"
        
    db.commit()
    return total_chunks
