"""Tests for the Phase 2 Planner Node."""

import unittest
from unittest.mock import patch, MagicMock

from app.agent.nodes import planner_node, PlannerOutput
from app.agent.state import AgentState

class TestPlannerNode(unittest.TestCase):
    
    @patch("app.agent.nodes.get_planner_llm")
    def test_planner_simple_question(self, mock_get_llm):
        """Test a simple question produces a single sub-goal."""
        mock_llm = MagicMock()
        mock_structured_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_get_llm.return_value = mock_llm
        
        # Mock the chain invocation
        mock_chain = mock_structured_llm
        # The chain invoke is on the prompt | structured_llm, so the mock needs to handle .invoke() correctly
        # When we do prompt | structured_llm, the result of invoke is whatever structured_llm returns.
        
        # Wait, if we mock get_planner_llm(), we return an object that responds to with_structured_output().
        # However, the prompt | llm creates a RunnableSequence. If we mock llm, the sequence invoke() will call the mock.
        
        mock_structured_llm.invoke.return_value = PlannerOutput(
            sub_goals=["Find flight details to Boston"]
        )
        
        state: AgentState = {
            "user_id": "u1",
            "question": "When is my flight to Boston?",
            "sub_goals": [],
            "tool_calls": [],
            "retrieved_chunks": [],
            "conflicts_detected": [],
            "final_answer": None
        }
        
        # We must mock the actual chain execution to return our PlannerOutput because `prompt | structured_llm` is hard to mock partially.
        # Actually, if mock_structured_llm is just a MagicMock, `prompt | mock_structured_llm` might not return a RunnableSequence properly in standard Langchain unless the mock subclasses Runnable.
        # Let's patch `chain.invoke` or `PromptTemplate.__or__`? No, let's patch the structured_llm's invoke if it's evaluated, or better, let's patch `prompt | structured_llm`.
        pass

    @patch("app.agent.nodes.PromptTemplate.from_template")
    @patch("app.agent.nodes.get_planner_llm")
    def test_planner_simple_question_mocked_chain(self, mock_get_llm, mock_prompt):
        """Test a simple question produces a single sub-goal using a fully mocked chain."""
        mock_chain = MagicMock()
        mock_prompt.return_value.__or__.return_value = mock_chain
        
        mock_chain.invoke.return_value = PlannerOutput(
            sub_goals=["Find flight details to Boston"]
        )
        
        state: AgentState = {
            "user_id": "u1",
            "question": "When is my flight to Boston?",
            "sub_goals": [],
            "tool_calls": [],
            "retrieved_chunks": [],
            "conflicts_detected": [],
            "final_answer": None
        }
        
        new_state = planner_node(state)
        
        self.assertEqual(len(new_state["sub_goals"]), 1)
        self.assertEqual(new_state["sub_goals"][0], "Find flight details to Boston")
        
    @patch("app.agent.nodes.PromptTemplate.from_template")
    @patch("app.agent.nodes.get_planner_llm")
    def test_planner_complex_question_mocked_chain(self, mock_get_llm, mock_prompt):
        """Test a complex question produces multiple sub-goals."""
        mock_chain = MagicMock()
        mock_prompt.return_value.__or__.return_value = mock_chain
        
        mock_chain.invoke.return_value = PlannerOutput(
            sub_goals=[
                "Find all application-related emails",
                "Identify most recent status per application",
                "Check for stalled threads"
            ]
        )
        
        state: AgentState = {
            "user_id": "u1",
            "question": "What's the status of my applications?",
            "sub_goals": [],
            "tool_calls": [],
            "retrieved_chunks": [],
            "conflicts_detected": [],
            "final_answer": None
        }
        
        new_state = planner_node(state)
        
        self.assertEqual(len(new_state["sub_goals"]), 3)
        self.assertEqual(new_state["sub_goals"][0], "Find all application-related emails")

    @patch("app.agent.nodes.PromptTemplate.from_template")
    @patch("app.agent.nodes.get_planner_llm")
    def test_planner_retry_on_failure(self, mock_get_llm, mock_prompt):
        """Test that planner retries once if LLM returns malformed output, then succeeds."""
        mock_chain = MagicMock()
        mock_prompt.return_value.__or__.return_value = mock_chain
        
        # First call fails (malformed output), second call succeeds
        mock_chain.invoke.side_effect = [
            ValueError("Malformed JSON"),
            PlannerOutput(sub_goals=["Success on retry"])
        ]
        
        state: AgentState = {
            "user_id": "u1",
            "question": "Test retry?",
            "sub_goals": [],
            "tool_calls": [],
            "retrieved_chunks": [],
            "conflicts_detected": [],
            "final_answer": None
        }
        
        new_state = planner_node(state)
        
        self.assertEqual(mock_chain.invoke.call_count, 2)
        self.assertEqual(len(new_state["sub_goals"]), 1)
        self.assertEqual(new_state["sub_goals"][0], "Success on retry")

    @patch("app.agent.nodes.PromptTemplate.from_template")
    @patch("app.agent.nodes.get_planner_llm")
    def test_planner_fails_clearly(self, mock_get_llm, mock_prompt):
        """Test that planner throws an exception after max retries are exhausted."""
        mock_chain = MagicMock()
        mock_prompt.return_value.__or__.return_value = mock_chain
        
        # All calls fail
        mock_chain.invoke.side_effect = ValueError("Always Malformed")
        
        state: AgentState = {
            "user_id": "u1",
            "question": "Test fail?",
            "sub_goals": [],
            "tool_calls": [],
            "retrieved_chunks": [],
            "conflicts_detected": [],
            "final_answer": None
        }
        
        with self.assertRaises(ValueError) as context:
            planner_node(state)
            
        self.assertIn("Planner node failed to produce valid sub-goals", str(context.exception))
        self.assertEqual(mock_chain.invoke.call_count, 2)  # Initial + 1 retry

if __name__ == "__main__":
    unittest.main()
