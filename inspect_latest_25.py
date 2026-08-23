import os
import sys
from app.core.database import SessionLocal
from app.models.user import User
from app.services.gmail_fetcher import fetch_recent_emails
from app.services.domain_filter import is_career_related

def main():
    db = SessionLocal()
    user = db.query(User).first()
    if not user:
        print("No user")
        sys.exit(1)
        
    print(f"User: {user.email}")
    
    try:
        emails = fetch_recent_emails(user.id, max_results=25)
        print(f"Fetched {len(emails)} emails")
    except Exception as e:
        print(f"Error fetching: {e}")
        sys.exit(1)
        
    career_emails = []
    for e in emails:
        if is_career_related(e.get('subject', ''), e.get('sender', ''), e.get('snippet', '')):
            career_emails.append(e)
            
    print(f"Career related: {len(career_emails)} emails")
    
    for idx, e in enumerate(career_emails):
        print(f"{idx+1}. From: {e['sender']}, Subject: {e['subject']}")
        print(f"   Snippet: {e['snippet'][:150]}...\n")

if __name__ == "__main__":
    main()
