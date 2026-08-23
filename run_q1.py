import os
import json
from dotenv import load_dotenv
load_dotenv()

from app.agent.graph import run_agent_graph
from app.core.database import SessionLocal
from app.models.user import User

def main():
    with open("eval/eval_questions.json", "r") as f:
        questions = json.load(f)
        
    q1 = questions[0]
    print(f"Running Q1: {q1['question']}")
    
    db = SessionLocal()
    user = db.query(User).filter_by(email="one@gmail.com").first()
    if not user:
        print("User not found.")
        return
        
    res = run_agent_graph(user_id=user.id, question=q1['question'])
    
    print("\n--- SUB GOALS ---")
    print(res.get("sub_goals", []))
    
    print("\n--- TOOL CALLS ---")
    print(res.get("tool_calls", []))
    
    print("\n--- RETRIEVED CHUNKS ---")
    for chunk in res.get("retrieved_chunks", []):
        meta = chunk.get("metadata", {})
        print(f"Sender: {meta.get('sender')}, Subject: {meta.get('subject')}, Date: {meta.get('sent_at')}")
        print(f"Content: {chunk.get('text')[:100]}...")
        print("-")
        
    print("\n--- CONFLICTS ---")
    conflicts = res.get("conflicts_detected", [])
    if conflicts:
        for c in conflicts:
            print(c)
    else:
        print("No conflicts detected.")
        
    print("\n--- FINAL ANSWER ---")
    print(res.get("final_answer", ""))

if __name__ == "__main__":
    main()
