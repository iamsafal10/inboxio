import sys
from app.core.database import SessionLocal
from app.models.user import User
import chromadb
from app.core.config import settings
from pathlib import Path

def main():
    db = SessionLocal()
    user = db.query(User).first()
    if not user:
        print("No user")
        sys.exit(1)
        
    user_id = user.id
    collection_name = f"inboxio_user_{user_id}".replace("-", "_")
    print(f"Collection: {collection_name}")
    
    persist_dir = str(Path(settings.CHROMA_PERSIST_DIR).resolve())
    client = chromadb.PersistentClient(path=persist_dir)
    
    try:
        collection = client.get_collection(collection_name)
    except Exception as e:
        print(f"Collection missing: {e}")
        # Try to find any collection
        cols = client.list_collections()
        if cols:
            print(f"Found other collections: {[c.name for c in cols]}")
            # Try to find a non-empty one
            for c in cols:
                if c.name.startswith("inboxio_user_"):
                    collection = c
                    print(f"Using {collection.name} as fallback to read data")
                    break
        else:
            sys.exit(1)
            
    results = collection.get(include=["metadatas", "documents"])
    total = len(results['ids'])
    print(f"Total chunks: {total}")
    
    # We want the most recent 25 emails. We can sort by sent_at in metadata.
    # A single email might have multiple chunks, so group by subject/sender/date
    emails = {}
    for i in range(total):
        meta = results['metadatas'][i]
        doc = results['documents'][i]
        key = (meta.get('sender'), meta.get('subject'), meta.get('sent_at'))
        if key not in emails:
            emails[key] = []
        emails[key].append(doc)
        
    # Sort emails by sent_at descending
    sorted_keys = sorted(emails.keys(), key=lambda k: k[2] or "", reverse=True)
    
    print("\n--- RECENT EMAILS ---")
    for k in sorted_keys[:25]:
        sender, subject, date = k
        text = " ".join(emails[k])
        print(f"Date: {date}")
        print(f"From: {sender}")
        print(f"Subject: {subject}")
        print(f"Snippet: {text[:300].replace(chr(10), ' ')}")
        print("-" * 50)

if __name__ == "__main__":
    main()
