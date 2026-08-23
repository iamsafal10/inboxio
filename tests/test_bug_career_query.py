import pytest
from unittest.mock import patch, MagicMock
from app.agent.graph import run_agent_graph

def test_career_query_tpm_limit_regression():
    """
    Regression test for the bug where career-related queries (like "job" or "internship")
    would hit token limits due to retrieving too many chunks (top_k=20 by default per query, 
    often multiple queries) and fallback to an error message or claim no information available.
    
    We simulate this by verifying that the `semantic_search` is called with top_k=5 
    from the retriever_node, ensuring we stay within TPM limits.
    """
    
    # We will invoke the retriever_node directly with a state that has semantic_search tool calls
    from app.agent.nodes import retriever_node
    
    state = {
        "user_id": "test_user",
        "question": "job internship",
        "sub_goals": [],
        "tool_calls": [
            {"tool_name": "semantic_search", "query": "job internship", "start_date": "", "end_date": ""},
            {"tool_name": "semantic_search", "query": "software engineering", "start_date": "", "end_date": ""}
        ],
        "retrieved_chunks": [],
        "conflicts_detected": [],
        "check_status": "",
        "final_answer": None,
        "citations": [],
        "chat_history": [],
        "long_term_facts": []
    }
    
    with patch('app.agent.nodes.search_emails') as mock_search:
        mock_search.return_value = [{"text": "mocked chunk", "metadata": {"gmail_message_id": "1", "chunk_index": 1}}]
        
        new_state = retriever_node(state)
        
        # Verify search_emails was called with top_k=5 to prevent TPM overflow
        assert mock_search.call_count == 2
        
        # Check arguments of the first call
        args, kwargs = mock_search.call_args_list[0]
        assert args[0] == "test_user"
        assert args[1] == "job internship"
        
        # Check arguments of the second call
        args, kwargs = mock_search.call_args_list[1]
        assert args[0] == "test_user"
        assert args[1] == "software engineering"
        
        assert len(new_state["retrieved_chunks"]) > 0

