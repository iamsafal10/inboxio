import unittest
from unittest.mock import patch
import uuid

from app.services.retrieval_tools import (
    search_by_sender,
    reconstruct_thread,
    search_by_date_range
)
from app.services.semantic_search import search_emails

class TestZeroLLMCalls(unittest.TestCase):
    @patch("app.llm.llm_setup.get_llm")
    @patch("app.services.retrieval_tools.SessionLocal")
    def test_retrieval_tools_make_no_llm_calls(self, mock_session, mock_get_llm):
        """
        Ensures that none of the retrieval tools instantiate or call an LLM.
        They must remain deterministic and fast.
        """
        user_id = str(uuid.uuid4())
        
        # We don't care if they return empty lists (since DB is empty),
        # we only care that mock_get_llm is NEVER called.
        mock_session.return_value.__enter__.return_value = mock_session
        
        search_by_sender(user_id, "test_sender")
        self.assertEqual(mock_get_llm.call_count, 0)
        
        reconstruct_thread(user_id, "test_thread")
        self.assertEqual(mock_get_llm.call_count, 0)
        
        search_by_date_range(user_id, "2023-01-01", "2023-12-31")
        self.assertEqual(mock_get_llm.call_count, 0)
        
        # semantic_search uses Chroma which handles embeddings, but no LLM.
        search_emails(user_id, "test query")
        self.assertEqual(mock_get_llm.call_count, 0)
        
if __name__ == "__main__":
    unittest.main()
