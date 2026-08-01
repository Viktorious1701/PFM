"""UM-US-02 — Activate a User Account.

One test per test case in specs/001-user-onboarding/test_cases.md (TC-28..TC-56).
Names state what the test proves, not what it calls.

`_seed_invitation` constructs preconditions the public API cannot itself
produce — a PENDING invitation whose user has since become ACTIVE or
DEACTIVATED (EC-06, EC-07), or an already-EXPIRED/ACCEPTED/SUPERSEDED
invitation without needing a real invite-then-supersede round trip. This is a
defensive-check surface: at most one invitation is ever PENDING per address
through the real API (UM-US-01 FR-11), so these states are only reachable by
direct arrangement, exactly like `conftest.py`'s own `_make_user` helper
arranges `admin_user`/`normal_user` directly rather than through an endpoint.
"""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock, security
from app.models.invitation import InvitationModel, InvitationStatus
from app.models.user import UserModel, UserRole, UserStatus
from app.repositories import user_repo
from app.services.email.sender import RecordingEmailSender
from tests.integration.test_um_us_01_invite import token_from

INVITE_URL = "/api/v1/users/invite"
ACTIVATE_URL = "/api/v1/users/activate"
TARGET_EMAIL = "activate.user@example.com"
VALID_PASSWORD = "SecurePassword123!"


# --- helpers ----------------------------------------------------------------


def get_token_from_invite(
    client: TestClient,
    admin_headers: dict[str, str],
    email_sender: RecordingEmailSender,
    email: str = TARGET_EMAIL,
) -> str:
    """Invite `email` for real and pull the raw token out of the recorded mail."""
    response = client.post(INVITE_URL, json={"email": email}, headers=admin_headers)
    assert response.status_code == 201
    return token_from(email_sender.sent[-1])


def _seed_invitation(
    db: Session,
    *,
    admin_user: UserModel,
    email: str,
    user_status: UserStatus,
    invitation_status: InvitationStatus,
    expires_delta: timedelta = timedelta(hours=24),
) -> tuple[UserModel, str]:
    """Directly arrange a user + invitation pair in an otherwise-unreachable
    state, for the defensive checks EC-06/EC-07/EC-09/EC-11 exercise.
    """
    user = user_repo.get_by_email(db, email)
    if user is None:
        has_credentials = user_status is not UserStatus.PENDING
        user = UserModel(
            email=email,
            password_hash=security.hash_password("ExistingPassw0rd!") if has_credentials else None,
            full_name="Existing User" if has_credentials else None,
            status=user_status,
            role=UserRole.USER,
        )
        db.add(user)
        db.flush()
    else:
        user.status = user_status

    raw_token = security.generate_invitation_token()
    invitation = InvitationModel(
        email=email,
        token_hash=security.hash_token(raw_token),
        expires_at=clock.utcnow() + expires_delta,
        status=invitation_status,
        invited_by_id=admin_user.id,
    )
    db.add(invitation)
    db.commit()
    db.refresh(user)
    return user, raw_token


def _row_snapshot(db: Session, email: str) -> tuple[dict[str, object], dict[str, object]]:
    db.expire_all()
    user = user_repo.get_by_email(db, email)
    assert user is not None
    invitation = db.scalars(
        select(InvitationModel)
        .where(InvitationModel.email == email)
        .order_by(InvitationModel.created_at.desc())
    ).first()
    assert invitation is not None
    return (
        {"status": user.status, "full_name": user.full_name, "password_hash": user.password_hash},
        {"status": invitation.status, "id": invitation.id},
    )


# --- TC-28..TC-33: activation refusals in BR-02's fixed order ---------------


