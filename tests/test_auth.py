"""Tests for authentication endpoints and OAuth2 password flow."""

import unittest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestAuthFlow(unittest.TestCase):
    """Test suite covering user signup, standard JSON login, and Swagger OAuth2 password flow."""

    def test_auth_full_flow(self):
        test_email = "oauth_flow_user@example.com"
        test_password = "securepassword123"

        # 1. Signup
        signup_res = client.post(
            "/auth/signup",
            json={"email": test_email, "password": test_password},
        )
        self.assertIn(signup_res.status_code, (201, 400))

        # 2. JSON Login (Standard API payload)
        json_login_res = client.post(
            "/auth/login",
            json={"email": test_email, "password": test_password},
        )
        self.assertEqual(json_login_res.status_code, 200)
        self.assertIn("access_token", json_login_res.json())
        self.assertEqual(json_login_res.json()["token_type"], "bearer")

        # 3. OAuth2 Password Form Login (Swagger UI Authorize modal)
        # Swagger sends application/x-www-form-urlencoded with 'username' and 'password'
        oauth2_form_res = client.post(
            "/auth/login",
            data={"username": test_email, "password": test_password},
        )
        self.assertEqual(oauth2_form_res.status_code, 200)
        oauth2_token = oauth2_form_res.json()["access_token"]
        self.assertEqual(oauth2_form_res.json()["token_type"], "bearer")

        # 4. Access protected route with token obtained via OAuth2 flow
        me_res = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {oauth2_token}"},
        )
        self.assertEqual(me_res.status_code, 200)
        user_data = me_res.json()
        self.assertEqual(user_data["email"], test_email)
        self.assertFalse(user_data["gmail_connected"])
        self.assertFalse(user_data["gmail_send_scope_granted"])

        # 5. Invalid credentials rejection
        invalid_login_res = client.post(
            "/auth/login",
            data={"username": test_email, "password": "wrongpassword"},
        )
        self.assertEqual(invalid_login_res.status_code, 401)
        self.assertEqual(
            invalid_login_res.json()["detail"],
            "Incorrect email or password",
        )

        # 6. Invalid token rejection on protected route
        invalid_me_res = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid.token.value"},
        )
        self.assertEqual(invalid_me_res.status_code, 401)


if __name__ == "__main__":
    unittest.main()
