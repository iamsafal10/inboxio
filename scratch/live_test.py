import sys
from app.agent.graph import run_agent_graph
from app.core.database import SessionLocal
from app.models.user import User

def main():
    db = SessionLocal()
    user = db.query(User).first()
    if not user:
        print("No user found.")
        return
        
    query = "job internship"
    print(f"Running query: {query}")
    state = run_agent_graph(str(user.id), query)
    
    print("\nFinal Answer:")
    print(state.get("final_answer", "NO ANSWER"))

if __name__ == "__main__":
    main()
