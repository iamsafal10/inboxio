"""Service for semantic search over embedded email chunks."""

from typing import List, Dict, Any
from app.services.embedder import chroma_client, get_embedding_function

def search_emails(user_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Embeds the query and semantically searches the user's isolated Chroma collection.
    Returns the top_k most relevant chunks with their text, metadata, and distance score.
    """
    collection_name = f"inboxio_user_{user_id}".replace("-", "_")
    
    try:
        # get_collection raises an exception if it doesn't exist
        collection = chroma_client.get_collection(
            name=collection_name,
            embedding_function=get_embedding_function()
        )
    except Exception:
        # Collection might not exist if they haven't embedded anything yet.
        return []
        
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
    )
    
    # Format the results into a clean list of dictionaries
    formatted_results = []
    
    if not results.get('documents') or not results['documents'][0]:
        return formatted_results
        
    docs = results['documents'][0]
    metas = results['metadatas'][0]
    distances = results.get('distances', [[None]*len(docs)])[0]
    
    for i in range(len(docs)):
        formatted_results.append({
            "text": docs[i],
            "metadata": metas[i],
            "distance": distances[i]
        })
        
    return formatted_results
