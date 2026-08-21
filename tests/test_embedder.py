"""Tests for embedding pipeline into ChromaDB."""

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.models.chunk import Chunk
from app.models.email_indexed import EmailIndexed
from app.services.embedder import process_unembedded_chunks, embed_and_store_batch

class TestEmbedder(unittest.TestCase):
    @patch('app.services.embedder.get_embedding_function')
    @patch('app.services.embedder.chroma_client')
    def test_process_unembedded_chunks(self, mock_chroma_client, mock_get_embedding):
        """Test batching, per-user collection naming, and metadata formatting."""
        
        mock_collection = MagicMock()
        mock_chroma_client.get_or_create_collection.return_value = mock_collection
        mock_get_embedding.return_value = MagicMock()
        
        mock_db = MagicMock()
        
        # Create 3 chunks
        chunks = [
            Chunk(
                id=f"c{i}", 
                text=f"text {i}", 
                gmail_message_id=f"msg{i}", 
                gmail_thread_id="t1", 
                sender="foo", 
                subject=None,
                sent_at=datetime(2026, 8, 21, tzinfo=timezone.utc),
                chunk_index=i,
                status="chunked"
            ) for i in range(3)
        ]
        
        # Setup mock db query
        mock_query = mock_db.query.return_value
        mock_join = mock_query.join.return_value
        mock_filter = mock_join.filter.return_value
        mock_filter.all.return_value = chunks
        
        # Run with batch size 2, so it processes 2 batches
        total = process_unembedded_chunks("user-123", mock_db, batch_size=2)
        
        self.assertEqual(total, 3)
        self.assertEqual(chunks[0].status, "embedded")
        
        # Collection name should be sanitized and per-user
        mock_chroma_client.get_or_create_collection.assert_called_with(
            name="inboxio_user_user_123",
            embedding_function=mock_get_embedding.return_value
        )
        
        # Should be called twice due to batch_size 2
        self.assertEqual(mock_collection.add.call_count, 2)
        
        # Check first batch metadata
        first_call = mock_collection.add.call_args_list[0]
        self.assertEqual(first_call.kwargs['ids'], ['c0', 'c1'])
        self.assertEqual(first_call.kwargs['documents'], ['text 0', 'text 1'])
        self.assertEqual(first_call.kwargs['metadatas'][0]['gmail_message_id'], 'msg0')
        self.assertEqual(first_call.kwargs['metadatas'][0]['subject'], '') # None converted to ""

    @patch('app.services.embedder.time.sleep')
    def test_exponential_backoff(self, mock_sleep):
        """Test the backoff retry wrapper on transient errors."""
        mock_collection = MagicMock()
        mock_collection.add.side_effect = [Exception("Transient DB Error"), Exception("Timeout"), None]
        
        chunk = Chunk(
            id="c1", text="hello", gmail_message_id="1", gmail_thread_id="1", 
            sender="a", subject="a", sent_at=datetime(2026, 8, 21, tzinfo=timezone.utc), chunk_index=0
        )
        
        embed_and_store_batch(mock_collection, [chunk])
        
        # Should have called add 3 times (failed twice, succeeded third time)
        self.assertEqual(mock_collection.add.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

if __name__ == '__main__':
    unittest.main()
