import logging
from typing import Any
from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate

from app.agent.state import AgentState
from app.core.config import settings

logger = logging.getLogger(__name__)

class PlannerOutput(BaseModel):
    sub_goals: list[str] = Field(description="A clean list of concrete sub-goals required to answer the user's question.")

class ToolCallOutput(BaseModel):
    tool_name: str = Field(description="Must be one of: 'search_by_sender', 'reconstruct_thread', 'search_by_date_range', or 'semantic_search'")
    query: str = Field(description="The search string, sender name, or thread ID. Leave empty if not needed.", default="")
    start_date: str = Field(description="Start date in ISO format, if applicable.", default="")
    end_date: str = Field(description="End date in ISO format, if applicable.", default="")

class ToolSelectionList(BaseModel):
    tool_calls: list[ToolCallOutput] = Field(description="List of tools to execute for the given sub-goals.")

class ConflictDetail(BaseModel):
    claim_a: str = Field(description="The first conflicting claim or fact.")
    claim_b: str = Field(description="The second claim or fact that contradicts the first.")
    source_a: str = Field(description="The source or context (e.g., sender, date, subject) of the first claim.")
    source_b: str = Field(description="The source or context of the second claim.")

class ConflictOutput(BaseModel):
    has_contradictions: bool = Field(description="True if genuine contradictions were found in the evidence.")
    conflicts: list[ConflictDetail] = Field(description="List of specific contradictions. Empty if none found.", default=[])

class Citation(BaseModel):
    source_id: int = Field(description="The numeric citation ID used in the text, e.g. 1.")
    sender: str = Field(description="The sender of the email cited.")
    subject: str = Field(description="The subject of the email cited.")
    date: str = Field(description="The date of the email cited.")

class SynthesisOutput(BaseModel):
    answer: str = Field(description="The final comprehensive answer to the user's question, containing inline citations like [1] or [1, 2].")
    citations: list[Citation] = Field(description="The structured list of all sources cited in the answer.")

from app.llm.llm_setup import get_llm

def get_planner_llm():
    return get_llm(temperature=0.0)

def planner_node(state: AgentState) -> AgentState:
    """
    Parses the question into concrete sub_goals using Gemini structured output.
    For simple questions, it returns a single sub-goal.
    For complex questions, it breaks it down into multiple logical sub-goals.
    """
    question = state.get("question", "")
    logger.info(f"Running planner_node for question: {question}")
    
    if not question.strip():
        return {**state, "sub_goals": []}
    chat_history = state.get("chat_history", [])
    
    formatted_history = "No prior conversation in this session."
    if chat_history:
        lines = []
        for msg in chat_history:
            role = "User" if msg.get("role") == "human" else "Agent"
            lines.append(f"{role}: {msg.get('content')}")
        formatted_history = "\n".join(lines)

    prompt = PromptTemplate.from_template(
        "You are an expert planner for an email assistant agent.\n"
        "Your task is to break down the following user question into a small, ordered list of concrete sub-goals "
        "that need to be achieved to answer it fully.\n"
        "- If the question refers to prior context (e.g., 'what about the other one?'), use the Recent Conversation History to resolve the reference.\n"
        "- If the question is simple and requires only looking up a single fact, return exactly one sub-goal.\n"
        "- If the question is complex, break it into logical steps (e.g. find all related threads, check latest status).\n\n"
        "Recent Conversation History:\n{chat_history}\n\n"
        "User Question: {question}\n\n"
        "Output a structured list of sub_goals."
    )
    
    llm = get_planner_llm()
    structured_llm = llm.with_structured_output(PlannerOutput)
    chain = prompt | structured_llm
    
    max_retries = 1
    for attempt in range(max_retries + 1):
        try:
            result = chain.invoke({
                "question": question,
                "chat_history": formatted_history
            })
            if not result or not hasattr(result, "sub_goals"):
                raise ValueError("LLM returned malformed structured output.")
                
            sub_goals = result.sub_goals
            logger.info(f"Planner extracted sub_goals: {sub_goals}")
            return {**state, "sub_goals": sub_goals}
            
        except Exception as e:
            logger.warning(f"Planner failed on attempt {attempt + 1}: {e}")
            if attempt == max_retries:
                logger.error("Planner completely failed to produce valid structured output.")
                raise ValueError(f"Planner node failed to produce valid sub-goals: {str(e)}") from e
                
    return state

