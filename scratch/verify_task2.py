import os
import sys
from app.core.database import SessionLocal
from app.models.user import User
from app.services.cold_email import draft_cold_email

def main(email: str):
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        print(f"User {email} not found in DB.")
        sys.exit(1)
        
    print(f"Generating cold email draft for {email}...")
    target_context = "Applying for an AI Engineering role at OpenAI. Need to show I have experience in generative AI and software engineering."
    
    result = draft_cold_email(user.id, target_context)
    
    print("\n================== DRAFT ==================\n")
    print(result["draft_text"])
    
    print("\n================ USED CHUNKS ================\n")
    for i, chunk in enumerate(result["used_chunks"]):
        print(f"\n[Chunk {i+1}]")
        print(chunk)
        
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_task2.py <your_email>")
        sys.exit(1)
    main(sys.argv[1])
