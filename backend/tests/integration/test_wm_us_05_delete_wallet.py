"""WM-US-05 — Delete a Wallet (soft-delete / archive).

One test per test case in specs/003-wallet-management/test_cases.md
(TC-71..TC-90). Names state what the test proves, not what it calls.

`WALLETS_URL`/`_create_wallet`/`_fields`/`_expired_token` are reused by
import from test_wm_us_02_list_wallets.py, the same precedent
test_wm_us_04_update_wallet.py already set for its own WM-US-04 imports —
wallets are seeded through the real POST /api/v1/wallets endpoint (WM-US-01,
already implemented), never inserted directly.

Categories are constructed directly against the `db` session (the same
"arrange via direct model construction" style test_tm_us_01_create_transaction.py
and test_bm_us_01_create_budget.py already use for their own prerequisite
categories) — no public category-creation endpoint is part of this story's
own scope.

Stored state is always re-read through `_stored()`, which expires the test
session's identity map first — otherwise a read could return the test
session's own cached copy instead of what the request actually committed
(the same QF-09 discipline test_wm_us_04_update_wallet.py already
established).

TC-79's idempotency proof reuses conftest.py's `frozen_now`/`advance_clock`
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

from app.models.budget import BudgetModel
from app.models.category import CategoryModel, CategoryType
from app.models.transaction import TransactionModel
from app.models.user import UserModel
from app.models.wallet import WalletModel
from tests.integration.test_wm_us_02_list_wallets import WALLETS_URL, _create_wallet

TRANSACTIONS_URL = "/api/v1/transactions"
BUDGETS_URL = "/api/v1/budgets"

NONEXISTENT_WALLET_ID = "00000000-0000-0000-0000-000000000000"


# --- helpers ----------------------------------------------------------------


def _url(wallet_id: str) -> str:
    return f"{WALLETS_URL}/{wallet_id}"


def _stored(db: Session, wallet_id: str) -> WalletModel:
    """The committed `wallets` row, read fresh rather than from the identity map."""
    db.expire_all()
    wallet = db.get(WalletModel, wallet_id)
    assert wallet is not None
    return wallet


def _wallet_row_count(db: Session, wallet_id: str) -> int:
    return (
        db.scalar(select(func.count()).select_from(WalletModel).where(WalletModel.id == wallet_id))
        or 0
    )


def _make_category(
    db: Session, *, user_id: str, category_type: CategoryType, name: str = "Groceries"
) -> CategoryModel:
    category = CategoryModel(user_id=user_id, name=name, type=category_type)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def _assert_timestamp(value: object) -> datetime:
    assert isinstance(value, str)
    parsed = datetime.fromisoformat(value)
    assert parsed.tzinfo is not None
    return parsed


# --- TC-71: the happy path ----------------------------------------------------


def test_an_authenticated_owner_archives_a_wallet_200_other_fields_unchanged(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-71: wallet name "Old Checking"/type "BANK"/currency "USD"/balance
    500.00, not yet archived -> DELETE -> 200; id unchanged,
    name/type/currency/balance unchanged, archived_at set to a real
    timestamp.
    """
    wallet = _create_wallet(
        client,
        user_headers,
        name="Old Checking",
        type="BANK",
        currency="USD",
        initial_balance="500.00",
    )

    response = client.delete(_url(str(wallet["id"])), headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == wallet["id"]
    assert body["name"] == "Old Checking"
    assert body["type"] == "BANK"
    assert body["currency"] == "USD"
    assert Decimal(str(body["balance"])) == Decimal("500.00")
    _assert_timestamp(body["archived_at"])


# --- TC-72: persistence on the same single row --------------------------------


def test_archiving_a_wallet_persists_the_new_state_on_the_same_single_row(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-72: direct inspection of the `wallets` row shows `archived_at`
    set to a non-NULL value; exactly one row still exists for that id.
    """
    wallet = _create_wallet(client, user_headers)

    response = client.delete(_url(str(wallet["id"])), headers=user_headers)

    assert response.status_code == 200
    stored = _stored(db, str(wallet["id"]))
    assert stored.archived_at is not None
    assert _wallet_row_count(db, str(wallet["id"])) == 1


# --- TC-73: authentication -----------------------------------------------------


def test_an_unauthenticated_caller_is_denied_with_401_and_nothing_is_archived(
    client: TestClient, admin_headers: dict[str, str], db: Session
) -> None:
    """TC-73: no Authorization header, against an existing wallet belonging
    to some other, real User -> 401 NOT_AUTHENTICATED; the target wallet's
    archived_at remains NULL.
    """
    other_wallet = _create_wallet(client, admin_headers, name="Someone Else's")

    response = client.delete(_url(str(other_wallet["id"])))

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"
    assert _stored(db, str(other_wallet["id"])).archived_at is None


# --- TC-74/TC-75/TC-76/TC-77/TC-78: not-found/ownership collapse (QF-16) ------


def test_a_wallet_id_matching_no_wallet_at_all_is_rejected_with_404(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-74: a wallet_id matching no wallet in the system -> 404
    WALLET_NOT_FOUND; nothing archived.
    """
    response = client.delete(_url(str(uuid4())), headers=user_headers)

    assert response.status_code == 404
    assert response.json()["error_code"] == "WALLET_NOT_FOUND"


def test_a_wallet_belonging_to_a_different_user_gets_the_identical_404_as_not_found(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    db: Session,
) -> None:
    """TC-75: B owns a wallet, A submits DELETE against it -> 404 identical
    (error_code/message/details) to TC-74's not-found-at-all response; B's
    wallet remains unarchived.
    """
    b_wallet = _create_wallet(client, admin_headers, name="B's Wallet")

    not_owned = client.delete(_url(str(b_wallet["id"])), headers=user_headers)
    not_found = client.delete(_url(str(uuid4())), headers=user_headers)

    assert not_owned.status_code == 404
    assert not_owned.json()["error_code"] == "WALLET_NOT_FOUND"
    assert not_owned.json() == not_found.json()
    assert _stored(db, str(b_wallet["id"])).archived_at is None


def test_a_malformed_wallet_reference_gets_the_same_404_as_a_well_formed_unknown_one(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-76: DELETE /wallets/not-a-real-id -> 404 WALLET_NOT_FOUND,
    identical to TC-74's response.
    """
    malformed = client.delete(_url("not-a-real-id"), headers=user_headers)
    unknown = client.delete(_url(str(uuid4())), headers=user_headers)

    assert malformed.status_code == 404
    assert malformed.json()["error_code"] == "WALLET_NOT_FOUND"
    assert malformed.json() == unknown.json()


def test_a_caller_who_owns_a_different_wallet_cannot_archive_another_users_wallet(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    db: Session,
) -> None:
    """TC-77: A owns WA, B owns WB; A submits DELETE against WB -> 404
    WALLET_NOT_FOUND identical to TC-74/TC-75; WB remains unarchived, A's
    own WA is unaffected.
    """
    wa = _create_wallet(client, user_headers, name="A's Wallet")
    wb = _create_wallet(client, admin_headers, name="B's Wallet")

    response = client.delete(_url(str(wb["id"])), headers=user_headers)
    not_found = client.delete(_url(str(uuid4())), headers=user_headers)

    assert response.status_code == 404
    assert response.json()["error_code"] == "WALLET_NOT_FOUND"
    assert response.json() == not_found.json()
    assert _stored(db, str(wb["id"])).archived_at is None
    assert _stored(db, str(wa["id"])).archived_at is None


def test_an_admin_role_caller_cannot_archive_another_users_wallet_through_this_endpoint(
    client: TestClient,
    admin_headers: dict[str, str],
    user_headers: dict[str, str],
    db: Session,
) -> None:
    """TC-78: an ADMIN-role caller submits DELETE against another User's
    wallet -> 404 WALLET_NOT_FOUND -- the same outcome any non-ADMIN caller
    would get; no role grants authority through this endpoint.
    """
    user_wallet = _create_wallet(client, user_headers, name="User's Wallet")

    response = client.delete(_url(str(user_wallet["id"])), headers=admin_headers)

    assert response.status_code == 404
    assert response.json()["error_code"] == "WALLET_NOT_FOUND"
    assert _stored(db, str(user_wallet["id"])).archived_at is None


# --- TC-79: idempotency (QF-14) ------------------------------------------------


def test_a_repeated_archive_request_succeeds_again_with_the_identical_archive_time(
    client: TestClient,
    user_headers: dict[str, str],
    frozen_now: datetime,
    advance_clock: Callable[[timedelta], datetime],
) -> None:
    """TC-79: a first DELETE records archived_at at T1; a second DELETE,
    issued a real time gap later, returns 200 (not 404/409) with the
    identical archived_at -- not a new, later timestamp.
    """
    wallet = _create_wallet(client, user_headers)

    first = client.delete(_url(str(wallet["id"])), headers=user_headers)
    assert first.status_code == 200
    t1 = first.json()["archived_at"]

    advance_clock(timedelta(hours=1))

    second = client.delete(_url(str(wallet["id"])), headers=user_headers)

    assert second.status_code == 200
    assert second.json()["archived_at"] == t1


# --- TC-80: name/type/currency/balance unchanged, verified against storage ----


def test_archiving_leaves_name_type_currency_and_balance_unchanged_verified_against_storage(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-80: wallet name "Old Checking"/type "BANK"/currency "USD"/balance
    750.25 -> archive succeeds -> a direct read of the `wallets` row
    confirms all four are identical to their pre-archive values.
    """
    wallet = _create_wallet(
        client,
        user_headers,
        name="Old Checking",
        type="BANK",
        currency="USD",
        initial_balance="750.25",
    )

    response = client.delete(_url(str(wallet["id"])), headers=user_headers)

    assert response.status_code == 200
    stored = _stored(db, str(wallet["id"]))
    assert stored.name == "Old Checking"
    assert stored.type == "BANK"
    assert stored.currency == "USD"
    assert stored.balance == Decimal("750.25")


# --- TC-81/TC-82: list exclusion, items and total together (QF-15) ------------


def test_an_archived_wallet_is_excluded_from_both_items_and_total_of_the_default_list(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-81: one active wallet and one already-archived wallet for the
    same caller -> GET /wallets items contains only the active wallet,
    total is 1.
    """
    active = _create_wallet(client, user_headers, name="Active")
    to_archive = _create_wallet(client, user_headers, name="To Archive")
    archived = client.delete(_url(str(to_archive["id"])), headers=user_headers)
    assert archived.status_code == 200

    response = client.get(WALLETS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == active["id"]
    assert all(item["id"] != to_archive["id"] for item in body["items"])


def test_a_caller_whose_only_wallet_is_archived_receives_an_empty_list_and_zero_total(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-82: a caller's only wallet is already archived -> GET /wallets
    items is empty, total is 0, not 1.
    """
    only = _create_wallet(client, user_headers, name="Only Wallet")
    archived = client.delete(_url(str(only["id"])), headers=user_headers)
    assert archived.status_code == 200

    response = client.get(WALLETS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


# --- TC-83/TC-84: still individually viewable, no leak (QF-18) ----------------


def test_an_archived_wallet_can_still_be_viewed_directly_by_its_own_identifier(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-83: an already-archived wallet -> GET /wallets/{id} -> 200, not
    404; full, unchanged detail exactly as WM-US-03 already defines it.
    """
    wallet = _create_wallet(client, user_headers, name="Archived One")
    archived = client.delete(_url(str(wallet["id"])), headers=user_headers)
    assert archived.status_code == 200

    response = client.get(_url(str(wallet["id"])), headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == wallet["id"]
    assert body["name"] == "Archived One"


def test_viewing_an_archived_wallet_exposes_exactly_the_six_original_fields(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-84: GET /wallets/{id} for an already-archived wallet -> the
    response body's keys are exactly id, user_id, name, type, currency,
    balance -- no more, and in particular no archived_at/is_archived/any
    other archived-state field.
    """
    wallet = _create_wallet(client, user_headers)
    archived = client.delete(_url(str(wallet["id"])), headers=user_headers)
    assert archived.status_code == 200

    response = client.get(_url(str(wallet["id"])), headers=user_headers)

    assert response.status_code == 200
    assert set(response.json().keys()) == {
        "id",
        "user_id",
        "name",
        "type",
        "currency",
        "balance",
    }


# --- TC-85/TC-86: archived wallet blocks new Transactions/Budgets (QF-17) -----


def test_a_new_transaction_against_an_archived_wallet_is_rejected_with_409(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
) -> None:
    """TC-85: an already-archived wallet and an existing category of the
    caller's own -> POST /transactions referencing the archived wallet ->
    409 TRANSACTION_WALLET_ARCHIVED; direct inspection of the
    `transactions` table confirms no new row was created.
    """
    wallet = _create_wallet(client, user_headers, initial_balance="1000.00")
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    archived = client.delete(_url(str(wallet["id"])), headers=user_headers)
    assert archived.status_code == 200

    before = db.scalar(select(func.count()).select_from(TransactionModel)) or 0
    response = client.post(
        TRANSACTIONS_URL,
        json={
            "wallet_id": wallet["id"],
            "category_id": category.id,
            "amount": "50.00",
            "type": "EXPENSE",
        },
        headers=user_headers,
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "TRANSACTION_WALLET_ARCHIVED"
    after = db.scalar(select(func.count()).select_from(TransactionModel)) or 0
    assert after == before


def test_a_new_budget_against_an_archived_wallet_is_rejected_with_409(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
) -> None:
    """TC-86: an already-archived wallet and an existing category of the
    caller's own -> POST /budgets referencing the archived wallet -> 409
    BUDGET_WALLET_ARCHIVED; direct inspection of the `budgets` table
    confirms no new row was created.
    """
    wallet = _create_wallet(client, user_headers)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    archived = client.delete(_url(str(wallet["id"])), headers=user_headers)
    assert archived.status_code == 200

    before = db.scalar(select(func.count()).select_from(BudgetModel)) or 0
    response = client.post(
        BUDGETS_URL,
        json={
            "wallet_id": wallet["id"],
            "category_id": category.id,
            "amount_limit": "200.00",
        },
        headers=user_headers,
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "BUDGET_WALLET_ARCHIVED"
    after = db.scalar(select(func.count()).select_from(BudgetModel)) or 0
    assert after == before


# --- TC-87/TC-88: existing history and balance untouched ----------------------


def test_archiving_a_wallet_with_existing_transactions_and_budgets_leaves_them_untouched(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
) -> None:
    """TC-87: a wallet with one existing Transaction and one existing
    Budget already recorded -> archive succeeds -> both rows are
    unchanged (same ids, same wallet_id, same amounts) and remain
    retrievable through their own already-existing endpoints exactly as
    before.
    """
    wallet = _create_wallet(client, user_headers, initial_balance="1000.00")
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    txn_response = client.post(
        TRANSACTIONS_URL,
        json={
            "wallet_id": wallet["id"],
            "category_id": category.id,
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
            "wallet_id": wallet["id"],
            "category_id": category.id,
            "amount_limit": "200.00",
        },
        headers=user_headers,
    )
    assert budget_response.status_code == 201
    budget = budget_response.json()

    archived = client.delete(_url(str(wallet["id"])), headers=user_headers)
    assert archived.status_code == 200

    view_txn = client.get(f"{TRANSACTIONS_URL}/{transaction['id']}", headers=user_headers)
    assert view_txn.status_code == 200
    assert view_txn.json()["id"] == transaction["id"]
    assert view_txn.json()["wallet_id"] == wallet["id"]
    assert Decimal(str(view_txn.json()["amount"])) == Decimal("50.00")

    budget_list = client.get(BUDGETS_URL, headers=user_headers)
    assert budget_list.status_code == 200
    matching = [item for item in budget_list.json()["items"] if item["id"] == budget["id"]]
    assert len(matching) == 1
    assert matching[0]["wallet_id"] == wallet["id"]
    assert Decimal(str(matching[0]["amount_limit"])) == Decimal("200.00")

    stored_txn = db.get(TransactionModel, transaction["id"])
    assert stored_txn is not None
    assert stored_txn.wallet_id == wallet["id"]
    assert stored_txn.amount == Decimal("50.00")
    stored_budget = db.get(BudgetModel, budget["id"])
    assert stored_budget is not None
    assert stored_budget.wallet_id == wallet["id"]
    assert stored_budget.amount_limit == Decimal("200.00")


def test_an_archived_wallets_stored_balance_is_unaffected_by_the_archive_operation(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-88: wallet balance 312.40, shaped by prior Transaction activity
    -> archive succeeds -> response balance is 312.40, identical to its
    pre-archive value; a direct read of the stored row confirms the same.
    """
    wallet = _create_wallet(client, user_headers, initial_balance="312.40")

    response = client.delete(_url(str(wallet["id"])), headers=user_headers)

    assert response.status_code == 200
    assert Decimal(str(response.json()["balance"])) == Decimal("312.40")
    stored = _stored(db, str(wallet["id"]))
    assert stored.balance == Decimal("312.40")


# --- TC-89: exact response shape ----------------------------------------------


def test_the_response_exposes_exactly_the_seven_documented_fields(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-89: response body's keys are exactly id, user_id, name, type,
    currency, balance, archived_at -- no more, no other invented field.
    """
    wallet = _create_wallet(client, user_headers)

    response = client.delete(_url(str(wallet["id"])), headers=user_headers)

    assert response.status_code == 200
    assert set(response.json().keys()) == {
        "id",
        "user_id",
        "name",
        "type",
        "currency",
        "balance",
        "archived_at",
    }


# --- TC-90: credentials evaluated before the wallet reference is looked up ----


def test_credentials_are_evaluated_before_the_wallet_reference_is_looked_up(
    client: TestClient,
) -> None:
    """TC-90: no credentials, against a wallet_id matching no wallet at
    all -> 401 NOT_AUTHENTICATED, not 404 -- mirrors WM-US-03 TC-70/TM-US-03
    TC-82's own ordering.
    """
    response = client.delete(_url(NONEXISTENT_WALLET_ID))

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"
