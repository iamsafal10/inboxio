import asyncio
from app.core.database import SessionLocal
from app.models.user import User
from app.agent.graph import run_agent_graph
from unittest.mock import patch

async def main():
    db = SessionLocal()
    user_id = 'e6ab2b03-2d1f-4046-b0a3-77114322aa38'
    user = db.query(User).filter(User.id == user_id).first()
        
    question = "Do I have any emails about a job or internship?"
    
    # Run graph with mocked search_emails to limit chunks and avoid rate limit
    from app.services import semantic_search
    original_search = semantic_search.search_emails
    
    def mocked_search(u_id, query, top_k=20):
        return original_search(u_id, query, top_k=2) # Force top_k=2
        
    with patch('app.services.semantic_search.search_emails', side_effect=mocked_search):
        state = run_agent_graph(str(user.id), question)
    
    print("\nGraph State:")
    print("Planner sub-goals:", state.get("sub_goals"))
    print("Tool calls:", state.get("tool_calls"))
    print("Evidence length:", len(state.get("retrieved_chunks", [])))
    print("Final answer:", state.get("final_answer"))

if __name__ == "__main__":
    asyncio.run(main())
