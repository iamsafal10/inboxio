import pytest
from unittest.mock import patch, MagicMock
from app.services.cold_email import draft_cold_email, DRAFT_EMAIL_PROMPT


def _mock_llm(subject="Backend Intern application", body="Hello, this is a draft."):
    """LLM mock whose structured-output path returns a subject + body."""
    mock_llm = MagicMock()
    structured = MagicMock()
    structured.invoke.return_value = MagicMock(subject=subject, body=body)
    mock_llm.with_structured_output.return_value = structured
    return mock_llm, structured


@patch("app.services.cold_email.get_profile_collection")
@patch("app.services.cold_email.get_llm")
def test_draft_cold_email_success(mock_get_llm, mock_get_collection):
    mock_llm, structured = _mock_llm()
    mock_get_llm.return_value = mock_llm

    # Mock Chroma
    mock_collection = MagicMock()
    mock_collection.get.return_value = {"documents": ["I write short emails."]}
    mock_collection.query.return_value = {"documents": [["I am a backend engineer.", "I know Python."]]}
    mock_get_collection.return_value = mock_collection

    result = draft_cold_email(
        "user-123",
        role_specialization="Backend Engineering Intern",
        recipient_email="hr@stripe.com",
        company="Stripe",
        target_context="Applying for Stripe",
    )

    # Verify isolation (user_id passed correctly)
    mock_get_collection.assert_called_once_with("user-123")

    # Verify response
    assert result["draft_text"] == "Hello, this is a draft."
    assert result["subject"] == "Backend Intern application"
    assert "I write short emails." in result["used_chunks"]
    assert "I am a backend engineer." in result["used_chunks"]

    # Verify prompt construction carries recipient, role and profile facts
    called_prompt = structured.invoke.call_args[0][0]
    assert "hr@stripe.com" in called_prompt
    assert "Backend Engineering Intern" in called_prompt
    assert "Stripe" in called_prompt
    assert "Applying for Stripe" in called_prompt
    assert "I am a backend engineer." in called_prompt
    assert "I write short emails." in called_prompt


@patch("app.services.cold_email.get_profile_collection")
@patch("app.services.cold_email.get_llm")
def test_draft_cold_email_retrieval_query_uses_role(mock_get_llm, mock_get_collection):
    """The profile search must be driven by the role, not just free text."""
    mock_llm, _ = _mock_llm()
    mock_get_llm.return_value = mock_llm

    mock_collection = MagicMock()
    mock_collection.get.return_value = {"documents": ["sample"]}
    mock_collection.query.return_value = {"documents": [["fact"]]}
    mock_get_collection.return_value = mock_collection

    draft_cold_email("user-123", role_specialization="Machine Learning Intern", company="Vertex")

    query_texts = mock_collection.query.call_args.kwargs["query_texts"][0]
    assert "Machine Learning Intern" in query_texts
    assert "Vertex" in query_texts


@patch("app.services.cold_email.get_profile_collection")
@patch("app.services.cold_email.get_llm")
def test_draft_cold_email_anti_fabrication(mock_get_llm, mock_get_collection):
    """Thin-but-present profile still gets the anti-fabrication instructions."""
    mock_llm, structured = _mock_llm(body="Draft.")
    mock_get_llm.return_value = mock_llm

    mock_collection = MagicMock()
    mock_collection.get.return_value = {"documents": ["I write short emails."]}
    mock_collection.query.return_value = {}
    mock_get_collection.return_value = mock_collection

    draft_cold_email("user-123", role_specialization="Thin profile test")

    called_prompt = structured.invoke.call_args[0][0]

    # Validate the core anti-fabrication instructions are in the prompt
    assert "DO NOT invent skills, jobs, experience" in called_prompt
    assert "No resume facts found." in called_prompt


@patch("app.services.cold_email.get_profile_collection")
@patch("app.services.cold_email.get_llm")
def test_draft_cold_email_requires_profile(mock_get_llm, mock_get_collection):
    """With no profile content at all, drafting fails loudly instead of inventing one."""
    mock_llm, _ = _mock_llm()
    mock_get_llm.return_value = mock_llm

    mock_collection = MagicMock()
    mock_collection.get.return_value = {}
    mock_collection.query.return_value = {}
    mock_get_collection.return_value = mock_collection

    with pytest.raises(ValueError, match="No profile content"):
        draft_cold_email("user-123", role_specialization="Backend Intern")


@patch("app.services.cold_email.get_profile_collection")
@patch("app.services.cold_email.get_llm")
def test_draft_cold_email_falls_back_when_structured_output_fails(mock_get_llm, mock_get_collection):
    """Weaker models can fail structured output; the draft must still come back."""
    mock_llm = MagicMock()
    mock_llm.with_structured_output.side_effect = RuntimeError("no tool support")
    mock_llm.invoke.return_value = MagicMock(content="Plain draft body.")
    mock_get_llm.return_value = mock_llm

    mock_collection = MagicMock()
    mock_collection.get.return_value = {"documents": ["sample"]}
    mock_collection.query.return_value = {"documents": [["fact"]]}
    mock_get_collection.return_value = mock_collection

    result = draft_cold_email("user-123", role_specialization="Backend Intern", company="Acme")

    assert result["draft_text"] == "Plain draft body."
    assert "Backend Intern" in result["subject"]
