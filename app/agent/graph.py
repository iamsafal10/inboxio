from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent.nodes import (
    planner_node,
    tool_selector_node,
    retriever_node,
    conflict_checker_node,
    synthesizer_node
)
from app.core.database import SessionLocal
from app.agent.memory_reader import get_relevant_facts

def should_loop_back(state: AgentState) -> str:
    """
    Stub for loop-back condition. 
    If we need more info (multi-hop), go back to tool_selector.
    Otherwise go to synthesize.
    """
    # For now, always route to synthesize.
    return "synthesize"

def build_graph():
    workflow = StateGraph(AgentState)
    
    # 1. Add nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("tool_selector", tool_selector_node)
    workflow.add_node("retriever", retriever_node)
    workflow.add_node("conflict_checker", conflict_checker_node)
    workflow.add_node("synthesizer", synthesizer_node)
    
    # 2. Add edges
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "tool_selector")
    workflow.add_edge("tool_selector", "retriever")
    workflow.add_edge("retriever", "conflict_checker")
    
    # 3. Conditional edge for potential multi-hop loop-back
    workflow.add_conditional_edges(
        "conflict_checker",
        should_loop_back,
        {
            "synthesize": "synthesizer",
            "loop_back": "tool_selector"
        }
    )
    
    workflow.add_edge("synthesizer", END)
    
    return workflow.compile()

# Compile graph once at startup
app_graph = build_graph()

# In-memory store for session context.
# Key: user_id (for session scoping), Value: List of {"role": str, "content": str}
SESSION_HISTORY = {}

def run_agent_graph(user_id: str, question: str) -> AgentState:
    """
    Entry point to invoke the agent graph.
    Currently runs through stub nodes returning the state untouched.
    """
    chat_history = SESSION_HISTORY.get(user_id, [])
    
    # Extract durable facts
    db = SessionLocal()
    try:
        long_term_facts = get_relevant_facts(user_id, question, db)
    finally:
        db.close()
    
    initial_state = AgentState(
        user_id=user_id,
        question=question,
        sub_goals=[],
        tool_calls=[],
        retrieved_chunks=[],
        conflicts_detected=[],
        check_status="",
        final_answer=None,
        citations=[],
        chat_history=chat_history.copy(),
        long_term_facts=long_term_facts
    )
    result = app_graph.invoke(initial_state)
    
    # Update short-term memory with this turn
    history = SESSION_HISTORY.get(user_id, [])
    history.append({"role": "human", "content": question})
    if result.get("final_answer"):
        history.append({"role": "agent", "content": result["final_answer"]})
    else:
        history.append({"role": "agent", "content": "I couldn't generate an answer."})
        
    # Cap history to last 6 messages (3 turns)
    if len(history) > 6:
        history = history[-6:]
        
    SESSION_HISTORY[user_id] = history
    return result
