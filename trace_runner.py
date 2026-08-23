import os
import time
from langsmith import Client

# Make sure we load the env
from dotenv import load_dotenv
load_dotenv()

from app.agent.graph import run_agent_graph
from app.core.database import SessionLocal
from app.models.user import User

def main():
    db = SessionLocal()
    user = db.query(User).filter_by(email="one@gmail.com").first()
    if not user:
        print("User not found.")
        return

    print("Running query...")
    # Run the query
    result = run_agent_graph(
        user_id=user.id,
        question="Which platform notified me that the name 'S. Tripathi' was mentioned in a Computer Science paper?"
    )
    print("Answer:", getattr(result, "final_answer", result.get("final_answer", "No answer found")))
    
    # Wait a bit for trace to upload
    time.sleep(2)
    
    try:
        client = Client()
        project_name = os.getenv("LANGCHAIN_PROJECT", os.getenv("LANGSMITH_PROJECT", "default"))
        runs = list(client.list_runs(project_name=project_name, execution_order=1, limit=1))
        if runs:
            print("Trace URL:", runs[0].url)
            print("Trace ID:", runs[0].id)
        else:
            print("No trace found in project:", project_name)
    except Exception as e:
        print("LangSmith Client Error:", e)

if __name__ == "__main__":
    main()
