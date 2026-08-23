import os
import sys
import logging
import httplib2

httplib2.debuglevel = 4
logging.basicConfig(level=logging.DEBUG)

from app.core.database import SessionLocal
from app.models.user import User
from app.services.gmail_sender import _get_user_credentials
from googleapiclient.discovery import build
import google_auth_httplib2

def main():
    db = SessionLocal()
    user = db.query(User).filter(User.email == "one@gmail.com").first()
    if not user:
        print("User not found.")
        sys.exit(1)

    creds = _get_user_credentials(user)
    
    # We can explicitly force a timeout on httplib2 to see if it hangs indefinitely
    http = httplib2.Http(timeout=5)
    
    # Wrap it in auth
    authed_http = google_auth_httplib2.AuthorizedHttp(creds, http=http)
    
    try:
        print(f"Credentials expired: {creds.expired}")
        print(f"Credentials valid: {creds.valid}")
        print(f"Has token: {bool(creds.token)}")
        print(f"Has refresh token: {bool(creds.refresh_token)}")

        print("Attempting to fetch Gmail discovery document...")
        service = build("gmail", "v1", http=authed_http)
        print("Discovery document fetched successfully.")
        
        print("Attempting to call labels API...")
        labels = service.users().labels().list(userId="me").execute()
        print("Labels API succeeded:")
        print(labels)
        
    except Exception as e:
        print(f"FAILED with exception: {e}")

if __name__ == "__main__":
    main()
