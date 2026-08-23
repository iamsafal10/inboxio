"""Domain filter to restrict emails and questions to career-related topics only."""

import logging

logger = logging.getLogger(__name__)

CAREER_KEYWORDS = {
    "job", "internship", "application", "interview", "offer", 
    "rejection", "recruiter", "referral", "deadline", "career",
    "resume", "cover letter", "assessment", "hire", "hiring", "opportunities"
}

def is_career_related(subject: str, sender: str, body: str) -> bool:
    """
    Determines if an email is career-related based on heuristics.
    Returns True if related, False otherwise.
    Err on the side of True to avoid false negatives.
    """
    text_to_search = f"{subject} {sender} {body}".lower()
    
    # Check if any keyword is present
    for keyword in CAREER_KEYWORDS:
        if keyword in text_to_search:
            return True
            
    logger.info(f"Filtered out non-career email. Subject: '{subject}', Sender: '{sender}'")
    return False

def is_career_question(question: str) -> bool:
    """
    Determines if a user question is career-related based on heuristics.
    Returns True if related, False otherwise.
    """
    text_to_search = question.lower()
    
    for keyword in CAREER_KEYWORDS:
        if keyword in text_to_search:
            return True
            
    logger.info(f"Filtered out non-career question: '{question}'")
    return False
