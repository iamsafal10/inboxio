import pytest
import unittest
import uuid
from sqlalchemy.exc import IntegrityError
from app.models.memory_fact import MemoryFact
from app.models.user import User
from app.core.database import SessionLocal

class TestMemorySchema(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_memory_fact_creation(self):
        unique_email = f"memorytest_schema_{uuid.uuid4()}@example.com"
        user = User(email=unique_email, hashed_password="fake")
        self.db.add(user)
        self.db.commit()
        
        fact = MemoryFact(
            user_id=user.id,
            fact_text="User prefers emails after 5pm",
            fact_type="preference",
            source="session_123"
        )
        self.db.add(fact)
        self.db.commit()
        
        saved_fact = self.db.query(MemoryFact).filter_by(id=fact.id).first()
        self.assertIsNotNone(saved_fact)
        self.assertEqual(saved_fact.user_id, user.id)
        self.assertEqual(saved_fact.fact_text, "User prefers emails after 5pm")
        self.assertEqual(saved_fact.fact_type, "preference")
        self.assertEqual(saved_fact.source, "session_123")
        self.assertTrue(saved_fact.active)
        self.assertIsNotNone(saved_fact.created_at)
        self.assertIsNone(saved_fact.deleted_at)

    def test_memory_fact_requires_user_id(self):
        fact = MemoryFact(
            fact_text="Missing user",
            fact_type="constraint"
        )
        self.db.add(fact)
        with pytest.raises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_memory_fact_requires_fact_text(self):
        unique_email = f"memorytest2_schema_{uuid.uuid4()}@example.com"
        user = User(email=unique_email, hashed_password="fake")
        self.db.add(user)
        self.db.commit()
        
        fact = MemoryFact(
            user_id=user.id,
            fact_type="preference"
        )
        self.db.add(fact)
        with pytest.raises(IntegrityError):
            self.db.commit()
        self.db.rollback()
