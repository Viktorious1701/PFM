"""Authentication edge cases and the error envelope.

Every branch here produces spec AC-05's single 401. Constitution SEC-07 requires
authorization to be proven by test rather than by inspection, and these are the
ways a caller can present something that is not a usable credential.

Also covers the API-02 envelope for framework-raised errors, so a 404 or an
unhandled exception cannot escape with a different shape than a domain error.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import Settings
from app.models.user import UserModel, UserRole, UserStatus

INVITE_URL = "/api/v1/users/invite"
PAYLOAD = {"email": "someone@example.com"}


def test_health_reports_ok(client: TestClient) -> None:
    """The liveness probe the Deploy gate checks."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "environment": "test"}


@pytest.mark.parametrize(
    ("header", "why"),
    [
        ("", "empty header"),
        ("Bearer", "scheme with no token"),
        ("Bearer ", "scheme with blank token"),
        ("Basic dXNlcjpwYXNz", "wrong scheme"),
        ("Token abc123", "unknown scheme"),
        ("abc123", "bare token, no scheme"),
        ("Bearer not-a-jwt", "malformed JWT"),
        ("Bearer a.b.c", "JWT-shaped but unverifiable"),
    ],
)
def test_an_unusable_authorization_header_is_always_401(
    client: TestClient, header: str, why: str
) -> None:
    """AC-05 draws no distinction between absent, invalid and expired.

    Distinguishing them would tell an attacker which half to work on (SEC-10).
    """
    response = client.post(INVITE_URL, json=PAYLOAD, headers={"Authorization": header})

    assert response.status_code == 401, f"{why} was not rejected"
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"


def test_a_token_signed_with_the_wrong_secret_is_401(
    client: TestClient, admin_user: UserModel, settings: Settings
) -> None:
    forged = security.encode_jwt(
        subject=admin_user.id,
        role="ADMIN",
        secret="an-attackers-secret-of-sufficient-length-here",
        ttl_minutes=60,
        algorithm=settings.jwt_algorithm,
    )

    response = client.post(INVITE_URL, json=PAYLOAD, headers={"Authorization": f"Bearer {forged}"})

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"


def test_a_valid_token_for_a_deleted_user_is_401(
    client: TestClient, admin_user: UserModel, settings: Settings, db: Session
) -> None:
    """The token verifies, but its subject no longer exists."""
    token = security.encode_jwt(
        subject=admin_user.id,
        role="ADMIN",
        secret=settings.jwt_secret,
        ttl_minutes=60,
        algorithm=settings.jwt_algorithm,
    )
    db.delete(admin_user)
    db.commit()

    response = client.post(INVITE_URL, json=PAYLOAD, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_a_token_with_a_non_string_subject_is_401(client: TestClient, settings: Settings) -> None:
    """A structurally valid JWT whose `sub` claim is not an id."""
    import jwt as pyjwt

    token = pyjwt.encode(
        {"sub": 12345, "role": "ADMIN"}, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )

    response = client.post(INVITE_URL, json=PAYLOAD, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


@pytest.mark.parametrize("status", [UserStatus.PENDING, UserStatus.DEACTIVATED])
def test_a_non_active_account_cannot_act_even_with_a_valid_token(
    client: TestClient, db: Session, settings: Settings, status: UserStatus
) -> None:
    """spec BR-06: a PENDING account holds no credentials and cannot act.

    A DEACTIVATED one has had them withdrawn. Neither may pass, even holding a
    token that is still cryptographically valid — otherwise deactivation would
    not take effect until the token expired.
    """
    user = UserModel(
        email=f"{status.value.lower()}@example.com",
        status=status,
        role=UserRole.ADMIN,  # ADMIN on purpose: status must win over role
        password_hash=None,
        full_name=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = security.encode_jwt(
        subject=user.id,
        role=user.role.value,
        secret=settings.jwt_secret,
        ttl_minutes=60,
        algorithm=settings.jwt_algorithm,
    )

    response = client.post(INVITE_URL, json=PAYLOAD, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"


# --- The documented auth scheme ------------------------------------------


def test_auth_is_declared_as_a_bearer_security_scheme_not_a_raw_header(
    app: FastAPI,
) -> None:
    """SDS §6.1 — and a usability guard.

    The endpoint originally took `Authorization` as a plain `Header()` parameter.
    Swagger rendered that as a bare text box, so the obvious thing to do — paste
    the JWT — produced a 401 that looked like a bad token rather than a missing
    `Bearer ` prefix. Declaring the security scheme makes Swagger add the prefix
    itself.

    This asserts the declaration so a future refactor cannot quietly reintroduce
    the raw header.
    """
    spec = app.openapi()

    schemes = spec["components"]["securitySchemes"]
    assert "BearerToken" in schemes
    assert schemes["BearerToken"]["type"] == "http"
    assert schemes["BearerToken"]["scheme"] == "bearer"

    operation = spec["paths"][INVITE_URL]["post"]
    assert {"BearerToken": []} in operation["security"]

    # No hand-rolled Authorization parameter competing with the scheme.
    names = {p["name"].lower() for p in operation.get("parameters", [])}
    assert "authorization" not in names


# --- API-02: one envelope for every failure ------------------------------


def test_an_unknown_route_uses_the_same_error_envelope(client: TestClient) -> None:
    """API-02: a framework 404 has the same flat shape as a domain error."""
    response = client.get("/api/v1/no-such-route")

    assert response.status_code == 404
    body = response.json()
    assert set(body) == {"error_code", "message", "details"}
    assert body["error_code"] == "NOT_FOUND"


def test_a_wrong_method_uses_the_same_error_envelope(client: TestClient) -> None:
    response = client.get(INVITE_URL)

    assert response.status_code == 405
    assert response.json()["error_code"] == "METHOD_NOT_ALLOWED"


def test_an_unhandled_exception_becomes_a_500_without_leaking_internals(
    app: FastAPI, settings: Settings
) -> None:
    """LA-01: the trace is logged, never returned."""

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("database password is hunter2")

    with TestClient(app, raise_server_exceptions=False) as bare_client:
        response = bare_client.get("/boom")

    assert response.status_code == 500
    body = response.json()
    assert body == {
        "error_code": "INTERNAL_ERROR",
        "message": "Unexpected server error.",
        "details": {},
    }
    assert "hunter2" not in response.text
