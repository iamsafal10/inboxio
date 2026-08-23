import asyncio
from app.agent.graph import run_agent_graph
from app.core.database import SessionLocal

user_id = "00000000-0000-0000-0000-000000000000"
state = run_agent_graph(user_id, "recent job mail")
print("Sub goals:", state.get("sub_goals"))
print("Tool calls:", state.get("tool_calls"))
print("Chunks:", len(state.get("retrieved_chunks", [])))
print("Final Answer:", state.get("final_answer"))
