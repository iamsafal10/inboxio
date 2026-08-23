import logging
import httplib2
httplib2.debuglevel = 4
logging.basicConfig(level=logging.DEBUG)
import os
from app.core.database import SessionLocal
from app.models.user import User
from app.services.gmail_sender import _get_user_credentials
from googleapiclient.discovery import build

db = SessionLocal()
user = db.query(User).filter(User.email == "one@gmail.com").first()
creds = _get_user_credentials(user)
print("Building service...")
service = build("gmail", "v1", credentials=creds)
print("Service built. Trying to list labels...")
labels = service.users().labels().list(userId="me").execute()
print(labels)
