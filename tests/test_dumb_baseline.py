"""Tests for the dumb baseline RAG agent."""

import unittest
from unittest.mock import MagicMock, patch

from app.baseline.dumb_baseline import answer_question_baseline, format_chunks_for_prompt

class TestDumbBaseline(unittest.TestCase):
    def test_format_chunks_for_prompt(self):
        chunks = [{
            "text": "Hello world",
            "metadata": {"sender": "Alice", "subject": "Test", "sent_at": "2026"}
        }]
        formatted = format_chunks_for_prompt(chunks)
        self.assertIn("From: Alice", formatted)
        self.assertIn("Hello world", formatted)

    @patch('app.baseline.dumb_baseline.get_llm')
    @patch('app.baseline.dumb_baseline.search_emails')
    def test_answer_question_baseline(self, mock_search, mock_get_llm):
        """Test search is called EXACTLY ONCE and LLM gets stuffed prompt."""
        
        # Mock search return
        mock_chunks = [{"text": "chunk1", "metadata": {}}]
        mock_search.return_value = mock_chunks
        
        # Mock LLM instance and invoke
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Mocked answer"
        mock_llm_instance.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm_instance
        
        result = answer_question_baseline("user-123", "What is the status?")
        
        # VERIFY: Search tool called exactly once (The "Dumb" constraint)
        self.assertEqual(mock_search.call_count, 1)
        mock_search.assert_called_with(user_id="user-123", query="What is the status?", top_k=5)
        
        # VERIFY: LLM called exactly once
        self.assertEqual(mock_llm_instance.invoke.call_count, 1)
        
        # VERIFY: Output contains answer and raw chunks
        self.assertEqual(result["answer"], "Mocked answer")
        self.assertEqual(result["chunks_used"], mock_chunks)
        self.assertEqual(result["question"], "What is the status?")
        
        # VERIFY: Prompt contains the question and context
        prompt_val = mock_llm_instance.invoke.call_args[0][0]
        prompt_text = prompt_val.to_string()
        self.assertIn("What is the status?", prompt_text)
        self.assertIn("chunk1", prompt_text)

if __name__ == '__main__':
    unittest.main()
