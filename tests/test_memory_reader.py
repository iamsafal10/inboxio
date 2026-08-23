import unittest
import uuid
from app.agent.memory_reader import get_relevant_facts
from app.models.user import User
from app.models.memory_fact import MemoryFact
from app.core.database import SessionLocal

class TestMemoryReader(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        
        self.unique_email = f"memory_reader_test_{uuid.uuid4()}@example.com"
        self.user = User(email=self.unique_email, hashed_password="fake")
        self.db.add(self.user)
        self.db.commit()
        
        self.user_id = self.user.id
        
        self.unique_email_b = f"memory_reader_test_b_{uuid.uuid4()}@example.com"
        self.user_b = User(email=self.unique_email_b, hashed_password="fake")
        self.db.add(self.user_b)
        self.db.commit()
        
        self.user_b_id = self.user_b.id

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_relevance_matching(self):
        # Insert more than 3 facts to trigger the keyword filter logic
        facts = [
            MemoryFact(user_id=self.user_id, fact_text="User prefers backend engineering roles.", fact_type="preference", source="manual"),
            MemoryFact(user_id=self.user_id, fact_text="User wants to work in San Francisco.", fact_type="preference", source="manual"),
            MemoryFact(user_id=self.user_id, fact_text="User graduates in June 2027.", fact_type="target_date", source="manual"),
            MemoryFact(user_id=self.user_id, fact_text="User hates writing frontend React code.", fact_type="constraint", source="manual")
        ]
        self.db.add_all(facts)
        self.db.commit()
        
        # Test 1: Should match backend fact
        res1 = get_relevant_facts(self.user_id, "find me some backend jobs", self.db)
        self.assertIn("User prefers backend engineering roles.", res1)
        self.assertNotIn("User wants to work in San Francisco.", res1)
        
        # Test 2: Should match frontend fact
        res2 = get_relevant_facts(self.user_id, "what about frontend positions?", self.db)
        self.assertIn("User hates writing frontend React code.", res2)
        self.assertNotIn("User graduates in June 2027.", res2)
        
    def test_few_facts_fallback(self):
        # Only 2 facts: should always return all facts regardless of keywords
        facts = [
            MemoryFact(user_id=self.user_id, fact_text="User prefers backend engineering roles.", fact_type="preference", source="manual"),
            MemoryFact(user_id=self.user_id, fact_text="User wants to work in San Francisco.", fact_type="preference", source="manual")
        ]
        self.db.add_all(facts)
        self.db.commit()
        
        res = get_relevant_facts(self.user_id, "hello, what is my name?", self.db)
        self.assertEqual(len(res), 2)
        self.assertIn("User prefers backend engineering roles.", res)

    def test_per_user_isolation(self):
        # User A has 4 facts
        facts_a = [
            MemoryFact(user_id=self.user_id, fact_text="User prefers backend engineering roles.", fact_type="preference", source="manual"),
            MemoryFact(user_id=self.user_id, fact_text="User wants to work in San Francisco.", fact_type="preference", source="manual"),
            MemoryFact(user_id=self.user_id, fact_text="User graduates in June 2027.", fact_type="target_date", source="manual"),
            MemoryFact(user_id=self.user_id, fact_text="User hates writing frontend React code.", fact_type="constraint", source="manual")
        ]
        self.db.add_all(facts_a)
        
        # User B has 1 fact
        fact_b = MemoryFact(user_id=self.user_b_id, fact_text="User loves embedded systems.", fact_type="preference", source="manual")
        self.db.add(fact_b)
        self.db.commit()
        
        # Query for User A about embedded systems (should not match 'roles' or anything else in A)
        res = get_relevant_facts(self.user_id, "find me embedded hardware jobs", self.db)
        self.assertEqual(len(res), 0) # Should NOT match User B's fact, and no match in A