def test_activate_happy_path_activates_user_and_marks_invitation_accepted(
    client: TestClient,
    admin_headers: dict[str, str],
    email_sender: RecordingEmailSender,
    db: Session,
) -> None:
    """TC-28 (and TC-42, same node — see test_cases.md Test Implementation Map):
    valid token + full name + valid password -> 200, both rows transition together.
    """
    token = get_token_from_invite(client, admin_headers, email_sender)

    response = client.post(
        ACTIVATE_URL,
        json={"token": token, "full_name": "Jane Doe", "password": VALID_PASSWORD},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"

    db.expire_all()
    user = user_repo.get_by_email(db, TARGET_EMAIL)
    assert user is not None
    assert user.status is UserStatus.ACTIVE
    assert user.full_name == "Jane Doe"
    assert user.password_hash is not None
    assert security.verify_password(VALID_PASSWORD, user.password_hash)

    invitation = db.scalars(
        select(InvitationModel).where(InvitationModel.email == TARGET_EMAIL)
    ).one()
    assert invitation.status is InvitationStatus.ACCEPTED


def test_activate_expired_token_returns_400_token_expired(
    client: TestClient,
    admin_headers: dict[str, str],
    email_sender: RecordingEmailSender,
    frozen_now: object,
    advance_clock: object,
    db: Session,
) -> None:
    """TC-29: expired token -> 400 INVITATION_TOKEN_EXPIRED, user stays PENDING,
    invitation's stored state is untouched.
    """
    token = get_token_from_invite(client, admin_headers, email_sender)
    invitation_before = db.scalars(
        select(InvitationModel).where(InvitationModel.email == TARGET_EMAIL)
    ).one()
    status_before = invitation_before.status

    advance_clock(timedelta(hours=25))  # type: ignore[operator]

    response = client.post(
        ACTIVATE_URL,
        json={"token": token, "full_name": "Jane Doe", "password": VALID_PASSWORD},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "INVITATION_TOKEN_EXPIRED"

    db.expire_all()
    user = user_repo.get_by_email(db, TARGET_EMAIL)
    assert user is not None and user.status is UserStatus.PENDING
    invitation_after = db.scalars(
        select(InvitationModel).where(InvitationModel.email == TARGET_EMAIL)
    ).one()
    assert invitation_after.status is status_before


def test_activate_unknown_token_returns_400_token_invalid(client: TestClient) -> None:
    """TC-30: a token matching no invitation -> 400 INVITATION_TOKEN_INVALID."""
    response = client.post(
        ACTIVATE_URL,
        json={"token": "unknown-token-12345", "full_name": "Jane Doe", "password": VALID_PASSWORD},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "INVITATION_TOKEN_INVALID"


def test_activate_already_used_token_returns_400_token_invalid(
    client: TestClient,
    admin_headers: dict[str, str],
    email_sender: RecordingEmailSender,
    db: Session,
) -> None:
    """TC-31: re-submitting an already-ACCEPTED token -> 400 INVITATION_TOKEN_INVALID,
    the first activation's full_name/password_hash are unchanged.
    """
    token = get_token_from_invite(client, admin_headers, email_sender)

    first = client.post(
        ACTIVATE_URL,
        json={"token": token, "full_name": "Jane Doe", "password": VALID_PASSWORD},
    )
    assert first.status_code == 200

    db.expire_all()
    user_after_first = user_repo.get_by_email(db, TARGET_EMAIL)
    assert user_after_first is not None
    hash_after_first = user_after_first.password_hash

    second = client.post(
        ACTIVATE_URL,
        json={"token": token, "full_name": "Someone Else", "password": "AnotherPassw0rd!"},
    )
    assert second.status_code == 400
    assert second.json()["error_code"] == "INVITATION_TOKEN_INVALID"

    db.expire_all()
    user_after_second = user_repo.get_by_email(db, TARGET_EMAIL)
    assert user_after_second is not None
    assert user_after_second.full_name == "Jane Doe"
    assert user_after_second.password_hash == hash_after_first


def test_activate_superseded_token_returns_400_token_invalid(
    client: TestClient, admin_headers: dict[str, str], email_sender: RecordingEmailSender
) -> None:
    """TC-32: the earlier of two invitations to the same address, after re-invite
    supersedes it, is refused generically -> 400 INVITATION_TOKEN_INVALID.
    """
    old_token = get_token_from_invite(client, admin_headers, email_sender)
    # Re-inviting the same still-PENDING address supersedes the outstanding one
    # (UM-US-01 EC-02/EC-03) and issues a fresh token.
    get_token_from_invite(client, admin_headers, email_sender)

    response = client.post(
        ACTIVATE_URL,
        json={"token": old_token, "full_name": "Jane Doe", "password": VALID_PASSWORD},
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "INVITATION_TOKEN_INVALID"


@pytest.mark.parametrize(
    "invalid_password",
    [
        "short1!",  # too short
        "nouppercase1!",  # no uppercase
        "NoDigitsHere!",  # no digit
        "NoSpecialChar1",  # no special character
    ],
)
def test_activate_weak_password_returns_422_validation_error(
    client: TestClient,
    admin_headers: dict[str, str],
    email_sender: RecordingEmailSender,
    invalid_password: str,
) -> None:
    """TC-33: each documented password-policy violation -> 422 VALIDATION_ERROR
    identifying the password field. VL-04 requires uppercase/digit/special —
    NOT lowercase, so a password missing only lowercase is deliberately absent
    from this list; it is accepted (constitution VL-04, spec BR-09/EC-02).
    """
    token = get_token_from_invite(client, admin_headers, email_sender)

    response = client.post(
        ACTIVATE_URL,
        json={"token": token, "full_name": "Jane Doe", "password": invalid_password},
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"
    fields = [f["location"][-1] for f in response.json()["details"]["fields"]]
    assert "password" in fields


# --- TC-34/35: password boundary -------------------------------------------


def test_activate_over_long_password_rejected_not_truncated(
    client: TestClient,
    admin_headers: dict[str, str],
    email_sender: RecordingEmailSender,
    db: Session,
) -> None:
    """TC-34: a password of 73 bytes UTF-8 (one past bcrypt's 72-byte ceiling)
    is rejected with 422, not silently shortened; nothing is persisted.
    """
    token = get_token_from_invite(client, admin_headers, email_sender)
    over_long = "Aa1!" + "x" * 69  # 73 bytes total, otherwise policy-compliant

    response = client.post(
        ACTIVATE_URL,
        json={"token": token, "full_name": "Jane Doe", "password": over_long},
    )

    assert response.status_code == 422
    db.expire_all()
    user = user_repo.get_by_email(db, TARGET_EMAIL)
    assert user is not None and user.status is UserStatus.PENDING


def test_activate_password_at_exact_policy_boundary_is_accepted(
    client: TestClient, admin_headers: dict[str, str], email_sender: RecordingEmailSender
) -> None:
    """TC-35: exactly 8 characters, one uppercase, one digit, one special
    character -> 200. The policy is a floor, not a target.
    """
    token = get_token_from_invite(client, admin_headers, email_sender)

    response = client.post(
        ACTIVATE_URL,
        json={"token": token, "full_name": "Jane Doe", "password": "Aa1!aaaa"},
    )

    assert response.status_code == 200


# --- TC-36/37/38: full name validation --------------------------------------


@pytest.mark.parametrize("bad_name", ["", "   "])
def test_activate_empty_or_whitespace_full_name_returns_422(
    client: TestClient,
    admin_headers: dict[str, str],
    email_sender: RecordingEmailSender,
    bad_name: str,
) -> None:
    """TC-36: an empty or whitespace-only full name -> 422 identifying full_name."""
    token = get_token_from_invite(client, admin_headers, email_sender)

    response = client.post(
        ACTIVATE_URL,
        json={"token": token, "full_name": bad_name, "password": VALID_PASSWORD},
    )

    assert response.status_code == 422
    fields = [f["location"][-1] for f in response.json()["details"]["fields"]]
    assert "full_name" in fields


def test_activate_missing_full_name_field_returns_422(
    client: TestClient, admin_headers: dict[str, str], email_sender: RecordingEmailSender
) -> None:
    """TC-36 (continued): full_name absent from the payload entirely -> 422."""
    token = get_token_from_invite(client, admin_headers, email_sender)

    response = client.post(ACTIVATE_URL, json={"token": token, "password": VALID_PASSWORD})

    assert response.status_code == 422


def test_activate_full_name_with_surrounding_whitespace_is_trimmed(
    client: TestClient,
    admin_headers: dict[str, str],
    email_sender: RecordingEmailSender,
    db: Session,
) -> None:
    """TC-37: "  Jane Doe  " is stored as "Jane Doe" — interior spacing kept,
    surrounding whitespace removed.
    """
    token = get_token_from_invite(client, admin_headers, email_sender)

    response = client.post(
        ACTIVATE_URL,
        json={"token": token, "full_name": "  Jane Doe  ", "password": VALID_PASSWORD},
    )

    assert response.status_code == 200
    db.expire_all()
    user = user_repo.get_by_email(db, TARGET_EMAIL)
    assert user is not None and user.full_name == "Jane Doe"


def test_activate_non_ascii_full_name_stored_exactly(
    client: TestClient,
    admin_headers: dict[str, str],
    email_sender: RecordingEmailSender,
    db: Session,
) -> None:
    """TC-38: a Vietnamese name is persisted byte-for-byte — no transliteration,
    accent-stripping, or case-folding.
    """
    token = get_token_from_invite(client, admin_headers, email_sender)
    name = "Đặng Ngọc Thịnh"

    response = client.post(
        ACTIVATE_URL,
        json={"token": token, "full_name": name, "password": VALID_PASSWORD},
    )

    assert response.status_code == 200
    db.expire_all()
    user = user_repo.get_by_email(db, TARGET_EMAIL)
    assert user is not None and user.full_name == name


# --- TC-39/40/41/44: credential exposure and audit --------------------------


def test_activate_response_body_never_contains_password_hash_or_token(
    client: TestClient,
    admin_headers: dict[str, str],
    email_sender: RecordingEmailSender,
    db: Session,
) -> None:
    """TC-39: the raw password, its hash, and the submitted token appear nowhere
    in the response body — asserted positively (mirrors UM-US-01 QF-04's method).
    """
    token = get_token_from_invite(client, admin_headers, email_sender)

    response = client.post(
        ACTIVATE_URL,
        json={"token": token, "full_name": "Jane Doe", "password": VALID_PASSWORD},
    )
    assert response.status_code == 200

    db.expire_all()
    user = user_repo.get_by_email(db, TARGET_EMAIL)
    assert user is not None and user.password_hash is not None

    body = response.text
    assert VALID_PASSWORD not in body
    assert user.password_hash not in body
    assert token not in body


def test_activate_success_emits_audit_record_without_credential(
    client: TestClient,
    admin_headers: dict[str, str],
    email_sender: RecordingEmailSender,
    db: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """TC-40: a successful activation emits one audit record with the LA-02
    fields (actor, timestamp, action, target, result) and no credential.
    """
    token = get_token_from_invite(client, admin_headers, email_sender)

    with caplog.at_level("INFO", logger="app.audit"):
        response = client.post(
            ACTIVATE_URL,
            json={"token": token, "full_name": "Jane Doe", "password": VALID_PASSWORD},
        )
    assert response.status_code == 200

    audit_lines = [r.getMessage() for r in caplog.records if r.name == "app.audit"]
    success_lines = [line for line in audit_lines if "USER_ACTIVATED" in line]
    assert len(success_lines) == 1
    assert "SUCCESS" in success_lines[0]
    assert VALID_PASSWORD not in success_lines[0]
    assert token not in success_lines[0]


def test_activate_refusal_emits_audit_record_marked_failure(
    client: TestClient,
    admin_headers: dict[str, str],
    email_sender: RecordingEmailSender,
    frozen_now: object,
    advance_clock: object,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """TC-41: a refused activation (here, expired) also emits an audit record,
    result FAILURE, with no credential in it.
    """
    token = get_token_from_invite(client, admin_headers, email_sender)
    advance_clock(timedelta(hours=25))  # type: ignore[operator]

    with caplog.at_level("INFO", logger="app.audit"):
        response = client.post(
            ACTIVATE_URL,
            json={"token": token, "full_name": "Jane Doe", "password": VALID_PASSWORD},
        )
    assert response.status_code == 400

    audit_lines = [r.getMessage() for r in caplog.records if r.name == "app.audit"]
    failure_lines = [line for line in audit_lines if "USER_ACTIVATION_FAILED" in line]
    assert len(failure_lines) == 1
    assert "FAILURE" in failure_lines[0]
    assert token not in failure_lines[0]


def test_activate_success_response_exposes_exactly_two_fields_no_session(
    client: TestClient, admin_headers: dict[str, str], email_sender: RecordingEmailSender
) -> None:
    """TC-44: the success body's keys are exactly `status` and `message` — no
    token, no access_token, no session identifier of any kind.
    """
    token = get_token_from_invite(client, admin_headers, email_sender)

    response = client.post(
        ACTIVATE_URL,
        json={"token": token, "full_name": "Jane Doe", "password": VALID_PASSWORD},
    )

    assert response.status_code == 200
    assert set(response.json().keys()) == {"status", "message"}


# --- TC-43: every refusal leaves both rows untouched ------------------------


def test_activate_every_refusal_leaves_rows_byte_for_byte_unchanged(
    client: TestClient, admin_user: UserModel, db: Session
) -> None:
    """TC-43: expired, already-accepted, superseded, user-ACTIVE, and
    user-DEACTIVATED preconditions all leave both rows exactly as they were.
    """
    cases = [
        (
            "expired.tc43@example.com",
            UserStatus.PENDING,
            InvitationStatus.PENDING,
            timedelta(hours=-1),
        ),
        (
            "accepted.tc43@example.com",
            UserStatus.ACTIVE,
            InvitationStatus.ACCEPTED,
            timedelta(hours=24),
        ),
        (
            "superseded.tc43@example.com",
            UserStatus.PENDING,
            InvitationStatus.SUPERSEDED,
            timedelta(hours=24),
        ),
        (
            "active.tc43@example.com",
            UserStatus.ACTIVE,
            InvitationStatus.PENDING,
            timedelta(hours=24),
        ),
        (
            "deactivated.tc43@example.com",
            UserStatus.DEACTIVATED,
            InvitationStatus.PENDING,
            timedelta(hours=24),
        ),
    ]

    for email, user_status, invitation_status, expires_delta in cases:
        _, raw_token = _seed_invitation(
            db,
            admin_user=admin_user,
            email=email,
            user_status=user_status,
            invitation_status=invitation_status,
            expires_delta=expires_delta,
        )
        before = _row_snapshot(db, email)

        response = client.post(
            ACTIVATE_URL,
            json={"token": raw_token, "full_name": "Attempted Name", "password": VALID_PASSWORD},
        )
        assert response.status_code == 400, f"expected refusal for {email}"

        after = _row_snapshot(db, email)
        assert before == after, f"row changed for {email}"


# --- TC-45/46: state check reads without mutating ---------------------------


def test_check_token_state_reports_usable_without_mutating(
    client: TestClient, admin_headers: dict[str, str], email_sender: RecordingEmailSender
) -> None:
    """TC-45: a fresh token reports `usable`, and a subsequent activation with
    the same token still succeeds — the check changed nothing.
    """
    token = get_token_from_invite(client, admin_headers, email_sender)

    state_response = client.get(ACTIVATE_URL, params={"token": token})
    assert state_response.status_code == 200
    assert state_response.json()["state"] == "usable"

    activate_response = client.post(
        ACTIVATE_URL,
        json={"token": token, "full_name": "Jane Doe", "password": VALID_PASSWORD},
    )
    assert activate_response.status_code == 200


def test_check_token_state_reports_expired_without_mutating(
    client: TestClient,
    admin_headers: dict[str, str],
    email_sender: RecordingEmailSender,
    frozen_now: object,
    advance_clock: object,
    db: Session,
) -> None:
    """TC-46: an expired token reports `expired`, and the check itself advances
    nothing in the stored invitation.
    """
    token = get_token_from_invite(client, admin_headers, email_sender)
    invitation_before = db.scalars(
        select(InvitationModel).where(InvitationModel.email == TARGET_EMAIL)
    ).one()
    status_before = invitation_before.status

    advance_clock(timedelta(hours=25))  # type: ignore[operator]

    state_response = client.get(ACTIVATE_URL, params={"token": token})
    assert state_response.status_code == 200
    assert state_response.json()["state"] == "expired"

    db.expire_all()
    invitation_after = db.scalars(
        select(InvitationModel).where(InvitationModel.email == TARGET_EMAIL)
    ).one()
    assert invitation_after.status is status_before


# --- TC-47/48: the four non-expiry refusals are indistinguishable ----------


def _four_not_usable_preconditions(db: Session, admin_user: UserModel) -> list[tuple[str, str]]:
    """Returns (label, raw_token) for AC-03/AC-04/AC-05/EC-06's four cases,
    each of which must answer identically to the other three (BR-10).
    """
    cases = [
        ("unrecognised", None, None),
        ("already-used", UserStatus.ACTIVE, InvitationStatus.ACCEPTED),
        ("superseded", UserStatus.PENDING, InvitationStatus.SUPERSEDED),
        ("user-active", UserStatus.ACTIVE, InvitationStatus.PENDING),
    ]
    tokens: list[tuple[str, str]] = []
    for label, user_status, invitation_status in cases:
        if label == "unrecognised":
            tokens.append((label, "unrecognised-token-value"))
            continue
        email = f"{label}.tc4748@example.com"
        _, raw_token = _seed_invitation(
            db,
            admin_user=admin_user,
            email=email,
            user_status=user_status,  # type: ignore[arg-type]
            invitation_status=invitation_status,  # type: ignore[arg-type]
        )
        tokens.append((label, raw_token))
    return tokens


def test_state_check_answers_identically_across_the_four_not_usable_cases(
    client: TestClient, admin_user: UserModel, db: Session
) -> None:
    """TC-47: unrecognised, already-used, superseded, and user-ACTIVE tokens
    all produce the exact same `not_usable` state-check response body.
    """
    bodies = []
    for _label, raw_token in _four_not_usable_preconditions(db, admin_user):
        response = client.get(ACTIVATE_URL, params={"token": raw_token})
        assert response.status_code == 200
        bodies.append(response.json())

    assert all(body == {"state": "not_usable"} for body in bodies)
    assert len({str(b) for b in bodies}) == 1


def test_activation_attempt_answers_identically_across_the_four_not_usable_cases(
    client: TestClient, admin_user: UserModel, db: Session
) -> None:
    """TC-48: the same four preconditions produce byte-identical 400 bodies on
    an actual activation attempt — the oracle AC-03 forbids stays closed.
    """
    bodies = []
    for _label, raw_token in _four_not_usable_preconditions(db, admin_user):
        response = client.post(
            ACTIVATE_URL,
            json={"token": raw_token, "full_name": "Jane Doe", "password": VALID_PASSWORD},
        )
        assert response.status_code == 400
        bodies.append(response.json())

    assert all(body == bodies[0] for body in bodies)
    assert bodies[0]["error_code"] == "INVITATION_TOKEN_INVALID"


# --- TC-49: no authentication required --------------------------------------


def test_activate_endpoints_require_no_authentication(
    client: TestClient, admin_headers: dict[str, str], email_sender: RecordingEmailSender
) -> None:
    """TC-49: both routes process the request with no credentials at all — an
    invited person has no account yet, so requiring auth would be impossible.
    """
    token = get_token_from_invite(client, admin_headers, email_sender)

    state_response = client.get(ACTIVATE_URL, params={"token": token})
    assert state_response.status_code != 401

    activate_response = client.post(
        ACTIVATE_URL,
        json={"token": token, "full_name": "Jane Doe", "password": VALID_PASSWORD},
    )
    assert activate_response.status_code != 401
    assert activate_response.status_code == 200


# --- TC-50/51: wrong user state ---------------------------------------------


def test_activate_token_whose_user_is_active_is_refused(
    client: TestClient, admin_user: UserModel, db: Session
) -> None:
    """TC-50: a token whose user has since become ACTIVE is refused generically."""
    _, raw_token = _seed_invitation(
        db,
        admin_user=admin_user,
        email="already-active.tc50@example.com",
        user_status=UserStatus.ACTIVE,
        invitation_status=InvitationStatus.PENDING,
    )

    response = client.post(
        ACTIVATE_URL,
        json={"token": raw_token, "full_name": "Jane Doe", "password": VALID_PASSWORD},
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "INVITATION_TOKEN_INVALID"


def test_activate_token_whose_user_is_deactivated_is_refused(
    client: TestClient, admin_user: UserModel, db: Session
) -> None:
    """TC-51: a token whose user is DEACTIVATED is refused — a withdrawn
    account is not restored by an old invitation link.
    """
    _, raw_token = _seed_invitation(
        db,
        admin_user=admin_user,
        email="deactivated.tc51@example.com",
        user_status=UserStatus.DEACTIVATED,
        invitation_status=InvitationStatus.PENDING,
    )

    response = client.post(
        ACTIVATE_URL,
        json={"token": raw_token, "full_name": "Jane Doe", "password": VALID_PASSWORD},
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "INVITATION_TOKEN_INVALID"


# --- TC-52: exact match, no normalisation ------------------------------------


def test_activate_token_with_altered_whitespace_does_not_match(
    client: TestClient, admin_headers: dict[str, str], email_sender: RecordingEmailSender
) -> None:
    """TC-52: a token with a leading space is compared exactly and treated as
    unrecognised — no normalisation is applied, unlike an email address.
    """
    token = get_token_from_invite(client, admin_headers, email_sender)

    response = client.post(
        ACTIVATE_URL,
        json={"token": " " + token, "full_name": "Jane Doe", "password": VALID_PASSWORD},
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "INVITATION_TOKEN_INVALID"


# --- TC-53: exact-instant expiry boundary -----------------------------------


def test_activate_token_at_exact_instant_of_expiry_is_treated_as_expired(
    client: TestClient, admin_user: UserModel, db: Session
) -> None:
    """TC-53: expiry is valid strictly *until* its instant — a token whose
    expiry equals the moment of use is already too late (EC-10, BR-03).
    """
    _, raw_token = _seed_invitation(
        db,
        admin_user=admin_user,
        email="exact-expiry.tc53@example.com",
        user_status=UserStatus.PENDING,
        invitation_status=InvitationStatus.PENDING,
        expires_delta=timedelta(seconds=0),
    )

    response = client.post(
        ACTIVATE_URL,
        json={"token": raw_token, "full_name": "Jane Doe", "password": VALID_PASSWORD},
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "INVITATION_TOKEN_EXPIRED"


# --- TC-54: the constructable half of the concurrency guard -----------------


def test_sequential_double_submission_of_one_token_succeeds_exactly_once(
    client: TestClient,
    admin_headers: dict[str, str],
    email_sender: RecordingEmailSender,
    db: Session,
) -> None:
    """TC-54: two immediate submissions of the identical payload — exactly one
    returns 200 and activates the account, the other 400 INVITATION_TOKEN_INVALID.
    True parallel writers are deferred to a PostgreSQL run (QF-02).
    """
    token = get_token_from_invite(client, admin_headers, email_sender)
    payload = {"token": token, "full_name": "Jane Doe", "password": VALID_PASSWORD}

    first = client.post(ACTIVATE_URL, json=payload)
    second = client.post(ACTIVATE_URL, json=payload)

    statuses = sorted([first.status_code, second.status_code])
    assert statuses == [200, 400]

    db.expire_all()
    user = user_repo.get_by_email(db, TARGET_EMAIL)
    assert user is not None and user.status is UserStatus.ACTIVE


# --- TC-55: expiry never overrides another refusal reason -------------------


def test_expiry_never_overrides_another_refusal_reason(
    client: TestClient, admin_user: UserModel, db: Session
) -> None:
    """TC-55: four preconditions that are unusable AND well past their TTL
    still answer `not_usable`, never `expired` — on both endpoints. If expiry
    were checked before outstanding/user state, this would flip after 24h.
    """
    cases = [
        ("accepted-expired.tc55@example.com", UserStatus.ACTIVE, InvitationStatus.ACCEPTED),
        ("superseded-expired.tc55@example.com", UserStatus.PENDING, InvitationStatus.SUPERSEDED),
        ("active-expired.tc55@example.com", UserStatus.ACTIVE, InvitationStatus.PENDING),
        ("deactivated-expired.tc55@example.com", UserStatus.DEACTIVATED, InvitationStatus.PENDING),
    ]

    for email, user_status, invitation_status in cases:
        _, raw_token = _seed_invitation(
            db,
            admin_user=admin_user,
            email=email,
            user_status=user_status,
            invitation_status=invitation_status,
            expires_delta=timedelta(hours=-48),  # well past the 24h TTL
        )

        state_response = client.get(ACTIVATE_URL, params={"token": raw_token})
        assert state_response.json()["state"] == "not_usable", email

        activate_response = client.post(
            ACTIVATE_URL,
            json={"token": raw_token, "full_name": "Jane Doe", "password": VALID_PASSWORD},
        )
        assert activate_response.status_code == 400, email
        assert activate_response.json()["error_code"] == "INVITATION_TOKEN_INVALID", email


# --- TC-56: full name bounded at the column width ---------------------------


def test_activate_full_name_over_255_characters_rejected_not_truncated(
    client: TestClient,
    admin_headers: dict[str, str],
    email_sender: RecordingEmailSender,
    db: Session,
) -> None:
    """TC-56: a 256-character full name is rejected with 422, deterministically
    — not silently truncated and not left to fail as a 500 on PostgreSQL.
    """
    token = get_token_from_invite(client, admin_headers, email_sender)
    over_long_name = "A" * 256

    response = client.post(
        ACTIVATE_URL,
        json={"token": token, "full_name": over_long_name, "password": VALID_PASSWORD},
    )

    assert response.status_code == 422
    fields = [f["location"][-1] for f in response.json()["details"]["fields"]]
    assert "full_name" in fields

    db.expire_all()
    user = user_repo.get_by_email(db, TARGET_EMAIL)
    assert user is not None and user.status is UserStatus.PENDING
