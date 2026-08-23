import requests

BASE_URL = "http://127.0.0.1:8000"
test_email = "test_send@example.com"
test_password = "password123"

requests.post(f"{BASE_URL}/auth/signup", json={"email": test_email, "password": test_password})
r = requests.post(f"{BASE_URL}/auth/login", json={"email": test_email, "password": test_password})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

profile_data = {"resume_text": "Backend Engineer", "career_info": "Looking for startup jobs", "writing_style_samples": "Hello world"}
requests.post(f"{BASE_URL}/api/profile", headers=headers, json=profile_data)

r = requests.post(f"{BASE_URL}/cold_email/api/draft", headers=headers, json={"target_context": "Hiring manager at OpenAI"})
data = r.json()
draft_id = data["id"]
has_flags = len(data.get("flags", [])) > 0

r2 = requests.post(f"{BASE_URL}/cold_email/api/send/{draft_id}", headers=headers, json={"edited_body": "This is a test email.", "acknowledge_flags": has_flags})
if r2.status_code == 200:
    print("Send API Success:", r2.json())
else:
    print("Send API Failed:", r2.status_code, r2.text)
