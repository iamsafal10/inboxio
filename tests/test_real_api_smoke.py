import os
import pytest
from pydantic import BaseModel, Field

# Skip this entire module by default unless explicitly asked for,
# because it hits real external APIs.
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_REAL_API_TESTS") != "true",
    reason="Only run real API smoke tests when RUN_REAL_API_TESTS=true"
)

from app.llm.llm_setup import get_llm
from langchain_core.prompts import PromptTemplate

class SmokeOutput(BaseModel):
    is_success: bool = Field(description="Must be true if you can read this.")
    message: str = Field(description="A short greeting.")

def test_real_api_smoke():
    """
    Tests the Ox Alpha provider (or whichever is currently active)
    with a real structured output call to ensure compatibility.
    """
    llm = get_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(SmokeOutput)
    
    prompt = PromptTemplate.from_template("Say hello and confirm success.")
    chain = prompt | structured_llm
    
    result = chain.invoke({})
    
    assert hasattr(result, "is_success")
    assert result.is_success is True
    assert hasattr(result, "message")
    assert isinstance(result.message, str)

def test_real_api_smoke_tools():
    """
    Tests the Ox Alpha provider with a real tool calling call.
    """
    llm = get_llm(temperature=0.0)
    
    # Define a simple mock tool
    def get_weather(location: str) -> str:
        """Get the current weather in a given location."""
        return f"The weather in {location} is sunny."
        
    llm_with_tools = llm.bind_tools([get_weather])
    
    response = llm_with_tools.invoke("What is the weather in Paris?")
    
    # Assert tool call was made
    assert hasattr(response, "tool_calls")
    assert len(response.tool_calls) > 0
    assert response.tool_calls[0]["name"] == "get_weather"
    assert "location" in response.tool_calls[0]["args"]
