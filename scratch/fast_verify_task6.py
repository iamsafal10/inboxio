import sys
import httpx
from app.core.database import SessionLocal
from app.models.user import User
from app.models.cold_email_draft import ColdEmailDraft
from app.services.critique import self_critique
from app.core.security import create_access_token

def main():
    email = "one@gmail.com"
    base_url = "http://127.0.0.1:8000"
    
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        print("User not found.")
        sys.exit(1)
        
    token = create_access_token(subject=user.id)
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n--- 1. Planted False Claim & Critique ---")
    draft_body = (
        "Hi SpaceX Team,\n\n"
        "I'm reaching out because I saw the opening for a Senior Backend Engineer. "
        "I also have 10 years of experience as a NASA astronaut, so I'm well prepared for space! "
        "Looking forward to connecting.\n\nBest,\nS."
    )
    # The user has NO profile chunks about being an astronaut.
    chunks = ["Software Engineer at Acme Corp. 2 years of experience building Python APIs."]
    
    print("[DRAFT BODY]")
    print(draft_body)
    
    print("\nRunning self-critique...")
    flags = self_critique(draft_body, chunks)
    
    print("\n[CRITIQUE FLAGS DETECTED]")
    if flags:
        for idx, flag in enumerate(flags):
            print(f"  Flag {idx+1}:")
            print(f"    Claim in Draft: {flag.get('claim')}")
            print(f"    Profile Truth:  {flag.get('truth')}")
    else:
        print("  No flags detected. (Something is wrong!)")
        
    # 2. Save Draft
    draft = ColdEmailDraft(
        user_id=user.id,
        target_context="Applying to SpaceX",
        original_body=draft_body,
        flags=flags,
        status="DRAFTED"
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    
    print("\n--- 2. Attempting to Send WITHOUT Acknowledging Flags ---")
    bypass_res = httpx.post(f"{base_url}/cold_email/api/send/{draft.id}", headers=headers, json={
        "acknowledge_flags": False
    })
    print(f"Response Status: {bypass_res.status_code}")
    print(f"Response Body: {bypass_res.text}")
    if bypass_res.status_code == 400:
        print("=> SUCCESS: Approval gate blocked the one-click send.")
    else:
        print("=> FAILURE: Approval gate bypassed!")

if __name__ == "__main__":
    main()
