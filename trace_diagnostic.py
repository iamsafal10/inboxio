import logging
from app.core.database import SessionLocal
from app.models.user import User
from app.models.email_indexed import EmailIndexed
from app.models.chunk import Chunk
from app.services.embedder import chroma_client
from app.services.domain_filter import is_career_question
from app.agent.graph import run_agent_graph
import os

logging.basicConfig(level=logging.INFO)

with SessionLocal() as db:
    user = db.query(User).filter(User.email == "one@gmail.com").first()
    if not user:
        user = db.query(User).first()
        
    print(f"--- USER INFO ---")
    print(f"User ID: {user.id}")
    print(f"Email: {user.email}")
    print(f"Gmail Connected: {user.gmail_connected}")
    
    email_count = db.query(EmailIndexed).filter(EmailIndexed.user_id == user.id).count()
    chunk_count = db.query(Chunk).join(EmailIndexed).filter(EmailIndexed.user_id == user.id).count()
    print(f"Emails Indexed: {email_count}")
    print(f"Chunks in DB: {chunk_count}")
    
    collection_name = f"inboxio_user_{user.id}".replace("-", "_")
    try:
        col = chroma_client.get_collection(name=collection_name)
        print(f"Chroma Chunks: {col.count()}")
    except Exception as e:
        print(f"Chroma Chunks: Collection not found or error ({e})")
        
    print("\n--- DOMAIN FILTER TEST ---")
    for q in ["intern", "any inetrn opeing mail in", "recent job mail"]:
        print(f"'{q}' -> is_career_question: {is_career_question(q)}")
        
    print("\n--- AGENT TRACE ('recent job mail') ---")
    if email_count > 0:
        result = run_agent_graph(str(user.id), "recent job mail")
        print("Final Answer:")
        print(result.get("final_answer"))
    else:
        print("Skipping agent trace because no emails are indexed.")
