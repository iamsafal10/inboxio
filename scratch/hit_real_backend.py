import requests
import json
import time

print("1. Logging in...")
login_res = requests.post(
    "http://127.0.0.1:8000/auth/login",
    json={"email": "one@gmail.com", "password": "password123"}
)
if login_res.status_code != 200:
    print(f"Login failed: {login_res.status_code} - {login_res.text}")
    exit(1)

token = login_res.json()["access_token"]
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

