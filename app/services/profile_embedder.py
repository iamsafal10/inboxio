import logging
from typing import List, Dict, Any

from app.services.embedder import chroma_client, get_embedding_function, with_exponential_backoff
from app.services.email_chunker import split_text_into_chunks
from app.core.config import settings
from app.models.profile import Profile

logger = logging.getLogger(__name__)

def get_profile_collection(user_id: str):
    """Returns the dedicated Chroma collection for the user's profile."""
    collection_name = f"inboxio_profile_{user_id.replace('-', '')}"
    return chroma_client.get_or_create_collection(
        name=collection_name,
        embedding_function=get_embedding_function(),
        metadata={"user_id": user_id, "type": "profile"}
    )

@with_exponential_backoff(max_retries=3, base_delay=1.0)
def embed_profile_content(user_id: str, profile: Profile):
    """
    Chunks and embeds the user's profile fields into their dedicated profile collection.
    Clears the existing collection before embedding to keep it clean.
    """
    collection = get_profile_collection(user_id)
    
    # Clear existing data so updates are clean
    existing = collection.get()
    if existing and existing["ids"]:
        collection.delete(ids=existing["ids"])
        logger.info(f"Cleared existing profile embeddings for user {user_id}")
        
    documents = []
    metadatas = []
    ids = []
    
    def process_field(field_name: str, content: str):
        if not content:
            return
        chunks = split_text_into_chunks(content, settings.MAX_CHUNK_CHARS)
        for i, chunk_text in enumerate(chunks):
            chunk_id = f"{field_name}_{i}"
            documents.append(chunk_text)
            metadatas.append({
                "field": field_name,
                "user_id": user_id
            })
            ids.append(chunk_id)
            
    process_field("resume", profile.resume_text)
    process_field("career_info", profile.career_info)
    process_field("writing_samples", profile.writing_style_samples)
    
    if not documents:
        logger.info(f"No profile content to embed for user {user_id}")
        return
        
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    logger.info(f"Embedded {len(documents)} profile chunks for user {user_id}")
