import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import uuid
from unittest.mock import patch

from app.main import app
from app.models.user import User
from app.models.cold_email_draft import ColdEmailDraft
from app.core.database import SessionLocal
from app.core.security import create_access_token

client = TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.rollback()
    db.close()

@pytest.fixture
def auth_header(db_session: Session):
    unique_email = f"gate_test_{uuid.uuid4()}@example.com"
    user = User(email=unique_email, hashed_password="fake")
    db_session.add(user)
    db_session.commit()
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}, user

def test_api_send_without_draft_fails(auth_header):
    headers, _ = auth_header
    res = client.post("/cold_email/api/send/invalid-id", headers=headers, json={"acknowledge_flags": False})
    assert res.status_code == 404

@patch("app.routers.cold_email.send_email")
def test_api_send_unflagged_draft_succeeds(mock_send, db_session: Session, auth_header):
    headers, user = auth_header
    mock_send.return_value = {"status": "SUCCESS"}
    
    draft = ColdEmailDraft(
        user_id=user.id,
        target_context="Target",
        original_body="Body",
        flags=[],
        status="DRAFTED"
    )
    db_session.add(draft)
    db_session.commit()
    
    res = client.post(f"/cold_email/api/send/{draft.id}", headers=headers, json={
        "acknowledge_flags": False
    })
    
    assert res.status_code == 200
    assert res.json()["status"] == "SUCCESS"
    
    db_session.refresh(draft)
    assert draft.status == "SENT"

@patch("app.routers.cold_email.send_email")
def test_api_send_flagged_draft_bypassed_fails(mock_send, db_session: Session, auth_header):
    headers, user = auth_header
    
    draft = ColdEmailDraft(
        user_id=user.id,
        target_context="Target",
        original_body="Body",
        flags=[{"draft_claim": "X", "profile_truth": "Y"}],
        status="DRAFTED"
    )
    db_session.add(draft)
    db_session.commit()
    
    # Try sending without acknowledging flags
    res = client.post(f"/cold_email/api/send/{draft.id}", headers=headers, json={
        "acknowledge_flags": False
    })
    
    assert res.status_code == 400
    assert "must explicitly acknowledge them" in res.json()["detail"]
    assert mock_send.call_count == 0

@patch("app.routers.cold_email.send_email")
def test_api_send_flagged_draft_acknowledged_succeeds(mock_send, db_session: Session, auth_header):
    headers, user = auth_header
    mock_send.return_value = {"status": "SUCCESS"}
    
    draft = ColdEmailDraft(
        user_id=user.id,
        target_context="Target",
        original_body="Body",
        flags=[{"draft_claim": "X", "profile_truth": "Y"}],
        status="DRAFTED"
    )
    db_session.add(draft)
    db_session.commit()
    
    # Try sending WITH acknowledging flags
    res = client.post(f"/cold_email/api/send/{draft.id}", headers=headers, json={
        "acknowledge_flags": True,
        "edited_body": "Fixed Body"
    })
    
    assert res.status_code == 200
    assert mock_send.call_count == 1
    
    # Check what was passed to send_email
    call_kwargs = mock_send.call_args[1]
    assert call_kwargs["draft"] == "Fixed Body"
