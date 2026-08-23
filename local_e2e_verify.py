import os
import time
import requests

BASE_URL = "http://127.0.0.1:8000"
test_email = f"test_{int(time.time())}@example.com"
test_password = "password123"
token = None

def run_test():
    global token
    print("1. Testing UIs load...")
    for route in ["/chat-ui", "/profile/ui", "/cold_email/ui"]:
        r = requests.get(f"{BASE_URL}{route}")
        assert r.status_code == 200, f"{route} failed to load: {r.status_code}"
    print("✅ UIs load successfully")

    print("2. Testing Signup/Login...")
    r = requests.post(f"{BASE_URL}/auth/signup", json={"email": test_email, "password": test_password})
    assert r.status_code == 201, f"Signup failed: {r.text}"
    token = r.json()["access_token"]
    
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": test_email, "password": test_password})
    assert r.status_code == 200, f"Login failed: {r.text}"
    token = r.json()["access_token"]
    print("✅ Signup/Login works")

    print("3. Testing Gmail Connection URL...")
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{BASE_URL}/gmail/oauth/connect", headers=headers)
    assert r.status_code == 200, f"Gmail connect URL failed: {r.text}"
    assert "authorization_url" in r.json()
    print("✅ Gmail OAuth connect endpoint works")

    print("4. Testing Profile UI API...")
    profile_data = {
        "resume_text": "Backend Engineer",
        "career_info": "Looking for startup jobs",
        "writing_style_samples": "Hello world"
    }
    r = requests.post(f"{BASE_URL}/api/profile", headers=headers, json=profile_data)
    if r.status_code != 200:
        print(f"❌ Profile saving failed: {r.text}")
        return False
    print("✅ Profile API works")

    print("5. Testing Cold Email Draft API...")
    draft_req = {"target_context": "Hiring manager at OpenAI"}
    r = requests.post(f"{BASE_URL}/cold_email/api/draft", headers=headers, json=draft_req)
    if r.status_code != 200:
        print(f"❌ Cold Email draft failed: {r.text}")
        return False
    print("✅ Cold Email drafting works")

    print("6. Testing Chat API...")
    chat_req = {"message": "Summarize my recent emails"}
    r = requests.post(f"{BASE_URL}/chat", headers=headers, json=chat_req)
    if r.status_code != 200:
        print(f"❌ Chat failed: {r.text}")
        return False
    print("✅ Chat works")

    return True

if __name__ == "__main__":
    try:
        if run_test():
            print("ALL TESTS PASSED")
    except Exception as e:
        print(f"Exception: {str(e)}")

