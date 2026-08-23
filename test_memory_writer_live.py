import os
from app.agent.graph import SESSION_HISTORY
from app.agent.memory_writer import extract_and_store_facts
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
    
    print("--- Simulating a real session ---")
    
    # Mocking a session with some personal details and some random chit-chat
    SESSION_HISTORY[user_id] = [
        {"role": "human", "content": "I am currently looking for software engineering roles, preferably backend."},
        {"role": "agent", "content": "Got it. I'll focus on backend software engineering roles."},
        {"role": "human", "content": "By the way, my target start date is June 2027 after I graduate."},
        {"role": "agent", "content": "Noted. June 2027 start date."},
        {"role": "human", "content": "Did MCube AI say it's an internship?"},
        {"role": "agent", "content": "Yes, MCube AI is hiring for an internship."}
    ]
    
    print(f"Triggering extraction for user {user.email}...")
    new_facts = extract_and_store_facts(user_id, db)
    
    print("\n--- Extraction Results ---")
    if not new_facts:
        print("No new facts extracted or saved.")
    else:
        for f in new_facts:
            print(f"- [{f['fact_type']}] {f['fact_text']}")

if __name__ == "__main__":
    main()
