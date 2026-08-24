import logging
from app.core.database import SessionLocal
from app.models.user import User
from app.agent.graph import run_agent_graph
from app.services.domain_filter import is_career_question

logging.basicConfig(level=logging.INFO)

with SessionLocal() as db:
    user = db.query(User).filter(User.email == "one@gmail.com").first()

    q = "recent job oppurtunity mail at honeywell summary"
    print(f"is_career: {is_career_question(q)}")
    result = run_agent_graph(str(user.id), q)
    print("Final Answer:")
    print(result.get("final_answer"))
