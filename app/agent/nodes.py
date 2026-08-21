import logging
from typing import Any
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate

from app.agent.state import AgentState
from app.core.config import settings

logger = logging.getLogger(__name__)

class PlannerOutput(BaseModel):
    sub_goals: list[str] = Field(description="A clean list of concrete sub-goals required to answer the user's question.")

def get_planner_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-3.5-flash",
        temperature=0.0,
        google_api_key=settings.GEMINI_API_KEY or "dummy_key"
    )

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
    Stub for tool selection. 
    Will choose which search/tools to run based on goals.
    """
    logger.info("Running tool_selector_node")
    return state

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
