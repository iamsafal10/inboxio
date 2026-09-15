import traceback
from pydantic import BaseModel, Field
from app.llm.llm_setup import get_llm
from langchain_core.prompts import PromptTemplate

class TestOutput(BaseModel):
    summary: str = Field(description="A short summary")
    count: int = Field(description="A count")

try:
    print("Initializing LLM...")
    llm = get_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(TestOutput)
    prompt = PromptTemplate.from_template("Summarize the text: {text} and count the words.")
    chain = prompt | structured_llm
    
    print("Invoking chain...")
    result = chain.invoke({"text": "Hello world, this is a test of OpenRouter."})
    print("Result:", result)
except Exception as e:
    print(f"Exception caught: {e}")
    traceback.print_exc()
