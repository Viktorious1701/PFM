"""CM-US-05 — Delete a Category (soft-delete / archive).

One test per test case in specs/004-category-management/test_cases.md
(TC-74..TC-93). Names state what the test proves, not what it calls.

`CATEGORIES_URL`/`_create_category` are reused by import from
test_cm_us_02_list_categories.py, the same precedent
test_cm_us_04_update_category.py already set for its own CM-US-02 imports —
categories are seeded through the real POST /api/v1/categories endpoint
(CM-US-01, already implemented), never inserted directly.

Wallets are a bare prerequisite for TC-88/TC-89/TC-90 (a real wallet is
required by POST /transactions and POST /budgets, but is not itself under
test here), so they are constructed directly against `db` — mirrors
`test_cm_us_04_update_category.py`'s own `_make_wallet` and
`test_wm_us_05_delete_wallet.py`'s own analogous `_make_category`.

Stored state is always re-read through `_stored()`, which expires the test
session's identity map first — otherwise a read could return the test
session's own cached copy instead of what the request actually committed
(the same QF-10 discipline test_cm_us_04_update_category.py already
established, reused here for CM-US-05).

TC-82's idempotency proof reuses conftest.py's `frozen_now`/`advance_clock`
fixtures — the same clock-monkeypatch seam every other story in this
codebase already uses instead of freezegun — to get a real, provable time
gap between the first and second archive requests.
"""

from collections.abc import Callable
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import clock
from app.models.budget import BudgetModel
from app.models.category import CategoryModel
from app.models.transaction import TransactionModel
from app.models.user import UserModel
from app.models.wallet import WalletModel
from tests.integration.test_cm_us_02_list_categories import CATEGORIES_URL, _create_category

TRANSACTIONS_URL = "/api/v1/transactions"
BUDGETS_URL = "/api/v1/budgets"

NONEXISTENT_CATEGORY_ID = "00000000-0000-0000-0000-000000000000"


# --- helpers ----------------------------------------------------------------


def _url(category_id: str) -> str:
    return f"{CATEGORIES_URL}/{category_id}"


def _stored(db: Session, category_id: str) -> CategoryModel:
    """The committed `categories` row, read fresh rather than from the
    identity map.
    """
    db.expire_all()
    category = db.get(CategoryModel, category_id)
    assert category is not None
    return category


def _category_row_count(db: Session, category_id: str) -> int:
    return (
        db.scalar(
            select(func.count()).select_from(CategoryModel).where(CategoryModel.id == category_id)
        )
        or 0
    )


def _make_wallet(
    db: Session, *, user_id: str, name: str = "Main Checking", balance: Decimal = Decimal("1000.00")
) -> WalletModel:
    """A wallet as a bare prerequisite for TC-88/TC-89/TC-90 — not itself
    under test, so it is constructed directly against `db`, mirroring
    `test_cm_us_04_update_category.py`'s own `_make_wallet`.
    """
    wallet = WalletModel(user_id=user_id, name=name, type="BANK", currency="USD", balance=balance)
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return wallet


def _assert_timestamp(value: object) -> datetime:
    assert isinstance(value, str)
    parsed = datetime.fromisoformat(value)
    assert parsed.tzinfo is not None
    return parsed


# --- TC-74: the happy path ----------------------------------------------------


