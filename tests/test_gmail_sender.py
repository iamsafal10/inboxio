import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.email_send_log import EmailSendLog
from app.services.gmail_sender import send_email
from app.core.database import SessionLocal
import uuid

@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
    db.rollback()
    db.close()

@pytest.fixture
def user(db_session: Session):
    unique_email = f"sender_test_{uuid.uuid4()}@example.com"
    u = User(email=unique_email, hashed_password="fake")
    db_session.add(u)
    db_session.commit()
    return u

def test_send_email_fails_without_scope(db_session: Session, user: User):
    user.gmail_send_scope_granted = False
    db_session.commit()
    
    with pytest.raises(RuntimeError, match="has not granted the Gmail send scope"):
        send_email(user.id, "test@example.com", "Subject", "Draft", db_session)
    
    # Verify no log was created because it failed before DB insertion
    logs = db_session.query(EmailSendLog).filter(EmailSendLog.user_id == user.id).all()
    assert len(logs) == 0

@patch("app.services.gmail_sender.build")
@patch("app.services.gmail_sender._get_user_credentials")
def test_send_email_success(mock_get_creds, mock_build, db_session: Session, user: User):
    user.gmail_send_scope_granted = True
    db_session.commit()
    
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.users().messages().send().execute.return_value = {"id": "msg-123"}
    
    result = send_email(user.id, "test@example.com", "Subject", "Draft text", db_session)
    
    assert result["status"] == "SUCCESS"
    assert result["message_id"] == "msg-123"
    
    # Verify log
    logs = db_session.query(EmailSendLog).filter(EmailSendLog.user_id == user.id).all()
    assert len(logs) == 1
    assert logs[0].status == "SUCCESS"
    assert logs[0].recipient == "test@example.com"
    assert logs[0].draft_reference == "Draft text"

@patch("app.services.gmail_sender.build")
@patch("app.services.gmail_sender._get_user_credentials")
def test_send_email_api_failure_is_logged(mock_get_creds, mock_build, db_session: Session, user: User):
    user.gmail_send_scope_granted = True
    db_session.commit()
    
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.users().messages().send().execute.side_effect = Exception("API Timeout")
    
    with pytest.raises(RuntimeError, match="Failed to send email"):
        send_email(user.id, "test@example.com", "Subject", "Draft text", db_session)
    
    # Verify log was created and marked as FAILED
    logs = db_session.query(EmailSendLog).filter(EmailSendLog.user_id == user.id).all()
    assert len(logs) == 1
    assert logs[0].status == "FAILED"
    assert logs[0].error_message == "API Timeout"
