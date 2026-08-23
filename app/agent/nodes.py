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
        
    prompt = PromptTemplate.from_template(
        "You are an expert planner for an email assistant agent.\n"
        "Your task is to break down the following user question into a small, ordered list of concrete sub-goals "
        "that need to be achieved to answer it fully.\n"
        "- If the question is simple and requires only looking up a single fact, return exactly one sub-goal.\n"
        "- If the question is complex, break it into logical steps (e.g. find all related threads, check latest status).\n\n"
        "User Question: {question}\n\n"
        "Output a structured list of sub_goals."
    )
    
    llm = get_planner_llm()
    structured_llm = llm.with_structured_output(PlannerOutput)
    chain = prompt | structured_llm
    
    max_retries = 1
    for attempt in range(max_retries + 1):
        try:
            result = chain.invoke({"question": question})
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
    Stub for conflict checker.
    Will identify contradictions across retrieved chunks.
    """
    logger.info("Running conflict_checker_node")
    return state

def synthesizer_node(state: AgentState) -> AgentState:
    """
    Stub for synthesizer.
    Will generate the final answer or determine more info is needed.
    """
    logger.info("Running synthesizer_node")
    return state
