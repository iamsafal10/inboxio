from app.core.database import SessionLocal
from app.models.user import User
from app.services.embedder import chroma_client

db = SessionLocal()
user = db.query(User).first()
if user:
    collection_name = f"inboxio_user_{user.id}".replace("-", "_")
    try:
        col = chroma_client.get_collection(collection_name)
        count = col.count()
        print(f"Chroma collection {collection_name} count: {count}")
    except Exception as e:
        print("Error:", e)
