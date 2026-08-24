import logging
import traceback
import sys
from app.core.database import SessionLocal
from app.models.user import User
from app.agent.graph import run_agent_graph

# Flush stdout automatically
sys.stdout.reconfigure(line_buffering=True)
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

print("=== REPRODUCING 500 ERROR ===")
with SessionLocal() as db:
    user = db.query(User).filter(User.email == "one@gmail.com").first()
    if not user:
        print("User not found!")
        exit(1)

    question = "What recent job opportunities did I receive?"
    print(f"Query: {question}")
    
    try:
        result = run_agent_graph(user_id=str(user.id), question=question)
        print("=== SUCCESS ===")
        print(result)
    except Exception as e:
        print("\n=== EXCEPTION CAUGHT ===")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print("\n=== TRACEBACK ===")
        traceback.print_exc()
        sys.exit(1)
