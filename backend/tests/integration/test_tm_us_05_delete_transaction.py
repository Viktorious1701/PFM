"""TM-US-05 — Delete a Transaction.

One test per test case in specs/006-transaction-management/test_cases.md
(TC-113..TC-126). Names state what the test proves, not what it calls.

Wallet/category/transaction seeding reuses TM-US-02's own helpers by import
(`_make_wallet`, `_make_category`, `_create_transaction`, `TRANSACTIONS_URL`),
the same precedent TM-US-03/TM-US-04's own test files already set.
Transactions are always seeded through the real `POST /api/v1/transactions`
endpoint (TM-US-01, already implemented), never inserted directly, so a
transaction's `id` is whatever the server actually assigned.

Stored state is always re-read through `_stored_wallet()`/`_stored_transaction()`,
which expire the test session's identity map first -- otherwise a read could
return the test session's own cached copy instead of what the request
actually committed (the `_stored()` technique BM-US-04/CM-US-04/BM-US-05
already established).

TC-119 compares the full response body of the ownership-mismatch case
against the full response body of the corresponding not-found-at-all case
(TC-118) and asserts they match exactly -- the identical technique
BM-US-05 QF-20/TC-89 established (QF-21 here).

Decimal amounts are always sent as JSON strings, never Python floats,
mirroring every prior story's tests.
"""

from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import CategoryModel, CategoryType
from app.models.transaction import TransactionModel
from app.models.user import UserModel
from app.models.wallet import WalletModel
from tests.integration.test_tm_us_02_list_transactions import (
    TRANSACTIONS_URL,
    _create_transaction,
    _make_category,
    _make_wallet,
)

MALFORMED_ID = "not-a-real-id"


# --- helpers ----------------------------------------------------------------


def _url(transaction_id: str) -> str:
    return f"{TRANSACTIONS_URL}/{transaction_id}"


def _stored_wallet(db: Session, wallet_id: str) -> WalletModel:
    """The committed `wallets` row, read fresh rather than from the identity
    map.
    """
    db.expire_all()
    wallet = db.get(WalletModel, wallet_id)
    assert wallet is not None
    return wallet


def _stored_transaction(db: Session, transaction_id: str) -> TransactionModel | None:
    """The committed `transactions` row, read fresh rather than from the
    identity map -- `None` once the row has genuinely been removed.
    """
    db.expire_all()
    return db.get(TransactionModel, transaction_id)


# --- TC-113/TC-114: EXPENSE deletion reverses (increases) the balance -------