def tool_selector_node(state: AgentState) -> AgentState:
    """
    Picks which retrieval tool(s) fit each sub-goal.
    Uses a simple LLM routing to map obvious signals (person/sender, time period, thread, or generic).
    """
    sub_goals = state.get("sub_goals", [])
    logger.info(f"Running tool_selector_node for {len(sub_goals)} sub_goals")
    
    if not sub_goals:
        return {**state, "tool_calls": []}
        
    prompt = PromptTemplate.from_template(
        "You are a routing assistant. Map the following sub-goals to exactly one appropriate tool each.\n"
        "Available tools:\n"
        "1. 'search_by_sender': If the sub-goal mentions a specific person, sender, or email address.\n"
        "2. 'reconstruct_thread': If the sub-goal mentions reading a full 'thread' or 'conversation'.\n"
        "3. 'search_by_date_range': If the sub-goal mentions a time period (e.g. 'last month', '2023').\n"
        "4. 'semantic_search': For any general topic, question, or fact lookup.\n\n"
        "Sub-goals:\n{sub_goals}\n\n"
        "Output a list of tool selections, filling in the query/date fields appropriately based on the sub-goal."
    )
    
    llm = get_planner_llm()
    structured_llm = llm.with_structured_output(ToolSelectionList)
    chain = prompt | structured_llm
    
    try:
        sub_goals_str = "\n".join(f"- {g}" for g in sub_goals)
        result = chain.invoke({"sub_goals": sub_goals_str})
        
        # Convert from Pydantic to dicts for state
        tool_calls = [tc.model_dump() for tc in result.tool_calls]
        logger.info(f"Tool selector picked: {tool_calls}")
        
        return {**state, "tool_calls": tool_calls}
    except Exception as e:
        logger.error(f"Tool selector failed: {e}")
        # Fallback: just semantic search everything
        fallback_calls = [{"tool_name": "semantic_search", "query": g, "start_date": "", "end_date": ""} for g in sub_goals]
        return {**state, "tool_calls": fallback_calls}

def retriever_node(state: AgentState) -> AgentState:
    """
    Stub for retrieving evidence.
    Will execute chosen tools to fetch chunks from Chroma.
    """
    logger.info("Running retriever_node")
    return state

def conflict_checker_node(state: AgentState) -> AgentState:
    """
    Identifies contradictions across retrieved chunks using structured LLM output.
    Batches evidence if it is too large for a single context window.
    Returns explicit check_status='failed' if LLM fails, never silencing errors as an empty list.
    """
    logger.info("Running conflict_checker_node")
    retrieved_chunks = state.get("retrieved_chunks", [])
    
    if not retrieved_chunks:
        return {**state, "conflicts_detected": [], "check_status": "passed"}

    # Format chunks into a single text representation
    formatted_evidence = []
    for i, chunk in enumerate(retrieved_chunks):
        meta = chunk.get("metadata", {})
        sender = meta.get("sender", "Unknown")
        date = meta.get("sent_at", "Unknown")
        subject = meta.get("subject", "No Subject")
        text = chunk.get("text", "")
        formatted_evidence.append(f"--- Evidence {i+1} ---\nSender: {sender}\nDate: {date}\nSubject: {subject}\nContent: {text}\n")
    
    full_text = "\n".join(formatted_evidence)
    
    # Batching logic: chunk text if extremely large (e.g., > 30000 chars)
    max_chars_per_batch = 30000
    batches = [full_text[i:i+max_chars_per_batch] for i in range(0, len(full_text), max_chars_per_batch)]
    
    llm = get_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(ConflictOutput)
    
    prompt = PromptTemplate.from_template(
        "You are an expert fact-checker for an email assistant agent.\n"
        "Your task is to analyze the following retrieved email excerpts (evidence) and detect any genuine "
        "contradictions or conflicting information. "
        "A contradiction occurs when two or more pieces of evidence state facts that cannot both be true "
        "(e.g., 'interview is on Monday' vs 'interview is on Tuesday', or 'offer extended' vs 'position filled' for the same role).\n\n"
        "Evidence:\n{evidence}\n\n"
        "Output a structured result indicating if contradictions exist, and list them with their sources."
    )
    chain = prompt | structured_llm
    
    all_conflicts = []
    max_retries = 2
    
    for batch_idx, batch_text in enumerate(batches):
        batch_success = False
        for attempt in range(max_retries + 1):
            try:
                result = chain.invoke({"evidence": batch_text})
                if not result or not hasattr(result, "has_contradictions"):
                    raise ValueError("LLM returned malformed structured output.")
                
                if result.has_contradictions and result.conflicts:
                    all_conflicts.extend([c.model_dump() for c in result.conflicts])
                
                batch_success = True
                break
                
            except Exception as e:
                logger.warning(f"Conflict checker failed on batch {batch_idx + 1}, attempt {attempt + 1}: {e}")
                if attempt == max_retries:
                    logger.error(f"Conflict checker completely failed on batch {batch_idx + 1}.")
        
        # If any batch completely fails, return failure state explicitly
        if not batch_success:
            return {**state, "conflicts_detected": all_conflicts, "check_status": "failed"}
            
    logger.info(f"Conflict checker found {len(all_conflicts)} conflicts.")
    return {**state, "conflicts_detected": all_conflicts, "check_status": "passed"}

