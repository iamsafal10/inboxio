import logging
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from langchain_core.prompts import PromptTemplate

from app.llm.llm_setup import get_llm
from app.models.memory_fact import MemoryFact
from app.agent.graph import SESSION_HISTORY

logger = logging.getLogger(__name__)

class ExtractedFact(BaseModel):
    fact_text: str = Field(description="The core durable fact, stated clearly.")
    fact_type: str = Field(description="Category of the fact, e.g., 'preference', 'constraint', 'target_date', 'personal_detail'.")

class ExtractionOutput(BaseModel):
    facts: list[ExtractedFact] = Field(description="List of extracted durable facts. Return an empty list if nothing qualifies.", default=[])

def extract_and_store_facts(user_id: str, db: Session) -> list[dict]:
    """
    Extracts durable long-term facts from the user's current session history
    and persists them to the database, avoiding duplicates.
    Returns a list of newly stored facts.
    """
    history = SESSION_HISTORY.get(user_id, [])
    if not history:
        logger.info(f"No session history found for user {user_id}. Skipping extraction.")
        return []
        
    lines = []
    for msg in history:
        role = "User" if msg.get("role") == "human" else "Agent"
        lines.append(f"{role}: {msg.get('content')}")
    formatted_history = "\n".join(lines)
    
    prompt = PromptTemplate.from_template(
        "You are an expert memory extraction module for an AI assistant.\n"
        "Your task is to review the following conversation history and extract ONLY durable, genuinely reusable personal facts "
        "that the assistant should remember for future sessions.\n\n"
        "CRITICAL RULES:\n"
        "1. Be extremely conservative. Do not extract speculative, uncertain, or ephemeral information.\n"
        "2. Do not extract facts about external entities (e.g., 'The role at MCube AI is an internship').\n"
        "3. Only extract personal details, explicit preferences, or constraints (e.g., 'User prefers backend roles', 'User graduates in 2027').\n"
        "4. If nothing qualifies as a durable personal fact, return an empty list.\n\n"
        "Conversation History:\n{history}\n\n"
        "Output a structured list of extracted facts."
    )
    
    llm = get_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(ExtractionOutput)
    chain = prompt | structured_llm
    
    try:
        result = chain.invoke({"history": formatted_history})
    except Exception as e:
        logger.error(f"Failed to extract facts due to LLM error: {e}")
        return []
        
    if not result or not result.facts:
        logger.info("No durable facts extracted.")
        return []
        
    new_facts = []
    for f in result.facts:
        # Simple deduplication: Check if this exact fact text already exists for this user
        existing = db.query(MemoryFact).filter(
            MemoryFact.user_id == user_id,
            MemoryFact.fact_text == f.fact_text
        ).first()
        
        if existing:
            logger.info(f"Fact already exists, skipping: {f.fact_text}")
            continue
            
        new_fact = MemoryFact(
            user_id=user_id,
            fact_text=f.fact_text,
            fact_type=f.fact_type,
            source="session_history",
            active=True
        )
        db.add(new_fact)
        new_facts.append(new_fact)
        logger.info(f"Stored new fact: {f.fact_text}")
        
        
    if new_facts:
        db.commit()
        
    return [{"fact_text": nf.fact_text, "fact_type": nf.fact_type} for nf in new_facts]

def delete_memory_fact(fact_id: str, user_id: str, db: Session) -> bool:
    """
    Deletes a specific memory fact for the user. Returns True if deleted, False if not found.
    """
    fact = db.query(MemoryFact).filter(
        MemoryFact.id == fact_id,
        MemoryFact.user_id == user_id
    ).first()
    
    if fact:
        db.delete(fact)
        db.commit()
        logger.info(f"Deleted memory fact ID {fact_id} for user {user_id}")
        return True
    return False
