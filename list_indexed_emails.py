from app.core.database import SessionLocal
from app.models.email_indexed import EmailIndexed

with SessionLocal() as db:
    emails = db.query(EmailIndexed).limit(10).all()
    print("--- Sample of 10 Indexed Emails ---")
    for e in emails:
        print(f"Subject: {e.subject}")
        print(f"Sender: {e.sender}")
        print("-" * 20)
