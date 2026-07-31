"""Token generation, hashing, and JWT encode/decode.

Constitution: SEC-02 (entropy), SEC-03 (hash at rest), SEC-06 (JWT), VL-04
(password policy).

Two different hashing jobs live here and must not be confused:

* **Invitation tokens** are hashed with plain SHA-256. They are already 256 bits
  of uniform randomness, so there is nothing to brute-force and no salt to add —
  a slow KDF would buy nothing and cost latency on every activation.
* **Passwords** are hashed with bcrypt, which is deliberately slow, because a
  human-chosen password is low-entropy and guessable.
"""

import hashlib
import secrets
from datetime import timedelta
from typing import Any

import bcrypt
import jwt

from app.core import clock

# spec FR-08 / AC-06 / SEC-02: 32 random bytes = 256 bits, comfortably over
# NFR-04's 128-bit floor. urlsafe_b64 of 32 bytes is always 43 characters
# (test_cases TC-08 asserts exactly that shape).
_TOKEN_BYTES = 32

# bcrypt silently truncates at 72 bytes rather than erroring, so an over-long
# password would appear to work while only its first 72 bytes mattered. Rejected
# at the boundary instead (spike finding 5, constitution VL-04).
BCRYPT_MAX_BYTES = 72


def generate_invitation_token() -> str:
    """A fresh, unguessable invitation token. Returned raw — never persisted raw."""
    return secrets.token_urlsafe(_TOKEN_BYTES)


def hash_token(raw_token: str) -> str:
    """SHA-256 hex of an invitation token (SEC-03).

    Only this value reaches the database; the raw token exists solely in the
    delivered email (spec BR-07, plan.md A2). Deterministic, so activation can
    look the invitation up by hashing what the user presents.
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def hash_password(plain: str) -> str:
    """bcrypt hash. Raises ValueError past bcrypt's silent-truncation ceiling."""
    encoded = plain.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_BYTES:
        raise ValueError(
            f"Password exceeds bcrypt's {BCRYPT_MAX_BYTES}-byte limit and would be truncated."
        )
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, password_hash: str) -> bool:
    """Constant-time comparison via bcrypt. False for any malformed hash."""
    encoded = plain.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, password_hash.encode("utf-8"))
    except ValueError:
        # A stored value that is not a bcrypt hash is a failed match, not a crash.
        return False


def encode_jwt(subject: str, role: str, secret: str, ttl_minutes: int, algorithm: str) -> str:
    """Sign an access token (SEC-06).

    UM-US-01 does not expose an endpoint that calls this — issuing tokens is
    SS-US-01's job (plan.md A11). It exists here so tests and the dev
    `mint-token` CLI can produce a credential to verify against.
    """
    now = clock.utcnow()
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=ttl_minutes),
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_jwt(token: str, secret: str, algorithm: str) -> dict[str, Any]:
    """Verify and decode an access token.

    Raises `jwt.InvalidTokenError` (which covers expiry, bad signature and
    malformed input) so the caller maps every failure mode to one 401 — spec
    AC-05 draws no distinction between absent, invalid and expired credentials.
    """
    decoded: dict[str, Any] = jwt.decode(token, secret, algorithms=[algorithm])
    return decoded
