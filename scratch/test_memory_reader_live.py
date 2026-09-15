import os
import uuid
from app.agent.graph import run_agent_graph, SESSION_HISTORY
from app.core.database import SessionLocal
from app.models.user import User
from app.models.memory_fact import MemoryFact

def main():
    db = SessionLocal()
    
    # Create a fresh test user
    email = f"live_reader_test_{uuid.uuid4()}@example.com"
    user = User(email=email, hashed_password="fake")
    db.add(user)
    db.commit()
    user_id = user.id
    
    print(f"--- Created temporary user {email} ---")
    
    # Seed a durable fact from a previous "session"
    fact = MemoryFact(
        user_id=user_id,
        fact_text="User is only interested in remote roles.",
        fact_type="constraint",
        source="manual"
    )
    db.add(fact)
    db.commit()
    print(f"Seeded Fact: {fact.fact_text}")
    
    # Start a brand new session (SESSION_HISTORY is implicitly empty since the user was just created)
    print("\n--- Brand New Session ---")
    question = "Do you see any internships?"
    print(f"User: {question}")
    
    print("Agent is thinking... (should incorporate the 'remote only' constraint into sub-goals and answer)")
    result = run_agent_graph(user_id, question)
    
    # Clean up DB
    db.delete(fact)
    db.delete(user)
    db.commit()
    db.close()
    
    # Print the result
    print("\n--- Result ---")
    sub_goals = result.get("sub_goals", [])
    print(f"Planner Sub-Goals:")
    for sg in sub_goals:
        print(f"- {sg}")
        
    print(f"\nFinal Answer: {result.get('final_answer')}")

if __name__ == "__main__":
    main()
