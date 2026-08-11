"""UM-US-03 — List Users.

One test per test case in specs/001-user-onboarding/test_cases.md (TC-57..TC-72).
Names state what the test proves, not what it calls.

`_seed_user` constructs preconditions the public API cannot itself produce:
a controlled, explicit `created_at` for the ordering/pagination assertions
(TC-57, TC-62, TC-63, TC-69, TC-70, TC-72), and a `DEACTIVATED` account for
TC-68 — no story in this MVP round has a public path that creates one
(spec Out-of-scope note; test_cases QF-02). This mirrors
`test_um_us_02_activate.py`'s own `_seed_invitation` technique.

**Why `created_at` is set explicitly rather than via `frozen_now`/`advance_clock`:**
`UserModel.created_at`'s column default is `mapped_column(default=clock.utcnow)`
(`app/models/user.py`) — that binds the *function object* `clock.utcnow`
at import time, when `app.models.user` is first imported (at test collection,
long before any test runs). Monkeypatching the module attribute
`app.core.clock.utcnow` afterwards — what `frozen_now`/`advance_clock` do —
replaces the name in the module's namespace, but the already-bound default
callable keeps its original reference and keeps returning the real wall
clock. This is unlike `invitation_service`'s own `clock.utcnow()` calls,
which look the attribute up fresh on every call and do observe the patch.
Concretely: every row's `created_at` in this file is real wall-clock time
unless set explicitly. This story's ACs don't require frozen instants, only
correct *relative* order and *count*, so every multi-user test anchors off
`admin_user.created_at` (itself real time) and adds strictly increasing
offsets — deterministic, and not a product defect since no AC asks for a
frozen `created_at`.
"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import Settings
from app.models.user import UserModel, UserRole, UserStatus

LIST_URL = "/api/v1/users"


# --- helpers ------------------------------------------------------------


def _seed_user(
    db: Session,
    *,
    email: str,
    created_at: datetime,
    status: UserStatus = UserStatus.ACTIVE,
    full_name: str | None = "Seeded User",
    role: UserRole = UserRole.USER,
) -> UserModel:
    """Directly arrange a user row with a controlled `created_at`, and/or a
    status (`DEACTIVATED`) no public path can produce this round.

    A `PENDING` user always gets no credentials and no name (spec AC-07,
    BR-06) regardless of the `full_name` argument, matching every PENDING
    account this codebase can otherwise produce.
    """
    is_pending = status is UserStatus.PENDING
    user = UserModel(
        email=email,
        password_hash=None if is_pending else security.hash_password("Str0ng-Passw0rd!"),
        full_name=None if is_pending else full_name,
        status=status,
        role=role,
        created_at=created_at,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _after(anchor: datetime, minutes: int) -> datetime:
    """One instant of a strictly increasing sequence starting after `anchor`."""
    return anchor + timedelta(minutes=minutes)


def _items_by_email(body: dict[str, object]) -> dict[str, dict[str, object]]:
    items = body["items"]
    assert isinstance(items, list)
    return {item["email"]: item for item in items}  # type: ignore[index]


def _expired_token(admin_user: UserModel, settings: Settings) -> str:
    return security.encode_jwt(
        subject=admin_user.id,
        role=admin_user.role.value,
        secret=settings.jwt_secret,
        ttl_minutes=-1,  # already past
        algorithm=settings.jwt_algorithm,
    )


# --- TC-57/58: the happy path envelope --------------------------------------


def test_admin_lists_all_users_newest_first_order(
    client: TestClient,
    admin_headers: dict[str, str],
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-57: three users created in sequence at distinct, controlled instants
    all appear, ordered newest first — c@x.com, then b@x.com, then a@x.com.
    """
    anchor = admin_user.created_at
    _seed_user(db, email="a@x.com", created_at=_after(anchor, 1))
    _seed_user(db, email="b@x.com", created_at=_after(anchor, 2))
    _seed_user(db, email="c@x.com", created_at=_after(anchor, 3))

    response = client.get(LIST_URL, headers=admin_headers)

    assert response.status_code == 200
    emails = [item["email"] for item in response.json()["items"]]
    assert {"a@x.com", "b@x.com", "c@x.com"}.issubset(set(emails))
    assert emails.index("c@x.com") < emails.index("b@x.com") < emails.index("a@x.com")


