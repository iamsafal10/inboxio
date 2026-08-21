"""Additional retrieval tools for the LangGraph agent."""

from typing import List, Dict, Any, Optional
from datetime import datetime
from dateutil.parser import parse as parse_date

from app.core.database import SessionLocal
from app.models.chunk import Chunk
from app.models.email_indexed import EmailIndexed
from app.services.semantic_search import search_emails

def _format_chunk(chunk: Chunk) -> Dict[str, Any]:
    """Helper to format a DB Chunk into the standard retrieval shape."""
    return {
        "text": chunk.text,
        "metadata": {
            "sender": chunk.sender,
            "subject": chunk.subject or "",
            "sent_at": chunk.sent_at.isoformat() if chunk.sent_at else "",
            "gmail_thread_id": chunk.gmail_thread_id,
            "gmail_message_id": chunk.gmail_message_id,
            "chunk_index": chunk.chunk_index
        },
        "distance": None
    }

def search_by_sender(user_id: str, sender_query: str, top_k: int = 10) -> List[Dict[str, Any]]:
    """Retrieves chunks from a specific sender using DB fuzzy match."""
    with SessionLocal() as db:
        chunks = db.query(Chunk).join(EmailIndexed).filter(
            EmailIndexed.user_id == user_id,
            Chunk.sender.ilike(f"%{sender_query}%")
        ).order_by(Chunk.sent_at.desc(), Chunk.chunk_index.asc()).limit(top_k).all()
        
        return [_format_chunk(c) for c in chunks]

def reconstruct_thread(user_id: str, thread_id: str) -> List[Dict[str, Any]]:
    """Retrieves all chunks belonging to a specific thread in chronological order."""
    with SessionLocal() as db:
        chunks = db.query(Chunk).join(EmailIndexed).filter(
            EmailIndexed.user_id == user_id,
            Chunk.gmail_thread_id == thread_id
        ).order_by(Chunk.sent_at.asc(), Chunk.chunk_index.asc()).all()
        
        return [_format_chunk(c) for c in chunks]

def search_by_date_range(user_id: str, start_date: str, end_date: str, query: Optional[str] = None, top_k: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieves chunks within a date range.
    If query is provided, uses semantic search and filters results.
    """
    try:
        start_dt = parse_date(start_date)
        end_dt = parse_date(end_date)
    except Exception:
        # Invalid date format, return empty list
        return []
        
    if query:
        # Fetch more from Chroma then filter
        results = search_emails(user_id, query, top_k=top_k * 5)
        filtered = []
        for r in results:
            sent_at_str = r["metadata"].get("sent_at", "")
            if not sent_at_str:
                continue
            try:
                sent_dt = parse_date(sent_at_str)
                # Ensure timezone awareness matches for comparison
                if start_dt.tzinfo is None and sent_dt.tzinfo is not None:
                    start_dt = start_dt.replace(tzinfo=sent_dt.tzinfo)
                if end_dt.tzinfo is None and sent_dt.tzinfo is not None:
                    end_dt = end_dt.replace(tzinfo=sent_dt.tzinfo)
                    
                if start_dt <= sent_dt <= end_dt:
                    filtered.append(r)
            except Exception:
                pass
                    
            if len(filtered) >= top_k:
                break
        return filtered
    else:
        # Pure DB query
        with SessionLocal() as db:
            chunks = db.query(Chunk).join(EmailIndexed).filter(
                EmailIndexed.user_id == user_id,
                Chunk.sent_at >= start_dt,
                Chunk.sent_at <= end_dt
            ).order_by(Chunk.sent_at.desc(), Chunk.chunk_index.asc()).limit(top_k).all()
            
            return [_format_chunk(c) for c in chunks]
