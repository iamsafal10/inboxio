import pytest
from unittest.mock import patch, MagicMock

from app.agent.graph import run_agent_graph, SESSION_HISTORY
from app.agent.state import AgentState

@pytest.fixture(autouse=True)
def clear_session_history():
    """Clear the global session history before each test to ensure isolation."""
    SESSION_HISTORY.clear()
    yield
    SESSION_HISTORY.clear()

def test_session_history_accumulates_and_caps():
    user_id = "test_user_1"
    
    with patch("app.agent.graph.app_graph.invoke") as mock_invoke:
        # Mock the graph to just return a dummy final_answer
        mock_invoke.return_value = {"final_answer": "Mocked Answer 1"}
        
        # Turn 1
        res1 = run_agent_graph(user_id, "Question 1")
        assert len(SESSION_HISTORY[user_id]) == 2
        assert SESSION_HISTORY[user_id][0]["content"] == "Question 1"
        assert SESSION_HISTORY[user_id][1]["content"] == "Mocked Answer 1"
        
        # Turn 2
        mock_invoke.return_value = {"final_answer": "Mocked Answer 2"}
        res2 = run_agent_graph(user_id, "Question 2")
        assert len(SESSION_HISTORY[user_id]) == 4
        assert SESSION_HISTORY[user_id][2]["content"] == "Question 2"
        assert SESSION_HISTORY[user_id][3]["content"] == "Mocked Answer 2"
        
        # Turn 3
        mock_invoke.return_value = {"final_answer": "Mocked Answer 3"}
        res3 = run_agent_graph(user_id, "Question 3")
        assert len(SESSION_HISTORY[user_id]) == 6
        assert SESSION_HISTORY[user_id][4]["content"] == "Question 3"
        assert SESSION_HISTORY[user_id][5]["content"] == "Mocked Answer 3"
        
        # Turn 4 (Should trigger capping to last 6 messages)
        mock_invoke.return_value = {"final_answer": "Mocked Answer 4"}
        res4 = run_agent_graph(user_id, "Question 4")
        assert len(SESSION_HISTORY[user_id]) == 6
        assert SESSION_HISTORY[user_id][0]["content"] == "Question 2" # Q1 shifted out
        assert SESSION_HISTORY[user_id][4]["content"] == "Question 4"
        assert SESSION_HISTORY[user_id][5]["content"] == "Mocked Answer 4"

def test_session_history_isolation():
    user1 = "user_A"
    user2 = "user_B"
    
    with patch("app.agent.graph.app_graph.invoke") as mock_invoke:
        mock_invoke.return_value = {"final_answer": "Response"}
        
        run_agent_graph(user1, "Question from A")
        run_agent_graph(user2, "Question from B")
        
        assert len(SESSION_HISTORY[user1]) == 2
        assert SESSION_HISTORY[user1][0]["content"] == "Question from A"
        
        assert len(SESSION_HISTORY[user2]) == 2
        assert SESSION_HISTORY[user2][0]["content"] == "Question from B"
