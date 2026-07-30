"""Password hashing, invitation-token generation, JWT minting.

Kept dependency-light on purpose: `bcrypt` directly rather than `passlib`, which
is unmaintained and warns loudly against modern bcrypt releases.
"""

import hashlib
import hmac
import secrets
from datetime import timedelta
from typing import Any

import bcrypt
import jwt

from app.core.clock import utcnow
from app.core.config import Settings

# 32 bytes -> 256 bits of entropy, well above NFR-1's 128-bit floor.
# urlsafe_b64 of 32 bytes is 43 chars, so the emailed link stays compact.
_TOKEN_BYTES = 32

# A real hash, computed once at import, used to burn the same time as a genuine
# verify when the account does not exist — so login latency does not reveal which
# emails are registered. Hand-written constants risk being unparseable, which
# would silently skip the bcrypt round and reintroduce the timing leak.
_DUMMY_HASH = bcrypt.hashpw(b"timing-equalizer", bcrypt.gensalt()).decode("ascii")


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str | None) -> bool:
    """Constant-ish time. A None hash (PENDING user) still costs one bcrypt round."""
    target = hashed or _DUMMY_HASH
    try:
        matched = bcrypt.checkpw(plain.encode("utf-8"), target.encode("ascii"))
    except ValueError:
        return False
    return matched and hashed is not None


def generate_invitation_token() -> str:
    """Cryptographically secure, unguessable raw token (US-01-01 AC-3, NFR-1)."""
    return secrets.token_urlsafe(_TOKEN_BYTES)


def hash_token(raw_token: str) -> str:
    """What actually gets stored.

    Only the hash is persisted; the raw token exists solely inside the email.
    A leaked database therefore cannot be used to hijack pending invitations.
    SHA-256 (not bcrypt) because the input is already high-entropy — no
    stretching required, and lookups stay a single indexed query.
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def tokens_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


def create_access_token(subject: str, settings: Settings) -> tuple[str, int]:
    """Returns (jwt, expires_in_seconds)."""
    expires_in = settings.jwt_ttl_minutes * 60
    now = utcnow()
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    """Raises jwt.PyJWTError (incl. ExpiredSignatureError) on any problem."""
    decoded: dict[str, Any] = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    return decoded
