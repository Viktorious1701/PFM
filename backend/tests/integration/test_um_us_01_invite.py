"""UM-US-01 — Invite a User via Email.

One test per test case in specs/001-user-onboarding/test_cases.md. Each docstring
opens with its `TC-NN` so the Coverage Matrix can be filled with real node ids
(constitution TST-01, TST-02).

Names state what the test proves, not what it calls.
"""

import re
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import clock
from app.core.config import Settings
from app.models.invitation import InvitationModel, InvitationStatus
from app.models.user import UserModel, UserRole, UserStatus
from app.repositories import user_repo
from app.services.email.sender import EmailMessage, RecordingEmailSender
from tests.conftest import FROZEN_NOW, live_smtp_settings, smtp_credentials_present

INVITE_URL = "/api/v1/users/invite"

TARGET = "family.member@gmail.com"


# --- helpers --------------------------------------------------------------


def token_from(message: EmailMessage) -> str:
    """Pull the raw token out of the activation link in a recorded email.

    The email is the only place the raw token legitimately appears (spec BR-07),
    so this is how a test gets hold of it to prove it is absent elsewhere.
    """
    match = re.search(r"https?://\S+", message.text_body)
    assert match, "no activation URL in the text body"
    query = parse_qs(urlparse(match.group(0)).query)
    return query["token"][0]


def count_users(db: Session, email: str) -> int:
    return int(
        db.scalar(select(func.count()).select_from(UserModel).where(UserModel.email == email)) or 0
    )


def count_invitations(db: Session, email: str) -> int:
    return int(
        db.scalar(
            select(func.count()).select_from(InvitationModel).where(InvitationModel.email == email)
        )
        or 0
    )


def make_user(
    db: Session, *, email: str, status: UserStatus, role: UserRole = UserRole.USER
) -> UserModel:
    user = UserModel(email=email, status=status, role=role, full_name=None, password_hash=None)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# --- AC-01: the happy path ------------------------------------------------


