import os
import json
import base64
from app.core.database import SessionLocal
from app.models.user import User
from app.services.gmail_fetcher import _get_user_credentials, execute_request, parse_message_payload
from googleapiclient.discovery import build
from app.services.domain_filter import is_career_related

with SessionLocal() as db:
    user = db.query(User).filter(User.email == "one@gmail.com").first()
    creds = _get_user_credentials(user)
    service = build('gmail', 'v1', credentials=creds)

    print("Querying Gmail API directly for 'honeywell'...")
    request = service.users().messages().list(userId='me', q='honeywell', maxResults=10)
    response = execute_request(request)
    
    messages = response.get('messages', [])
    print(f"Found {len(messages)} emails matching 'honeywell' in Gmail.")
    
    for i, msg_ref in enumerate(messages):
        msg_id = msg_ref['id']
        msg_request = service.users().messages().get(userId='me', id=msg_id, format='full')
        msg_payload = execute_request(msg_request)
        
        parsed = parse_message_payload(msg_payload)
        print(f"\n--- Email {i+1} ---")
        print(f"Subject: {parsed['subject']}")
        print(f"Sender: {parsed['sender']}")
        print(f"Date: {parsed['sent_at']}")
        
        # Check if domain filter would reject it
        would_pass = is_career_related(parsed['subject'], parsed['sender'], parsed['body'])
        print(f"Would pass career filter? {would_pass}")
        
        if not would_pass:
            print("REASON: Did not contain any career keywords.")
