"""Tests for Phase 2 retrieval tools and tool selector routing."""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.user import User
from app.models.email_indexed import EmailIndexed
from app.models.chunk import Chunk
from app.services.retrieval_tools import (
    search_by_sender,
    reconstruct_thread,
    search_by_date_range
)
from app.agent.nodes import tool_selector_node, ToolSelectionList, ToolCallOutput
from app.agent.state import AgentState

class TestRetrievalTools(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Setup in-memory SQLite for isolated DB
        cls.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        cls.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)
        
        cls.user1_id = str(uuid.uuid4())
        cls.user2_id = str(uuid.uuid4())
        
        # Populate fixture data
        db = cls.TestingSessionLocal()
        user1 = User(id=cls.user1_id, email="u1@test.com", gmail_connected=True, hashed_password="fake")
        user2 = User(id=cls.user2_id, email="u2@test.com", gmail_connected=True, hashed_password="fake")
        db.add_all([user1, user2])
        
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        last_week = now - timedelta(days=7)
        
        # User 1 Emails
        # Sender target
        e1 = EmailIndexed(id="e1", user_id=cls.user1_id, gmail_message_id="m1", gmail_thread_id="t1",
                          sender="recruiter@google.com", recipient="u1@test.com", subject="Interview", sent_at=yesterday)
        c1 = Chunk(id="c1", email_id="e1", gmail_message_id="m1", gmail_thread_id="t1", sender="recruiter@google.com",
                   subject="Interview", sent_at=yesterday, chunk_index=0, text="Let's schedule an interview.")
        
        # Thread target (2 chunks)
        e2 = EmailIndexed(id="e2", user_id=cls.user1_id, gmail_message_id="m2", gmail_thread_id="thread_xyz",
                          sender="friend@test.com", recipient="u1@test.com", subject="Weekend", sent_at=last_week)
        c2 = Chunk(id="c2", email_id="e2", gmail_message_id="m2", gmail_thread_id="thread_xyz", sender="friend@test.com",
                   subject="Weekend", sent_at=last_week, chunk_index=0, text="Are we still on for Saturday?")
        e3 = EmailIndexed(id="e3", user_id=cls.user1_id, gmail_message_id="m3", gmail_thread_id="thread_xyz",
                          sender="u1@test.com", recipient="friend@test.com", subject="Re: Weekend", sent_at=yesterday)
        c3 = Chunk(id="c3", email_id="e3", gmail_message_id="m3", gmail_thread_id="thread_xyz", sender="u1@test.com",
                   subject="Re: Weekend", sent_at=yesterday, chunk_index=0, text="Yes, see you then!")
                   
        # User 2 Emails (Leak check)
        e4 = EmailIndexed(id="e4", user_id=cls.user2_id, gmail_message_id="m4", gmail_thread_id="thread_xyz",
                          sender="recruiter@google.com", recipient="u2@test.com", subject="Offer", sent_at=now)
        c4 = Chunk(id="c4", email_id="e4", gmail_message_id="m4", gmail_thread_id="thread_xyz", sender="recruiter@google.com",
                   subject="Offer", sent_at=now, chunk_index=0, text="Here is your offer.")
                   
        db.add_all([e1, e2, e3, e4, c1, c2, c3, c4])
        db.commit()
        db.close()
        
    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=cls.engine)
        cls.engine.dispose()

    def setUp(self):
        # Patch SessionLocal to use our TestingSessionLocal
        self.session_patcher = patch("app.services.retrieval_tools.SessionLocal", new=self.TestingSessionLocal)
        self.session_patcher.start()

    def tearDown(self):
        self.session_patcher.stop()

    def test_search_by_sender(self):
        """Test finding chunks from a specific sender."""
        results = search_by_sender(self.user1_id, "recruiter")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["metadata"]["sender"], "recruiter@google.com")
        self.assertEqual(results[0]["text"], "Let's schedule an interview.")
        self.assertIsNone(results[0]["distance"])

    def test_search_by_sender_isolation(self):
        """Test sender search doesn't leak to other users."""
        results = search_by_sender(self.user2_id, "recruiter")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["text"], "Here is your offer.")

    def test_reconstruct_thread(self):
        """Test finding chunks by thread ID chronologically."""
        results = reconstruct_thread(self.user1_id, "thread_xyz")
        self.assertEqual(len(results), 2)
        # Should be chronological (oldest first)
        self.assertEqual(results[0]["text"], "Are we still on for Saturday?")
        self.assertEqual(results[1]["text"], "Yes, see you then!")
        
    def test_reconstruct_thread_isolation(self):
        """Test thread reconstruction doesn't leak between users with same thread ID."""
        results = reconstruct_thread(self.user2_id, "thread_xyz")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["text"], "Here is your offer.")

    def test_search_by_date_range_no_query(self):
        """Test date range filtering on pure DB chunks."""
        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=2)).isoformat()
        end = now.isoformat()
        
        # User 1 has e1 (yesterday) and e3 (yesterday) in this range, e2 is last week
        results = search_by_date_range(self.user1_id, start, end)
        self.assertEqual(len(results), 2)
        texts = [r["text"] for r in results]
        self.assertIn("Let's schedule an interview.", texts)
        self.assertIn("Yes, see you then!", texts)
        self.assertNotIn("Are we still on for Saturday?", texts) # from last week

    @patch("app.agent.nodes.get_planner_llm")
    @patch("app.agent.nodes.PromptTemplate.from_template")
    def test_tool_selector_routing(self, mock_prompt, mock_get_llm):
        """Test tool selector routes to correct tools based on obvious signals."""
        mock_chain = MagicMock()
        mock_prompt.return_value.__or__.return_value = mock_chain
        
        # We mock the LLM output to simulate the parsing
        mock_chain.invoke.return_value = ToolSelectionList(
            tool_calls=[
                ToolCallOutput(tool_name="search_by_sender", query="Alice", start_date="", end_date=""),
                ToolCallOutput(tool_name="search_by_date_range", query="internship", start_date="2023-01-01", end_date="2023-12-31"),
                ToolCallOutput(tool_name="semantic_search", query="generic question", start_date="", end_date="")
            ]
        )
        
        state: AgentState = {
            "user_id": "u1",
            "question": "Mixed bag",
            "sub_goals": [
                "Find emails from Alice",
                "Look for internship emails in 2023",
                "Check for generic question"
            ],
            "tool_calls": [],
            "retrieved_chunks": [],
            "conflicts_detected": [],
            "final_answer": None
        }
        
        new_state = tool_selector_node(state)
        
        calls = new_state["tool_calls"]
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[0]["tool_name"], "search_by_sender")
        self.assertEqual(calls[0]["query"], "Alice")
        self.assertEqual(calls[1]["tool_name"], "search_by_date_range")
        self.assertEqual(calls[2]["tool_name"], "semantic_search")

if __name__ == "__main__":
    unittest.main()
