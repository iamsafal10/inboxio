import os
import sys
from app.services.embedder import chroma_client
from app.core.database import SessionLocal
from app.models.user import User

def main(email: str):
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        print(f"User {email} not found in DB.")
        sys.exit(1)
        
    print(f"Found User ID: {user.id}")
    collection_name = f"inboxio_profile_{user.id.replace('-', '')}"
    
    try:
        collection = chroma_client.get_collection(collection_name)
        data = collection.get()
        print(f"\n--- Found {len(data['ids'])} Embedded Profile Chunks in ChromaDB ---")
        for i, (doc, meta) in enumerate(zip(data['documents'], data['metadatas'])):
            print(f"\n[Chunk {i+1} | Field: {meta['field']}]")
            print(doc[:200] + "..." if len(doc) > 200 else doc)
    except Exception as e:
        print(f"Could not find or read collection {collection_name}: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_profile_db.py <your_email>")
        sys.exit(1)
    main(sys.argv[1])
