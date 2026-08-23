import pytest
from app.agent.nodes import synthesizer_node

def test_synthesizer_context_length_handling():
    # If we pass 10,000 words of context to the synthesizer, it previously crashed
    # with a 413 TPM error from Groq. With context limiting, it should handle this gracefully
    # by truncating the evidence and returning a synthesized response.
    
    huge_context = "job opportunity " * 5000  # ~15,000 tokens
    
    # Mock some chunks to pass as retrieved_chunks
    state = {
        "messages": [],
        "question": "What job opportunities do I have?",
        "retrieved_chunks": [
            {"text": huge_context, "metadata": {"sender": "Test", "sent_at": "2023-01-01"}, "distance": 0.1}
        ],
        "is_career_related": True,
        "requires_tools": True,
        "tool_names": [],
        "user_id": "test_user_id"
    }
    
    result = synthesizer_node(state)
    
    # It should not return the fallback error string, it should synthesize properly.
    assert "I apologize, but I encountered an error" not in result.get("final_answer", "")
