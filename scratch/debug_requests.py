import os
import requests

from app.core.database import SessionLocal
from app.models.user import User
from app.services.gmail_sender import _get_user_credentials

def main():
    db = SessionLocal()
    user = db.query(User).filter(User.email == "one@gmail.com").first()
    creds = _get_user_credentials(user)
    
    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Accept": "application/json"
    }
    
    url = "https://gmail.googleapis.com/gmail/v1/users/me/labels"
    print(f"Making direct requests.get to {url}")
    try:
        response = requests.get(url, headers=headers, timeout=5)
        print(f"Status: {response.status_code}")
        print(response.json())
    except Exception as e:
        print(f"requests.get FAILED with exception: {e}")

if __name__ == "__main__":
    main()
