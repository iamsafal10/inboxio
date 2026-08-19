"""Cryptographic utilities for encrypting and decrypting OAuth tokens at rest."""

import base64
import hashlib
from typing import Union
from cryptography.fernet import Fernet

from app.core.config import settings


def _get_fernet() -> Fernet:
    """Derive a deterministic 32-byte URL-safe base64 Fernet key from APP_SECRET_KEY."""
    sha256_digest = hashlib.sha256(settings.APP_SECRET_KEY.encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(sha256_digest)
    return Fernet(fernet_key)


def encrypt_token(plain_token: Union[str, bytes]) -> bytes:
    """Encrypt a plain text or byte token using Fernet symmetric encryption."""
    if isinstance(plain_token, str):
        token_bytes = plain_token.encode("utf-8")
    else:
        token_bytes = plain_token

    fernet = _get_fernet()
    return fernet.encrypt(token_bytes)


def decrypt_token(encrypted_token: Union[bytes, memoryview, None]) -> Union[str, None]:
    """Decrypt Fernet-encrypted token bytes and return the plain text string."""
    if encrypted_token is None:
        return None

    if isinstance(encrypted_token, memoryview):
        token_bytes = bytes(encrypted_token)
    else:
        token_bytes = encrypted_token

    fernet = _get_fernet()
    decrypted_bytes = fernet.decrypt(token_bytes)
    return decrypted_bytes.decode("utf-8")
