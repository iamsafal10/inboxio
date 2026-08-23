import pytest
from unittest.mock import patch, MagicMock
from app.services.cold_email import draft_cold_email, DRAFT_EMAIL_PROMPT

@patch("app.services.cold_email.get_profile_collection")
@patch("app.services.cold_email.get_llm")
def test_draft_cold_email_success(mock_get_llm, mock_get_collection):
    # Mock LLM
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="Hello, this is a draft.")
    mock_get_llm.return_value = mock_llm
    
    # Mock Chroma
    mock_collection = MagicMock()
    mock_collection.get.return_value = {"documents": ["I write short emails."]}
    mock_collection.query.return_value = {"documents": [["I am a backend engineer.", "I know Python."]]}
    mock_get_collection.return_value = mock_collection
    
    result = draft_cold_email("user-123", "Applying for Stripe")
    
    # Verify isolation (user_id passed correctly)
    mock_get_collection.assert_called_once_with("user-123")
    
    # Verify response
    assert result["draft_text"] == "Hello, this is a draft."
    assert "I write short emails." in result["used_chunks"]
    assert "I am a backend engineer." in result["used_chunks"]
    
    # Verify prompt construction
    called_prompt = mock_llm.invoke.call_args[0][0]
    assert "Applying for Stripe" in called_prompt
    assert "I am a backend engineer." in called_prompt
    assert "I write short emails." in called_prompt

@patch("app.services.cold_email.get_profile_collection")
@patch("app.services.cold_email.get_llm")
def test_draft_cold_email_anti_fabrication(mock_get_llm, mock_get_collection):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="Draft.")
    mock_get_llm.return_value = mock_llm
    
    mock_collection = MagicMock()
    mock_collection.get.return_value = {}
    mock_collection.query.return_value = {}
    mock_get_collection.return_value = mock_collection
    
    draft_cold_email("user-123", "Thin profile test")
    
    called_prompt = mock_llm.invoke.call_args[0][0]
    
    # Validate the core anti-fabrication instructions are in the prompt
    assert "DO NOT invent skills, jobs, experience" in called_prompt
    assert "No resume facts found." in called_prompt
    assert "No writing samples found." in called_prompt