def test_an_authenticated_owner_archives_a_category_200_other_fields_unchanged(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-74: category name "Old Groceries"/type "EXPENSE"/icon
    "shopping-cart", not yet archived -> DELETE -> 200; id unchanged,
    name/type/icon unchanged, archived_at set to a real timestamp.

    `icon` is not part of CategoryCreate (CM-US-01) -- it is set afterward
    through CM-US-04's own PATCH, the only way a category acquires one.
    """
    category = _create_category(client, user_headers, name="Old Groceries", type="EXPENSE")
    patched = client.patch(
        _url(str(category["id"])), json={"icon": "shopping-cart"}, headers=user_headers
    )
    assert patched.status_code == 200

    response = client.delete(_url(str(category["id"])), headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == category["id"]
    assert body["name"] == "Old Groceries"
    assert body["type"] == "EXPENSE"
    assert body["icon"] == "shopping-cart"
    _assert_timestamp(body["archived_at"])


# --- TC-75: persistence on the same single row --------------------------------


def test_archiving_a_category_persists_the_new_state_on_the_same_single_row(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-75: direct inspection of the `categories` row shows `archived_at`
    set to a non-NULL value; exactly one row still exists for that id.
    """
    category = _create_category(client, user_headers)

    response = client.delete(_url(str(category["id"])), headers=user_headers)

    assert response.status_code == 200
    stored = _stored(db, str(category["id"]))
    assert stored.archived_at is not None
    assert _category_row_count(db, str(category["id"])) == 1


# --- TC-76: authentication -----------------------------------------------------


def test_an_unauthenticated_caller_is_denied_with_401_and_nothing_is_archived(
    client: TestClient, admin_headers: dict[str, str], db: Session
) -> None:
    """TC-76: no Authorization header, against an existing category
    belonging to some other, real User -> 401 NOT_AUTHENTICATED; the
    target category's archived_at remains NULL.
    """
    other_category = _create_category(client, admin_headers, name="Someone Else's")

    response = client.delete(_url(str(other_category["id"])))

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"
    assert _stored(db, str(other_category["id"])).archived_at is None


# --- TC-77/TC-78/TC-79/TC-80/TC-81: not-found/ownership collapse (QF-17) ------


def test_a_category_id_matching_no_category_at_all_is_rejected_with_404(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-77: a category_id matching no category in the system -> 404
    CATEGORY_NOT_FOUND; nothing archived.
    """
    response = client.delete(_url(str(uuid4())), headers=user_headers)

    assert response.status_code == 404
    assert response.json()["error_code"] == "CATEGORY_NOT_FOUND"


def test_a_category_belonging_to_a_different_user_gets_the_identical_404_as_not_found(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    db: Session,
) -> None:
    """TC-78: B owns a category, A submits DELETE against it -> 404
    identical (error_code/message/details) to TC-77's not-found-at-all
    response; B's category remains unarchived.
    """
    b_category = _create_category(client, admin_headers, name="B's Category")

    not_owned = client.delete(_url(str(b_category["id"])), headers=user_headers)
    not_found = client.delete(_url(str(uuid4())), headers=user_headers)

    assert not_owned.status_code == 404
    assert not_owned.json()["error_code"] == "CATEGORY_NOT_FOUND"
    assert not_owned.json() == not_found.json()
    assert _stored(db, str(b_category["id"])).archived_at is None


def test_a_malformed_category_reference_gets_the_same_404_as_a_well_formed_unknown_one(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-79: DELETE /categories/not-a-real-id -> 404 CATEGORY_NOT_FOUND,
    identical to TC-77's response.
    """
    malformed = client.delete(_url("not-a-real-id"), headers=user_headers)
    unknown = client.delete(_url(str(uuid4())), headers=user_headers)

    assert malformed.status_code == 404
    assert malformed.json()["error_code"] == "CATEGORY_NOT_FOUND"
    assert malformed.json() == unknown.json()


def test_a_caller_who_owns_a_different_category_cannot_archive_another_users_category(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    db: Session,
) -> None:
    """TC-80: A owns CA, B owns CB; A submits DELETE against CB -> 404
    CATEGORY_NOT_FOUND identical to TC-77/TC-78; CB remains unarchived, A's
    own CA is unaffected.
    """
    ca = _create_category(client, user_headers, name="A's Category")
    cb = _create_category(client, admin_headers, name="B's Category")

    response = client.delete(_url(str(cb["id"])), headers=user_headers)
    not_found = client.delete(_url(str(uuid4())), headers=user_headers)

    assert response.status_code == 404
    assert response.json()["error_code"] == "CATEGORY_NOT_FOUND"
    assert response.json() == not_found.json()
    assert _stored(db, str(cb["id"])).archived_at is None
    assert _stored(db, str(ca["id"])).archived_at is None


def test_an_admin_role_caller_cannot_archive_another_users_category_through_this_endpoint(
    client: TestClient,
    admin_headers: dict[str, str],
    user_headers: dict[str, str],
    db: Session,
) -> None:
    """TC-81: an ADMIN-role caller submits DELETE against another User's
    category -> 404 CATEGORY_NOT_FOUND -- the same outcome any non-ADMIN
    caller would get; no role grants authority through this endpoint.
    """
    user_category = _create_category(client, user_headers, name="User's Category")

    response = client.delete(_url(str(user_category["id"])), headers=admin_headers)

    assert response.status_code == 404
    assert response.json()["error_code"] == "CATEGORY_NOT_FOUND"
    assert _stored(db, str(user_category["id"])).archived_at is None


# --- TC-82: idempotency (QF-15) ------------------------------------------------


def test_a_repeated_archive_request_succeeds_again_with_the_identical_archive_time(
    client: TestClient,
    user_headers: dict[str, str],
    frozen_now: datetime,
    advance_clock: Callable[[timedelta], datetime],
) -> None:
    """TC-82: a first DELETE records archived_at at T1; a second DELETE,
    issued a real time gap later, returns 200 (not 404/409) with the
    identical archived_at -- not a new, later timestamp.
    """
    category = _create_category(client, user_headers)

    first = client.delete(_url(str(category["id"])), headers=user_headers)
    assert first.status_code == 200
    t1 = first.json()["archived_at"]

    advance_clock(timedelta(hours=1))

    second = client.delete(_url(str(category["id"])), headers=user_headers)

    assert second.status_code == 200
    assert second.json()["archived_at"] == t1


# --- TC-83: name/type/icon unchanged, verified against storage ---------------


def test_archiving_leaves_name_type_and_icon_unchanged_verified_against_storage(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-83: category name "Old Groceries"/type "EXPENSE"/icon
    "shopping-cart" -> archive succeeds -> a direct read of the
    `categories` row confirms all three are identical to their pre-archive
    values.

    `icon` is set through CM-US-04's own PATCH, the only way a category
    acquires one (CategoryCreate carries no icon field).
    """
    category = _create_category(client, user_headers, name="Old Groceries", type="EXPENSE")
    patched = client.patch(
        _url(str(category["id"])), json={"icon": "shopping-cart"}, headers=user_headers
    )
    assert patched.status_code == 200

    response = client.delete(_url(str(category["id"])), headers=user_headers)

    assert response.status_code == 200
    stored = _stored(db, str(category["id"]))
    assert stored.name == "Old Groceries"
    assert stored.type.value == "EXPENSE"
    assert stored.icon == "shopping-cart"


# --- TC-84/TC-85: list exclusion, items and total together (QF-16) ------------


def test_an_archived_category_is_excluded_from_both_items_and_total_of_the_default_list(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-84: one active category and one already-archived category for the
    same caller -> GET /categories items contains only the active
    category, total is 1.
    """
    active = _create_category(client, user_headers, name="Active")
    to_archive = _create_category(client, user_headers, name="To Archive")
    archived = client.delete(_url(str(to_archive["id"])), headers=user_headers)
    assert archived.status_code == 200

    response = client.get(CATEGORIES_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == active["id"]
    assert all(item["id"] != to_archive["id"] for item in body["items"])


def test_a_caller_whose_only_category_is_archived_receives_an_empty_list_and_zero_total(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-85: a caller's only category is already archived -> GET
    /categories items is empty, total is 0, not 1.
    """
    only = _create_category(client, user_headers, name="Only Category")
    archived = client.delete(_url(str(only["id"])), headers=user_headers)
    assert archived.status_code == 200

    response = client.get(CATEGORIES_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


# --- TC-86/TC-87: still individually viewable, no leak (QF-19) ----------------


def test_an_archived_category_can_still_be_viewed_directly_by_its_own_identifier(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-86: an already-archived category -> GET /categories/{id} -> 200,
    not 404; full, unchanged detail exactly as CM-US-03 already defines it.
    """
    category = _create_category(client, user_headers, name="Archived One")
    archived = client.delete(_url(str(category["id"])), headers=user_headers)
    assert archived.status_code == 200

    response = client.get(_url(str(category["id"])), headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == category["id"]
    assert body["name"] == "Archived One"


def test_viewing_an_archived_category_exposes_exactly_the_five_original_fields(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-87: GET /categories/{id} for an already-archived category -> the
    response body's keys are exactly id, user_id, name, type, icon -- no
    more, and in particular no archived_at/is_archived/any other
    archived-state field.
    """
    category = _create_category(client, user_headers)
    archived = client.delete(_url(str(category["id"])), headers=user_headers)
    assert archived.status_code == 200

    response = client.get(_url(str(category["id"])), headers=user_headers)

    assert response.status_code == 200
    assert set(response.json().keys()) == {
        "id",
        "user_id",
        "name",
        "type",
        "icon",
    }


# --- TC-88/TC-89: archived category blocks new Transactions/Budgets (QF-18) --


def test_a_new_transaction_against_an_archived_category_is_rejected_with_409(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
) -> None:
    """TC-88: an already-archived category and an existing wallet of the
    caller's own -> POST /transactions referencing the archived category ->
    409 TRANSACTION_CATEGORY_ARCHIVED; direct inspection of the
    `transactions` table confirms no new row was created.
    """
    category = _create_category(client, user_headers, type="EXPENSE")
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("1000.00"))
    archived = client.delete(_url(str(category["id"])), headers=user_headers)
    assert archived.status_code == 200

    before = db.scalar(select(func.count()).select_from(TransactionModel)) or 0
    response = client.post(
        TRANSACTIONS_URL,
        json={
            "wallet_id": wallet.id,
            "category_id": category["id"],
            "amount": "50.00",
            "type": "EXPENSE",
        },
        headers=user_headers,
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "TRANSACTION_CATEGORY_ARCHIVED"
    after = db.scalar(select(func.count()).select_from(TransactionModel)) or 0
    assert after == before


def test_a_new_budget_against_an_archived_category_is_rejected_with_409(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
) -> None:
    """TC-89: an already-archived category and an existing wallet of the
    caller's own -> POST /budgets referencing the archived category -> 409
    BUDGET_CATEGORY_ARCHIVED; direct inspection of the `budgets` table
    confirms no new row was created.
    """
    category = _create_category(client, user_headers, type="EXPENSE")
    wallet = _make_wallet(db, user_id=normal_user.id)
    archived = client.delete(_url(str(category["id"])), headers=user_headers)
    assert archived.status_code == 200

    before = db.scalar(select(func.count()).select_from(BudgetModel)) or 0
    response = client.post(
        BUDGETS_URL,
        json={
            "wallet_id": wallet.id,
            "category_id": category["id"],
            "amount_limit": "200.00",
        },
        headers=user_headers,
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "BUDGET_CATEGORY_ARCHIVED"
    after = db.scalar(select(func.count()).select_from(BudgetModel)) or 0
    assert after == before


# --- TC-90: existing history untouched ----------------------------------------


def test_archiving_a_category_with_existing_transactions_and_budgets_leaves_them_untouched(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
) -> None:
    """TC-90: a category with one existing Transaction and one existing
    Budget already recorded against it -> archive succeeds -> both rows are
    unchanged (same ids, same category_id, same amounts) and remain
    retrievable through their own already-existing endpoints exactly as
    before.
    """
    category = _create_category(client, user_headers, type="EXPENSE")
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("1000.00"))

    txn_response = client.post(
        TRANSACTIONS_URL,
        json={
            "wallet_id": wallet.id,
            "category_id": category["id"],
            "amount": "50.00",
            "type": "EXPENSE",
        },
        headers=user_headers,
    )
    assert txn_response.status_code == 201
    transaction = txn_response.json()

    budget_response = client.post(
        BUDGETS_URL,
        json={
            "wallet_id": wallet.id,
            "category_id": category["id"],
            "amount_limit": "200.00",
        },
        headers=user_headers,
    )
    assert budget_response.status_code == 201
    budget = budget_response.json()

    archived = client.delete(_url(str(category["id"])), headers=user_headers)
    assert archived.status_code == 200

    view_txn = client.get(f"{TRANSACTIONS_URL}/{transaction['id']}", headers=user_headers)
    assert view_txn.status_code == 200
    assert view_txn.json()["id"] == transaction["id"]
    assert view_txn.json()["category_id"] == category["id"]
    assert Decimal(str(view_txn.json()["amount"])) == Decimal("50.00")

    budget_list = client.get(BUDGETS_URL, headers=user_headers)
    assert budget_list.status_code == 200
    matching = [item for item in budget_list.json()["items"] if item["id"] == budget["id"]]
    assert len(matching) == 1
    assert matching[0]["category_id"] == category["id"]
    assert Decimal(str(matching[0]["amount_limit"])) == Decimal("200.00")

    stored_txn = db.get(TransactionModel, transaction["id"])
    assert stored_txn is not None
    assert stored_txn.category_id == category["id"]
    assert stored_txn.amount == Decimal("50.00")
    stored_budget = db.get(BudgetModel, budget["id"])
    assert stored_budget is not None
    assert stored_budget.category_id == category["id"]
    assert stored_budget.amount_limit == Decimal("200.00")


# --- TC-91: exact response shape ----------------------------------------------


def test_the_response_exposes_exactly_the_six_documented_fields(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-91: response body's keys are exactly id, user_id, name, type,
    icon, archived_at -- no more, no other invented field.
    """
    category = _create_category(client, user_headers)

    response = client.delete(_url(str(category["id"])), headers=user_headers)

    assert response.status_code == 200
    assert set(response.json().keys()) == {
        "id",
        "user_id",
        "name",
        "type",
        "icon",
        "archived_at",
    }


# --- TC-92: credentials evaluated before the category reference is looked up -


def test_credentials_are_evaluated_before_the_category_reference_is_looked_up(
    client: TestClient,
) -> None:
    """TC-92: no credentials, against a category_id matching no category at
    all -> 401 NOT_AUTHENTICATED, not 404 -- mirrors CM-US-03 TC-73/WM-US-05
    TC-90's own ordering.
    """
    response = client.delete(_url(NONEXISTENT_CATEGORY_ID))

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"


# --- TC-93: CM-US-04's own PATCH still succeeds against an archived category --


def test_updating_an_archived_categorys_name_type_or_icon_via_patch_still_succeeds(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-93: an already-archived category -> PATCH /categories/{id} with a
    new name -> 200, not 409; the category's name changes exactly as
    CM-US-04 already defines, and its archived_at remains unchanged --
    demonstrating spec.md BR-05's own scope limit: this story's
    archived-category restriction reaches only new Transactions and new
    Budgets, never CM-US-04's own update operation.
    """
    category = _create_category(client, user_headers, name="Old Name")
    archived = client.delete(_url(str(category["id"])), headers=user_headers)
    assert archived.status_code == 200
    original_archived_at = datetime.fromisoformat(archived.json()["archived_at"])

    response = client.patch(
        _url(str(category["id"])), json={"name": "New Name"}, headers=user_headers
    )

    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    stored = _stored(db, str(category["id"]))
    assert stored.archived_at is not None
    assert clock.ensure_aware(stored.archived_at) == original_archived_at
