import unittest
from unittest.mock import patch

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from app.llm.llm_setup import get_llm, OpenRouterChatModel
from app.core.config import settings

class TestLLMSetup(unittest.TestCase):

    @patch('app.llm.llm_setup.settings')
    def test_get_llm_gemini(self, mock_settings):
        mock_settings.LLM_PROVIDER = 'gemini'
        mock_settings.GEMINI_API_KEY = 'test_gemini_key'
        llm = get_llm()
        self.assertIsInstance(llm, ChatGoogleGenerativeAI)
        self.assertEqual(llm.model, 'gemini-3.5-flash')

    @patch('app.llm.llm_setup.settings')
    def test_get_llm_groq(self, mock_settings):
        mock_settings.LLM_PROVIDER = 'groq'
        mock_settings.GROQ_API_KEY = 'test_groq_key'
        llm = get_llm()
        self.assertIsInstance(llm, ChatGroq)
        self.assertEqual(llm.model_name, 'openai/gpt-oss-120b')

    @patch('app.llm.llm_setup.settings')
    def test_get_llm_openrouter(self, mock_settings):
        mock_settings.LLM_PROVIDER = 'openrouter_ox_alpha'
        mock_settings.OPENROUTER_API_KEY = 'test_or_key'
        llm = get_llm()
        self.assertIsInstance(llm, OpenRouterChatModel)
        self.assertEqual(llm.model_name, 'stealth/ox-alpha')

if __name__ == '__main__':
    unittest.main()
