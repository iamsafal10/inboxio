"""Tests for semantic search retrieval logic."""

import unittest
from unittest.mock import MagicMock, patch

from app.services.semantic_search import search_emails

class TestSemanticSearch(unittest.TestCase):
    @patch('app.services.semantic_search.get_embedding_function')
    @patch('app.services.semantic_search.chroma_client')
    def test_search_emails_success(self, mock_chroma_client, mock_get_embedding):
        """Test search calls the right collection and returns formatted results."""
        mock_collection = MagicMock()
        mock_chroma_client.get_collection.return_value = mock_collection
        
        # Mock Chroma query response
        mock_collection.query.return_value = {
            "documents": [["chunk 1", "chunk 2"]],
            "metadatas": [[{"sender": "a"}, {"sender": "b"}]],
            "distances": [[0.1, 0.5]]
        }
        
        results = search_emails("user-123", "test query", top_k=2)
        
        # Verify collection isolation
        mock_chroma_client.get_collection.assert_called_with(
            name="inboxio_user_user_123",
            embedding_function=mock_get_embedding.return_value
        )
        
        # Verify query call
        mock_collection.query.assert_called_with(
            query_texts=["test query"],
            n_results=2
        )
        
        # Verify formatting
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["text"], "chunk 1")
        self.assertEqual(results[0]["metadata"]["sender"], "a")
        self.assertEqual(results[0]["distance"], 0.1)

    @patch('app.services.semantic_search.chroma_client')
    def test_search_emails_no_collection(self, mock_chroma_client):
        """Test search handles missing collection gracefully."""
        mock_chroma_client.get_collection.side_effect = Exception("Collection not found")
        
        results = search_emails("user-123", "test query", top_k=5)
        
        self.assertEqual(results, [])

    @patch('app.services.semantic_search.get_embedding_function')
    @patch('app.services.semantic_search.chroma_client')
    def test_search_emails_default_top_k(self, mock_chroma_client, mock_get_embedding):
        """Test search uses top_k=20 by default and retrieves all."""
        mock_collection = MagicMock()
        mock_chroma_client.get_collection.return_value = mock_collection
        
        # Mock Chroma query returning 6 results (beyond the old limit of 5)
        docs = [f"chunk {i}" for i in range(6)]
        metas = [{"sender": f"s{i}"} for i in range(6)]
        distances = [0.1 * i for i in range(6)]
        
        mock_collection.query.return_value = {
            "documents": [docs],
            "metadatas": [metas],
            "distances": [distances]
        }
        
        results = search_emails("user-123", "test query")
        
        # Verify query call uses default top_k=20
        mock_collection.query.assert_called_with(
            query_texts=["test query"],
            n_results=20
        )
        
        # Verify all 6 items were returned (beyond rank 5)
        self.assertEqual(len(results), 6)

if __name__ == '__main__':
    unittest.main()
