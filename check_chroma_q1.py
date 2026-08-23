import sys
from app.core.database import SessionLocal
from app.models.user import User
import chromadb
from app.core.config import settings
from pathlib import Path
from app.services.embedder import get_embedding_function

def main():
    db = SessionLocal()
    user = db.query(User).filter_by(email="one@gmail.com").first()
    if not user:
        print("No user")
        sys.exit(1)
        
    user_id = user.id
    collection_name = f"inboxio_user_{user_id}".replace("-", "_")
    
    persist_dir = str(Path(settings.CHROMA_PERSIST_DIR).resolve())
    client = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_collection(collection_name, embedding_function=get_embedding_function())
    
    results = collection.get(include=["metadatas", "documents"])
    print("--- CHECKING FOR MCUBE / INTERNSHALA EMAILS IN DB ---")
    for meta, doc in zip(results["metadatas"], results["documents"]):
        sender = meta.get("sender", "").lower()
        if "mcube" in sender or "internshala" in sender:
            print(f"SENDER: {meta.get('sender')}")
            print(f"SUBJECT: {meta.get('subject')}")
            print(f"TEXT SNIPPET: {doc[:150]}")
            print("-" * 40)
            
    print("\n--- RUNNING SEMANTIC SEARCH ---")
    query = "I received an email about MCube AI hiring a Backend Development intern. Did Internshala also send me an email about 'Web Development' internships, and if so, which one arrived first?"
    print(f"Query: {query}")
    
    search_results = collection.query(
        query_texts=[query],
        n_results=10
    )
    
    docs = search_results['documents'][0]
    metas = search_results['metadatas'][0]
    distances = search_results['distances'][0]
    
    for i in range(len(docs)):
        print(f"Rank {i+1} | Distance: {distances[i]:.4f}")
        print(f"Sender: {metas[i].get('sender')}, Subject: {metas[i].get('subject')}")
        print(f"Text Snippet: {docs[i][:150]}")
        print("-" * 40)

if __name__ == "__main__":
    main()
