"""Unit tests for app.core.security.

These are **not** implementations of test cases from test_cases.md — the TCs are
behavioural and live in tests/integration/. These cover code paths the endpoint
cannot reach (bcrypt's ceiling, a malformed stored hash, JWT expiry), which
DOD-03's coverage bar requires and which are genuinely worth asserting.
"""

import re
from datetime import timedelta

import jwt
import pytest

from app.core import clock, security

SECRET = "unit-test-secret-long-enough-for-hs256-rfc7518"
ALGORITHM = "HS256"


def test_generated_tokens_are_43_urlsafe_chars_and_distinct() -> None:
    """SEC-02: 32 random bytes, base64url-encoded, over NFR-04's 128-bit floor."""
    tokens = {security.generate_invitation_token() for _ in range(200)}
    assert len(tokens) == 200
    assert all(re.fullmatch(r"[A-Za-z0-9_-]{43}", token) for token in tokens)


def test_token_hashing_is_deterministic_and_hides_the_input() -> None:
    """SEC-03: activation looks the invitation up by hashing what the user presents."""
    token = security.generate_invitation_token()

    first = security.hash_token(token)
    assert first == security.hash_token(token)
    assert len(first) == 64
    assert token not in first
    assert security.hash_token(token + "x") != first


def test_password_round_trips_and_wrong_password_is_rejected() -> None:
    password = "Str0ng-Passw0rd!"
    stored = security.hash_password(password)

    assert stored != password
    assert security.verify_password(password, stored)
    assert not security.verify_password("wrong", stored)


def test_a_password_past_bcrypts_ceiling_is_rejected_not_truncated() -> None:
    """VL-04: bcrypt truncates silently at 72 bytes, so it is refused at the boundary.

    Without this, two different passwords sharing their first 72 bytes would both
    authenticate.
    """
    too_long = "a" * (security.BCRYPT_MAX_BYTES + 1)

    with pytest.raises(ValueError, match="72-byte"):
        security.hash_password(too_long)

    # And verification refuses it too, rather than comparing a truncated prefix.
    stored = security.hash_password("a" * security.BCRYPT_MAX_BYTES)
    assert not security.verify_password(too_long, stored)


def test_verifying_against_a_malformed_hash_is_false_not_an_exception() -> None:
    """A corrupted stored value is a failed match, not a 500."""
    assert not security.verify_password("anything", "not-a-bcrypt-hash")


def test_jwt_round_trips_the_subject_and_role() -> None:
    token = security.encode_jwt(
        subject="user-123", role="ADMIN", secret=SECRET, ttl_minutes=60, algorithm=ALGORITHM
    )

    payload = security.decode_jwt(token, SECRET, ALGORITHM)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "ADMIN"


def test_an_expired_jwt_is_rejected() -> None:
    """SEC-06: expiry is enforced by the library, and surfaces as InvalidTokenError."""
    token = security.encode_jwt(
        subject="user-123", role="ADMIN", secret=SECRET, ttl_minutes=-1, algorithm=ALGORITHM
    )

    with pytest.raises(jwt.InvalidTokenError):
        security.decode_jwt(token, SECRET, ALGORITHM)


def test_a_jwt_signed_with_another_secret_is_rejected() -> None:
    token = security.encode_jwt(
        subject="user-123", role="ADMIN", secret=SECRET, ttl_minutes=60, algorithm=ALGORITHM
    )

    with pytest.raises(jwt.InvalidTokenError):
        security.decode_jwt(token, "a-different-secret-of-sufficient-length", ALGORITHM)


def test_jwt_expiry_is_derived_from_the_clock_seam(monkeypatch: pytest.MonkeyPatch) -> None:
    """The seam covers auth too, so a frozen clock produces a predictable exp."""
    fixed = clock.utcnow()
    monkeypatch.setattr("app.core.clock.utcnow", lambda: fixed)

    token = security.encode_jwt(
        subject="s", role="USER", secret=SECRET, ttl_minutes=30, algorithm=ALGORITHM
    )
    payload = security.decode_jwt(token, SECRET, ALGORITHM)

    assert payload["exp"] - payload["iat"] == int(timedelta(minutes=30).total_seconds())
