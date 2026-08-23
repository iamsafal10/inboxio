import unittest
from unittest.mock import patch, MagicMock
from langchain_core.runnables import Runnable
from app.agent.nodes import conflict_checker_node, ConflictOutput, ConflictDetail

class MockRunnable(Runnable):
    def __init__(self, return_value=None, side_effect=None):
        self._return_value = return_value
        self._side_effect = side_effect
        self.call_count = 0
    def invoke(self, *args, **kwargs):
        self.call_count += 1
        if self._side_effect:
            raise self._side_effect
        return self._return_value

class TestConflictCheckerNode(unittest.TestCase):

    def setUp(self):
        self.base_state = {
            "user_id": "test_user",
            "question": "What is the status?",
            "sub_goals": [],
            "tool_calls": [],
            "retrieved_chunks": [],
            "conflicts_detected": [],
            "check_status": "",
            "final_answer": None
        }

    def test_no_retrieved_chunks(self):
        result = conflict_checker_node(self.base_state)
        self.assertEqual(result["check_status"], "passed")
        self.assertEqual(len(result["conflicts_detected"]), 0)

    @patch('app.agent.nodes.get_llm')
    def test_conflict_detected(self, mock_get_llm):
        mock_output = ConflictOutput(
            has_contradictions=True,
            conflicts=[
                ConflictDetail(
                    claim_a="Interview is Monday",
                    claim_b="Interview is Tuesday",
                    source_a="Evidence 1",
                    source_b="Evidence 2"
                )
            ]
        )
        mock_runnable = MockRunnable(return_value=mock_output)
        
        mock_llm_instance = MagicMock()
        mock_llm_instance.with_structured_output.return_value = mock_runnable
        mock_get_llm.return_value = mock_llm_instance

        state = self.base_state.copy()
        state["retrieved_chunks"] = [
            {"text": "Interview is Monday", "metadata": {"sender": "Alice"}},
            {"text": "Actually, interview is Tuesday", "metadata": {"sender": "Bob"}}
        ]

        result = conflict_checker_node(state)

        self.assertEqual(result["check_status"], "passed")
        self.assertEqual(len(result["conflicts_detected"]), 1)
        self.assertEqual(result["conflicts_detected"][0]["claim_a"], "Interview is Monday")

    @patch('app.agent.nodes.get_llm')
    def test_no_conflict_detected(self, mock_get_llm):
        mock_output = ConflictOutput(
            has_contradictions=False,
            conflicts=[]
        )
        mock_runnable = MockRunnable(return_value=mock_output)
        
        mock_llm_instance = MagicMock()
        mock_llm_instance.with_structured_output.return_value = mock_runnable
        mock_get_llm.return_value = mock_llm_instance

        state = self.base_state.copy()
        state["retrieved_chunks"] = [
            {"text": "Interview is Monday", "metadata": {"sender": "Alice"}}
        ]

        result = conflict_checker_node(state)

        self.assertEqual(result["check_status"], "passed")
        self.assertEqual(len(result["conflicts_detected"]), 0)

    @patch('app.agent.nodes.get_llm')
    def test_llm_failure_exhausts_retries(self, mock_get_llm):
        mock_runnable = MockRunnable(side_effect=ValueError("API Error"))
        
        mock_llm_instance = MagicMock()
        mock_llm_instance.with_structured_output.return_value = mock_runnable
        mock_get_llm.return_value = mock_llm_instance

        state = self.base_state.copy()
        state["retrieved_chunks"] = [
            {"text": "Some chunk", "metadata": {}}
        ]

        result = conflict_checker_node(state)

        # Expected explicit failure state, not an empty list silently
        self.assertEqual(result["check_status"], "failed")
        self.assertEqual(mock_runnable.call_count, 3)

    @patch('app.agent.nodes.get_llm')
    def test_batching_logic(self, mock_get_llm):
        mock_output = ConflictOutput(has_contradictions=False, conflicts=[])
        mock_runnable = MockRunnable(return_value=mock_output)
        
        mock_llm_instance = MagicMock()
        mock_llm_instance.with_structured_output.return_value = mock_runnable
        mock_get_llm.return_value = mock_llm_instance

        state = self.base_state.copy()
        
        # Max chars is 30,000. So we need text > 30,000 chars.
        large_text = "A" * 35000 
        state["retrieved_chunks"] = [{"text": large_text, "metadata": {}}]

        result = conflict_checker_node(state)
        
        self.assertEqual(result["check_status"], "passed")
        # Ensure LLM was called at least twice
        self.assertGreaterEqual(mock_runnable.call_count, 2)

if __name__ == '__main__':
    unittest.main()
