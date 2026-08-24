import logging
import json
from app.core.database import SessionLocal
from app.models.user import User
from app.models.email_indexed import EmailIndexed
from app.models.chunk import Chunk
from app.services.embedder import chroma_client
from app.agent.state import AgentState
from app.agent.nodes import (
    planner_node, 
    tool_selector_node, 
    retriever_node, 
    conflict_checker_node, 
    synthesizer_node
)

logging.basicConfig(level=logging.INFO)

with SessionLocal() as db:
    user = db.query(User).filter(User.email == "one@gmail.com").first()
    if not user:
        user = db.query(User).first()
        
    print("=================== INGESTION COUNTS ===================")
    email_count = db.query(EmailIndexed).filter(EmailIndexed.user_id == user.id).count()
    chunk_count = db.query(Chunk).join(EmailIndexed).filter(EmailIndexed.user_id == user.id).count()
    print(f"Total Emails Indexed in DB for this user: {email_count}")
    print(f"Total Chunks in DB for this user: {chunk_count}")
    
    collection_name = f"inboxio_user_{user.id}".replace("-", "_")
    try:
        col = chroma_client.get_collection(name=collection_name)
        print(f"Total Chunks in Chroma for this user: {col.count()}")
    except Exception as e:
        print(f"Chroma Collection Error: {e}")

    # Let's see if any email subject or body contains "honeywell"
    honeywell_emails = db.query(EmailIndexed).filter(EmailIndexed.user_id == user.id).filter(
        (EmailIndexed.subject.ilike("%honeywell%")) | (EmailIndexed.body.ilike("%honeywell%"))
    ).count()
    print(f"Emails in DB containing 'honeywell': {honeywell_emails}")

    print("\n=================== AGENT TRACE ===================")
    q = "recent job oppurtunity mail at honeywell summary"
    state: AgentState = {
        "user_id": str(user.id),
        "question": q,
        "chat_history": [],
        "long_term_facts": [],
        "sub_goals": [],
        "tool_calls": [],
        "retrieved_chunks": [],
        "conflicts_detected": [],
        "check_status": "",
        "final_answer": None,
        "citations": []
    }
    
    print("\n--- 1. PLANNER NODE ---")
    state = planner_node(state)
    print(f"Sub-goals: {state['sub_goals']}")
    
    print("\n--- 2. TOOL SELECTOR NODE ---")
    state = tool_selector_node(state)
    print(f"Tool Calls: {json.dumps(state['tool_calls'], indent=2)}")
    
    print("\n--- 3. RETRIEVER NODE ---")
    state = retriever_node(state)
    retrieved = state['retrieved_chunks']
    print(f"Number of Retrieved Chunks: {len(retrieved)}")
    for i, c in enumerate(retrieved):
        print(f"  Chunk {i+1} [Distance: {c.get('distance')}]: {c.get('metadata', {}).get('subject')} (Sender: {c.get('metadata', {}).get('sender')})")
    
    print("\n--- 4. CONFLICT CHECKER NODE ---")
    state = conflict_checker_node(state)
    print(f"Check Status: {state['check_status']}")
    print(f"Conflicts Detected: {state['conflicts_detected']}")
    
    print("\n--- 5. SYNTHESIZER NODE ---")
    state = synthesizer_node(state)
    print(f"Final Answer:\n{state['final_answer']}")
