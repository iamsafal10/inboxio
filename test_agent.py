import logging
logging.basicConfig(level=logging.DEBUG)

from app.core.database import SessionLocal
from app.models.user import User
from app.agent.graph import run_agent_graph

db = SessionLocal()
user = db.query(User).filter(User.email == 'one@gmail.com').first()
if user:
    print(f"Testing for user ID: {user.id}")
    state = run_agent_graph(str(user.id), "What job or internship opportunities did I receive recently?")
    print("FINAL ANSWER:", state.get("final_answer"))
else:
    print("User not found")
db.close()
