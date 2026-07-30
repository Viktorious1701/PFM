"""US-01-01: Invite a User via Email.

Every acceptance criterion from SRS §4 Feature-01 has a named test here; the
mapping is recorded in docs/stories/US-01-01.md.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_token
from app.models import User, UserStatus

ENDPOINT = "/api/v1/users/invitations"


# --- AC-1: email format is validated -------------------------------------


@pytest.mark.parametrize(
    "bad_email",
    ["not-an-email", "missing@tld", "@nolocal.com", "spaces in@email.com", "", "a@b@c.com"],
)
def test_ac1_rejects_malformed_email(
    client: TestClient, auth_headers: dict[str, str], bad_email: str
) -> None:
    response = client.post(ENDPOINT, json={"email": bad_email}, headers=auth_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"]["fields"], "expected field-level detail"


def test_ac1_accepts_wellformed_email(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(ENDPOINT, json={"email": "new.member@gmail.com"}, headers=auth_headers)
    assert response.status_code == 201, response.text


# --- AC-2: no duplicate ACTIVE accounts ----------------------------------


def test_ac2_rejects_email_of_active_account(
    client: TestClient, auth_headers: dict[str, str], active_user: User
) -> None:
    response = client.post(ENDPOINT, json={"email": active_user.email}, headers=auth_headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_ACTIVE"


def test_ac2_is_case_insensitive(
    client: TestClient, auth_headers: dict[str, str], active_user: User
) -> None:
    """ADMIN@Family.TEST must collide with admin@family.test."""
    response = client.post(
        ENDPOINT, json={"email": active_user.email.upper()}, headers=auth_headers
    )
    assert response.status_code == 409


def test_ac2_allows_reinvite_of_pending_email(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    """The SRS only forbids duplicates in ACTIVE status. Re-inviting a PENDING
    address rotates the token and restarts the TTL — the recovery path for an
    invitation that expired or never arrived."""
    first = client.post(ENDPOINT, json={"email": "pending@gmail.com"}, headers=auth_headers)
    assert first.status_code == 201

    user = db_session.scalar(select(User).where(User.email == "pending@gmail.com"))
    assert user is not None
    original_hash = user.invitation_token_hash

    second = client.post(ENDPOINT, json={"email": "pending@gmail.com"}, headers=auth_headers)
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"], "must reuse the same user row"

    db_session.expire_all()
    user = db_session.scalar(select(User).where(User.email == "pending@gmail.com"))
    assert user is not None
    assert user.invitation_token_hash != original_hash, "token must be rotated"


# --- AC-3: secure token + 24h TTL ----------------------------------------


def test_ac3_token_is_unguessable_and_only_stored_hashed(
    client: TestClient, auth_headers: dict[str, str], db_session: Session, email_sender
) -> None:
    client.post(ENDPOINT, json={"email": "token@gmail.com"}, headers=auth_headers)

    raw_token = email_sender.token()
    # secrets.token_urlsafe(32) -> 43 urlsafe chars -> 256 bits, over NFR-1's 128.
    assert len(raw_token) == 43

    user = db_session.scalar(select(User).where(User.email == "token@gmail.com"))
    assert user is not None
    assert user.invitation_token_hash == hash_token(raw_token)
    assert raw_token not in (user.invitation_token_hash or ""), "raw token must not be stored"


def test_ac3_tokens_are_unique_across_invitations(
    client: TestClient, auth_headers: dict[str, str], email_sender
) -> None:
    for i in range(5):
        client.post(ENDPOINT, json={"email": f"u{i}@gmail.com"}, headers=auth_headers)

    tokens = {msg.text_body.split("token=", 1)[1].split()[0] for msg in email_sender.sent}
    assert len(tokens) == 5


def test_ac3_ttl_is_exactly_24_hours(
    client: TestClient, auth_headers: dict[str, str], db_session: Session, freeze_time
) -> None:
    start = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
    freeze_time(start)

    response = client.post(ENDPOINT, json={"email": "ttl@gmail.com"}, headers=auth_headers)

    assert response.status_code == 201
    assert response.json()["token_expires_at"] == (start + timedelta(hours=24)).isoformat()


# --- AC-4: user row created as PENDING -----------------------------------


def test_ac4_creates_pending_user_without_credentials(
    client: TestClient, auth_headers: dict[str, str], db_session: Session, active_user: User
) -> None:
    client.post(ENDPOINT, json={"email": "pendingcheck@gmail.com"}, headers=auth_headers)

    user = db_session.scalar(select(User).where(User.email == "pendingcheck@gmail.com"))
    assert user is not None
    assert user.status is UserStatus.PENDING
    assert user.password_hash is None, "an invited user has no password yet"
    assert user.full_name is None, "name is supplied at activation (US-01-02 AC-3)"
    assert user.invited_by_id == active_user.id


# --- AC-5: email dispatched with the activation link ---------------------


def test_ac5_sends_one_email_containing_the_activation_link(
    client: TestClient, auth_headers: dict[str, str], email_sender, settings
) -> None:
    client.post(ENDPOINT, json={"email": "invitee@gmail.com"}, headers=auth_headers)

    assert len(email_sender.sent) == 1
    message = email_sender.last
    assert message.to == "invitee@gmail.com"

    expected_url = settings.activation_url_template.format(token=email_sender.token())
    assert expected_url == email_sender.activation_url()
    # The link must be present in both alternatives, since clients pick either.
    assert expected_url in message.text_body
    assert expected_url in message.html_body


def test_ac5_email_survives_smtp_failure_without_failing_the_request(
    client: TestClient, auth_headers: dict[str, str], email_sender, db_session: Session
) -> None:
    """Background dispatch means a broken SMTP config cannot roll back an
    invitation that is already committed. The user row must still be PENDING and
    re-invitable, which is the documented recovery path."""
    email_sender.fail_with = RuntimeError("smtp exploded")

    response = client.post(ENDPOINT, json={"email": "smtpfail@gmail.com"}, headers=auth_headers)

    assert response.status_code == 201
    user = db_session.scalar(select(User).where(User.email == "smtpfail@gmail.com"))
    assert user is not None and user.status is UserStatus.PENDING


def test_sync_mode_surfaces_smtp_failure_as_502(
    settings, db_session: Session, email_sender, active_user: User
) -> None:
    """EMAIL_SEND_MODE=sync trades NFR-3 latency for immediate feedback while
    first wiring Gmail up."""
    from fastapi.testclient import TestClient as SyncClient

    from app.core.config import get_settings
    from app.core.deps import get_email_sender
    from app.db.session import get_db
    from app.main import create_app

    sync_settings = settings.model_copy(update={"email_send_mode": "sync"})
    app = create_app(sync_settings)
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_email_sender] = lambda: email_sender
    app.dependency_overrides[get_settings] = lambda: sync_settings

    with SyncClient(app, raise_server_exceptions=False) as sync_client:
        login = sync_client.post(
            "/api/v1/auth/login",
            json={"email": active_user.email, "password": "adminpass123"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        from app.core.errors import EmailDeliveryError

        email_sender.fail_with = EmailDeliveryError("no credentials")
        response = sync_client.post(ENDPOINT, json={"email": "x@gmail.com"}, headers=headers)

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "EMAIL_DELIVERY_FAILED"


# --- AC-6: 201 with metadata, never the token ----------------------------


def test_ac6_returns_201_with_metadata_and_no_token(
    client: TestClient, auth_headers: dict[str, str], email_sender
) -> None:
    response = client.post(ENDPOINT, json={"email": "meta@gmail.com"}, headers=auth_headers)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {
        "id",
        "email",
        "status",
        "token_expires_at",
        "created_at",
        "email_dispatched",
    }
    assert body["email"] == "meta@gmail.com"
    assert body["status"] == "PENDING"

    # The whole point: an authenticated caller must not learn the token, or they
    # could activate an account they merely invited.
    assert email_sender.token() not in response.text
    assert "invitation_token" not in body
    assert "invitation_token_hash" not in body


# --- Precondition: caller is authenticated -------------------------------


def test_requires_authentication(client: TestClient) -> None:
    response = client.post(ENDPOINT, json={"email": "nobody@gmail.com"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"
