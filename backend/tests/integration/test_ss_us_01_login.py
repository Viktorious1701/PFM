"""SS-US-01 — Login.

One test per test case in specs/002-system-security/test_cases.md (TC-01..TC-11).
Names state what the test proves, not what it calls.
"""

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import Settings
from app.models.user import UserModel, UserRole, UserStatus

LOGIN_URL = "/api/v1/auth/login"
KNOWN_EMAIL = "jane@gmail.com"
KNOWN_PASSWORD = "SecurePassword123!"


def _make_user(db: Session, *, email: str, status: UserStatus, password: str | None) -> UserModel:
    user = UserModel(
        email=email,
        password_hash=security.hash_password(password) if password else None,
        full_name="Jane Doe" if password else None,
        status=status,
        role=UserRole.USER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_successful_login_for_active_account_issues_a_signed_token(
    client: TestClient, db: Session, settings: Settings
) -> None:
    """TC-01: correct email + password for ACTIVE -> 200, valid JWT."""
    _make_user(db, email=KNOWN_EMAIL, status=UserStatus.ACTIVE, password=KNOWN_PASSWORD)

    response = client.post(LOGIN_URL, json={"email": KNOWN_EMAIL, "password": KNOWN_PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.jwt_ttl_minutes * 60
    assert body["role"] == "USER"

    decoded = jwt.decode(
        body["access_token"], settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    user = db.query(UserModel).filter_by(email=KNOWN_EMAIL).one()
    assert decoded["sub"] == user.id
    assert decoded["role"] == "USER"


def test_pending_account_refused_regardless_of_password_submitted(
    client: TestClient, db: Session
) -> None:
    """TC-02: PENDING has no password_hash, so any password gets ACCOUNT_NOT_ACTIVATED."""
    _make_user(db, email="pending@gmail.com", status=UserStatus.PENDING, password=None)

    response = client.post(
        LOGIN_URL, json={"email": "pending@gmail.com", "password": "anything-at-all-1!"}
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "ACCOUNT_NOT_ACTIVATED"
    assert response.json()["message"] == (
        "Your account is not activated. Please check your email invitation."
    )


def test_unknown_email_and_wrong_password_against_active_both_return_401(
    client: TestClient, db: Session
) -> None:
    """TC-03: unknown email and wrong password (ACTIVE account) both -> 401 INVALID_CREDENTIALS."""
    _make_user(db, email=KNOWN_EMAIL, status=UserStatus.ACTIVE, password=KNOWN_PASSWORD)

    unknown = client.post(LOGIN_URL, json={"email": "nobody@gmail.com", "password": "whatever1!"})
    wrong_password = client.post(LOGIN_URL, json={"email": KNOWN_EMAIL, "password": "WrongPass1!"})

    for response in (unknown, wrong_password):
        assert response.status_code == 401
        assert response.json()["error_code"] == "INVALID_CREDENTIALS"


def test_unknown_wrong_password_and_deactivated_answer_identically(
    client: TestClient, db: Session
) -> None:
    """TC-04: unknown email, wrong password (ACTIVE), and DEACTIVATED (correct password)
    all produce byte-identical 401 bodies.
    """
    _make_user(db, email="active@gmail.com", status=UserStatus.ACTIVE, password=KNOWN_PASSWORD)
    _make_user(
        db, email="deactivated@gmail.com", status=UserStatus.DEACTIVATED, password=KNOWN_PASSWORD
    )

    unknown = client.post(LOGIN_URL, json={"email": "nobody@gmail.com", "password": "whatever1!"})
    wrong_password = client.post(
        LOGIN_URL, json={"email": "active@gmail.com", "password": "WrongPass1!"}
    )
    deactivated = client.post(
        LOGIN_URL, json={"email": "deactivated@gmail.com", "password": KNOWN_PASSWORD}
    )

    bodies = [r.json() for r in (unknown, wrong_password, deactivated)]
    assert all(r.status_code == 401 for r in (unknown, wrong_password, deactivated))
    assert all(body == bodies[0] for body in bodies)
    assert bodies[0]["error_code"] == "INVALID_CREDENTIALS"


def test_deactivated_account_with_correct_password_refused_generically(
    client: TestClient, db: Session
) -> None:
    """TC-05: DEACTIVATED + correct password -> 401 INVALID_CREDENTIALS, not 403."""
    _make_user(
        db, email="deactivated@gmail.com", status=UserStatus.DEACTIVATED, password=KNOWN_PASSWORD
    )

    response = client.post(
        LOGIN_URL, json={"email": "deactivated@gmail.com", "password": KNOWN_PASSWORD}
    )

    assert response.status_code == 401
    assert response.json()["error_code"] == "INVALID_CREDENTIALS"


def test_deactivated_account_with_wrong_password_refused_identically_to_correct(
    client: TestClient, db: Session
) -> None:
    """TC-06: DEACTIVATED + wrong password -> same 401 as the correct-password case —
    the password check still runs for an account that has one.
    """
    _make_user(
        db, email="deactivated@gmail.com", status=UserStatus.DEACTIVATED, password=KNOWN_PASSWORD
    )

    correct = client.post(
        LOGIN_URL, json={"email": "deactivated@gmail.com", "password": KNOWN_PASSWORD}
    )
    wrong = client.post(
        LOGIN_URL, json={"email": "deactivated@gmail.com", "password": "WrongPass1!"}
    )

    assert correct.status_code == wrong.status_code == 401
    assert correct.json() == wrong.json()


def test_response_and_audit_log_never_contain_password_or_hash(
    client: TestClient, db: Session, caplog: pytest.LogCaptureFixture
) -> None:
    """TC-07: neither the response body nor the captured audit line contains
    the submitted password or the stored hash.
    """
    user = _make_user(db, email=KNOWN_EMAIL, status=UserStatus.ACTIVE, password=KNOWN_PASSWORD)

    with caplog.at_level("INFO", logger="app.audit"):
        response = client.post(LOGIN_URL, json={"email": KNOWN_EMAIL, "password": KNOWN_PASSWORD})

    assert response.status_code == 200
    assert KNOWN_PASSWORD not in response.text
    assert user.password_hash not in response.text

    audit_lines = [r.getMessage() for r in caplog.records if r.name == "app.audit"]
    assert audit_lines
    assert all(
        KNOWN_PASSWORD not in line and user.password_hash not in line for line in audit_lines
    )


def test_refused_login_emits_audit_record_marked_failure(
    client: TestClient, db: Session, caplog: pytest.LogCaptureFixture
) -> None:
    """TC-08: a refused login (unknown email) emits one FAILURE audit record."""
    with caplog.at_level("INFO", logger="app.audit"):
        response = client.post(
            LOGIN_URL, json={"email": "nobody@gmail.com", "password": "whatever1!"}
        )

    assert response.status_code == 401
    audit_lines = [r.getMessage() for r in caplog.records if r.name == "app.audit"]
    failure_lines = [line for line in audit_lines if "LOGIN_FAILED" in line]
    assert len(failure_lines) == 1
    assert "FAILURE" in failure_lines[0]
    assert "nobody@gmail.com" in failure_lines[0]


@pytest.mark.parametrize(
    "payload",
    [
        {"email": KNOWN_EMAIL},
        {"password": KNOWN_PASSWORD},
        {"email": "not-an-email", "password": KNOWN_PASSWORD},
        {"email": KNOWN_EMAIL, "password": ""},
    ],
)
def test_malformed_or_missing_payload_rejected_with_422_before_any_lookup(
    client: TestClient, db: Session, caplog: pytest.LogCaptureFixture, payload: dict[str, str]
) -> None:
    """TC-09: missing/malformed fields -> 422, no audit record emitted."""
    with caplog.at_level("INFO", logger="app.audit"):
        response = client.post(LOGIN_URL, json=payload)

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"
    audit_lines = [r.getMessage() for r in caplog.records if r.name == "app.audit"]
    assert audit_lines == []


def test_login_accepts_a_request_with_no_bearer_token(client: TestClient, db: Session) -> None:
    """TC-10: no Authorization header at all -> processed normally, never 401 for its absence."""
    _make_user(db, email=KNOWN_EMAIL, status=UserStatus.ACTIVE, password=KNOWN_PASSWORD)

    response = client.post(LOGIN_URL, json={"email": KNOWN_EMAIL, "password": KNOWN_PASSWORD})

    assert "authorization" not in {k.lower() for k in response.request.headers}
    assert response.status_code == 200


def test_email_differing_by_case_and_whitespace_still_matches(
    client: TestClient, db: Session
) -> None:
    """TC-11: "  Jane@Gmail.COM  " matches the stored "jane@gmail.com" account."""
    _make_user(db, email=KNOWN_EMAIL, status=UserStatus.ACTIVE, password=KNOWN_PASSWORD)

    response = client.post(
        LOGIN_URL, json={"email": "  Jane@Gmail.COM  ", "password": KNOWN_PASSWORD}
    )

    assert response.status_code == 200
