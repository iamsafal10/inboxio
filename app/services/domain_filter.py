"""Domain filter to restrict emails and questions to career-related topics only."""

import logging

logger = logging.getLogger(__name__)

CAREER_KEYWORDS = {
    "job", "internship", "intern", "application", "interview", "offer", 
    "rejection", "recruiter", "referral", "deadline", "career",
    "resume", "cover letter", "assessment", "hire", "hiring", "opportunities",
    "role", "position"
}

def _has_career_keyword(text: str) -> bool:
    """Helper to check for exact substring or fuzzy matched keywords."""
    text_lower = text.lower()
    
    # Fast exact substring match
    for keyword in CAREER_KEYWORDS:
        if keyword in text_lower:
            return True
            
    # Fuzzy match for minor typos (e.g., 'inetrn', 'oppurtunity')
    words = set(text_lower.replace(",", " ").replace(".", " ").split())
    
    # We use a simple fuzzy match strategy: difflib.get_close_matches
    # Cutoff of 0.8 allows slight transpositions (like inetrn -> intern)
    from difflib import get_close_matches
    for word in words:
        if len(word) >= 4:  # Only fuzzy match words of reasonable length
            matches = get_close_matches(word, CAREER_KEYWORDS, n=1, cutoff=0.8)
            if matches:
                return True
                
    return False

def is_career_related(subject: str, sender: str, body: str) -> bool:
    """
    Determines if an email is career-related based on heuristics.
    Returns True if related, False otherwise.
    Err on the side of True to avoid false negatives.
    """
    text_to_search = f"{subject} {sender} {body}"
    if _has_career_keyword(text_to_search):
        return True
            
    logger.info(f"Filtered out non-career email. Subject: '{subject}', Sender: '{sender}'")
    return False

def is_career_question(question: str) -> bool:
    """
    Determines if a user question is career-related based on heuristics.
    Returns True if related, False otherwise.
    """
    if _has_career_keyword(question):
        return True
            
    logger.info(f"Filtered out non-career question: '{question}'")
    return False
