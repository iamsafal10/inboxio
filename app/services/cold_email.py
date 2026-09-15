import logging
from typing import Any, Dict, Optional

from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from app.services.profile_embedder import get_profile_collection
from app.llm.llm_setup import get_llm

logger = logging.getLogger(__name__)


class ColdEmailOutput(BaseModel):
    subject: str = Field(description="A short, specific subject line for the cold email. No placeholders.")
    body: str = Field(description="The full body of the cold email, including greeting and sign-off. No placeholders like [Your Name].")


DRAFT_EMAIL_PROMPT = PromptTemplate.from_template("""You are an expert cold email writer. Your job is to draft a cold email based strictly on the user's profile and the target context.

RECIPIENT: {recipient_email}{company_line}
ROLE / SPECIALIZATION THE USER IS INTERESTED IN: {role_specialization}

TARGET SCENARIO / CONTEXT:
{target_context}

USER FACTS (Resume & Career Info):
{facts}

WRITING STYLE SAMPLES (Use these to match the user's voice):
{samples}

STRICT INSTRUCTIONS:
1. Write a professional cold email addressed to the RECIPIENT, enquiring about or applying for the stated ROLE / SPECIALIZATION.
2. The subject line and the opening must both make the specific role clear.
3. ANTI-FABRICATION RULE: DO NOT invent skills, jobs, experience, numbers, or any facts not explicitly present in the USER FACTS. If the profile is thin, keep the email brief rather than inventing qualifications. Do not say things like "I have 10 years of experience" unless it's in the facts.
4. STYLE MATCH: Adopt the tone, length, and formatting style of the provided WRITING STYLE SAMPLES as closely as possible. If they write short and casual emails, do the same.
5. Do not leave placeholder text such as [Your Name] or [Company] — use only what the USER FACTS and the context above give you.

Draft the email now:
""")


def draft_cold_email(
    user_id: str,
    role_specialization: str,
    recipient_email: str = "",
    company: Optional[str] = None,
    target_context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieves profile chunks for a user and drafts a grounded cold email
    targeted at a specific recipient and role specialization.

    Returns a dict with 'subject', 'draft_text' and 'used_chunks'.
    Raises ValueError if the user has no profile content to ground the draft in.
    """
    collection = get_profile_collection(user_id)
    used_chunks = []

    # 1. Get writing samples (we get all of them up to a reasonable limit)
    samples_data = collection.get(where={"field": "writing_samples"})
    sample_texts = samples_data.get("documents", []) if samples_data else []

    # 2. Get relevant resume / career info via semantic search. The query is
    # built from the role so the retrieved facts actually match the target.
    retrieval_query = " ".join(
        part for part in [role_specialization, company or "", target_context or ""] if part
    ).strip()

    try:
        results = collection.query(
            query_texts=[retrieval_query or role_specialization],
            n_results=5,
            where={"field": {"$in": ["resume", "career_info"]}}
        )
        fact_texts = results.get("documents", [[]])[0] if results and results.get("documents") else []
    except Exception as e:
        logger.warning(f"Failed to query profile chunks for user {user_id}: {e}")
        fact_texts = []

    if not fact_texts and not sample_texts:
        raise ValueError(
            "No profile content found. Save your resume and career info on the "
            "Profile page before drafting a cold email."
        )

    # Combine chunks for tracking
    used_chunks.extend(fact_texts)
    used_chunks.extend(sample_texts)

    # Format prompt parts
    facts_str = "\n---\n".join(fact_texts) if fact_texts else "No resume facts found."
    samples_str = "\n---\n".join(sample_texts) if sample_texts else "No writing samples found."

    prompt_value = DRAFT_EMAIL_PROMPT.format(
        recipient_email=recipient_email or "a hiring contact",
        company_line=f" at {company}" if company else "",
        role_specialization=role_specialization,
        target_context=target_context or "Cold outreach enquiring about openings.",
        facts=facts_str,
        samples=samples_str
    )

    llm = get_llm(temperature=0.4)

    try:
        structured = llm.with_structured_output(ColdEmailOutput).invoke(prompt_value)
        subject = structured.subject.strip()
        draft_text = structured.body.strip()
    except Exception as e:
        # Structured output can fail on weaker models; fall back to a plain
        # completion with a derived subject rather than failing the request.
        logger.warning(f"Structured cold email output failed, falling back: {e}")
        response = llm.invoke(prompt_value)
        draft_text = str(response.content).strip()
        subject = f"Application for {role_specialization}" + (f" at {company}" if company else "")

    return {
        "subject": subject,
        "draft_text": draft_text,
        "used_chunks": used_chunks
    }
