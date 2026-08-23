import os
import sys
from app.core.database import SessionLocal
from app.models.user import User
from app.models.email_send_log import EmailSendLog
from app.services.gmail_sender import send_email

def main(email: str):
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        print(f"User {email} not found in DB.")
        sys.exit(1)
        
    print(f"Attempting to send an email for {email}...")
    
    recipient = email # send to self
    subject = "Phase 4 Task 4 Test"
    draft = "This is a test email sent from the Inboxio agent."
    
    if not user.gmail_send_scope_granted:
        print("ERROR: User has not granted the send scope.")
        print("Please hit http://127.0.0.1:8000/gmail/oauth/connect/send in your browser, grant the permission, and try again.")
        sys.exit(1)
        
    try:
        result = send_email(user.id, recipient, subject, draft, db)
        print("SUCCESS:", result)
        
        # Verify log
        logs = db.query(EmailSendLog).filter(EmailSendLog.user_id == user.id).order_by(EmailSendLog.created_at.desc()).first()
        print(f"Latest DB Log Status: {logs.status}")
        
    except Exception as e:
        print(f"FAILED: {e}")
        logs = db.query(EmailSendLog).filter(EmailSendLog.user_id == user.id).order_by(EmailSendLog.created_at.desc()).first()
        if logs:
            print(f"Latest DB Log Status: {logs.status}, Error: {logs.error_message}")
        
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_task4.py <your_email>")
        sys.exit(1)
    main(sys.argv[1])
