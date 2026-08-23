"""Service for managing Gmail OAuth2 flows, PKCE verifiers, token exchanges, and refreshes."""

import json
import secrets
import string
from typing import Any, Dict, List, Optional, Tuple
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from app.core.config import settings
from app.core.crypto import decrypt_token, encrypt_token

READ_SCOPES: List[str] = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

SEND_SCOPES: List[str] = [
    "https://www.googleapis.com/auth/gmail.send",
]


def generate_code_verifier(length: int = 128) -> str:
    """Generate a high-entropy cryptographic PKCE code verifier."""
    chars = string.ascii_letters + string.digits + "-._~"
    return "".join(secrets.choice(chars) for _ in range(length))


def encode_oauth_state(user_id: str, code_verifier: str, intent: str = "read") -> str:
    """Encrypt user_id, PKCE code_verifier, and intent into a tamper-proof state string."""
    payload = json.dumps({"user_id": user_id, "code_verifier": code_verifier, "intent": intent})
    return encrypt_token(payload).decode("utf-8")


def decode_oauth_state(state: str) -> Tuple[str, Optional[str], str]:
    """Decrypt state parameter to extract user_id, PKCE code_verifier, and intent."""
    try:
        decrypted = decrypt_token(state.encode("utf-8"))
        if decrypted:
            data = json.loads(decrypted)
            if isinstance(data, dict) and "user_id" in data:
                return data["user_id"], data.get("code_verifier"), data.get("intent", "read")
    except Exception:
        pass
    # Fallback if state was passed as raw user_id
    return state, None, "read"


def _get_client_config() -> Dict[str, Any]:
    """Construct Google OAuth client configuration dict from app settings."""
    return {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }


def build_flow(scopes: List[str], state: Optional[str] = None) -> Flow:
    """Build a Google OAuth Flow configured with client credentials and redirect URI."""
    client_config = _get_client_config()
    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=scopes,
        state=state,
    )
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    return flow


def get_authorization_url(user_id: str, include_send_scope: bool = False) -> str:
    """Generate the Google OAuth consent URL with PKCE and offline access.

    Embeds user_id and the generated PKCE code_verifier into the encrypted state parameter.
    """
    scopes = READ_SCOPES.copy()
    if include_send_scope:
        scopes.extend(SEND_SCOPES)

    code_verifier = generate_code_verifier()
    intent = "send" if include_send_scope else "read"
    state = encode_oauth_state(user_id=user_id, code_verifier=code_verifier, intent=intent)

    flow = build_flow(scopes=scopes, state=state)
    flow.code_verifier = code_verifier

    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=state,
    )
    return authorization_url


def exchange_code_for_tokens(
    code: str,
    state: str,
    code_verifier: Optional[str] = None,
    include_send_scope: bool = False,
) -> Credentials:
    """Exchange OAuth authorization code for Google credentials using matching PKCE code_verifier."""
    scopes = READ_SCOPES.copy()
    if include_send_scope:
        scopes.extend(SEND_SCOPES)

    if code_verifier is None:
        _, extracted_verifier, _ = decode_oauth_state(state)
        code_verifier = extracted_verifier

    flow = build_flow(scopes=scopes, state=state)
    flow.code_verifier = code_verifier
    flow.fetch_token(code=code, code_verifier=code_verifier)
    return flow.credentials


def refresh_credentials(credentials: Credentials) -> Credentials:
    """Refresh Google OAuth credentials if expired and a refresh token is present."""
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    return credentials
