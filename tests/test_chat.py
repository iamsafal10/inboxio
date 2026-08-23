"""Tests for chat UI and API endpoints."""

import unittest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestChat(unittest.TestCase):
    """Test suite covering the minimal web chat UI and placeholder endpoint."""

    def test_chat_ui_serves_html(self):
        """Verify the /chat-ui endpoint serves the HTML page correctly."""
        res = client.get("/chat-ui")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/html", res.headers["content-type"])

    def test_chat_endpoint_requires_auth(self):
        """Verify the /chat endpoint rejects unauthenticated requests."""
        res = client.post("/chat", json={"message": "hello"})
        self.assertEqual(res.status_code, 401)

    from unittest.mock import patch

    @patch("app.routers.chat.run_agent_graph")
    def test_chat_endpoint_calls_agent_graph(self, mock_run_agent_graph):
        """Verify the /chat endpoint calls the real agent graph."""
        mock_run_agent_graph.return_value = {"final_answer": "Mocked AI response"}
        
        test_email = "chat_test_user@example.com"
        test_password = "securepassword123"

        # 1. Signup / Login to get token
        client.post("/auth/signup", json={"email": test_email, "password": test_password})
        login_res = client.post("/auth/login", json={"email": test_email, "password": test_password})
        token = login_res.json().get("access_token")
        
        # 2. Test authenticated request
        res = client.post(
            "/chat", 
            json={"message": "Did I get any interview invites?"},
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["response"], "Mocked AI response")
        mock_run_agent_graph.assert_called_once()

if __name__ == "__main__":
    unittest.main()
