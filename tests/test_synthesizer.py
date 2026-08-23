import unittest
from unittest.mock import patch, MagicMock
from langchain_core.runnables import Runnable
from app.agent.nodes import synthesizer_node, SynthesisOutput, Citation

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

class TestSynthesizerNode(unittest.TestCase):

    def setUp(self):
        self.base_state = {
            "user_id": "test_user",
            "question": "When is the interview?",
            "sub_goals": [],
            "tool_calls": [],
            "retrieved_chunks": [
                {"text": "The interview is on Monday.", "metadata": {"sender": "Alice", "subject": "Interview", "sent_at": "2026-08-01"}}
            ],
            "conflicts_detected": [],
            "check_status": "passed",
            "final_answer": None,
            "citations": []
        }

    @patch('app.agent.nodes.get_llm')
    def test_normal_case_with_citations(self, mock_get_llm):
        mock_output = SynthesisOutput(
            answer="The interview is on Monday [1].",
            citations=[
                Citation(source_id=1, sender="Alice", subject="Interview", date="2026-08-01")
            ]
        )
        mock_runnable = MockRunnable(return_value=mock_output)
        
        mock_llm_instance = MagicMock()
        mock_llm_instance.with_structured_output.return_value = mock_runnable
        mock_get_llm.return_value = mock_llm_instance

        result = synthesizer_node(self.base_state)

        self.assertIn("[1]", result["final_answer"])
        self.assertEqual(len(result["citations"]), 1)
        self.assertEqual(result["citations"][0]["sender"], "Alice")

    @patch('app.agent.nodes.get_llm')
    def test_contradiction_surfaced(self, mock_get_llm):
        state = self.base_state.copy()
        state["conflicts_detected"] = [
            {
                "claim_a": "Interview is on Monday",
                "claim_b": "Interview is on Tuesday",
                "source_a": "Alice",
                "source_b": "Bob"
            }
        ]
        
        mock_output = SynthesisOutput(
            answer="I found conflicting info: Alice says it's Monday, but Bob says it's Tuesday [1].",
            citations=[
                Citation(source_id=1, sender="Alice", subject="Interview", date="2026-08-01")
            ]
        )
        mock_runnable = MockRunnable(return_value=mock_output)
        
        mock_llm_instance = MagicMock()
        mock_llm_instance.with_structured_output.return_value = mock_runnable
        mock_get_llm.return_value = mock_llm_instance

        result = synthesizer_node(state)
        
        self.assertIn("conflicting info", result["final_answer"])

    @patch('app.agent.nodes.get_llm')
    def test_failed_check_case(self, mock_get_llm):
        state = self.base_state.copy()
        state["check_status"] = "failed"
        
        mock_output = SynthesisOutput(
            answer="Note: I couldn't verify the evidence for contradictions due to an internal error. The interview is on Monday [1].",
            citations=[
                Citation(source_id=1, sender="Alice", subject="Interview", date="2026-08-01")
            ]
        )
        mock_runnable = MockRunnable(return_value=mock_output)
        
        mock_llm_instance = MagicMock()
        mock_llm_instance.with_structured_output.return_value = mock_runnable
        mock_get_llm.return_value = mock_llm_instance

        result = synthesizer_node(state)
        
        self.assertIn("couldn't verify the evidence", result["final_answer"])

    @patch('app.agent.nodes.get_llm')
    def test_thin_evidence(self, mock_get_llm):
        state = self.base_state.copy()
        state["retrieved_chunks"] = []
        
        mock_output = SynthesisOutput(
            answer="I couldn't find enough evidence to answer your question.",
            citations=[]
        )
        mock_runnable = MockRunnable(return_value=mock_output)
        
        mock_llm_instance = MagicMock()
        mock_llm_instance.with_structured_output.return_value = mock_runnable
        mock_get_llm.return_value = mock_llm_instance

        result = synthesizer_node(state)
        
        self.assertIn("couldn't find enough evidence", result["final_answer"])
        self.assertEqual(len(result["citations"]), 0)

if __name__ == '__main__':
    unittest.main()
