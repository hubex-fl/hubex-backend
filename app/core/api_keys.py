"""API Key generation and hashing utilities."""

import secrets

from app.core.security import hash_device_token

API_KEY_PREFIX = "hbx_"


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key.

    Returns (key_plain, key_prefix, key_hash).
    key_plain is shown once to the user, key_hash is stored in DB.
    """
    raw = secrets.token_hex(32)
    key_plain = f"{API_KEY_PREFIX}{raw}"
    key_prefix = key_plain[:12]
    key_hash = hash_device_token(key_plain)
    return key_plain, key_prefix, key_hash


def is_api_key(token: str) -> bool:
    """Check if a bearer token is an API key (vs JWT)."""
    return token.startswith(API_KEY_PREFIX)
