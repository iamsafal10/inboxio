"""The 'dumb baseline' RAG agent for comparison against the real agent."""

import logging
from typing import Dict, Any, List
from langchain_core.prompts import PromptTemplate

from app.llm.llm_setup import get_llm

from app.services.semantic_search import search_emails
from app.core.config import settings

logger = logging.getLogger(__name__)

# Prompt for the baseline agent
BASELINE_PROMPT = PromptTemplate.from_template(
    """You are a helpful email assistant. Answer the user's question using ONLY the provided email excerpts.
If you cannot find the answer in the excerpts, clearly state that you do not have enough information.
Do not hallucinate or use outside knowledge.

Email Excerpts:
{context}

Question: {question}

Answer:"""
)

def format_chunks_for_prompt(chunks: List[Dict[str, Any]]) -> str:
    """Formats retrieved chunks into a single string for the prompt."""
    if not chunks:
        return "No emails found."
        
    formatted = []
    for i, c in enumerate(chunks, 1):
        meta = c["metadata"]
        text = c["text"]
        sender = meta.get("sender", "Unknown")
        date = meta.get("sent_at", "Unknown")
        subject = meta.get("subject", "No Subject")
        
        chunk_str = f"--- Excerpt {i} ---\nFrom: {sender}\nDate: {date}\nSubject: {subject}\nContent:\n{text}\n"
        formatted.append(chunk_str)
        
    return "\n".join(formatted)

def answer_question_baseline(user_id: str, question: str) -> Dict[str, Any]:
    """
    The naive baseline: one search call -> stuff into prompt -> return answer.
    """
    # 1. Single raw search call
    top_k = 5
    chunks = search_emails(user_id=user_id, query=question, top_k=top_k)
    
    # 2. Format context
    context_str = format_chunks_for_prompt(chunks)
    
    # 3. Call LLM
    try:
        llm = get_llm(temperature=0.0)
        prompt_val = BASELINE_PROMPT.invoke({"context": context_str, "question": question})
        response = llm.invoke(prompt_val)
        answer = response.content
    except Exception as e:
        logger.error(f"Baseline LLM call failed: {e}")
        answer = f"Error generating answer: {str(e)}"
        
    # 4. Return answer AND raw chunks for future comparison
    return {
        "question": question,
        "answer": answer,
        "chunks_used": chunks
    }
