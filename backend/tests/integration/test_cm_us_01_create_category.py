"""CM-US-01 — Create a Category.

One test per test case in specs/004-category-management/test_cases.md
(TC-01..TC-17). Names state what the test proves, not what it calls.

`_category_count` mirrors the existing `select(func.count()).select_from(...)`
idiom already used by `test_wm_us_01_create_wallet.py` for "nothing was
persisted" assertions.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import CategoryModel
from app.models.user import UserModel

CATEGORIES_URL = "/api/v1/categories"


# --- helpers ----------------------------------------------------------------


def _category_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(CategoryModel)) or 0


def _valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Groceries",
        "type": "EXPENSE",
    }
    payload.update(overrides)
    return payload


def _fields(body: dict[str, object]) -> list[str]:
    details = body["details"]
    assert isinstance(details, dict)
    return [f["location"][-1] for f in details["fields"]]  # type: ignore[index]


# --- TC-01/TC-02: the happy path ---------------------------------------------


def test_authenticated_user_creates_an_expense_category_201_with_created_category(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel
) -> None:
    """TC-01: name "Groceries", type "EXPENSE" -> 201; body carries id,
    user_id (caller's), name, type exactly as submitted.
    """
    response = client.post(
        CATEGORIES_URL, json=_valid_payload(name="Groceries", type="EXPENSE"), headers=user_headers
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == normal_user.id
    assert body["name"] == "Groceries"
    assert body["type"] == "EXPENSE"
    assert body.get("id")


def test_authenticated_user_creates_an_income_category_201_with_created_category(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel
) -> None:
    """TC-02: name "Salary", type "INCOME" -> 201; body carries id, user_id
    (caller's), name, type exactly as submitted.
    """
    response = client.post(
        CATEGORIES_URL, json=_valid_payload(name="Salary", type="INCOME"), headers=user_headers
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == normal_user.id
    assert body["name"] == "Salary"
    assert body["type"] == "INCOME"
    assert body.get("id")


# --- TC-03: persistence -------------------------------------------------------


def test_creating_a_category_persists_exactly_one_row_with_submitted_fields(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-03: exactly one `categories` row exists carrying the submitted
    `name` and `type`, owned by the caller.
    """
    response = client.post(CATEGORIES_URL, json=_valid_payload(), headers=user_headers)

    assert response.status_code == 201
    assert _category_count(db) == 1
    row = db.scalars(select(CategoryModel)).one()
    assert row.user_id == normal_user.id
    assert row.name == "Groceries"
    assert row.type.value == "EXPENSE"


# --- TC-04: authentication ----------------------------------------------------


def test_unauthenticated_caller_is_denied_with_401(client: TestClient, db: Session) -> None:
    """TC-04: no `Authorization` header -> 401 NOT_AUTHENTICATED; nothing
    persisted.
    """
    response = client.post(CATEGORIES_URL, json=_valid_payload())

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"
    assert _category_count(db) == 0


# --- TC-05/TC-06/TC-07: name validation ---------------------------------------


def test_a_missing_category_name_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-05: `name` absent -> 422 VALIDATION_ERROR naming `name`; nothing
    persisted.
    """
    payload = _valid_payload()
    del payload["name"]

    response = client.post(CATEGORIES_URL, json=payload, headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "name" in _fields(body)
    assert _category_count(db) == 0


def test_empty_or_whitespace_only_category_name_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-06: `name` `""` and, separately, `"   "` -> each 422 naming `name`;
    nothing persisted.
    """
    for bad_name in ("", "   "):
        response = client.post(
            CATEGORIES_URL, json=_valid_payload(name=bad_name), headers=user_headers
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error_code"] == "VALIDATION_ERROR"
        assert "name" in _fields(body)

    assert _category_count(db) == 0


def test_a_category_name_exceeding_100_characters_is_rejected_not_truncated(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-07: `name` of 101 characters -> 422; not truncated, nothing
    persisted.
    """
    response = client.post(
        CATEGORIES_URL, json=_valid_payload(name="x" * 101), headers=user_headers
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"
    assert _category_count(db) == 0


# --- TC-08: missing type -------------------------------------------------------


def test_a_missing_category_type_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-08: `type` absent -> 422 VALIDATION_ERROR naming `type`; nothing
    persisted.
    """
    payload = _valid_payload()
    del payload["type"]

    response = client.post(CATEGORIES_URL, json=payload, headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "type" in _fields(body)
    assert _category_count(db) == 0


# --- TC-09/TC-10/TC-11: type vocabulary is closed and exact --------------------


@pytest.mark.parametrize("bad_type", ["SAVINGS", "TRANSFER", ""])
def test_a_category_type_value_that_is_neither_income_nor_expense_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], db: Session, bad_type: str
) -> None:
    """TC-09: `type` in turn "SAVINGS", "TRANSFER", "" -> each 422 whose
    `details` names `type`; nothing persisted (assertion technique per
    QF-02).
    """
    response = client.post(CATEGORIES_URL, json=_valid_payload(type=bad_type), headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "type" in _fields(body)
    assert _category_count(db) == 0


@pytest.mark.parametrize("bad_type", ["expense", "Income"])
def test_a_lowercase_or_mixed_case_category_type_is_rejected_not_case_folded(
    client: TestClient, user_headers: dict[str, str], db: Session, bad_type: str
) -> None:
    """TC-10: `type` "expense" and, separately, "Income" -> each 422 whose
    `details` names `type`; no category is created with `type` "EXPENSE" or
    "INCOME" — not case-folded and accepted (assertion technique per QF-02).
    """
    response = client.post(CATEGORIES_URL, json=_valid_payload(type=bad_type), headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "type" in _fields(body)
    assert _category_count(db) == 0


@pytest.mark.parametrize("bad_type", [" EXPENSE", "INCOME "])
def test_a_category_type_with_surrounding_whitespace_is_rejected_not_trimmed(
    client: TestClient, user_headers: dict[str, str], db: Session, bad_type: str
) -> None:
    """TC-11: `type` " EXPENSE" and, separately, "INCOME " -> each 422 whose
    `details` names `type`; nothing persisted — unlike `name`, `type`
    receives no trimming (assertion technique per QF-02).
    """
    response = client.post(CATEGORIES_URL, json=_valid_payload(type=bad_type), headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "type" in _fields(body)
    assert _category_count(db) == 0


# --- TC-12: ownership cannot be overridden by the payload ----------------------


def test_created_category_is_always_owned_by_caller_never_by_payload_value(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    normal_user: UserModel,
    admin_user: UserModel,
) -> None:
    """TC-12: caller A (`normal_user`) submits an otherwise valid payload
    that additionally includes an unrecognised `"user_id"` key naming caller
    B (`admin_user`) -> 201; the created category's `user_id` equals A's id,
    never B's — the extra key is ignored, not honoured (assertion technique
    per QF-01).
    """
    payload = _valid_payload()
    payload["user_id"] = admin_user.id

    response = client.post(CATEGORIES_URL, json=payload, headers=user_headers)

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == normal_user.id
    assert body["user_id"] != admin_user.id


# --- TC-13: unrecognised `icon` field is silently ignored ----------------------


def test_an_unrecognised_icon_field_submitted_with_the_request_is_silently_ignored(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-13: an otherwise valid payload additionally includes
    `"icon": "shopping-cart"` -> 201; the category is built from `name` and
    `type` alone, and the response carries no `icon` key at all (assertion
    technique per QF-03).
    """
    payload = _valid_payload()
    payload["icon"] = "shopping-cart"

    response = client.post(CATEGORIES_URL, json=payload, headers=user_headers)

    assert response.status_code == 201
    body = response.json()
    assert "icon" not in body


# --- TC-14: exact response shape ----------------------------------------------


def test_response_exposes_exactly_the_four_documented_fields(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-14: response body's keys are exactly id, user_id, name, type — no
    more, and in particular no `icon` (plan.md A4, QF-04).
    """
    response = client.post(CATEGORIES_URL, json=_valid_payload(), headers=user_headers)

    assert response.status_code == 201
    expected_keys = {"id", "user_id", "name", "type"}
    assert set(response.json().keys()) == expected_keys


# --- TC-15: no uniqueness constraint on name -----------------------------------


def test_two_categories_with_the_same_name_for_the_same_user_both_succeed(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-15: a User with one existing category named "Utilities" submits
    another also named "Utilities" (type "EXPENSE" both times) -> 201; two
    rows exist, both named "Utilities", with distinct ids.
    """
    first = client.post(CATEGORIES_URL, json=_valid_payload(name="Utilities"), headers=user_headers)
    assert first.status_code == 201

    second = client.post(
        CATEGORIES_URL, json=_valid_payload(name="Utilities"), headers=user_headers
    )
    assert second.status_code == 201

    assert first.json()["id"] != second.json()["id"]
    assert _category_count(db) == 2
    names = {row.name for row in db.scalars(select(CategoryModel)).all()}
    assert names == {"Utilities"}


# --- TC-16: grouped validation failures ---------------------------------------


def test_multiple_validation_failures_in_one_submission_are_reported_together(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-16: `name` `""` and `type` "SAVINGS" in the same request -> a
    single 422 whose `details` identifies both fields, not just the first
    one encountered.
    """
    response = client.post(
        CATEGORIES_URL,
        json=_valid_payload(name="", type="SAVINGS"),
        headers=user_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    fields = _fields(body)
    assert "name" in fields
    assert "type" in fields
    assert _category_count(db) == 0


# --- TC-17: whitespace trimming -------------------------------------------------


def test_a_category_name_with_surrounding_whitespace_is_stored_trimmed(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-17: `name` "  Groceries  " -> 201; persisted `name` is "Groceries"
    — interior spacing preserved, surrounding whitespace removed.
    """
    response = client.post(
        CATEGORIES_URL, json=_valid_payload(name="  Groceries  "), headers=user_headers
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Groceries"
