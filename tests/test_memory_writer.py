import pytest
import unittest
import uuid
from unittest.mock import patch, MagicMock
from langchain_core.runnables import RunnableSequence
from app.agent.memory_writer import extract_and_store_facts, ExtractedFact
from app.models.user import User
from app.models.memory_fact import MemoryFact
from app.core.database import SessionLocal
from app.agent.graph import SESSION_HISTORY

class TestMemoryWriter(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        
        self.unique_email = f"memory_writer_test_{uuid.uuid4()}@example.com"
        self.user = User(email=self.unique_email, hashed_password="fake")
        self.db.add(self.user)
        self.db.commit()
        
        self.user_id = self.user.id

    def tearDown(self):
        self.db.rollback()
        if self.user_id in SESSION_HISTORY:
            del SESSION_HISTORY[self.user_id]
        self.db.close()

    @patch.object(RunnableSequence, "invoke")
    def test_extract_and_store_facts_success(self, mock_invoke):
        SESSION_HISTORY[self.user_id] = [
            {"role": "human", "content": "I only want backend roles."},
            {"role": "agent", "content": "Got it. I'll focus on backend roles."}
        ]
        
        mock_result = MagicMock()
        mock_result.facts = [
            ExtractedFact(fact_text="User prefers backend roles.", fact_type="preference")
        ]
        mock_invoke.return_value = mock_result
        
        new_facts = extract_and_store_facts(self.user_id, self.db)
        
        self.assertEqual(len(new_facts), 1)
        self.assertEqual(new_facts[0]["fact_text"], "User prefers backend roles.")
        
        db_facts = self.db.query(MemoryFact).filter(MemoryFact.user_id == self.user_id).all()
        self.assertEqual(len(db_facts), 1)
        self.assertEqual(db_facts[0].fact_text, "User prefers backend roles.")
        self.assertEqual(db_facts[0].fact_type, "preference")

    @patch.object(RunnableSequence, "invoke")
    def test_deduplication(self, mock_invoke):
        existing_fact = MemoryFact(
            user_id=self.user_id,
            fact_text="User prefers backend roles.",
            fact_type="preference",
            source="manual"
        )
        self.db.add(existing_fact)
        self.db.commit()
        
        SESSION_HISTORY[self.user_id] = [{"role": "human", "content": "I only want backend roles."}]
        
        mock_result = MagicMock()
        mock_result.facts = [
            ExtractedFact(fact_text="User prefers backend roles.", fact_type="preference")
        ]
        mock_invoke.return_value = mock_result
        
        new_facts = extract_and_store_facts(self.user_id, self.db)
        
        self.assertEqual(len(new_facts), 0)
        
        db_facts = self.db.query(MemoryFact).filter(MemoryFact.user_id == self.user_id).all()
        self.assertEqual(len(db_facts), 1)

    def test_no_history_returns_empty(self):
        SESSION_HISTORY[self.user_id] = []
        new_facts = extract_and_store_facts(self.user_id, self.db)
        self.assertEqual(len(new_facts), 0)
