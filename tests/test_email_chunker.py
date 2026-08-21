"""Tests for email chunking logic."""

import unittest
from datetime import datetime
from unittest.mock import MagicMock

from app.services.email_chunker import split_text_into_chunks, process_email_chunks
from app.models.email_indexed import EmailIndexed

class TestEmailChunker(unittest.TestCase):
    def test_split_text_short(self):
        """Short emails shouldn't be split."""
        text = "Hello\n\nWorld"
        chunks = split_text_into_chunks(text, max_length=100)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], "Hello\n\nWorld")

    def test_split_text_long(self):
        """Long emails should be split by paragraph."""
        p1 = "A" * 60
        p2 = "B" * 60
        text = f"{p1}\n\n{p2}"
        chunks = split_text_into_chunks(text, max_length=100)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0], p1)
        self.assertEqual(chunks[1], p2)
        
    def test_split_text_very_long_paragraph(self):
        """Paragraphs longer than max_length should be hard split."""
        text = "A" * 150
        chunks = split_text_into_chunks(text, max_length=100)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0], "A" * 100)
        self.assertEqual(chunks[1], "A" * 50)

    def test_process_email_chunks(self):
        """Verify chunk DB records and status transition."""
        mock_db = MagicMock()
        mock_email = EmailIndexed(
            id="e1", 
            user_id="u1", 
            gmail_message_id="msg1",
            gmail_thread_id="t1",
            sender="foo",
            subject="bar",
            sent_at=datetime.utcnow(),
            body="A" * 300,
            status="fetched"
        )
        mock_db.query().filter().all.return_value = [mock_email]
        
        import app.services.email_chunker
        app.services.email_chunker.settings.MAX_CHUNK_CHARS = 200
        
        total = process_email_chunks("u1", mock_db)
        
        self.assertEqual(total, 2)
        self.assertEqual(mock_db.add.call_count, 2)
        self.assertEqual(mock_email.status, "chunked")
        self.assertTrue(mock_db.commit.called)
        
        # Verify metadata
        added_chunk = mock_db.add.call_args_list[0][0][0]
        self.assertEqual(added_chunk.gmail_message_id, "msg1")
        self.assertEqual(added_chunk.chunk_index, 0)
        self.assertEqual(added_chunk.text, "A" * 200)
        self.assertEqual(added_chunk.status, "chunked")

if __name__ == '__main__':
    unittest.main()