def test_deleting_an_expense_transaction_succeeds_and_increases_wallet_balance_by_exact_amount(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-113: wallet balance 650.00, EXPENSE 150.00 already logged (recorded
    when balance was 800.00) -> DELETE -> 204, empty body; balance now
    exactly 800.00.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("800.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="150.00"
    )
    assert _stored_wallet(db, wallet.id).balance == Decimal("650.00")

    response = client.delete(_url(str(txn["id"])), headers=user_headers)

    assert response.status_code == 204
    assert response.content == b""
    assert _stored_wallet(db, wallet.id).balance == Decimal("800.00")


def test_deleting_an_expense_transaction_permanently_removes_its_row_from_storage(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-114 (QF-22): after a 204, a direct read of the `transactions`
    table for that id finds no row at all, and a direct read of the
    wallet's `balance` row shows exactly the reversed (increased) value --
    not inferred from the (empty) response body.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("1000.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="200.00"
    )

    response = client.delete(_url(str(txn["id"])), headers=user_headers)

    assert response.status_code == 204
    assert _stored_transaction(db, str(txn["id"])) is None
    count = db.scalar(
        select(func.count()).select_from(TransactionModel).where(TransactionModel.id == txn["id"])
    )
    assert count == 0
    assert _stored_wallet(db, wallet.id).balance == Decimal("1000.00")


# --- TC-115/TC-116: INCOME deletion reverses (decreases) the balance -------


def test_deleting_an_income_transaction_succeeds_and_decreases_wallet_balance_by_exact_amount(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-115: wallet balance 100.00, INCOME 500.00 logged (bringing it to
    600.00) -> DELETE -> 204; balance now exactly 100.00.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("100.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.INCOME)
    txn = _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=category.id,
        amount="500.00",
        txn_type="INCOME",
    )
    assert _stored_wallet(db, wallet.id).balance == Decimal("600.00")

    response = client.delete(_url(str(txn["id"])), headers=user_headers)

    assert response.status_code == 204
    assert _stored_wallet(db, wallet.id).balance == Decimal("100.00")


def test_deleting_an_income_transaction_permanently_removes_its_row_from_storage(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-116 (QF-22): after a 204, a direct read of the `transactions`
    table for that id finds no row at all, and a direct read of the
    wallet's `balance` row shows exactly the reversed (decreased) value.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("100.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.INCOME)
    txn = _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=category.id,
        amount="300.00",
        txn_type="INCOME",
    )

    response = client.delete(_url(str(txn["id"])), headers=user_headers)

    assert response.status_code == 204
    assert _stored_transaction(db, str(txn["id"])) is None
    assert _stored_wallet(db, wallet.id).balance == Decimal("100.00")


# --- TC-117: authentication ---------------------------------------------


def test_an_unauthenticated_caller_is_denied_and_nothing_is_deleted(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-117: no Authorization header -> 401 NOT_AUTHENTICATED; the
    transaction's row and its wallet's balance are both unchanged.
    """
    wallet = _make_wallet(db, user_id=admin_user.id, balance=Decimal("500.00"))
    category = _make_category(db, user_id=admin_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(
        client, admin_headers, wallet_id=wallet.id, category_id=category.id, amount="50.00"
    )

    response = client.delete(_url(str(txn["id"])))

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"
    assert _stored_transaction(db, str(txn["id"])) is not None
    assert _stored_wallet(db, wallet.id).balance == Decimal("450.00")


# --- TC-118/TC-119: not found and not owned, collapsed (QF-21) -----------


def test_a_transaction_id_matching_no_transaction_at_all_is_rejected_with_404(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-118: a well-formed id matching no transaction -> 404
    TRANSACTION_NOT_FOUND.
    """
    response = client.delete(_url(str(uuid4())), headers=user_headers)

    assert response.status_code == 404
    assert response.json()["error_code"] == "TRANSACTION_NOT_FOUND"


def test_a_transaction_belonging_to_a_different_user_is_rejected_identically_to_never_existed(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-119 (QF-21): A deletes B's transaction -> 404, and error_code,
    message, and details are all identical to TC-118's not-found-at-all
    body; B's transaction and wallet balance are unchanged.
    """
    b_wallet = _make_wallet(db, user_id=admin_user.id, balance=Decimal("500.00"))
    b_category = _make_category(db, user_id=admin_user.id, category_type=CategoryType.EXPENSE)
    b_txn = _create_transaction(
        client, admin_headers, wallet_id=b_wallet.id, category_id=b_category.id, amount="50.00"
    )

    not_owned = client.delete(_url(str(b_txn["id"])), headers=user_headers)
    not_found = client.delete(_url(str(uuid4())), headers=user_headers)

    assert not_owned.status_code == 404
    assert not_owned.json()["error_code"] == "TRANSACTION_NOT_FOUND"
    assert not_owned.json() == not_found.json()
    assert _stored_transaction(db, str(b_txn["id"])) is not None
    assert _stored_wallet(db, b_wallet.id).balance == Decimal("450.00")


# --- TC-120: malformed reference (EC-01) ----------------------------------


def test_a_malformed_transaction_id_gets_the_same_404_as_a_well_formed_unknown_one(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-120: DELETE /transactions/not-a-real-id -> 404
    TRANSACTION_NOT_FOUND, identical to TC-118's body.
    """
    malformed = client.delete(_url(MALFORMED_ID), headers=user_headers)
    unknown = client.delete(_url(str(uuid4())), headers=user_headers)

    assert malformed.status_code == 404
    assert malformed.json()["error_code"] == "TRANSACTION_NOT_FOUND"
    assert malformed.json() == unknown.json()


# --- TC-121: deleting a transaction touches nothing else (QF-23) ---------


def test_deleting_a_transaction_leaves_its_category_a_sibling_and_another_wallets_txn_unaffected(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-121 (QF-23): T1 logged under C1 against W1, a sibling T2 also
    against W1 under a different category, and a second wallet W2 with its
    own T3 -- deleting T1 leaves C1, T2, W2, and T3 all unchanged.
    """
    w1 = _make_wallet(db, user_id=normal_user.id, name="W1", balance=Decimal("1000.00"))
    c1 = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name="C1")
    c2 = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name="C2")
    w2 = _make_wallet(db, user_id=normal_user.id, name="W2", balance=Decimal("300.00"))

    t1 = _create_transaction(
        client, user_headers, wallet_id=w1.id, category_id=c1.id, amount="50.00"
    )
    t2 = _create_transaction(
        client, user_headers, wallet_id=w1.id, category_id=c2.id, amount="75.00"
    )
    t3 = _create_transaction(
        client, user_headers, wallet_id=w2.id, category_id=c1.id, amount="20.00"
    )

    db.expire_all()
    c1_before = db.get(CategoryModel, c1.id)
    t2_before = db.get(TransactionModel, str(t2["id"]))
    w2_before = db.get(WalletModel, w2.id)
    t3_before = db.get(TransactionModel, str(t3["id"]))
    assert c1_before is not None
    assert t2_before is not None
    assert w2_before is not None
    assert t3_before is not None
    c1_snapshot = (c1_before.user_id, c1_before.name, c1_before.type)
    t2_snapshot = (
        t2_before.wallet_id,
        t2_before.category_id,
        t2_before.amount,
        t2_before.type,
        t2_before.timestamp,
        t2_before.note,
    )
    w2_snapshot = (w2_before.user_id, w2_before.name, w2_before.type, w2_before.balance)
    t3_snapshot = (
        t3_before.wallet_id,
        t3_before.category_id,
        t3_before.amount,
        t3_before.type,
        t3_before.timestamp,
        t3_before.note,
    )

    response = client.delete(_url(str(t1["id"])), headers=user_headers)

    assert response.status_code == 204
    assert _stored_transaction(db, str(t1["id"])) is None
    db.expire_all()
    c1_after = db.get(CategoryModel, c1.id)
    t2_after = db.get(TransactionModel, str(t2["id"]))
    w2_after = db.get(WalletModel, w2.id)
    t3_after = db.get(TransactionModel, str(t3["id"]))
    assert c1_after is not None
    assert t2_after is not None
    assert w2_after is not None
    assert t3_after is not None
    assert (c1_after.user_id, c1_after.name, c1_after.type) == c1_snapshot
    assert (
        t2_after.wallet_id,
        t2_after.category_id,
        t2_after.amount,
        t2_after.type,
        t2_after.timestamp,
        t2_after.note,
    ) == t2_snapshot
    assert (w2_after.user_id, w2_after.name, w2_after.type, w2_after.balance) == w2_snapshot
    assert (
        t3_after.wallet_id,
        t3_after.category_id,
        t3_after.amount,
        t3_after.type,
        t3_after.timestamp,
        t3_after.note,
    ) == t3_snapshot
    # W1 starts at 1000.00; t1 EXPENSE 50.00 -> 950.00; t2 EXPENSE 75.00 ->
    # 875.00 (t3 is on W2, no effect on W1). Deleting t1 reverses its own
    # 50.00 only: 875.00 + 50.00 = 925.00.
    assert _stored_wallet(db, w1.id).balance == Decimal("925.00")


# --- TC-122: a deleted transaction never again appears anywhere ----------


def test_a_deleted_transaction_never_again_appears_in_a_list_or_a_direct_lookup(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-122: after a 204, GET /transactions/{id} -> 404
    TRANSACTION_NOT_FOUND, and GET /transactions' items no longer include
    the deleted transaction's id.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("500.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="25.00"
    )

    response = client.delete(_url(str(txn["id"])), headers=user_headers)
    assert response.status_code == 204

    direct = client.get(_url(str(txn["id"])), headers=user_headers)
    listed = client.get(TRANSACTIONS_URL, headers=user_headers)

    assert direct.status_code == 404
    assert direct.json()["error_code"] == "TRANSACTION_NOT_FOUND"
    assert listed.status_code == 200
    assert txn["id"] not in [item["id"] for item in listed.json()["items"]]


# --- TC-123: a repeated deletion is refused identically to never-existed (QF-24)


def test_deleting_a_transaction_a_second_time_is_rejected_identically_to_never_existed(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-123 (QF-24, EC-05): delete a transaction (204), then delete the
    same id again -> the second response is 404, with error_code, message,
    and details identical to a never-existed id's response -- not a
    distinct "already deleted" error (plan.md A8).
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("500.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="25.00"
    )

    first = client.delete(_url(str(txn["id"])), headers=user_headers)
    second = client.delete(_url(str(txn["id"])), headers=user_headers)
    never_existed = client.delete(_url(str(uuid4())), headers=user_headers)

    assert first.status_code == 204
    assert second.status_code == 404
    assert second.json()["error_code"] == "TRANSACTION_NOT_FOUND"
    assert second.json() == never_existed.json()


# --- TC-124: owning a transaction never grants access to someone else's -


def test_a_caller_who_owns_a_transaction_cannot_delete_another_users_transaction(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    normal_user: UserModel,
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-124 (EC-02): A owns TA, B owns TB; A deletes TB -> 404
    TRANSACTION_NOT_FOUND, identical to TC-118's response; TB is unchanged,
    and A's own TA is also unaffected.
    """
    a_wallet = _make_wallet(db, user_id=normal_user.id, name="A-W", balance=Decimal("500.00"))
    a_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name="A-C"
    )
    ta = _create_transaction(
        client, user_headers, wallet_id=a_wallet.id, category_id=a_category.id, amount="25.00"
    )
    b_wallet = _make_wallet(db, user_id=admin_user.id, name="B-W", balance=Decimal("500.00"))
    b_category = _make_category(
        db, user_id=admin_user.id, category_type=CategoryType.EXPENSE, name="B-C"
    )
    tb = _create_transaction(
        client, admin_headers, wallet_id=b_wallet.id, category_id=b_category.id, amount="25.00"
    )

    response = client.delete(_url(str(tb["id"])), headers=user_headers)
    not_found = client.delete(_url(str(uuid4())), headers=user_headers)

    assert response.status_code == 404
    assert response.json()["error_code"] == "TRANSACTION_NOT_FOUND"
    assert response.json() == not_found.json()
    assert _stored_transaction(db, str(tb["id"])) is not None
    assert _stored_transaction(db, str(ta["id"])) is not None
    assert _stored_wallet(db, b_wallet.id).balance == Decimal("475.00")


# --- TC-125: reversal scoped only to the deleted transaction's own amount -


def test_deleting_an_expense_transaction_reverses_only_its_own_amount_despite_other_activity_since(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-125 (EC-03): wallet 1000.00; T1 EXPENSE 200.00 (balance 800.00);
    T2 INCOME 300.00 (balance 1100.00); T3 EXPENSE 100.00 (balance
    1000.00) -> delete T1 -> 204; balance now exactly 1200.00 (1000.00 +
    T1's reversed 200.00); T2 and T3 remain exactly as they were.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("1000.00"))
    expense_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name="Expenses"
    )
    income_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.INCOME, name="Income"
    )

    t1 = _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=expense_category.id,
        amount="200.00",
    )
    assert _stored_wallet(db, wallet.id).balance == Decimal("800.00")
    t2 = _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=income_category.id,
        amount="300.00",
        txn_type="INCOME",
    )
    assert _stored_wallet(db, wallet.id).balance == Decimal("1100.00")
    t3 = _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=expense_category.id,
        amount="100.00",
    )
    assert _stored_wallet(db, wallet.id).balance == Decimal("1000.00")

    db.expire_all()
    t2_before = db.get(TransactionModel, str(t2["id"]))
    t3_before = db.get(TransactionModel, str(t3["id"]))
    assert t2_before is not None
    assert t3_before is not None
    t2_snapshot = (t2_before.amount, t2_before.type, t2_before.wallet_id, t2_before.category_id)
    t3_snapshot = (t3_before.amount, t3_before.type, t3_before.wallet_id, t3_before.category_id)

    response = client.delete(_url(str(t1["id"])), headers=user_headers)

    assert response.status_code == 204
    assert _stored_wallet(db, wallet.id).balance == Decimal("1200.00")
    db.expire_all()
    t2_after = db.get(TransactionModel, str(t2["id"]))
    t3_after = db.get(TransactionModel, str(t3["id"]))
    assert t2_after is not None
    assert t3_after is not None
    assert (t2_after.amount, t2_after.type, t2_after.wallet_id, t2_after.category_id) == t2_snapshot
    assert (t3_after.amount, t3_after.type, t3_after.wallet_id, t3_after.category_id) == t3_snapshot


# --- TC-126: an INCOME reversal is never refused, even driven negative (QF-25)


def test_deleting_an_income_transaction_is_accepted_unconditionally_even_driving_balance_negative(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-126 (EC-04, QF-25): wallet balance 100.00, with one INCOME
    transaction of 500.00 already logged against it (recorded when the
    balance was -400.00, reachable per WM-US-01 EC-02) -> delete -> 204,
    not refused for any balance-related reason; balance now exactly
    -400.00 (100.00 minus the reversed 500.00).
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("-400.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.INCOME)
    txn = _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=category.id,
        amount="500.00",
        txn_type="INCOME",
    )
    assert _stored_wallet(db, wallet.id).balance == Decimal("100.00")

    response = client.delete(_url(str(txn["id"])), headers=user_headers)

    assert response.status_code == 204
    assert _stored_wallet(db, wallet.id).balance == Decimal("-400.00")
