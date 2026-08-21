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
        self.assertIn("Inboxio Chat UI (Phase 0)", res.text)
        self.assertIn("Login", res.text)

    def test_chat_endpoint_requires_auth(self):
        """Verify the /chat endpoint rejects unauthenticated requests."""
        res = client.post("/chat", json={"message": "hello"})
        self.assertEqual(res.status_code, 401)

    def test_chat_endpoint_echoes_message(self):
        """Verify the /chat endpoint echoes the placeholder message when authenticated."""
        test_email = "chat_test_user@example.com"
        test_password = "securepassword123"

        # 1. Signup / Login to get token
        client.post("/auth/signup", json={"email": test_email, "password": test_password})
        login_res = client.post("/auth/login", json={"email": test_email, "password": test_password})
        token = login_res.json().get("access_token")
        
        # 2. Test authenticated request
        res = client.post(
            "/chat", 
            json={"message": "hello agent"},
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["response"], "Agent not built yet. You said: hello agent")

if __name__ == "__main__":
    unittest.main()
