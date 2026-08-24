import asyncio
from app.core.database import SessionLocal
from app.models.user import User
from app.agent.graph import run_agent_graph
import app.agent.nodes

async def main():
    db = SessionLocal()
    user_id = 'e6ab2b03-2d1f-4046-b0a3-77114322aa38'
    user = db.query(User).filter(User.id == user_id).first()
        
    question = "Do I have any emails about a job or internship?"
    
    # Patch the reference inside nodes.py
    original_search = app.agent.nodes.search_emails
    def mocked_search(u_id, query, top_k=20):
        # Force top_k to 3 to stay within limits
        return original_search(u_id, query, top_k=3)
    
    app.agent.nodes.search_emails = mocked_search
    
    print("Running graph...")
    state = run_agent_graph(str(user.id), question)
    
    print("\nGraph State:")
    print("Tool calls:", state.get("tool_calls"))
    print("Evidence length:", len(state.get("retrieved_chunks", [])))
    print("Final answer:", state.get("final_answer"))
    
    if state.get("retrieved_chunks"):
        print("First retrieved chunk:", state.get("retrieved_chunks")[0])

if __name__ == "__main__":
    asyncio.run(main())
