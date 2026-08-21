from typing import TypedDict, List, Any, Optional

class AgentState(TypedDict):
    """
    The state object that flows through the LangGraph.
    Later tasks will refine these types, but for now they allow pass-through.
    """
    user_id: str
    question: str
    sub_goals: List[str]
    tool_calls: List[Any]
    retrieved_chunks: List[Any]
    conflicts_detected: List[str]
    final_answer: Optional[str]
