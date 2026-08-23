import re
import logging
from sqlalchemy.orm import Session
from app.models.memory_fact import MemoryFact

logger = logging.getLogger(__name__)

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "is", "are", "was", "were", 
    "am", "be", "been", "being", "in", "on", "at", "to", "for", "with", 
    "about", "by", "from", "as", "of", "this", "that", "these", "those",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us",
    "them", "my", "your", "his", "their", "what", "which", "who", "whom",
    "whose", "why", "how", "when", "where", "do", "does", "did", "have",
    "has", "had", "can", "could", "should", "would", "may", "might", "must",
    "find", "show", "tell", "give", "get", "need", "want", "like", "search"
}

def get_relevant_facts(user_id: str, question: str, db: Session) -> list[str]:
    """
    Retrieves all active memory facts for the given user, and uses a lightweight
    keyword matching heuristic to return only the relevant ones based on the question.
    """
    active_facts = db.query(MemoryFact).filter(
        MemoryFact.user_id == user_id,
        MemoryFact.active == True
    ).all()
    
    if not active_facts:
        return []
        
    # Extract significant words from the question
    words = re.findall(r'\b[a-zA-Z]{3,}\b', question.lower())
    keywords = [w for w in words if w not in STOPWORDS]
    
    # If the question has almost no significant keywords, or if there are very few facts total,
    # just return all active facts to be safe, so we don't miss context.
    if not keywords or len(active_facts) <= 3:
        logger.info(f"Injecting all {len(active_facts)} facts (few facts or no strong keywords).")
        return [f.fact_text for f in active_facts]
        
    relevant_facts = []
    for fact in active_facts:
        fact_lower = fact.fact_text.lower()
        # If any keyword is found in the fact, consider it relevant
        if any(kw in fact_lower for kw in keywords):
            relevant_facts.append(fact.fact_text)
            
    logger.info(f"Filtered {len(active_facts)} total facts down to {len(relevant_facts)} relevant ones.")
    return relevant_facts
