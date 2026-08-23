"""LLM Provider setup and instantiation module."""

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import settings

class OpenRouterChatModel(ChatOpenAI):
    def with_structured_output(self, schema, **kwargs):
        kwargs.setdefault("method", "function_calling")
        return super().with_structured_output(schema, **kwargs)

def get_llm(temperature: float = 0.0) -> BaseChatModel:
    """
    Returns an instantiated LangChain Chat Model based on LLM_PROVIDER.
    Supports: 'gemini', 'groq', 'openrouter_ox_alpha'
    """
    provider = settings.LLM_PROVIDER.lower()

    if provider == "groq":
        return ChatGroq(
            model="llama3-8b-8192",  # Default groq model, can be made configurable
            temperature=temperature,
            api_key=settings.GROQ_API_KEY or "dummy_key"
        )
    elif provider == "openrouter_ox_alpha":
        return OpenRouterChatModel(
            model="stealth/ox-alpha",
            temperature=temperature,
            api_key=settings.OPENROUTER_API_KEY or "dummy_key",
            base_url="https://openrouter.ai/api/v1"
        )
    else:
        # Default to gemini
        return ChatGoogleGenerativeAI(
            model="gemini-3.5-flash",
            temperature=temperature,
            google_api_key=settings.GEMINI_API_KEY or "dummy_key"
        )
