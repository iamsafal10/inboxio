import os
import uuid
from app.agent.graph import run_agent_graph, SESSION_HISTORY
from app.agent.memory_writer import delete_memory_fact
from app.core.database import SessionLocal
from app.models.user import User
from app.models.memory_fact import MemoryFact

def main():
    db = SessionLocal()
    
    # Create a fresh test user
    email = f"live_deletion_test_{uuid.uuid4()}@example.com"
    user = User(email=email, hashed_password="fake")
    db.add(user)
    db.commit()
    user_id = user.id
    
    print(f"--- Created temporary user {email} ---")
    
    # Seed a durable fact
    fact_text = "The user explicitly hates machine learning and AI, and only wants traditional web development roles."
    fact = MemoryFact(
        user_id=user_id,
        fact_text=fact_text,
        fact_type="constraint",
        source="manual"
    )
    db.add(fact)
    db.commit()
    fact_id = fact.id
    print(f"Seeded Fact (ID: {fact_id}): {fact_text}")
    
    question = "Can you find me some software engineering roles?"
    
    # Run 1: Fact is present
    print("\n--- Run 1: Fact Present ---")
    print(f"User: {question}")
    print("Agent is thinking...")
    # Clear history to ensure a fresh start
    if user_id in SESSION_HISTORY:
        del SESSION_HISTORY[user_id]
        
    result_with_fact = run_agent_graph(user_id, question)
    answer_a = result_with_fact.get('final_answer')
    
    # Delete the fact
    print("\n--- Deleting Fact ---")
    deleted = delete_memory_fact(fact_id, user_id, db)
    print(f"Deleted successfully: {deleted}")
    
    # Run 2: Fact is deleted
    print("\n--- Run 2: Fact Deleted ---")
    print(f"User: {question}")
    print("Agent is thinking...")
    # Clear history again to ensure it's a completely fresh session and it doesn't remember the last turn
    if user_id in SESSION_HISTORY:
        del SESSION_HISTORY[user_id]
        
    result_without_fact = run_agent_graph(user_id, question)
    answer_b = result_without_fact.get('final_answer')
    
    # Print comparison
    print("\n================ COMPARISON ================")
    print(f"Q: {question}\n")
    print(f"ANSWER A (With Fact):\n{answer_a}\n")
    print(f"ANSWER B (Without Fact):\n{answer_b}\n")
    
    if "machine learning" in str(answer_a).lower() or "ai" in str(answer_a).lower() or "traditional" in str(answer_a).lower() or "web" in str(answer_a).lower():
        print("-> It appears Answer A correctly applied the constraint.")
    
    if answer_a != answer_b:
        print("-> SUCCESS: Answer meaningfully changed after memory deletion.")
    else:
        print("-> FAILURE: Answers are identical.")
    
    # Clean up DB
    db.delete(user)
    db.commit()
    db.close()

if __name__ == "__main__":
    main()
