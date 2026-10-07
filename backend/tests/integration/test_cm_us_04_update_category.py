"""CM-US-04 — Update a Category.

One test per test case in specs/004-category-management/test_cases.md
(TC-35..TC-63). Names state what the test proves, not what it calls.

`_stored()` always re-reads through `db.expire_all()` first, mirroring
`test_bm_us_04_update_budget.py`'s own helper of the same name (QF-19's own
technique, reused here for QF-10) — otherwise a read could return the test
session's cached copy instead of what the request actually committed.

TC-44/TC-46 compare the full response body of an ownership-mismatch case
against a genuinely-nonexistent-id case and assert they are identical, not
merely both 404 — the technique BM-US-04 QF-16/TC-68 already established,
now applied to a category's own id (QF-09).

TC-60/TC-61/TC-62 are this story's cross-story composition cases (QF-12):
a wallet is a bare prerequisite, so it is built directly against `db`
(mirrors `test_bm_us_02_list_budgets.py`'s own `_make_wallet`); the category
under test, and the Budget/Transaction whose behaviour is actually being
proven, are each created through their own real endpoint.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.category import CategoryModel
from app.models.transaction import TransactionModel
from app.models.user import UserModel
from app.models.wallet import WalletModel

CATEGORIES_URL = "/api/v1/categories"
BUDGETS_URL = "/api/v1/budgets"
TRANSACTIONS_URL = "/api/v1/transactions"


# --- helpers ----------------------------------------------------------------


def _url(category_id: str) -> str:
    return f"{CATEGORIES_URL}/{category_id}"


def _create_category(
    client: TestClient, headers: dict[str, str], **overrides: object
) -> dict[str, object]:
    """POST a category through the real CM-US-01 endpoint and return its body.

    Asserts 201 itself so a seeding failure fails loudly at the seeding line.
    """
    payload: dict[str, object] = {"name": "Utilities", "type": "EXPENSE"}
    payload.update(overrides)
    response = client.post(CATEGORIES_URL, json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


def _stored(db: Session, category_id: str) -> CategoryModel:
    """The committed `categories` row, read fresh rather than from the
    identity map (QF-10).
    """
    db.expire_all()
    category = db.get(CategoryModel, category_id)
    assert category is not None
    return category


def _fields(body: dict[str, object]) -> list[str]:
    details = body["details"]
    assert isinstance(details, dict)
    return [f["location"][-1] for f in details["fields"]]  # type: ignore[index]


def _make_wallet(
    db: Session, *, user_id: str, name: str = "Main Checking", balance: Decimal = Decimal("1000.00")
) -> WalletModel:
    """A wallet as a bare prerequisite for TC-60/TC-61/TC-62 — not itself
    under test, so it is constructed directly against `db`, mirroring
    `test_bm_us_02_list_budgets.py`'s own helper of the same name.
    """
    wallet = WalletModel(user_id=user_id, name=name, type="BANK", currency="USD", balance=balance)
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return wallet


def _create_transaction(
    client: TestClient,
    headers: dict[str, str],
    *,
    wallet_id: str,
    category_id: str,
    **overrides: object,
) -> dict[str, object]:
    """POST a transaction through the real TM-US-01 endpoint and return its
    body. Asserts 201 itself so a seeding failure fails loudly at the
    seeding line.
    """
    payload: dict[str, object] = {
        "wallet_id": wallet_id,
        "category_id": category_id,
        "amount": "10.00",
        "type": "EXPENSE",
    }
    payload.update(overrides)
    response = client.post(TRANSACTIONS_URL, json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


def _create_budget(
    client: TestClient,
    headers: dict[str, str],
    *,
    wallet_id: str,
    category_id: str,
    **overrides: object,
) -> dict[str, object]:
    """POST a budget through the real BM-US-01 endpoint and return its body."""
    payload: dict[str, object] = {
        "wallet_id": wallet_id,
        "category_id": category_id,
        "amount_limit": "200.00",
    }
    payload.update(overrides)
    response = client.post(BUDGETS_URL, json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


# --- TC-35: all three fields in one request ----------------------------------


def test_an_authenticated_user_updates_all_three_fields_in_one_request(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel
) -> None:
    """TC-35: name "Utilities"/type EXPENSE/no icon -> PATCH name "Bills",
    type INCOME, icon "receipt" -> 200; id unchanged, user_id the caller's,
    name/type/icon all updated.
    """
    category = _create_category(client, user_headers, name="Utilities", type="EXPENSE")

    response = client.patch(
        _url(str(category["id"])),
        json={"name": "Bills", "type": "INCOME", "icon": "receipt"},
        headers=user_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == category["id"]
    assert body["user_id"] == normal_user.id
    assert body["name"] == "Bills"
    assert body["type"] == "INCOME"
    assert body["icon"] == "receipt"


# --- TC-36/TC-37/TC-38/TC-39: partial updates, verified in storage (QF-10) --


def test_updating_only_name_leaves_type_and_icon_unchanged_verified_in_storage(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-36: name "Utilities"/type EXPENSE/icon "bolt" (set via a prior
    update) -> PATCH name only "Bills" -> 200 with name "Bills", type
    EXPENSE, icon "bolt"; a direct row read confirms type/icon unchanged.
    """
    category = _create_category(client, user_headers, name="Utilities", type="EXPENSE")
    client.patch(_url(str(category["id"])), json={"icon": "bolt"}, headers=user_headers)

    response = client.patch(_url(str(category["id"])), json={"name": "Bills"}, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Bills"
    assert body["type"] == "EXPENSE"
    assert body["icon"] == "bolt"
    stored = _stored(db, str(category["id"]))
    assert stored.type.value == "EXPENSE"
    assert stored.icon == "bolt"


def test_updating_only_type_leaves_name_and_icon_unchanged_verified_in_storage(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-37: name "Utilities"/type EXPENSE/icon "bolt" -> PATCH type only
    "INCOME" -> 200 with name "Utilities", type INCOME, icon "bolt"; a
    direct row read confirms name/icon unchanged.
    """
    category = _create_category(client, user_headers, name="Utilities", type="EXPENSE")
    client.patch(_url(str(category["id"])), json={"icon": "bolt"}, headers=user_headers)

    response = client.patch(
        _url(str(category["id"])), json={"type": "INCOME"}, headers=user_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Utilities"
    assert body["type"] == "INCOME"
    assert body["icon"] == "bolt"
    stored = _stored(db, str(category["id"]))
    assert stored.name == "Utilities"
    assert stored.icon == "bolt"


def test_updating_only_icon_first_time_leaves_name_type_unchanged_later_null_does_not_clear(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-38: name "Utilities"/type EXPENSE/no icon -> PATCH icon only
    "bolt" -> response and stored row both show icon "bolt", name/type
    unchanged; a second PATCH with name "Bills" and icon explicitly null ->
    name is "Bills" and icon is still "bolt" (assertion technique per
    QF-10, QF-13).
    """
    category = _create_category(client, user_headers, name="Utilities", type="EXPENSE")

    first = client.patch(_url(str(category["id"])), json={"icon": "bolt"}, headers=user_headers)
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["icon"] == "bolt"
    assert first_body["name"] == "Utilities"
    assert first_body["type"] == "EXPENSE"
    stored = _stored(db, str(category["id"]))
    assert stored.icon == "bolt"
    assert stored.name == "Utilities"
    assert stored.type.value == "EXPENSE"

    second = client.patch(
        _url(str(category["id"])),
        json={"name": "Bills", "icon": None},
        headers=user_headers,
    )
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["name"] == "Bills"
    assert second_body["icon"] == "bolt"
    stored2 = _stored(db, str(category["id"]))
    assert stored2.name == "Bills"
    assert stored2.icon == "bolt"


def test_changing_an_already_set_icon_to_a_different_value_succeeds_as_an_ordinary_update(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-39: icon already "bolt" -> PATCH icon "flash" -> 200 with icon
    "flash"; the stored row confirms it, not a conflict or no-op.
    """
    category = _create_category(client, user_headers)
    client.patch(_url(str(category["id"])), json={"icon": "bolt"}, headers=user_headers)

    response = client.patch(_url(str(category["id"])), json={"icon": "flash"}, headers=user_headers)

    assert response.status_code == 200
    assert response.json()["icon"] == "flash"
    assert _stored(db, str(category["id"])).icon == "flash"


# --- TC-40: no uniqueness constraint on name ---------------------------------


def test_an_updated_name_matching_another_of_the_callers_own_categories_names_still_succeeds(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-40: two categories "Utilities" and "Groceries" -> PATCH renames
    "Groceries" to "Utilities" -> 200; both now share the name, each with
    its own distinct id.
    """
    utilities = _create_category(client, user_headers, name="Utilities")
    groceries = _create_category(client, user_headers, name="Groceries")

    response = client.patch(
        _url(str(groceries["id"])), json={"name": "Utilities"}, headers=user_headers
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Utilities"
    assert response.json()["id"] != utilities["id"]


# --- TC-41/TC-42: authentication ---------------------------------------------


def test_an_unauthenticated_caller_is_denied_with_401(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-41: no Authorization header, otherwise valid payload against a
    real category -> 401 NOT_AUTHENTICATED; the target category's stored
    fields are unchanged.
    """
    category = _create_category(client, user_headers)

    response = client.patch(_url(str(category["id"])), json={"name": "Bills"})

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"
    assert _stored(db, str(category["id"])).name == "Utilities"


def test_credentials_are_evaluated_before_the_payload(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-42: no credentials, empty body ({}, otherwise 422-triggering) ->
    401 NOT_AUTHENTICATED, not 422 — mirrors CM-US-02 TC-22's ordering.
    """
    category = _create_category(client, user_headers)

    response = client.patch(_url(str(category["id"])), json={})

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"


# --- TC-43/TC-44/TC-45/TC-46: not found and not owned, collapsed (QF-09) ----


def test_a_category_id_matching_no_category_at_all_is_rejected_with_404(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-43: a well-formed id matching no category -> 404
    CATEGORY_NOT_FOUND.
    """
    response = client.patch(_url(str(uuid4())), json={"name": "Bills"}, headers=user_headers)

    assert response.status_code == 404
    assert response.json()["error_code"] == "CATEGORY_NOT_FOUND"


def test_a_category_id_belonging_to_a_different_user_gets_the_identical_outcome_as_not_found(
    client: TestClient, user_headers: dict[str, str], admin_headers: dict[str, str], db: Session
) -> None:
    """TC-44: B owns a category; A PATCHes B's category_id -> 404, and
    error_code/message/details are all identical to a genuinely
    not-found-at-all response (QF-09, mirrors BM-US-04 QF-16/TC-68); B's
    category is unchanged.
    """
    b_category = _create_category(client, admin_headers, name="B-Cat")

    not_owned = client.patch(
        _url(str(b_category["id"])), json={"name": "Hack"}, headers=user_headers
    )
    not_found = client.patch(_url(str(uuid4())), json={"name": "Hack"}, headers=user_headers)

    assert not_owned.status_code == 404
    assert not_owned.json()["error_code"] == "CATEGORY_NOT_FOUND"
    assert not_owned.json() == not_found.json()
    assert _stored(db, str(b_category["id"])).name == "B-Cat"


def test_a_malformed_category_reference_gets_the_same_404_as_a_well_formed_unknown_one(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-45: PATCH /categories/not-a-real-id -> 404 CATEGORY_NOT_FOUND,
    identical to a well-formed but non-existent id's response.
    """
    malformed = client.patch(_url("not-a-real-id"), json={"name": "Bills"}, headers=user_headers)
    unknown = client.patch(_url(str(uuid4())), json={"name": "Bills"}, headers=user_headers)

    assert malformed.status_code == 404
    assert malformed.json()["error_code"] == "CATEGORY_NOT_FOUND"
    assert malformed.json() == unknown.json()


def test_a_caller_who_owns_a_different_category_cannot_update_another_users_category(
    client: TestClient, user_headers: dict[str, str], admin_headers: dict[str, str], db: Session
) -> None:
    """TC-46: A owns CA, B owns CB -> A PATCHes CB -> 404 CATEGORY_NOT_FOUND;
    CB unchanged, A's own CA also unaffected.
    """
    ca = _create_category(client, user_headers, name="A-Cat")
    cb = _create_category(client, admin_headers, name="B-Cat")

    response = client.patch(_url(str(cb["id"])), json={"name": "Hack"}, headers=user_headers)

    assert response.status_code == 404
    assert response.json()["error_code"] == "CATEGORY_NOT_FOUND"
    assert _stored(db, str(cb["id"])).name == "B-Cat"
    assert _stored(db, str(ca["id"])).name == "A-Cat"


# --- TC-47: the cross-field "at least one" rule (QF-11) ---------------------


def test_a_submission_naming_none_of_name_type_or_icon_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-47: empty JSON body {} -> 422 VALIDATION_ERROR whose details/
    message names the "at least one field" rule, not a single field
    (assertion technique per QF-11); nothing changed.
    """
    category = _create_category(client, user_headers)

    response = client.patch(_url(str(category["id"])), json={}, headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    details = body["details"]
    assert isinstance(details, dict)
    messages = " ".join(f["message"] for f in details["fields"]).lower()
    assert "at least one" in messages
    assert _stored(db, str(category["id"])).name == "Utilities"


# --- TC-48/TC-49/TC-50: name validation, when submitted ----------------------


def test_a_blank_or_whitespace_only_name_when_submitted_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-48: name "" and, separately, "   " -> each 422 VALIDATION_ERROR
    identifying `name`; nothing persisted.
    """
    category = _create_category(client, user_headers)

    for bad_name in ("", "   "):
        response = client.patch(
            _url(str(category["id"])), json={"name": bad_name}, headers=user_headers
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error_code"] == "VALIDATION_ERROR"
        assert "name" in _fields(body)

    assert _stored(db, str(category["id"])).name == "Utilities"


def test_a_name_exceeding_100_characters_when_submitted_is_rejected_not_truncated(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-49: name of 101 characters -> 422 VALIDATION_ERROR; stored name
    unchanged, not truncated.
    """
    category = _create_category(client, user_headers)

    response = client.patch(
        _url(str(category["id"])), json={"name": "x" * 101}, headers=user_headers
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"
    assert _stored(db, str(category["id"])).name == "Utilities"


def test_a_name_with_surrounding_whitespace_is_stored_trimmed(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-50: name "  Bills  " -> 200; persisted name is "Bills"."""
    category = _create_category(client, user_headers)

    response = client.patch(
        _url(str(category["id"])), json={"name": "  Bills  "}, headers=user_headers
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Bills"
    assert _stored(db, str(category["id"])).name == "Bills"


# --- TC-51/TC-52/TC-53: type vocabulary is closed and exact, when submitted -


@pytest.mark.parametrize("bad_type", ["SAVINGS", "TRANSFER", ""])
def test_a_type_value_that_is_neither_income_nor_expense_when_submitted_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], db: Session, bad_type: str
) -> None:
    """TC-51: type in turn "SAVINGS", "TRANSFER", "" -> each 422 whose
    details names `type`; nothing persisted.
    """
    category = _create_category(client, user_headers)

    response = client.patch(
        _url(str(category["id"])), json={"type": bad_type}, headers=user_headers
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "type" in _fields(body)
    assert _stored(db, str(category["id"])).type.value == "EXPENSE"


@pytest.mark.parametrize("bad_type", ["expense", "Income"])
def test_a_lowercase_or_mixed_case_type_value_when_submitted_is_rejected_not_case_folded(
    client: TestClient, user_headers: dict[str, str], db: Session, bad_type: str
) -> None:
    """TC-52: type "expense" and, separately, "Income" -> each 422 whose
    details names `type`; the stored type is unchanged.
    """
    category = _create_category(client, user_headers)

    response = client.patch(
        _url(str(category["id"])), json={"type": bad_type}, headers=user_headers
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "type" in _fields(body)
    assert _stored(db, str(category["id"])).type.value == "EXPENSE"


@pytest.mark.parametrize("bad_type", [" EXPENSE", "INCOME "])
def test_a_type_value_with_surrounding_whitespace_when_submitted_is_rejected_not_trimmed(
    client: TestClient, user_headers: dict[str, str], db: Session, bad_type: str
) -> None:
    """TC-53: type " EXPENSE" and, separately, "INCOME " -> each 422 whose
    details names `type`; the stored type is unchanged — unlike name/icon,
    type receives no trimming.
    """
    category = _create_category(client, user_headers)

    response = client.patch(
        _url(str(category["id"])), json={"type": bad_type}, headers=user_headers
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "type" in _fields(body)
    assert _stored(db, str(category["id"])).type.value == "EXPENSE"


# --- TC-54/TC-55/TC-56/TC-63: icon validation, when submitted ----------------


def test_a_blank_or_whitespace_only_icon_when_submitted_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-54: icon "" and, separately, "   " -> each 422 VALIDATION_ERROR
    identifying `icon`; nothing persisted.
    """
    category = _create_category(client, user_headers)

    for bad_icon in ("", "   "):
        response = client.patch(
            _url(str(category["id"])), json={"icon": bad_icon}, headers=user_headers
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error_code"] == "VALIDATION_ERROR"
        assert "icon" in _fields(body)

    assert _stored(db, str(category["id"])).icon is None


def test_an_icon_exceeding_50_characters_when_submitted_is_rejected_not_truncated(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-55: icon of 51 characters -> 422 VALIDATION_ERROR; stored icon
    unchanged, not truncated.
    """
    category = _create_category(client, user_headers)

    response = client.patch(
        _url(str(category["id"])), json={"icon": "x" * 51}, headers=user_headers
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"
    assert _stored(db, str(category["id"])).icon is None


def test_an_icon_with_surrounding_whitespace_is_stored_trimmed(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-56: icon "  shopping-cart  " -> 200; persisted icon is
    "shopping-cart".
    """
    category = _create_category(client, user_headers)

    response = client.patch(
        _url(str(category["id"])), json={"icon": "  shopping-cart  "}, headers=user_headers
    )

    assert response.status_code == 200
    assert response.json()["icon"] == "shopping-cart"
    assert _stored(db, str(category["id"])).icon == "shopping-cart"


def test_an_icon_of_exactly_50_characters_is_accepted(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-63: icon of exactly 50 characters -> 200; stored icon is the full
    50-character value — the cap is a ceiling, not a target: 50 is
    honoured, only 51 is rejected (TC-55).
    """
    category = _create_category(client, user_headers)
    icon_50 = "x" * 50

    response = client.patch(_url(str(category["id"])), json={"icon": icon_50}, headers=user_headers)

    assert response.status_code == 200
    assert response.json()["icon"] == icon_50
    assert _stored(db, str(category["id"])).icon == icon_50


# --- TC-57: grouped validation failures --------------------------------------


def test_multiple_validation_failures_in_one_submission_are_reported_together(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-57: name "" and type "SAVINGS" in the same request -> a single 422
    whose details identifies both fields, not just the first one
    encountered.
    """
    category = _create_category(client, user_headers)

    response = client.patch(
        _url(str(category["id"])),
        json={"name": "", "type": "SAVINGS"},
        headers=user_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    fields = _fields(body)
    assert "name" in fields
    assert "type" in fields
    assert _stored(db, str(category["id"])).name == "Utilities"


# --- TC-58: ownership cannot be overridden by the payload --------------------


def test_a_successful_update_never_changes_the_categorys_owner(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-58: A owns a category; A submits a PATCH with a valid name change
    that additionally includes an unrecognised "user_id" naming B -> 200;
    the updated category's user_id is still A's, never B's — verified both
    in the response and by a direct row read (assertion technique per
    CM-US-01 QF-01/TC-12).
    """
    category = _create_category(client, user_headers)

    payload = {"name": "Bills", "user_id": admin_user.id}
    response = client.patch(_url(str(category["id"])), json=payload, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == normal_user.id
    assert body["user_id"] != admin_user.id
    assert _stored(db, str(category["id"])).user_id == normal_user.id


# --- TC-59: exact response shape ---------------------------------------------


def test_the_response_exposes_exactly_the_five_documented_fields(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-59: response body's keys are exactly id, user_id, name, type,
    icon — no more.
    """
    category = _create_category(client, user_headers)

    response = client.patch(_url(str(category["id"])), json={"name": "Bills"}, headers=user_headers)

    assert response.status_code == 200
    assert set(response.json().keys()) == {"id", "user_id", "name", "type", "icon"}


# --- TC-60/TC-61/TC-62: type changes carry no retroactive effect (QF-12) ----


def test_changing_a_categorys_type_does_not_alter_an_existing_transactions_own_stored_type(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-60: a wallet, an EXPENSE category, and an EXPENSE Transaction
    already recorded against them -> PATCH the category's type to INCOME ->
    200; a direct read of the transaction row shows its own type is still
    EXPENSE, unchanged (per QF-12, plan.md A13).
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _create_category(client, user_headers, name="Dining", type="EXPENSE")
    transaction = _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=str(category["id"]), amount="20.00"
    )

    response = client.patch(
        _url(str(category["id"])), json={"type": "INCOME"}, headers=user_headers
    )

    assert response.status_code == 200
    db.expire_all()
    stored_txn = db.get(TransactionModel, transaction["id"])
    assert stored_txn is not None
    assert stored_txn.type.value == "EXPENSE"


def test_changing_a_categorys_type_does_not_alter_a_budgets_already_recorded_spend(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-61: a wallet, an EXPENSE category, a Budget for that wallet and
    category, and a 150.00 EXPENSE Transaction already recorded -> PATCH the
    category's type to INCOME, then GET /budgets -> the listed budget's
    amount_spent is still 150.00 (per QF-12; cross-story composition with
    BM-US-02).
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _create_category(client, user_headers, name="Dining", type="EXPENSE")
    budget = _create_budget(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=str(category["id"]),
        amount_limit="200.00",
    )
    _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=str(category["id"]), amount="150.00"
    )

    patched = client.patch(_url(str(category["id"])), json={"type": "INCOME"}, headers=user_headers)
    listed = client.get(BUDGETS_URL, headers=user_headers)

    assert patched.status_code == 200
    assert listed.status_code == 200
    item = next(i for i in listed.json()["items"] if i["id"] == budget["id"])
    assert Decimal(str(item["amount_spent"])) == Decimal("150.00")


def test_after_a_type_change_a_new_transaction_of_the_old_type_is_refused(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-62: a category whose type was EXPENSE has just been updated to
    INCOME -> a new Transaction of type EXPENSE against it -> 409
    TRANSACTION_CATEGORY_TYPE_MISMATCH, TM-US-01's own existing check, now
    correctly evaluated against the new type — this story introduces no new
    rule to produce this outcome (per QF-12).
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _create_category(client, user_headers, name="Dining", type="EXPENSE")
    client.patch(_url(str(category["id"])), json={"type": "INCOME"}, headers=user_headers)

    response = client.post(
        TRANSACTIONS_URL,
        json={
            "wallet_id": wallet.id,
            "category_id": category["id"],
            "amount": "10.00",
            "type": "EXPENSE",
        },
        headers=user_headers,
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "TRANSACTION_CATEGORY_TYPE_MISMATCH"
