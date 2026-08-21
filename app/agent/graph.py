from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent.nodes import (
    planner_node,
    tool_selector_node,
    retriever_node,
    conflict_checker_node,
    synthesizer_node
)

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

def run_agent_graph(user_id: str, question: str) -> AgentState:
    """
    Entry point to invoke the agent graph.
    Currently runs through stub nodes returning the state untouched.
    """
    initial_state = AgentState(
        user_id=user_id,
        question=question,
        sub_goals=[],
        tool_calls=[],
        retrieved_chunks=[],
        conflicts_detected=[],
        final_answer=None
    )
    return app_graph.invoke(initial_state)
