"""Service for generating embeddings and storing them in ChromaDB."""

import logging
import time
from typing import List, Any
import chromadb
from chromadb.config import Settings as ChromaSettings
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.email_indexed import EmailIndexed
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize a global Chroma client
chroma_client = chromadb.PersistentClient(
    path=settings.CHROMA_PERSIST_DIR,
    settings=ChromaSettings(anonymized_telemetry=False)
)

_embedding_function = None

def get_embedding_function():
    """Lazy load the sentence-transformer model to avoid heavy startup overhead."""
    global _embedding_function
    if _embedding_function is None:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        # Using sentence-transformers locally for zero external dependency
        _embedding_function = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    return _embedding_function

def with_exponential_backoff(max_retries: int = 4, base_delay: float = 1.0):
    """Decorator to retry embedding batch calls if they hit a transient error."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = base_delay
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt < max_retries:
                        logger.warning(f"Embedding batch failed: {e}. Retrying in {delay}s...")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        raise
        return wrapper
    return decorator

@with_exponential_backoff(max_retries=3, base_delay=1.0)
def embed_and_store_batch(collection: Any, chunks: List[Chunk]):
    """Embeds a batch of chunks and stores them in ChromaDB with metadata."""
    if not chunks:
        return
        
    ids = [c.id for c in chunks]
    documents = [c.text for c in chunks]
    
    # Chroma requires metadata values to be str, int, float, or bool. None is not allowed.
    metadatas = []
    for c in chunks:
        meta = {
            "gmail_message_id": c.gmail_message_id,
            "gmail_thread_id": c.gmail_thread_id,
            "sender": c.sender,
            "chunk_index": c.chunk_index,
            # Handle optional fields safely
            "subject": c.subject or "",
            "sent_at": c.sent_at.isoformat() if c.sent_at else ""
        }
        metadatas.append(meta)
        
    # The embedding function handles text->vector internally when calling collection.add()
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )

def process_unembedded_chunks(user_id: str, db: Session, batch_size: int = 100) -> int:
    """
    Finds unembedded chunks for a user, batches them, stores them in Chroma,
    and updates the DB status.
    """
    chunks = db.query(Chunk).join(EmailIndexed).filter(
        EmailIndexed.user_id == user_id,
        Chunk.status == "chunked"
    ).all()
    
    if not chunks:
        return 0
        
    # Isolate vector storage per user (replace hyphens which Chroma might reject)
    collection_name = f"inboxio_user_{user_id}".replace("-", "_")
    
    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        embedding_function=get_embedding_function()
    )
    
    total_embedded = 0
    
    # Process in batches
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        
        # This wrapper handles rate limit/errors and actually inserts into Chroma
        embed_and_store_batch(collection, batch)
        
        # Mark as embedded
        for c in batch:
            c.status = "embedded"
            total_embedded += 1
            
        db.commit()
        
    return total_embedded
