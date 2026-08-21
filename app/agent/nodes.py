import logging
from typing import Any
from app.agent.state import AgentState

logger = logging.getLogger(__name__)

def planner_node(state: AgentState) -> AgentState:
    """
    Stub for planner logic (Task 2). 
    Will parse the question into sub_goals.
    """
    logger.info("Running planner_node")
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
