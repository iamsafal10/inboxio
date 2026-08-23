import sys
from app.core.database import SessionLocal
from app.models.user import User
from app.models.email_indexed import EmailIndexed

def main():
    db = SessionLocal()
    user = db.query(User).first()
    if not user:
        print("No user")
        sys.exit(1)
        
    emails = db.query(EmailIndexed).filter(EmailIndexed.user_id == user.id).order_by(EmailIndexed.sent_at.desc()).limit(50).all()
    
    print(f"Total emails for user: {db.query(EmailIndexed).filter(EmailIndexed.user_id == user.id).count()}")
    print(f"Showing top {len(emails)} emails:\n")
    
    for idx, e in enumerate(emails):
        print(f"{idx+1}. From: {e.sender}")
        print(f"   Subject: {e.subject}")
        print(f"   Date: {e.sent_at}")
        # print(f"   Snippet: {e.body[:150]}...")
        print("-" * 40)

if __name__ == "__main__":
    main()
