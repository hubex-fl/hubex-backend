"""TOTP MFA utilities.

Uses pyotp for TOTP generation/verification. Falls back to a minimal
HMAC-based implementation if pyotp is not installed.
"""

import base64
import hashlib
import hmac
import secrets
import struct
import time
import urllib.parse


def generate_totp_secret() -> str:
    """Generate a random 20-byte TOTP secret, base32-encoded."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii")


def get_provisioning_uri(secret: str, email: str, issuer: str = "HUBEX") -> str:
    """Generate an otpauth:// URI for QR code scanning."""
    label = urllib.parse.quote(f"{issuer}:{email}")
    params = urllib.parse.urlencode({
        "secret": secret,
        "issuer": issuer,
        "algorithm": "SHA1",
        "digits": "6",
        "period": "30",
    })
    return f"otpauth://totp/{label}?{params}"


def _compute_totp(secret: str, counter: int) -> str:
    """Compute a 6-digit TOTP code for the given counter."""
    key = base64.b32decode(secret.upper())
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    code = struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(code % 1_000_000).zfill(6)


def verify_totp(secret: str, code: str, window: int = 1) -> bool:
    """Verify a TOTP code, allowing ±window time steps (30s each)."""
    if not code or len(code) != 6 or not code.isdigit():
        return False
    counter = int(time.time()) // 30
    for offset in range(-window, window + 1):
        expected = _compute_totp(secret, counter + offset)
        if hmac.compare_digest(expected, code):
            return True
    return False


def generate_recovery_codes(count: int = 8) -> list[str]:
    """Generate a set of recovery codes (each 8 hex chars)."""
    return [secrets.token_hex(4).upper() for _ in range(count)]


def hash_recovery_code(code: str) -> str:
    """Hash a recovery code for storage."""
    return hashlib.sha256(code.upper().encode()).hexdigest()
