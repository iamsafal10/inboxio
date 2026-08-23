import sys
import httpx

from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import create_access_token

def main():
    email = "one@gmail.com"
    base_url = "http://127.0.0.1:8000"
    
    # Get token by minting it directly to bypass password requirement
    print(f"Logging in as {email}...")
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        print(f"User {email} not found in DB!")
        sys.exit(1)
        
    token = create_access_token(subject=user.id)
    headers = {"Authorization": f"Bearer {token}"}
    db.close()
        
    print("\n--- 1. Requesting Cold Email Draft ---")
    draft_req = {"target_context": "Reaching out to SpaceX for an engineering role."}
    try:
        draft_res = httpx.post(f"{base_url}/cold_email/api/draft", headers=headers, json=draft_req, timeout=300.0)
        draft_res.raise_for_status()
        data = draft_res.json()
        draft_id = data["draft_id"]
        
        print("\n[GENERATED DRAFT]")
        print(data["draft"])
        
        print("\n[CRITIQUE FLAGS DETECTED]")
        if data["flags"]:
            for idx, flag in enumerate(data["flags"]):
                print(f"  Flag {idx+1}:")
                print(f"    Claim in Draft: {flag.get('draft_claim')}")
                print(f"    Profile Truth:  {flag.get('profile_truth')}")
        else:
            print("  No flags detected. (Something is wrong, we planted a false claim!)")
            
    except Exception as e:
        print(f"Failed to generate draft: {e}")
        sys.exit(1)
        
    print("\n--- 2. Attempting to Send WITHOUT Acknowledging Flags ---")
    try:
        bypass_res = httpx.post(f"{base_url}/cold_email/api/send/{draft_id}", headers=headers, json={
            "acknowledge_flags": False
        }, timeout=30.0)
        
        print(f"Response Status: {bypass_res.status_code}")
        print(f"Response Body: {bypass_res.text}")
        if bypass_res.status_code == 400:
            print("=> SUCCESS: Approval gate blocked the send.")
        else:
            print("=> FAILURE: Approval gate did not block the send!")
    except Exception as e:
        print(f"Failed during send attempt: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
