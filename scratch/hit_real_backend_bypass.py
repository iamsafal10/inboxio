import requests
import time
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import create_access_token
from datetime import timedelta

print("1. Creating token...")
with SessionLocal() as db:
    user = db.query(User).filter(User.email == "one@gmail.com").first()
    
    access_token_expires = timedelta(minutes=60 * 24)
    token = create_access_token(subject=str(user.id), expires_delta=access_token_expires)

print("2. Sending chat query...")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
payload = {"message": "What recent job opportunities did I receive?"}

start_time = time.time()
try:
    chat_res = requests.post("http://127.0.0.1:8000/chat", headers=headers, json=payload)
    print(f"Status Code: {chat_res.status_code}")
    print(f"Response Body: {chat_res.text}")
    print(f"Time Taken: {time.time() - start_time:.2f}s")
except Exception as e:
    print(f"Exception during request: {e}")

