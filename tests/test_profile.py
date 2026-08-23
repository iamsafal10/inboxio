import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import uuid

from app.main import app
from app.models.user import User
from app.models.profile import Profile
from app.core.database import SessionLocal
from app.core.security import create_access_token
from app.services.profile_embedder import get_profile_collection

client = TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.rollback()
    db.close()

@pytest.fixture
def auth_header(db_session: Session):
    unique_email = f"profile_test_{uuid.uuid4()}@example.com"
    user = User(email=unique_email, hashed_password="fake")
    db_session.add(user)
    db_session.commit()
    token = create_access_token(subject=user.id)
    return {"Authorization": f"Bearer {token}"}, user.id

def test_get_profile_ui():
    response = client.get("/profile/ui")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Your Inboxio Profile" in response.text

def test_profile_empty_by_default(auth_header):
    headers, user_id = auth_header
    res = client.get("/api/profile", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["resume_text"] == ""
    assert data["career_info"] == ""
    assert data["writing_style_samples"] == ""

def test_save_and_embed_profile(auth_header, db_session: Session):
    headers, user_id = auth_header
    
    payload = {
        "resume_text": "Senior Backend Developer at TechCorp.",
        "career_info": "Looking for remote staff-level roles.",
        "writing_style_samples": "Hi there,\n\nI wanted to reach out regarding..."
    }
    
    res = client.post("/api/profile", headers=headers, json=payload)
    assert res.status_code == 200
    assert res.json()["status"] == "success"
    
    # 1. Check DB
    profile = db_session.query(Profile).filter(Profile.user_id == user_id).first()
    assert profile is not None
    assert profile.resume_text == payload["resume_text"]
    assert profile.career_info == payload["career_info"]
    
    # 2. Check Vector DB
    collection = get_profile_collection(user_id)
    embedded_data = collection.get()
    
    assert len(embedded_data["ids"]) > 0
    # There should be at least one chunk for each field
    field_types = set([meta["field"] for meta in embedded_data["metadatas"]])
    assert "resume" in field_types
    assert "career_info" in field_types
    assert "writing_samples" in field_types

def test_profile_isolation(auth_header, db_session: Session):
    headers_a, user_a_id = auth_header
    
    unique_email_b = f"profile_test_b_{uuid.uuid4()}@example.com"
    user_b = User(email=unique_email_b, hashed_password="fake")
    db_session.add(user_b)
    db_session.commit()
    token_b = create_access_token(subject=user_b.id)
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
    # User A saves profile
    client.post("/api/profile", headers=headers_a, json={"resume_text": "Resume A"})
    
    # User B saves profile
    client.post("/api/profile", headers=headers_b, json={"resume_text": "Resume B"})
    
    # Verify User A's collection doesn't have User B's data
    collection_a = get_profile_collection(user_a_id)
    data_a = collection_a.get()
    for doc in data_a["documents"]:
        assert "Resume B" not in doc
        assert "Resume A" in doc
        
    # Verify User B gets only their data
    res = client.get("/api/profile", headers=headers_b)
    assert res.json()["resume_text"] == "Resume B"
