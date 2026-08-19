"""Tests for Gmail OAuth helper functions, PKCE flow, crypto, and router endpoints."""

import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse
from fastapi.testclient import TestClient

from app.core.crypto import decrypt_token, encrypt_token
from app.main import app
from app.services.gmail_oauth import (
    READ_SCOPES,
    SEND_SCOPES,
    decode_oauth_state,
    encode_oauth_state,
    exchange_code_for_tokens,
    generate_code_verifier,
    get_authorization_url,
)

client = TestClient(app)


class TestGmailOAuth(unittest.TestCase):
    """Test suite covering crypto, scopes, PKCE parameter handling, and Gmail router endpoints."""

    def test_crypto_token_encryption_and_decryption(self):
        sample_token = "ya29.a0AfH6SMB_secret_access_token_12345"
        encrypted = encrypt_token(sample_token)
        self.assertIsInstance(encrypted, bytes)
        self.assertNotEqual(encrypted, sample_token.encode("utf-8"))

        decrypted = decrypt_token(encrypted)
        self.assertEqual(decrypted, sample_token)

        # Test memoryview support (Postgres bytea format)
        decrypted_mv = decrypt_token(memoryview(encrypted))
        self.assertEqual(decrypted_mv, sample_token)

        # Test None input
        self.assertIsNone(decrypt_token(None))

    def test_scopes_separation(self):
        # Enforce that send scope is strictly isolated from default read scopes
        self.assertIn("https://www.googleapis.com/auth/gmail.readonly", READ_SCOPES)
        self.assertNotIn("https://www.googleapis.com/auth/gmail.send", READ_SCOPES)
        self.assertIn("https://www.googleapis.com/auth/gmail.send", SEND_SCOPES)

    def test_pkce_verifier_and_state_roundtrip(self):
        verifier = generate_code_verifier(128)
        self.assertEqual(len(verifier), 128)

        user_id = "test-uuid-98765"
        encoded_state = encode_oauth_state(user_id=user_id, code_verifier=verifier)
        self.assertIsInstance(encoded_state, str)

        extracted_user_id, extracted_verifier = decode_oauth_state(encoded_state)
        self.assertEqual(extracted_user_id, user_id)
        self.assertEqual(extracted_verifier, verifier)

    def test_get_authorization_url_includes_pkce_params(self):
        user_id = "test-user-uuid-12345"
        auth_url = get_authorization_url(user_id=user_id)

        parsed = urlparse(auth_url)
        params = parse_qs(parsed.query)

        self.assertIn("code_challenge", params)
        self.assertIn("code_challenge_method", params)
        self.assertEqual(params["code_challenge_method"][0], "S256")
        self.assertIn("state", params)

        # Confirm state decodes to original user_id and non-empty code_verifier
        state_str = params["state"][0]
        decoded_user, decoded_verifier = decode_oauth_state(state_str)
        self.assertEqual(decoded_user, user_id)
        self.assertIsNotNone(decoded_verifier)
        self.assertEqual(len(decoded_verifier), 128)

    @patch("app.services.gmail_oauth.build_flow")
    def test_exchange_code_for_tokens_passes_pkce_verifier(self, mock_build_flow):
        mock_flow = MagicMock()
        mock_flow.credentials = MagicMock()
        mock_build_flow.return_value = mock_flow

        test_user_id = "user-123"
        test_verifier = "custom_pkce_verifier_string_123"
        state = encode_oauth_state(user_id=test_user_id, code_verifier=test_verifier)

        exchange_code_for_tokens(
            code="test_auth_code",
            state=state,
        )

        mock_flow.fetch_token.assert_called_once_with(
            code="test_auth_code",
            code_verifier=test_verifier,
        )
        self.assertEqual(mock_flow.code_verifier, test_verifier)

    def test_connect_endpoint_requires_auth(self):
        res = client.get("/gmail/oauth/connect")
        self.assertEqual(res.status_code, 401)

    def test_callback_missing_params(self):
        res = client.get("/gmail/oauth/callback")
        self.assertEqual(res.status_code, 400)

    def test_callback_invalid_user_state(self):
        res = client.get("/gmail/oauth/callback?code=mock_code&state=non_existent_uuid")
        self.assertEqual(res.status_code, 404)

    def test_connected_status_endpoint(self):
        res = client.get("/gmail/connected")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "success")


if __name__ == "__main__":
    unittest.main()
