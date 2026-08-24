import os
from app.agent.graph import run_agent_graph
from app.core.database import SessionLocal
from app.models.user import User

def main():
    db = SessionLocal()
    user = db.query(User).filter(User.email == "one@gmail.com").first()
    if not user:
        user = db.query(User).first()
        
    if not user:
        print("No user found in DB.")
        return
        
    user_id = user.id
    
    print("--- Turn 1 ---")
    q1 = "I received an email about MCube AI hiring an intern. What was the role?"
    print(f"User: {q1}")
    res1 = run_agent_graph(user_id, q1)
    print(f"Agent: {res1.get('final_answer')}\n")
    
    print("--- Turn 2 ---")
    q2 = "What about Internshala, did they send anything similar?"
    print(f"User: {q2}")
    res2 = run_agent_graph(user_id, q2)
    print(f"Agent: {res2.get('final_answer')}\n")
    
    print("--- Turn 3 ---")
    q3 = "Which one of those two emails arrived first?"
    print(f"User: {q3}")
    res3 = run_agent_graph(user_id, q3)
    print(f"Agent: {res3.get('final_answer')}\n")

if __name__ == "__main__":
    main()
