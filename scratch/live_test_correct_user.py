import sys
from app.agent.graph import run_agent_graph
from app.core.database import SessionLocal
from app.models.user import User
from app.models.chunk import Chunk
from app.models.email_indexed import EmailIndexed

def main():
    db = SessionLocal()
    # Find a user with chunks
    chunk = db.query(Chunk).first()
    if not chunk:
        print("No chunks found in DB.")
        return
        
    email = db.query(EmailIndexed).filter(EmailIndexed.id == chunk.email_id).first()
    if not email:
        print("No email found.")
        return
        
    user = db.query(User).filter(User.id == email.user_id).first()
    if not user:
        print("No user found.")
        return
        
    query = "job internship"
    print(f"Running query for user {user.email}: {query}")
    state = run_agent_graph(str(user.id), query)
    
    print("\nFinal Answer:")
    print(state.get("final_answer", "NO ANSWER"))

if __name__ == "__main__":
    main()