def test_invite_returns_201_with_the_invitation_record(
    client: TestClient, admin_headers: dict[str, str], frozen_now: object
) -> None:
    """TC-01: ADMIN invites a new address — 201 with invitation metadata."""
    response = client.post(INVITE_URL, json={"email": TARGET}, headers=admin_headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == TARGET
    assert body["status"] == "PENDING"
    assert body["id"]
    assert body["token_expires_at"]
    assert body["created_at"]
    assert body["message"] == "Invitation sent successfully"


def test_invite_writes_both_a_user_row_and_an_invitation_row(
    client: TestClient, admin_headers: dict[str, str], db: Session, admin_user: UserModel
) -> None:
    """TC-02: inviting writes both a user row and an invitation row (BR-08)."""
    client.post(INVITE_URL, json={"email": TARGET}, headers=admin_headers)

    assert count_users(db, TARGET) == 1
    user = user_repo.get_by_email(db, TARGET)
    assert user is not None
    assert user.status is UserStatus.PENDING

    invitations = list(db.scalars(select(InvitationModel).where(InvitationModel.email == TARGET)))
    assert len(invitations) == 1
    assert invitations[0].status is InvitationStatus.PENDING
    assert invitations[0].invited_by_id == admin_user.id


def test_invite_dispatches_an_email_containing_the_activation_link(
    client: TestClient,
    admin_headers: dict[str, str],
    email_sender: RecordingEmailSender,
    settings: Settings,
) -> None:
    """TC-03: an activation email is dispatched containing the activation link."""
    client.post(INVITE_URL, json={"email": TARGET}, headers=admin_headers)

    assert len(email_sender.sent) == 1
    message = email_sender.sent[0]
    assert message.to == TARGET

    token = token_from(message)
    expected_url = settings.activation_url_template.replace("{token}", token)
    # Both alternatives carry the link, so a text-only client can still activate.
    assert expected_url in message.text_body
    assert expected_url in message.html_body


# --- AC-02 / EC-01: the address is already taken --------------------------


def test_inviting_an_active_address_is_rejected_as_conflict(
    client: TestClient,
    admin_headers: dict[str, str],
    db: Session,
    email_sender: RecordingEmailSender,
) -> None:
    """TC-04: inviting an ACTIVE address is rejected with 409."""
    make_user(db, email=TARGET, status=UserStatus.ACTIVE)

    response = client.post(INVITE_URL, json={"email": TARGET}, headers=admin_headers)

    assert response.status_code == 409
    assert response.json()["error_code"] == "USER_EMAIL_ALREADY_ACTIVE"
    assert response.json()["message"] == "An account with this email already exists"
    # Nothing created, nothing sent.
    assert count_users(db, TARGET) == 1
    assert count_invitations(db, TARGET) == 0
    assert email_sender.sent == []


def test_duplicate_detection_ignores_case_and_surrounding_whitespace(
    client: TestClient,
    admin_headers: dict[str, str],
    db: Session,
    email_sender: RecordingEmailSender,
) -> None:
    """TC-05: duplicate detection ignores case and surrounding whitespace (EC-01)."""
    make_user(db, email=TARGET, status=UserStatus.ACTIVE)

    response = client.post(
        INVITE_URL, json={"email": "  Family.Member@Gmail.COM  "}, headers=admin_headers
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "USER_EMAIL_ALREADY_ACTIVE"
    # One mailbox, one account — no second row for the differently-cased form.
    assert db.scalar(select(func.count()).select_from(UserModel)) == 2  # admin + the ACTIVE target
    assert email_sender.sent == []


# --- AC-03 / EC-04: payload validation -----------------------------------


@pytest.mark.parametrize(
    "bad_email",
    ["not-an-email", "@nolocal.com", "spaces in@email.com", "a@b@c.com", ""],
)
def test_malformed_email_addresses_are_rejected_as_validation_errors(
    client: TestClient,
    admin_headers: dict[str, str],
    db: Session,
    email_sender: RecordingEmailSender,
    bad_email: str,
) -> None:
    """TC-06: malformed email addresses are rejected with 422."""
    response = client.post(INVITE_URL, json={"email": bad_email}, headers=admin_headers)

    assert response.status_code == 422, f"{bad_email!r} was accepted"
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    fields = body["details"]["fields"]
    assert fields, "no field detail returned"
    assert any("email" in field["location"] for field in fields)

    assert db.scalar(select(func.count()).select_from(InvitationModel)) == 0
    assert email_sender.sent == []


def test_a_missing_email_field_is_rejected_as_a_validation_error(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    """TC-07: a missing email field is rejected with 422 (VL-02)."""
    response = client.post(INVITE_URL, json={}, headers=admin_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert any("email" in field["location"] for field in body["details"]["fields"])


def test_an_over_long_email_address_is_rejected_not_truncated(
    client: TestClient, admin_headers: dict[str, str], db: Session
) -> None:
    """TC-09: an over-long email address is rejected with 422 (EC-04).

    321 characters — one past the inclusive 320 maximum (QF-08).
    """
    local = "a" * (321 - len("@example.com"))
    over_long = f"{local}@example.com"
    assert len(over_long) == 321

    response = client.post(INVITE_URL, json={"email": over_long}, headers=admin_headers)

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"
    # Not silently shortened to fit.
    assert db.scalar(select(func.count()).select_from(UserModel)) == 1  # the admin only


# --- AC-06: token and TTL -------------------------------------------------


def test_every_emitted_token_is_43_urlsafe_chars_and_unique(
    client: TestClient, admin_headers: dict[str, str], email_sender: RecordingEmailSender
) -> None:
    """TC-08: the emitted token is 43 URL-safe characters and never repeats.

    43 chars is the base64url encoding of 32 random bytes — 256 bits, above
    NFR-04's 128-bit floor. Entropy of the generator itself is out of scope for a
    test (QF-05); this asserts shape and uniqueness.
    """
    for index in range(50):
        response = client.post(
            INVITE_URL, json={"email": f"user{index}@example.com"}, headers=admin_headers
        )
        assert response.status_code == 201

    tokens = [token_from(message) for message in email_sender.sent]
    assert len(tokens) == 50
    assert all(re.fullmatch(r"[A-Za-z0-9_-]{43}", token) for token in tokens)
    assert len(set(tokens)) == 50


def test_the_invitation_expires_exactly_24_hours_after_creation(
    client: TestClient, admin_headers: dict[str, str], db: Session, frozen_now: object
) -> None:
    """TC-23: the invitation expires exactly 24 hours after creation.

    Also asserts the serialised value is timezone-aware. An earlier version of
    this test applied `ensure_aware` to the *response* before comparing, which
    made it pass while the API was emitting a naive timestamp — a client had no
    way to know the timezone of an expiry deadline. The offset is part of the
    contract, so it is asserted directly.
    """
    response = client.post(INVITE_URL, json={"email": TARGET}, headers=admin_headers)

    expected = FROZEN_NOW + timedelta(hours=24)

    for field in ("token_expires_at", "created_at"):
        parsed = datetime.fromisoformat(response.json()[field])
        assert parsed.tzinfo is not None, f"{field} was serialised without a timezone"

    assert datetime.fromisoformat(response.json()["token_expires_at"]) == expected

    # The stored value legitimately reads back naive on SQLite, which is why
    # ensure_aware exists — the guard belongs at the serialisation boundary.
    invitation = db.scalars(select(InvitationModel).where(InvitationModel.email == TARGET)).one()
    assert clock.ensure_aware(invitation.expires_at) == expected


def test_expiry_is_derived_from_the_timestamp_not_stored_as_a_status(
    client: TestClient,
    admin_headers: dict[str, str],
    db: Session,
    frozen_now: object,
    advance_clock: object,
) -> None:
    """TC-24: expiry is derived from the timestamp, not stored as a status."""
    client.post(INVITE_URL, json={"email": TARGET}, headers=admin_headers)

    later = advance_clock(timedelta(hours=25))  # type: ignore[operator]

    db.expire_all()
    invitation = db.scalars(select(InvitationModel).where(InvitationModel.email == TARGET)).one()

    # No sweeper mutated the row...
    assert invitation.status is InvitationStatus.PENDING
    # ...but a reader derives expiry by comparison.
    assert invitation.is_expired(later)


# --- AC-07: the invited account ------------------------------------------


def test_the_invited_account_has_no_credentials_and_the_default_role(
    client: TestClient, admin_headers: dict[str, str], db: Session
) -> None:
    """TC-10: the invited account carries no credentials and the default role."""
    client.post(INVITE_URL, json={"email": TARGET}, headers=admin_headers)

    user = user_repo.get_by_email(db, TARGET)
    assert user is not None
    assert user.password_hash is None
    assert user.full_name is None
    assert user.status is UserStatus.PENDING
    assert user.role is UserRole.USER


# --- AC-04 / AC-05: authorisation ----------------------------------------


def test_a_non_admin_caller_is_denied(
    client: TestClient,
    user_headers: dict[str, str],
    db: Session,
    email_sender: RecordingEmailSender,
) -> None:
    """TC-11: a non-ADMIN caller is denied with 403 (SEC-07)."""
    response = client.post(INVITE_URL, json={"email": TARGET}, headers=user_headers)

    assert response.status_code == 403
    assert response.json()["error_code"] == "FORBIDDEN"
    assert count_users(db, TARGET) == 0
    assert email_sender.sent == []


def test_an_unauthenticated_caller_is_denied(
    client: TestClient, db: Session, email_sender: RecordingEmailSender
) -> None:
    """TC-12: an unauthenticated caller is denied with 401 (SEC-07)."""
    response = client.post(INVITE_URL, json={"email": TARGET})

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"
    assert count_users(db, TARGET) == 0
    assert email_sender.sent == []


def test_credentials_are_evaluated_before_the_payload(client: TestClient) -> None:
    """TC-13: credentials are evaluated before the payload — 401, not 422.

    Proves the dependency ordering in plan.md A8: an unauthenticated caller must
    learn nothing about payload validity.
    """
    response = client.post(INVITE_URL, json={"email": "not-an-email"})

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"


def test_an_expired_token_is_denied(
    client: TestClient, admin_user: UserModel, settings: Settings
) -> None:
    """TC-12 (variant): an expired credential is denied with 401.

    AC-05 makes no distinction between absent, invalid and expired credentials,
    so this asserts the expiry path reaches the same 401.
    """
    from app.core import security

    expired = security.encode_jwt(
        subject=admin_user.id,
        role=admin_user.role.value,
        secret=settings.jwt_secret,
        ttl_minutes=-1,  # already past
        algorithm=settings.jwt_algorithm,
    )

    response = client.post(
        INVITE_URL, json={"email": TARGET}, headers={"Authorization": f"Bearer {expired}"}
    )

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"


# --- EC-05: uniqueness under contention ----------------------------------


def test_a_unique_constraint_violation_surfaces_as_conflict_not_server_error(
    client: TestClient,
    admin_headers: dict[str, str],
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-14: a unique-constraint violation surfaces as 409, not 500.

    Simulates the lost race by blinding the service's pre-check while the row
    exists, so the insert hits the unique index — the constructable half of EC-05
    (QF-02 defers true concurrency to a PostgreSQL run).
    """
    make_user(db, email=TARGET, status=UserStatus.PENDING)

    monkeypatch.setattr("app.repositories.user_repo.get_by_email", lambda *_a, **_k: None)

    response = client.post(INVITE_URL, json={"email": TARGET}, headers=admin_headers)

    assert response.status_code == 409
    assert response.json()["error_code"] == "USER_EMAIL_ALREADY_ACTIVE"

    db.expire_all()
    assert count_users(db, TARGET) == 1
    # No orphaned invitation from the failed attempt.
    assert count_invitations(db, TARGET) == 0


def test_repeated_submission_yields_exactly_one_account(
    client: TestClient, admin_headers: dict[str, str], db: Session
) -> None:
    """TC-15: repeated submission of the same new address yields exactly one account."""
    first = client.post(INVITE_URL, json={"email": TARGET}, headers=admin_headers)
    second = client.post(INVITE_URL, json={"email": TARGET}, headers=admin_headers)

    assert first.status_code == 201
    # Either a re-invite (EC-02) or a conflict — never a duplicate account.
    assert second.status_code in (201, 409)

    db.expire_all()
    assert count_users(db, TARGET) == 1


# --- AC-09 / AC-08: audit and non-disclosure -----------------------------


def test_a_successful_invitation_emits_an_audit_record_without_the_token(
    client: TestClient,
    admin_headers: dict[str, str],
    admin_user: UserModel,
    email_sender: RecordingEmailSender,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """TC-16: a successful invitation emits an audit record without the token.

    Log-boundary assertion only — durability of the audit trail is out of scope
    (QF-01).
    """
    with caplog.at_level("INFO", logger="app.audit"):
        response = client.post(INVITE_URL, json={"email": TARGET}, headers=admin_headers)
    assert response.status_code == 201

    audit_lines = [record.getMessage() for record in caplog.records]
    combined = "\n".join(audit_lines)

    assert "USER_INVITED" in combined
    assert admin_user.id in combined
    assert TARGET in combined
    assert "SUCCESS" in combined
    assert "timestamp" in combined

    # LA-01: the raw token appears nowhere in the captured output.
    token = token_from(email_sender.sent[0])
    assert token not in combined


def test_the_raw_token_appears_nowhere_in_the_response_body(
    client: TestClient, admin_headers: dict[str, str], email_sender: RecordingEmailSender
) -> None:
    """TC-17: the raw token appears nowhere in the response body."""
    response = client.post(INVITE_URL, json={"email": TARGET}, headers=admin_headers)

    token = token_from(email_sender.sent[0])
    assert token not in response.text


def test_the_response_exposes_exactly_the_six_documented_fields(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    """TC-18: the response exposes exactly the six documented fields.

    A closed key set, so no future field can leak the token unnoticed. If this
    fails because a field was added, that is the guard working (QF-04).
    """
    response = client.post(INVITE_URL, json={"email": TARGET}, headers=admin_headers)

    assert set(response.json()) == {
        "id",
        "email",
        "status",
        "token_expires_at",
        "created_at",
        "message",
    }


# --- EC-06 / EC-07: delivery failure -------------------------------------


def test_a_background_delivery_failure_does_not_fail_the_request(
    app: FastAPI,
    client: TestClient,
    admin_headers: dict[str, str],
    db: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """TC-19: a background delivery failure does not fail the request (EC-06)."""
    from app.core.deps import get_email_sender

    failing = RecordingEmailSender(fail=True)
    app.dependency_overrides[get_email_sender] = lambda: failing

    with caplog.at_level("ERROR"):
        response = client.post(INVITE_URL, json={"email": TARGET}, headers=admin_headers)

    assert response.status_code == 201
    assert failing.sent == []

    db.expire_all()
    user = user_repo.get_by_email(db, TARGET)
    assert user is not None and user.status is UserStatus.PENDING
    invitation = db.scalars(select(InvitationModel).where(InvitationModel.email == TARGET)).one()
    assert invitation.status is InvitationStatus.PENDING

    # SC-09: never silent.
    assert any("delivery failed" in record.getMessage() for record in caplog.records)


def test_a_sync_mode_delivery_failure_returns_bad_gateway(
    app: FastAPI,
    client: TestClient,
    admin_headers: dict[str, str],
    settings: Settings,
) -> None:
    """TC-20: a sync-mode delivery failure returns 502 (EC-07)."""
    from app.core.config import get_settings
    from app.core.deps import get_email_sender

    sync_settings = settings.model_copy(update={"email_send_mode": "sync"})
    app.dependency_overrides[get_settings] = lambda: sync_settings
    app.dependency_overrides[get_email_sender] = lambda: RecordingEmailSender(fail=True)

    response = client.post(INVITE_URL, json={"email": TARGET}, headers=admin_headers)

    assert response.status_code == 502
    assert response.json()["error_code"] == "EMAIL_DELIVERY_FAILED"


def test_an_address_whose_email_failed_can_be_reinvited(
    app: FastAPI,
    client: TestClient,
    admin_headers: dict[str, str],
    db: Session,
    email_sender: RecordingEmailSender,
) -> None:
    """TC-21: an address whose email failed can be re-invited successfully (EC-06)."""
    from app.core.deps import get_email_sender

    # First attempt: delivery fails in background mode.
    app.dependency_overrides[get_email_sender] = lambda: RecordingEmailSender(fail=True)
    first = client.post(INVITE_URL, json={"email": TARGET}, headers=admin_headers)
    assert first.status_code == 201

    # Second attempt: a working sender.
    app.dependency_overrides[get_email_sender] = lambda: email_sender
    second = client.post(INVITE_URL, json={"email": TARGET}, headers=admin_headers)

    assert second.status_code == 201
    assert len(email_sender.sent) == 1
    db.expire_all()
    assert count_users(db, TARGET) == 1


# --- EC-01: normalisation on write ---------------------------------------


def test_the_stored_email_is_normalised(
    client: TestClient,
    admin_headers: dict[str, str],
    db: Session,
    email_sender: RecordingEmailSender,
) -> None:
    """TC-25: the stored email is normalised (VL-03)."""
    client.post(INVITE_URL, json={"email": "  New.Member@GMAIL.com  "}, headers=admin_headers)

    assert user_repo.get_by_email(db, "new.member@gmail.com") is not None
    # Dispatched to the normalised address, not the submitted form.
    assert email_sender.sent[0].to == "new.member@gmail.com"


# --- EC-02 / EC-03: re-invitation ----------------------------------------


@pytest.mark.parametrize("advance_hours", [0, 25], ids=["still-valid", "already-expired"])
def test_reinviting_a_pending_address_rotates_the_token_and_supersedes_the_old_invitation(
    client: TestClient,
    admin_headers: dict[str, str],
    db: Session,
    email_sender: RecordingEmailSender,
    frozen_now: object,
    advance_clock: object,
    advance_hours: int,
) -> None:
    """TC-26: re-inviting a PENDING address rotates the token and supersedes the old one.

    Run both while the first invitation is valid (EC-02) and after it has expired
    (EC-03) — expiry must not be an obstacle to re-inviting.
    """
    first = client.post(INVITE_URL, json={"email": TARGET}, headers=admin_headers)
    assert first.status_code == 201
    first_token = token_from(email_sender.sent[0])
    first_user_id = first.json()["id"]

    if advance_hours:
        advance_clock(timedelta(hours=advance_hours))  # type: ignore[operator]

    second = client.post(INVITE_URL, json={"email": TARGET}, headers=admin_headers)

    assert second.status_code == 201
    # Same account.
    assert second.json()["id"] == first_user_id

    db.expire_all()
    assert count_users(db, TARGET) == 1

    invitations = list(db.scalars(select(InvitationModel).where(InvitationModel.email == TARGET)))
    assert len(invitations) == 2
    by_status = {invitation.status for invitation in invitations}
    assert by_status == {InvitationStatus.SUPERSEDED, InvitationStatus.PENDING}

    # A new token was issued, and a new email sent.
    assert len(email_sender.sent) == 2
    second_token = token_from(email_sender.sent[1])
    assert second_token != first_token

    # Expiry restarts from the moment of re-invitation.
    pending = next(i for i in invitations if i.status is InvitationStatus.PENDING)
    expected = clock.utcnow() + timedelta(hours=24)
    assert clock.ensure_aware(pending.expires_at) == expected


# --- AC-01 live delivery (opt-in) ----------------------------------------


@pytest.mark.smtp
@pytest.mark.skipif(
    not smtp_credentials_present(),
    reason="SMTP_USER / SMTP_PASSWORD absent from .env — TC-22 needs real Gmail credentials",
)
def test_a_real_message_is_delivered_through_gmail_smtp() -> None:
    """TC-22: a real message is delivered through Gmail SMTP.

    Opt-in (`-m smtp`), excluded from the default run (QF-07). Proves host, port,
    STARTTLS and the App Password are all correct — which is exactly the
    configuration EC-07 fails on when it is wrong.

    Sends to the configured account itself, so running it cannot spam anyone.

    **A send that does not raise is not proof the mail arrived.** SC-01
    additionally requires a manual inbox check, which is what the Deploy gate is
    for.
    """
    from app.services.email.smtp import GmailSmtpSender
    from app.services.email.templates import build_invitation_email

    settings = live_smtp_settings()

    sender = GmailSmtpSender(
        host=settings.smtp_host,
        port=settings.smtp_port,
        user=settings.smtp_user,
        password=settings.smtp_password,
        from_address=settings.email_from or settings.smtp_user,
    )
    message = build_invitation_email(
        to_email=settings.smtp_user,  # send to self
        raw_token="live-smtp-verification-token",
        activation_url_template=settings.activation_url_template,
        expires_in_hours=settings.invitation_ttl_hours,
    )

    sender.send(message)  # raises EmailDeliveryFailed on any failure
