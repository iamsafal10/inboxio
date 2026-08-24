import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import uuid

from app.main import app
from app.models.user import User
from app.core.database import SessionLocal
from app.services.profile_embedder import get_profile_collection

client = TestClient(app, raise_server_exceptions=True)

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.rollback()
    db.close()

@pytest.fixture
def test_user_and_token(db_session: Session):
    unique_email = f"e2e_proof_{uuid.uuid4()}@example.com"
    user = User(email=unique_email, hashed_password="hashed")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    from app.core.security import create_access_token
    token = create_access_token(subject=user.id)
    headers = {"Authorization": f"Bearer {token}"}
    return headers, user

def test_phase4_task6_e2e_proof(test_user_and_token, db_session: Session):
    """
    End-to-End proof that the self-critique catches a planted false claim 
    and the approval gate correctly blocks the send.
    """
    headers, user = test_user_and_token

    # 1. Setup real profile
    profile_payload = {
        "resume_text": "Software Engineer at Acme Corp. 2 years of experience building Python APIs.",
        "career_info": "Looking for backend engineering roles.",
        "writing_style_samples": "Hi, I'm reaching out because I saw the opening."
    }
    client.post("/profile/api/profile", headers=headers, json=profile_payload)

    # We want to run REAL draft creation, plant a fake claim, and run REAL critique.
    from app.services.cold_email import draft_cold_email as original_draft
    
    def mock_draft_with_planted_claim(*args, **kwargs):
        result = original_draft(*args, **kwargs)
        body = result["draft_text"] + "\n\nI also have 10 years of experience as a NASA astronaut."
        return {"draft_text": body, "used_chunks": result["used_chunks"]}

    with patch("app.routers.cold_email.draft_cold_email", side_effect=mock_draft_with_planted_claim):
        draft_req = {"target_context": "Reaching out to SpaceX for an engineering role."}
        draft_res = client.post("/cold_email/api/draft", headers=headers, json=draft_req)
        
        # Verify the endpoint returned 200 and critique actually caught it
        assert draft_res.status_code == 200, draft_res.text
        data = draft_res.json()
        
        # Ensure the false claim was planted
        assert "NASA astronaut" in data["body"]
        
        # Ensure self-critique caught it (flags array shouldn't be empty)
        assert data["flags"] is not None
        assert len(data["flags"]) > 0
        
        # Verify that at least one flag calls out the NASA claim
        found_nasa_flag = False
        for flag in data["flags"]:
            if "NASA" in flag.get("claim", "") or "NASA" in flag.get("truth", ""):
                found_nasa_flag = True
                break
        assert found_nasa_flag, f"Self-critique missed the planted NASA claim! Flags: {data['flags']}"
        
        draft_id = data["id"]

    # 2. Try to bypass the approval gate
    # Mock the actual Gmail send so we don't accidentally email anyone
    with patch("app.routers.cold_email.send_email") as mock_send:
        # Attempt 1: Hit send endpoint without acknowledging the flags
        bypass_res = client.post(f"/cold_email/api/send/{draft_id}", headers=headers, json={
            "acknowledge_flags": False
        })
        # Must be blocked
        assert bypass_res.status_code == 400
        assert "Draft contains unsupported claims" in bypass_res.json()["detail"]
        mock_send.assert_not_called()
        
        # Attempt 2: Explicitly acknowledge the flags (simulating the UI checkbox)
        mock_send.return_value = {"status": "SUCCESS", "message_id": "test_id"}
        success_res = client.post(f"/cold_email/api/send/{draft_id}", headers=headers, json={
            "acknowledge_flags": True
        })
        
        # Must succeed
        assert success_res.status_code == 200
        mock_send.assert_called_once()
