import pytest
from unittest.mock import patch, MagicMock
from app.services.critique import self_critique

@patch("app.services.critique.get_llm")
def test_critique_catches_false_claim(mock_get_llm):
    mock_llm = MagicMock()
    # Mock LLM correctly returning a JSON list with a flag
    mock_llm.invoke.return_value = MagicMock(content='[{"claim": "I have 5 years of Python experience", "truth": "Profile says 2 years"}]')
    mock_get_llm.return_value = mock_llm
    
    draft = "I have 5 years of Python experience."
    chunks = ["I have 2 years of Python experience."]
    
    flags = self_critique(draft, chunks)
    
    assert len(flags) == 1
    assert "5 years" in flags[0]["claim"]
    assert "2 years" in flags[0]["truth"]

@patch("app.services.critique.get_llm")
def test_critique_clean_draft(mock_get_llm):
    mock_llm = MagicMock()
    # Mock LLM returning empty list for a clean draft
    mock_llm.invoke.return_value = MagicMock(content="[]")
    mock_get_llm.return_value = mock_llm
    
    draft = "I have 2 years of Python experience."
    chunks = ["I have 2 years of Python experience."]
    
    flags = self_critique(draft, chunks)
    
    assert isinstance(flags, list)
    assert len(flags) == 0

@patch("app.services.critique.get_llm")
def test_critique_llm_failure_raises_error(mock_get_llm):
    mock_llm = MagicMock()
    # Mock LLM returning garbage instead of JSON
    mock_llm.invoke.return_value = MagicMock(content="This is just some text, not JSON.")
    mock_get_llm.return_value = mock_llm
    
    draft = "I have 2 years of Python experience."
    chunks = ["I have 2 years of Python experience."]
    
    # Must explicitly raise RuntimeError to prevent silent failure
    with pytest.raises(RuntimeError, match="Critique failed due to malformed LLM output"):
        self_critique(draft, chunks)

@patch("app.services.critique.get_llm")
def test_critique_llm_exception_raises_error(mock_get_llm):
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = Exception("API Timeout")
    mock_get_llm.return_value = mock_llm
    
    draft = "I have 2 years of Python experience."
    chunks = ["I have 2 years of Python experience."]
    
    with pytest.raises(RuntimeError, match="Critique failed due to LLM error"):
        self_critique(draft, chunks)
