import uvicorn
from app.main import app
import threading
import time
import requests

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")

thread = threading.Thread(target=run_server, daemon=True)
thread.start()

time.sleep(3)

from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import create_access_token
from datetime import timedelta

with SessionLocal() as db:
    user = db.query(User).filter(User.email == "one@gmail.com").first()
    access_token_expires = timedelta(minutes=60 * 24)
    token = create_access_token(subject=str(user.id), expires_delta=access_token_expires)

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
payload = {"message": "What recent job opportunities did I receive?"}

print("=== SENDING POST TO 8001 ===")
chat_res = requests.post("http://127.0.0.1:8001/chat", headers=headers, json=payload)
print(f"Status Code: {chat_res.status_code}")
print(f"Response: {chat_res.text}")
