"""Script to run 5 reference questions against the dumb baseline and save results."""

import os
import sys
import json
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).resolve().parent))

from app.core.database import SessionLocal
from app.models.user import User
from app.baseline.dumb_baseline import answer_question_baseline

QUESTIONS = [
    "What did the invitation to join the team for Flipkart GRiD 6.0 say?",
    "What are the latest updates or emails regarding hackathons and competitions?",
    "Who has sent me the most emails regarding software development tracks?",
    "Are there any pending deadlines or tasks I need to complete for my ongoing applications?",
    "Did I receive any rejection emails recently, or are all my applications still under review?"
]

def main():
    db = SessionLocal()
    user = db.query(User).first()
    if not user:
        print("No user found in the database. Please create a user and connect Gmail first.")
        sys.exit(1)
        
    user_id = user.id
    results = []
    
    print(f"Running baseline against 5 questions for user {user_id}...")
    
    for q in QUESTIONS:
        print(f"Q: {q}")
        # Run baseline
        baseline_res = answer_question_baseline(user_id=user_id, question=q)
        
        # Prepare result with manual judgment field
        entry = {
            "question": baseline_res["question"],
            "answer": baseline_res["answer"],
            "chunks_used": baseline_res["chunks_used"],
            "human_judgment": ""  # To be filled by user manually
        }
        results.append(entry)
        
    # Save to JSON
    output_path = Path(__file__).resolve().parent / "app" / "baseline" / "reference_results.json"
    
    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
        
    print(f"\nSaved {len(results)} reference results to {output_path}")
    print("Please review the file and fill in the 'human_judgment' fields.")

if __name__ == "__main__":
    main()
