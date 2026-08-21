"""Tests for the Phase 2 Agent Graph Structure."""

import unittest
from unittest.mock import patch, MagicMock

from app.agent.graph import build_graph
from app.agent.state import AgentState

class TestAgentGraph(unittest.TestCase):
    
    @patch("app.agent.graph.synthesizer_node")
    @patch("app.agent.graph.conflict_checker_node")
    @patch("app.agent.graph.retriever_node")
    @patch("app.agent.graph.tool_selector_node")
    @patch("app.agent.graph.planner_node")
    def test_agent_graph_execution_flow(self, mock_planner, mock_tool, mock_retriever, mock_conflict, mock_synthesizer):
        """Test the graph compiles and nodes execute in the correct default order."""
        
        # Make the mocks return the state untouched so the graph doesn't break
        def mock_node(state):
            return state
            
        mock_planner.side_effect = mock_node
        mock_tool.side_effect = mock_node
        mock_retriever.side_effect = mock_node
        mock_conflict.side_effect = mock_node
        mock_synthesizer.side_effect = mock_node
        
        # Create a mock object that tracks calls in order
        order_tracker = MagicMock()
        order_tracker.attach_mock(mock_planner, 'planner')
        order_tracker.attach_mock(mock_tool, 'tool_selector')
        order_tracker.attach_mock(mock_retriever, 'retriever')
        order_tracker.attach_mock(mock_conflict, 'conflict_checker')
        order_tracker.attach_mock(mock_synthesizer, 'synthesizer')
        
        # Execute the graph by rebuilding it with patched nodes
        test_graph = build_graph()
        
        initial_state = AgentState(
            user_id="user-123",
            question="What is the deadline?",
            sub_goals=[],
            tool_calls=[],
            retrieved_chunks=[],
            conflicts_detected=[],
            final_answer=None
        )
        result_state = test_graph.invoke(initial_state)
        
        # 1. Assert state carries through properly
        self.assertEqual(result_state["user_id"], "user-123")
        self.assertEqual(result_state["question"], "What is the deadline?")
        self.assertEqual(result_state["sub_goals"], [])
        self.assertIsNone(result_state["final_answer"])
        
        # 2. Assert node execution order
        expected_calls = [
            unittest.mock.call.planner({'user_id': 'user-123', 'question': 'What is the deadline?', 'sub_goals': [], 'tool_calls': [], 'retrieved_chunks': [], 'conflicts_detected': [], 'final_answer': None}),
            unittest.mock.call.tool_selector({'user_id': 'user-123', 'question': 'What is the deadline?', 'sub_goals': [], 'tool_calls': [], 'retrieved_chunks': [], 'conflicts_detected': [], 'final_answer': None}),
            unittest.mock.call.retriever({'user_id': 'user-123', 'question': 'What is the deadline?', 'sub_goals': [], 'tool_calls': [], 'retrieved_chunks': [], 'conflicts_detected': [], 'final_answer': None}),
            unittest.mock.call.conflict_checker({'user_id': 'user-123', 'question': 'What is the deadline?', 'sub_goals': [], 'tool_calls': [], 'retrieved_chunks': [], 'conflicts_detected': [], 'final_answer': None}),
            unittest.mock.call.synthesizer({'user_id': 'user-123', 'question': 'What is the deadline?', 'sub_goals': [], 'tool_calls': [], 'retrieved_chunks': [], 'conflicts_detected': [], 'final_answer': None})
        ]
        
        # We only check the order of methods called, filtering out internal bool checks
        call_order = [call[0] for call in order_tracker.mock_calls if not call[0].endswith('__bool__')]
        expected_order = ['planner', 'tool_selector', 'retriever', 'conflict_checker', 'synthesizer']
        
        self.assertEqual(call_order, expected_order)

if __name__ == "__main__":
    unittest.main()
