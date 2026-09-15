"""Tests for the recency retrieval tool and its wiring into the agent."""

from unittest.mock import patch, MagicMock

from app.agent.nodes import retriever_node


@patch("app.agent.nodes.list_recent_emails")
def test_retriever_dispatches_list_recent_emails(mock_recent):
    """'list_recent_emails' must be routed to the recency tool, not semantic search."""
    mock_recent.return_value = [{
        "text": "Internship offer",
        "metadata": {"gmail_message_id": "m1", "chunk_index": 0},
        "distance": None,
    }]

    state = {
        "user_id": "user-1",
        "tool_calls": [{
            "tool_name": "list_recent_emails",
            "query": "",
            "start_date": "",
            "end_date": "",
        }],
    }

    result = retriever_node(state)

    mock_recent.assert_called_once_with("user-1")
    assert len(result["retrieved_chunks"]) == 1
    assert result["retrieved_chunks"][0]["text"] == "Internship offer"


def test_list_recent_emails_orders_newest_first():
    """The query must order by sent_at descending so 'recent' means recent."""
    with patch("app.services.retrieval_tools.SessionLocal") as mock_session:
        db = MagicMock()
        mock_session.return_value.__enter__.return_value = db
        db.query.return_value.join.return_value.filter.return_value \
          .order_by.return_value.limit.return_value.all.return_value = []

        from app.services.retrieval_tools import list_recent_emails
        list_recent_emails("user-1", top_k=5)

        order_by = db.query.return_value.join.return_value.filter.return_value.order_by
        order_by.assert_called_once()
        rendered = str(order_by.call_args[0][0])
        assert "sent_at" in rendered
        assert "DESC" in rendered.upper()

        limit = order_by.return_value.limit
        limit.assert_called_once_with(5)


def test_recency_guarantee_survives_router_failure():
    """
    If the LLM tool router fails entirely, a 'recent emails' question must still
    get a date-ordered lookup rather than degrading to pure semantic search.
    """
    from app.agent.nodes import tool_selector_node

    with patch("app.agent.nodes.get_planner_llm") as mock_llm:
        mock_llm.return_value.with_structured_output.side_effect = RuntimeError("tool_use_failed")

        state = {"question": "what are my recent internship emails?",
                 "sub_goals": ["Find recent internship emails"]}
        result = tool_selector_node(state)

    names = [tc["tool_name"] for tc in result["tool_calls"]]
    assert "list_recent_emails" in names


def test_no_recency_tool_for_non_recency_question():
    from app.agent.nodes import _ensure_recency_tool

    calls = [{"tool_name": "semantic_search", "query": "offers"}]
    assert _ensure_recency_tool("did I get any offers?", calls) == calls
