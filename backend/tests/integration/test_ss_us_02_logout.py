"""SS-US-02 — Logout.

One test per test case in specs/002-system-security/test_cases.md (TC-12..TC-15).
Names state what the test proves, not what it calls.
"""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.core import security
from app.core.config import Settings
from app.models.user import UserModel

HeaderFactory = Callable[[UserModel, Settings], dict[str, str]]

LOGOUT_URL = "/api/v1/auth/logout"


def _expired_token(user: UserModel, settings: Settings) -> str:
    return security.encode_jwt(
        subject=user.id,
        role=user.role.value,
        secret=settings.jwt_secret,
        ttl_minutes=-1,  # already past
        algorithm=settings.jwt_algorithm,
    )


def _wrong_signature_token(user: UserModel, settings: Settings) -> str:
    return security.encode_jwt(
        subject=user.id,
        role=user.role.value,
        secret="a-completely-different-secret-key-padded-to-32-bytes",
        ttl_minutes=settings.jwt_ttl_minutes,
        algorithm=settings.jwt_algorithm,
    )


def test_successful_logout_returns_confirmation_with_no_credential(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-12: a valid bearer token -> 200 {"status": "SUCCESS", "message": ...},
    with no access_token or any other credential in the body.
    """
    response = client.post(LOGOUT_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "SUCCESS"
    assert "message" in body
    assert "access_token" not in body
    assert "token" not in body


def test_no_bearer_token_is_refused_with_401_not_authenticated(client: TestClient) -> None:
    """TC-13: no Authorization header at all -> 401 NOT_AUTHENTICATED."""
    response = client.post(LOGOUT_URL)

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"


@pytest.mark.parametrize(
    "make_header",
    [
        lambda user, settings: {"Authorization": "Bearer not-a-real-jwt"},
        lambda user, settings: {
            "Authorization": f"Bearer {_wrong_signature_token(user, settings)}"
        },
        lambda user, settings: {"Authorization": f"Bearer {_expired_token(user, settings)}"},
    ],
    ids=["malformed", "invalid-signature", "expired"],
)
def test_malformed_invalid_or_expired_token_refused_identically(
    client: TestClient,
    normal_user: UserModel,
    settings: Settings,
    make_header: HeaderFactory,
) -> None:
    """TC-14: a malformed token, one with an invalid signature, and one that
    is well-formed but expired are each refused with 401 NOT_AUTHENTICATED —
    indistinguishable from one another and from TC-13's no-token case.
    """
    headers = make_header(normal_user, settings)

    response = client.post(LOGOUT_URL, headers=headers)

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"


def test_token_still_authenticates_after_logout_until_its_own_expiry(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-15: logout performs no server-side revocation — the same token
    used to log out once succeeds again on a second logout call.
    """
    first = client.post(LOGOUT_URL, headers=user_headers)
    assert first.status_code == 200

    second = client.post(LOGOUT_URL, headers=user_headers)
    assert second.status_code == 200
    assert second.json()["status"] == "SUCCESS"
