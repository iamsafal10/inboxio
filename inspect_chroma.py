import os
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User
import chromadb
from pathlib import Path

def main():
    db = SessionLocal()
    user = db.query(User).first()
    if not user:
        print("No user found in db.")
        return
        
    user_id = user.id
    collection_name = f"inboxio_user_{user_id}".replace("-", "_")
    print(f"Checking collection: {collection_name}")
    
    persist_dir = str(Path(settings.CHROMA_PERSIST_DIR).resolve())
    client = chromadb.PersistentClient(path=persist_dir)
    
    collections = client.list_collections()
    print(f"Total collections: {len(collections)}")
    
    for coll in collections:
        results = coll.get(include=["metadatas"])
        print(f"Collection: {coll.name} - Chunks: {len(results['ids'])}")
        
        subjects = set()
        for meta in results['metadatas']:
            if meta:
                subjects.add(meta.get('subject', ''))
                
        print("  Subjects:")
        for s in sorted(list(subjects))[:10]:
    collection = client.get_collection(collection_name)
    
    results = collection.get(include=["metadatas"])
    print(f"Collection: {collection.name} - Chunks: {len(results['ids'])}")
    
    subjects = set()
    for meta in results['metadatas']:
        if meta:
            subjects.add(meta.get('subject', ''))
            
    print("  Subjects:")
    for s in sorted(list(subjects))[:10]:
        print(f"   - {s}")
    if len(subjects) > 10:
        print("   - ...")
    
    print(f"Total chunks in Chroma: {len(results['ids'])}")
    
    # Search for the questions' topics
    queries = [
        "Flipkart GRiD 6.0 team registration",
        "coding assessment deadline software engineering",
        "backend developer final round interview",
        "summer internship stipend compensation",
        "job application silence 2 weeks",
        "background check form confirmation",
        "Amazon recruiter initial phone screen",
        "technical onboarding session point of contact",
        "pending deadlines tasks applications",
        "negotiation start date company"
    ]
    
    for q in queries:
        res = collection.query(query_texts=[q], n_results=3)
        print(f"\nQuery: {q}")
        for doc in res['documents'][0]:
            print(f" - {doc[:100].replace(chr(10), ' ')}")

if __name__ == "__main__":
    main()
