"""Domain filter to restrict emails and questions to career-related topics only."""

import logging
import re
from difflib import get_close_matches

logger = logging.getLogger(__name__)

# Strict career vocabulary. This set gates EMAIL INGESTION, so it must stay
# tight — anything matched here gets stored and embedded.
CAREER_KEYWORDS = {
    "job", "jobs", "internship", "internships", "intern", "application",
    "applications", "applied", "apply", "interview", "interviews", "offer",
    "offers", "rejection", "rejected", "recruiter", "recruiting", "referral",
    "deadline", "career", "resume", "cv", "cover letter", "assessment",
    "hire", "hiring", "opportunity", "opportunities", "role", "roles",
    "position", "positions", "shortlist", "shortlisted", "placement",
    "stipend", "onboarding", "employer", "hackathon", "candidate",
}

# Extra vocabulary accepted only for QUESTIONS, never for email ingestion.
# Safe at the query layer because the corpus is already career-only, so
# "what are my recent emails?" can only ever surface career mail.
INBOX_KEYWORDS = {
    "email", "emails", "mail", "mails", "inbox", "recent", "latest", "newest",
    "update", "updates", "status", "company", "companies", "hr", "salary",
    "applications", "reply", "replied", "follow up", "followup",
}

QUERY_KEYWORDS = CAREER_KEYWORDS | INBOX_KEYWORDS

# Deterministic small-talk detection. No LLM call: keeps the gate free,
# instant and unit-testable (see tests/test_zero_llm_calls.py).
SMALLTALK_PATTERNS = (
    r"^(hi|hii+|hey+|hello+|yo|sup|howdy|hola|namaste)\b",
    r"^good\s+(morning|afternoon|evening|day)\b",
    r"^(thanks|thank you|thx|ty|cheers|awesome|nice|cool|ok|okay|great)\b",
    r"^(bye|goodbye|see you|cya)\b",
    r"\bwho are you\b",
    r"\bwhat (can|do) you do\b",
    r"\bwhat are you\b",
    r"\bhow (are|r) (you|u)\b",
    r"\bwhat('?s| is) (this|inboxio)\b",
    r"^help\b",
)

SMALLTALK_RESPONSE = (
    "Hi! I'm your Inboxio agent. I read the job and internship emails synced "
    "from your Gmail, so you can ask me things like \"what are my recent "
    "internship emails?\", \"did I get any offers?\", \"what did the recruiter "
    "at Acme say?\", or \"which application deadlines are coming up?\". "
    "I can also draft a cold email to a recruiter or HR contact from your "
    "saved profile — head to the Cold Email page for that."
)

OFFTOPIC_RESPONSE = (
    "I can only answer questions related to your career, job applications, "
    "or interviews."
)


def _match_keywords(text: str, keywords: set, fuzzy_keywords: set = None) -> bool:
    """
    Word-boundary match against `keywords`, then a fuzzy pass restricted to
    `fuzzy_keywords` (defaults to `keywords`).

    Fuzzy matching is deliberately limited to the strict career vocabulary,
    where typos are worth tolerating ('inetrn' -> 'intern'). Applying it to
    generic inbox words produces false positives such as 'last' -> 'latest',
    which would let "what did I order on Amazon last week?" through the gate.
    """
    text_lower = text.lower()
    fuzzy_keywords = keywords if fuzzy_keywords is None else fuzzy_keywords

    # Word-boundary match, so 'control' no longer matches the keyword 'role'.
    for keyword in keywords:
        if re.search(rf"\b{re.escape(keyword)}\b", text_lower):
            return True

    # Fuzzy match for minor typos (e.g. 'inetrn', 'oppurtunity').
    # Cutoff of 0.8 allows slight transpositions (like inetrn -> intern).
    words = set(re.split(r"[^a-z0-9]+", text_lower))
    for word in words:
        if len(word) >= 4:  # Only fuzzy match words of reasonable length
            if get_close_matches(word, fuzzy_keywords, n=1, cutoff=0.8):
                return True

    return False


def _has_career_keyword(text: str) -> bool:
    """Strict career check, used to gate email ingestion."""
    return _match_keywords(text, CAREER_KEYWORDS)


def is_smalltalk(question: str) -> bool:
    """True for greetings, thanks, and 'who are you' style meta questions."""
    text = question.strip().lower()
    if not text:
        return True

    return any(re.search(pattern, text) for pattern in SMALLTALK_PATTERNS)


def classify_question(question: str) -> str:
    """
    Classifies a user question into one of three intents:

    - 'career'    -> answer it with the RAG agent
    - 'smalltalk' -> greet and explain capabilities, no retrieval
    - 'offtopic'  -> politely refuse

    Career intent wins over small talk, so "hi, any internship offers?" is
    still routed to the agent rather than answered with a canned greeting.
    """
    if _match_keywords(question, QUERY_KEYWORDS, fuzzy_keywords=CAREER_KEYWORDS):
        return "career"

    if is_smalltalk(question):
        return "smalltalk"

    logger.info(f"Filtered out non-career question: '{question}'")
    return "offtopic"


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
    return classify_question(question) == "career"
