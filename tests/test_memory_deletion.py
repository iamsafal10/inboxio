import unittest
import uuid
from app.agent.memory_writer import delete_memory_fact
from app.models.user import User
from app.models.memory_fact import MemoryFact
from app.core.database import SessionLocal
from app.agent.graph import run_agent_graph
from unittest.mock import patch

class TestMemoryDeletion(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.unique_email = f"memory_del_test_{uuid.uuid4()}@example.com"
        self.user = User(email=self.unique_email, hashed_password="fake")
        self.db.add(self.user)
        self.db.commit()
        self.user_id = self.user.id
        
    def tearDown(self):
        self.db.rollback()
        self.db.close()

    @patch("app.agent.graph.app_graph")
    def test_memory_deletion_alters_state(self, mock_app_graph):
        """
        Tests that deleting a memory fact successfully removes it from the database,
        which in turn prevents it from being injected into the agent's long-term memory state.
        """
        # 1. Seed a fact
        fact = MemoryFact(
            user_id=self.user_id,
            fact_text="User loves the color purple.",
            fact_type="preference",
            source="manual"
        )
        self.db.add(fact)
        self.db.commit()
        fact_id = fact.id
        
        # Mock the graph execution to just return the state it was given (for inspection)
        def side_effect(state):
            # simulate a response based on whether the fact is in state
            facts = state.get("long_term_facts", [])
            answer = "purple answer" if any("purple" in f for f in facts) else "generic answer"
            return {**state, "final_answer": answer}
            
        mock_app_graph.invoke.side_effect = side_effect
        
        # 2. Run graph with fact present
        result_a = run_agent_graph(self.user_id, "What color should I use?")
        self.assertEqual(result_a["final_answer"], "purple answer")
        
        # 3. Delete the fact
        deleted = delete_memory_fact(fact_id, self.user_id, self.db)
        self.assertTrue(deleted)
        
        # 4. Run graph with fact deleted
        result_b = run_agent_graph(self.user_id, "What color should I use?")
        self.assertEqual(result_b["final_answer"], "generic answer")
        
        # 5. Assert A and B meaningfully differ in the mocked logic
        self.assertNotEqual(result_a["final_answer"], result_b["final_answer"])
        self.assertIn("purple", result_a["final_answer"])
        self.assertNotIn("purple", result_b["final_answer"])

    def test_delete_nonexistent_fact(self):
        deleted = delete_memory_fact("nonexistent-uuid-1234", self.user_id, self.db)
        self.assertFalse(deleted)
