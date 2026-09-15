import logging
from app.llm.llm_setup import get_llm
from app.agent.state import AgentState
from app.agent.nodes import planner_node

logging.basicConfig(level=logging.INFO)

llm = get_llm(temperature=0.0)
print("=== LLM CONFIGURATION ===")
print(f"Type: {type(llm).__name__}")
print(f"Model Name: {getattr(llm, 'model_name', 'Unknown')}")
print(f"Base URL: {getattr(llm, 'openai_api_base', 'Unknown')}")

print("\n=== RUNNING PLANNER ===")
state: AgentState = {
    "user_id": "test_user",
    "question": "What did LeetCode email me about?",
    "chat_history": [],
    "long_term_facts": [],
    "sub_goals": [],
    "tool_calls": [],
    "retrieved_chunks": [],
    "conflicts_detected": [],
    "check_status": "",
    "final_answer": None,
    "citations": []
}

state = planner_node(state)
print("\n=== PLANNER OUTPUT ===")
print(state["sub_goals"])