def test_response_item_exposes_exactly_five_fields_never_password_hash(
    client: TestClient,
    admin_headers: dict[str, str],
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-58: every item exposes exactly id, email, full_name, status,
    created_at — no more, and in particular no password_hash.
    """
    _seed_user(db, email="one@example.com", created_at=_after(admin_user.created_at, 1))

    response = client.get(LIST_URL, headers=admin_headers)

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 1
    expected_keys = {"id", "email", "full_name", "status", "created_at"}
    for item in items:
        assert set(item.keys()) == expected_keys


# --- TC-59/60/61: authorization and authentication ---------------------------


def test_non_admin_caller_is_denied_with_403(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-59: a non-ADMIN caller is denied with 403; no items are returned."""
    response = client.get(LIST_URL, headers=user_headers)

    assert response.status_code == 403
    body = response.json()
    assert body["error_code"] == "FORBIDDEN"
    assert "items" not in body


def test_unauthenticated_or_invalid_credential_caller_is_denied_with_401(
    client: TestClient, admin_user: UserModel, settings: Settings
) -> None:
    """TC-60: no credentials, and separately an expired token, both -> 401;
    no items are returned either way.
    """
    no_auth = client.get(LIST_URL)
    assert no_auth.status_code == 401
    assert no_auth.json()["error_code"] == "NOT_AUTHENTICATED"
    assert "items" not in no_auth.json()

    expired = client.get(
        LIST_URL, headers={"Authorization": f"Bearer {_expired_token(admin_user, settings)}"}
    )
    assert expired.status_code == 401
    assert expired.json()["error_code"] == "NOT_AUTHENTICATED"
    assert "items" not in expired.json()


def test_credentials_are_evaluated_before_any_query_parameter(client: TestClient) -> None:
    """TC-61: an out-of-range `page` from an unauthenticated caller still
    answers 401, not 422 — mirrors UM-US-01 TC-13's ordering.
    """
    response = client.get(LIST_URL, params={"page": 0})

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"


# --- TC-62/63: pagination defaults and explicit values -----------------------


def test_default_page_is_1_of_size_25_with_accurate_total(
    client: TestClient,
    admin_headers: dict[str, str],
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-62: no page/page_size supplied -> page 1, page_size 25, all users
    (fewer than the page size) returned, total accurate (admin + 2 = 3).
    """
    anchor = admin_user.created_at
    _seed_user(db, email="two@example.com", created_at=_after(anchor, 1))
    _seed_user(db, email="three@example.com", created_at=_after(anchor, 2))

    response = client.get(LIST_URL, headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 25
    assert len(body["items"]) == 3
    assert body["total"] == 3


def test_explicit_page_and_page_size_within_range_return_that_page_and_accurate_total(
    client: TestClient,
    admin_headers: dict[str, str],
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-63: page=2, page_size=2 over 5 total users (admin + 4) -> that page's
    two users (the third- and fourth-newest) and total=5.
    """
    anchor = admin_user.created_at
    emails = ["u1@example.com", "u2@example.com", "u3@example.com", "u4@example.com"]
    for i, email in enumerate(emails, start=1):
        _seed_user(db, email=email, created_at=_after(anchor, i))

    response = client.get(LIST_URL, params={"page": 2, "page_size": 2}, headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 2
    assert body["page_size"] == 2
    assert body["total"] == 5
    assert len(body["items"]) == 2
    # Newest first overall: u4, u3, u2, u1, admin. Page 2 of size 2 -> u2, u1.
    assert [item["email"] for item in body["items"]] == ["u2@example.com", "u1@example.com"]


# --- TC-64/65/66/67: pagination boundary validation --------------------------


@pytest.mark.parametrize("bad_page", [0, -1, "abc"])
def test_a_non_positive_or_non_integer_page_is_rejected_with_422(
    client: TestClient, admin_headers: dict[str, str], bad_page: object
) -> None:
    """TC-64: page in {0, -1, "abc"} -> 422 VALIDATION_ERROR naming `page`;
    no items are returned.
    """
    response = client.get(LIST_URL, params={"page": bad_page}, headers=admin_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    fields = [f["location"][-1] for f in body["details"]["fields"]]
    assert "page" in fields
    assert "items" not in body


@pytest.mark.parametrize("bad_page_size", [0, -1, "abc"])
def test_a_non_positive_or_non_integer_page_size_is_rejected_with_422(
    client: TestClient, admin_headers: dict[str, str], bad_page_size: object
) -> None:
    """TC-65: page_size in {0, -1, "abc"} -> 422 VALIDATION_ERROR naming
    `page_size`; no items are returned.
    """
    response = client.get(LIST_URL, params={"page_size": bad_page_size}, headers=admin_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    fields = [f["location"][-1] for f in body["details"]["fields"]]
    assert "page_size" in fields
    assert "items" not in body


def test_a_page_size_above_the_maximum_is_rejected_with_422(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    """TC-66: page_size=101 -> 422 VALIDATION_ERROR naming `page_size`; not
    silently capped at 100.
    """
    response = client.get(LIST_URL, params={"page_size": 101}, headers=admin_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    fields = [f["location"][-1] for f in body["details"]["fields"]]
    assert "page_size" in fields


def test_a_page_size_of_exactly_100_is_accepted(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    """TC-67: page_size=100 -> 200. The cap is a ceiling, not a target: only
    101 (TC-66) is rejected.
    """
    response = client.get(LIST_URL, params={"page_size": 100}, headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["page_size"] == 100


# --- TC-68: every status appears -------------------------------------------


def test_every_account_status_appears_in_the_list_carrying_its_actual_status(
    client: TestClient,
    admin_headers: dict[str, str],
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-68: PENDING, ACTIVE, and DEACTIVATED accounts (the last constructed
    directly against the store — QF-02, no public path creates one this
    round) all appear, each reporting its own actual status.
    """
    anchor = admin_user.created_at
    pending = _seed_user(
        db,
        email="pending.tc68@example.com",
        created_at=_after(anchor, 1),
        status=UserStatus.PENDING,
    )
    active = _seed_user(
        db, email="active.tc68@example.com", created_at=_after(anchor, 2), status=UserStatus.ACTIVE
    )
    deactivated = _seed_user(
        db,
        email="deactivated.tc68@example.com",
        created_at=_after(anchor, 3),
        status=UserStatus.DEACTIVATED,
    )

    response = client.get(LIST_URL, headers=admin_headers)

    assert response.status_code == 200
    by_email = _items_by_email(response.json())
    assert by_email[pending.email]["status"] == "PENDING"
    assert by_email[active.email]["status"] == "ACTIVE"
    assert by_email[deactivated.email]["status"] == "DEACTIVATED"


# --- TC-69: sole account -----------------------------------------------------


def test_caller_with_no_one_else_in_the_system_sees_just_their_own_account(
    client: TestClient, admin_headers: dict[str, str], admin_user: UserModel
) -> None:
    """TC-69: with no other user in the system, the list contains exactly the
    requesting ADMIN, total 1 — not an error or a null result.
    """
    response = client.get(LIST_URL, headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["email"] == admin_user.email


# --- TC-70: page beyond the last ---------------------------------------------


def test_a_page_beyond_the_last_available_page_returns_an_empty_list_with_accurate_total(
    client: TestClient,
    admin_headers: dict[str, str],
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-70: page=5 over 3 total users (admin + 2) -> 200, empty items,
    total still 3 — not a 404.
    """
    anchor = admin_user.created_at
    _seed_user(db, email="only1@example.com", created_at=_after(anchor, 1))
    _seed_user(db, email="only2@example.com", created_at=_after(anchor, 2))

    response = client.get(LIST_URL, params={"page": 5, "page_size": 25}, headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 3


# --- TC-71: unset full name --------------------------------------------------


def test_pending_user_with_no_full_name_yet_is_listed_with_explicit_null(
    client: TestClient,
    admin_headers: dict[str, str],
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-71: a PENDING user who has never activated is present in `items`
    with `full_name` equal to JSON `null` — not omitted, not an error
    (representation per QF-01).
    """
    pending = _seed_user(
        db,
        email="never-activated.tc71@example.com",
        created_at=_after(admin_user.created_at, 1),
        status=UserStatus.PENDING,
    )

    response = client.get(LIST_URL, headers=admin_headers)

    assert response.status_code == 200
    by_email = _items_by_email(response.json())
    assert pending.email in by_email
    assert by_email[pending.email]["full_name"] is None


# --- TC-72: paging through every page ----------------------------------------


def test_paging_through_every_page_returns_every_user_exactly_once_in_stable_order(
    client: TestClient,
    admin_headers: dict[str, str],
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-72: five total users (admin + 4, each at a distinct, controlled
    instant), paged with page_size=2 across page=1,2,3 -> the concatenation
    of all pages' items contains every user exactly once, no duplicate, no
    gap, in the same newest-first order TC-57 established.
    """
    anchor = admin_user.created_at
    emails = ["p1@example.com", "p2@example.com", "p3@example.com", "p4@example.com"]
    for i, email in enumerate(emails, start=1):
        _seed_user(db, email=email, created_at=_after(anchor, i))

    all_expected = {*emails, admin_user.email}
    seen: list[str] = []
    for page in (1, 2, 3):
        response = client.get(
            LIST_URL, params={"page": page, "page_size": 2}, headers=admin_headers
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 5
        seen.extend(item["email"] for item in body["items"])

    assert len(seen) == 5
    assert len(set(seen)) == 5
    assert set(seen) == all_expected
    # Newest first, stable across page boundaries: p4, p3, p2, p1, admin.
    assert seen == [
        "p4@example.com",
        "p3@example.com",
        "p2@example.com",
        "p1@example.com",
        admin_user.email,
    ]
