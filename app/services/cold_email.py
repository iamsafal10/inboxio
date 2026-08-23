import logging
from typing import Dict, Any
from langchain_core.prompts import PromptTemplate

from app.services.profile_embedder import get_profile_collection
from app.llm.llm_setup import get_llm

logger = logging.getLogger(__name__)

DRAFT_EMAIL_PROMPT = PromptTemplate.from_template("""You are an expert cold email writer. Your job is to draft a cold email based strictly on the user's profile and the target context.

TARGET SCENARIO / CONTEXT:
{target_context}

USER FACTS (Resume & Career Info):
{facts}

WRITING STYLE SAMPLES (Use these to match the user's voice):
{samples}

STRICT INSTRUCTIONS:
1. Write a professional cold email tailored to the TARGET SCENARIO.
2. ANTI-FABRICATION RULE: DO NOT invent skills, jobs, experience, numbers, or any facts not explicitly present in the USER FACTS. If the profile is thin, keep the email brief rather than inventing qualifications. Do not say things like "I have 10 years of experience" unless it's in the facts.
3. STYLE MATCH: Adopt the tone, length, and formatting style of the provided WRITING STYLE SAMPLES as closely as possible. If they write short and casual emails, do the same.

Draft the email now:
""")

def draft_cold_email(user_id: str, target_context: str) -> Dict[str, Any]:
    """
    Retrieves profile chunks for a user and drafts a grounded cold email.
    Returns a dict with 'draft_text' and 'used_chunks'.
    """
    collection = get_profile_collection(user_id)
    used_chunks = []
    
    # 1. Get writing samples (we get all of them up to a reasonable limit)
    samples_data = collection.get(where={"field": "writing_samples"})
    sample_texts = samples_data.get("documents", []) if samples_data else []
    
    # 2. Get relevant resume / career info via semantic search against target context
    # We use top_k=5 to get the most relevant facts
    try:
        results = collection.query(
            query_texts=[target_context],
            n_results=5,
            where={"field": {"$in": ["resume", "career_info"]}}
        )
        fact_texts = results.get("documents", [[]])[0] if results and results.get("documents") else []
    except Exception as e:
        logger.warning(f"Failed to query profile chunks for user {user_id}: {e}")
        fact_texts = []
        
    # Combine chunks for tracking
    used_chunks.extend(fact_texts)
    used_chunks.extend(sample_texts)
    
    # Format prompt parts
    facts_str = "\n---\n".join(fact_texts) if fact_texts else "No resume facts found."
    samples_str = "\n---\n".join(sample_texts) if sample_texts else "No writing samples found."
    
    prompt_value = DRAFT_EMAIL_PROMPT.format(
        target_context=target_context,
        facts=facts_str,
        samples=samples_str
    )
    
    llm = get_llm(temperature=0.4)
    response = llm.invoke(prompt_value)
    
    return {
        "draft_text": str(response.content),
        "used_chunks": used_chunks
    }
