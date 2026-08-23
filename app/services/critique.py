import logging
import json
from typing import List, Dict, Any
from langchain_core.prompts import PromptTemplate
from app.llm.llm_setup import get_llm

logger = logging.getLogger(__name__)

CRITIQUE_PROMPT = PromptTemplate.from_template("""You are a strict QA auditor reviewing a drafted cold email.
Your ONLY job is to verify that every factual claim in the DRAFT is fully supported by the PROVIDED PROFILE FACTS.

DRAFT EMAIL:
{draft}

PROVIDED PROFILE FACTS:
{facts}

INSTRUCTIONS:
1. Compare every claim about skills, experience, years, projects, metrics, or background in the draft against the profile facts.
2. If the draft invents, exaggerates, or claims something NOT explicitly stated in the profile facts, flag it.
3. If the draft is clean and strictly adheres to the facts, return an empty list of flags.
4. Output your answer EXACTLY as a JSON list of objects. Do not wrap it in markdown block quotes. Just the raw JSON.
5. Format each object like this:
   {{"claim": "The false claim made in the draft", "truth": "What the profile actually supports (or 'Not present in profile')"}}

JSON OUTPUT:
""")

def self_critique(draft: str, profile_chunks_used: List[str]) -> List[Dict[str, str]]:
    """
    Critiques a cold email draft against the profile chunks used to generate it.
    Returns a list of unsupported claims, if any.
    If the LLM fails, raises an exception to prevent silent failure.
    """
    facts_str = "\n---\n".join(profile_chunks_used) if profile_chunks_used else "No profile facts provided."
    
    prompt_value = CRITIQUE_PROMPT.format(
        draft=draft,
        facts=facts_str
    )
    
    llm = get_llm(temperature=0.0)  # zero temperature for deterministic QA
    
    try:
        response = llm.invoke(prompt_value)
        content = str(response.content).strip()
        
        # Remove markdown code blocks if the LLM hallucinated them despite instructions
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        content = content.strip()
        
        # Parse JSON
        flags = json.loads(content)
        
        if not isinstance(flags, list):
            raise ValueError("LLM returned JSON that is not a list.")
            
        return flags
        
    except json.JSONDecodeError as e:
        logger.error(f"Critique node failed to parse JSON: {e} - Content: {content}")
        raise RuntimeError("Critique failed due to malformed LLM output. Cannot guarantee draft is safe.") from e
    except Exception as e:
        logger.error(f"Critique node LLM call failed: {e}")
        raise RuntimeError("Critique failed due to LLM error. Cannot guarantee draft is safe.") from e