def synthesizer_node(state: AgentState) -> AgentState:
    """
    Generates a comprehensive final answer with inline citations.
    Surfaces contradictions clearly and flags if checks failed.
    Returns both the answer text and a structured list of citations.
    """
    logger.info("Running synthesizer_node")
    question = state.get("question", "")
    retrieved_chunks = state.get("retrieved_chunks", [])
    conflicts = state.get("conflicts_detected", [])
    check_status = state.get("check_status", "passed")
    
    # Format the evidence identically, assigning a Source ID to each chunk.
    formatted_evidence = []
    for i, chunk in enumerate(retrieved_chunks):
        meta = chunk.get("metadata", {})
        sender = meta.get("sender", "Unknown")
        date = meta.get("sent_at", "Unknown")
        subject = meta.get("subject", "No Subject")
        text = chunk.get("text", "")
        formatted_evidence.append(f"--- [Source ID: {i+1}] ---\nSender: {sender}\nDate: {date}\nSubject: {subject}\nContent: {text}\n")
    
    full_evidence = "\n".join(formatted_evidence)
    if not full_evidence:
        full_evidence = "No evidence found."
        
    formatted_conflicts = ""
    if conflicts:
        for i, conflict in enumerate(conflicts):
            formatted_conflicts += f"Conflict {i+1}:\n"
            if isinstance(conflict, dict):
                formatted_conflicts += f"- {conflict.get('source_a')}: {conflict.get('claim_a')}\n"
                formatted_conflicts += f"- {conflict.get('source_b')}: {conflict.get('claim_b')}\n"
            else:
                formatted_conflicts += f"- {conflict.source_a}: {conflict.claim_a}\n"
                formatted_conflicts += f"- {conflict.source_b}: {conflict.claim_b}\n"
    else:
        formatted_conflicts = "No contradictions detected."
        
    chat_history = state.get("chat_history", [])
    formatted_history = "No prior conversation in this session."
    if chat_history:
        lines = []
        for msg in chat_history:
            role = "User" if msg.get("role") == "human" else "Agent"
            lines.append(f"{role}: {msg.get('content')}")
        formatted_history = "\n".join(lines)
        
    llm = get_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(SynthesisOutput)
    
    prompt = PromptTemplate.from_template(
        "You are an expert email assistant.\n"
        "Your task is to synthesize a final answer to the user's question using ONLY the provided evidence.\n"
        "Use the Recent Conversation History to understand context and coreferences (e.g. 'what about the other one').\n\n"
        "CRITICAL RULES:\n"
        "1. Every claim MUST include an inline citation using the [Source ID] format (e.g., 'The meeting is on Tuesday [1].').\n"
        "2. All citations used MUST be mapped and returned in the structured `citations` list.\n"
        "3. If `Check Status` is 'failed', you MUST include this explicit disclaimer in your answer: 'Note: I couldn't verify the evidence for contradictions due to an internal error.'\n"
        "4. If `Contradictions` lists any conflicts, you MUST surface them explicitly (e.g., 'I found conflicting info: [Sender A] says X, but [Sender B] says Y.'). NEVER silently pick a side.\n"
        "5. If the evidence is thin or does not answer the question, state it plainly rather than guessing.\n\n"
        "Recent Conversation History:\n{chat_history}\n\n"
        "Question: {question}\n\n"
        "Check Status: {check_status}\n\n"
        "Contradictions:\n{conflicts}\n\n"
        "Evidence:\n{evidence}\n\n"
        "Output a structured result with the final `answer` and `citations` list."
    )
    
    chain = prompt | structured_llm
    
    try:
        result = chain.invoke({
            "question": question,
            "chat_history": formatted_history,
            "check_status": check_status,
            "conflicts": formatted_conflicts,
            "evidence": full_evidence
        })
        
        if not result or not hasattr(result, "answer"):
            raise ValueError("LLM returned malformed structured output.")
            
        final_answer = result.answer
        citations = [c.model_dump() for c in result.citations] if result.citations else []
        
        logger.info(f"Synthesizer generated answer with {len(citations)} citations.")
        return {**state, "final_answer": final_answer, "citations": citations}
        
    except Exception as e:
        logger.error(f"Synthesizer failed: {e}")
        fallback_answer = "I apologize, but I encountered an error while trying to synthesize the final answer."
        return {**state, "final_answer": fallback_answer, "citations": []}
