"""End-to-End integration test covering the Phase 0 + Phase 1 pipeline."""

import unittest
import tempfile
import uuid
import shutil
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

import chromadb
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.user import User
from app.models.email_indexed import EmailIndexed
from app.models.chunk import Chunk

import app.services.embedder
import app.services.semantic_search
from app.services.email_chunker import process_email_chunks
from app.services.embedder import process_unembedded_chunks
from app.services.semantic_search import search_emails
from app.baseline.dumb_baseline import answer_question_baseline

class TestIntegrationE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 1. Setup in-memory SQLite for isolated DB
        cls.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        cls.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)
        
        # 2. Setup temporary Chroma DB
        cls.temp_chroma_dir = tempfile.mkdtemp()
        cls.test_chroma_client = chromadb.PersistentClient(path=cls.temp_chroma_dir)
        
        # Override the global Chroma clients
        app.services.embedder.chroma_client = cls.test_chroma_client
        app.services.semantic_search.chroma_client = cls.test_chroma_client
        
        # Shared user IDs across sequential test steps
        cls.user1_id = str(uuid.uuid4())
        cls.user2_id = str(uuid.uuid4())

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=cls.engine)
        cls.engine.dispose()
        shutil.rmtree(cls.temp_chroma_dir)

    def setUp(self):
        self.db = self.TestingSessionLocal()

    def tearDown(self):
        self.db.close()

    def test_01_user_signup_and_gmail_connect(self):
        """Test Case 1: New user signs up, logs in, gets JWT, connects Gmail."""
        user1 = User(id=self.user1_id, email="u1@test.com", gmail_connected=True, hashed_password="fake")
        user2 = User(id=self.user2_id, email="u2@test.com", gmail_connected=True, hashed_password="fake")
        self.db.add_all([user1, user2])
        self.db.commit()
        
        u1 = self.db.query(User).filter(User.id == self.user1_id).first()
        self.assertTrue(u1.gmail_connected)

    def test_02_fetch_and_chunk(self):
        """Test Case 2: Fetch -> chunk runs against a small fixture set of sample emails."""
        now = datetime.now(timezone.utc)
        e1 = EmailIndexed(id=str(uuid.uuid4()), user_id=self.user1_id, gmail_message_id="m1", gmail_thread_id="t1",
                          sender="boss@corp.com", recipient="u1@test.com", subject="Deadline", body="The project deadline is Friday.",
                          sent_at=now, status="fetched")
        e2 = EmailIndexed(id=str(uuid.uuid4()), user_id=self.user2_id, gmail_message_id="m2", gmail_thread_id="t2",
                          sender="secret@corp.com", recipient="u2@test.com", subject="User 2 Secret", body="The launch code is 1234.",
                          sent_at=now, status="fetched")
        self.db.add_all([e1, e2])
        self.db.commit()
        
        process_email_chunks(self.user1_id, self.db)
        process_email_chunks(self.user2_id, self.db)
        
        chunks = self.db.query(Chunk).join(EmailIndexed, Chunk.email_id == EmailIndexed.id).filter(EmailIndexed.user_id == self.user1_id).all()
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].status, "chunked")

    def test_03_embed_chunks(self):
        """Test Case 3: Chunks are successfully embedded into Chroma."""
        # Note: assumes test_02 already ran and populated chunks.
        process_unembedded_chunks(self.user1_id, self.db)
        process_unembedded_chunks(self.user2_id, self.db)
        
        chunks = self.db.query(Chunk).join(EmailIndexed, Chunk.email_id == EmailIndexed.id).filter(EmailIndexed.user_id == self.user1_id).all()
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].status, "embedded")

    def test_04_semantic_search(self):
        """Test Case 4: Semantic search against the fixture returns expected chunk."""
        res_u1 = search_emails(self.user1_id, "When is the deadline?", top_k=2)
        self.assertTrue(len(res_u1) > 0)
        self.assertIn("Friday", res_u1[0]["text"])

    @patch('app.baseline.dumb_baseline.get_llm')
    def test_05_baseline_agent(self, mock_get_llm):
        """Test Case 5: Dumb baseline returns answer using the correct retrieved chunks."""
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "The deadline is Friday."
        mock_llm_instance.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm_instance
        
        ans = answer_question_baseline(self.user1_id, "When is the deadline?")
        self.assertEqual(ans["answer"], "The deadline is Friday.")
        self.assertEqual(len(ans["chunks_used"]), 1)
        self.assertEqual(ans["chunks_used"][0]["text"], "The project deadline is Friday.")
        
        prompt_call = mock_llm_instance.invoke.call_args[0][0].to_string()
        self.assertIn("The project deadline is Friday.", prompt_call)

    def test_06_per_user_isolation(self):
        """Test Case 6: Second user's data never leaks into the first user's results."""
        res_leak = search_emails(self.user1_id, "launch code", top_k=2)
        for r in res_leak:
            self.assertNotIn("launch code is 1234", r["text"])
            
        res_u2 = search_emails(self.user2_id, "launch code", top_k=2)
        self.assertTrue(len(res_u2) > 0)
        self.assertIn("launch code is 1234", res_u2[0]["text"])

if __name__ == '__main__':
    unittest.main()
