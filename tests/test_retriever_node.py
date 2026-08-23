import unittest
from unittest.mock import patch

from app.agent.nodes import retriever_node
from app.agent.state import AgentState

class TestRetrieverNode(unittest.TestCase):
    @patch("app.agent.nodes.search_by_sender")
    @patch("app.agent.nodes.reconstruct_thread")
    @patch("app.agent.nodes.search_by_date_range")
    @patch("app.agent.nodes.search_emails")
    def test_retriever_node_execution(self, mock_search_emails, mock_search_date, mock_reconstruct, mock_search_sender):
        """Test that retriever_node correctly calls tools and deduplicates results."""
        
        # Setup mocks
        mock_search_sender.return_value = [
            {"text": "Email 1", "metadata": {"gmail_message_id": "msg1", "chunk_index": 0}}
        ]
        mock_reconstruct.return_value = [
            {"text": "Email 1", "metadata": {"gmail_message_id": "msg1", "chunk_index": 0}}, # Duplicate
            {"text": "Email 2", "metadata": {"gmail_message_id": "msg2", "chunk_index": 0}}
        ]
        mock_search_date.return_value = []
        mock_search_emails.return_value = [
            {"text": "Email 3", "metadata": {"gmail_message_id": "msg3", "chunk_index": 0}}
        ]
        
        state = AgentState(
            user_id="test_user",
            question="",
            sub_goals=[],
            tool_calls=[
                {"tool_name": "search_by_sender", "query": "John"},
                {"tool_name": "reconstruct_thread", "query": "thread1"},
                {"tool_name": "semantic_search", "query": "something"}
            ],
            retrieved_chunks=[],
            conflicts_detected=[],
            check_status="",
            final_answer=None,
            citations=[],
            chat_history=[],
            long_term_facts=[]
        )
        
        result_state = retriever_node(state)
        
        # Verify calls
        mock_search_sender.assert_called_once_with("test_user", "John")
        mock_reconstruct.assert_called_once_with("test_user", "thread1")
        mock_search_emails.assert_called_once_with("test_user", "something")
        
        # Verify deduplication: msg1_0, msg2_0, msg3_0 should result in 3 chunks, not 4
        chunks = result_state["retrieved_chunks"]
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0]["text"], "Email 1")
        self.assertEqual(chunks[1]["text"], "Email 2")
        self.assertEqual(chunks[2]["text"], "Email 3")

if __name__ == "__main__":
    unittest.main()
