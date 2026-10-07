"""TM-US-04 — Update a Transaction.

One test per test case in specs/006-transaction-management/test_cases.md
(TC-83..TC-112). Names state what the test proves, not what it calls.

Wallet/category/transaction seeding reuses TM-US-02's own helpers by import
(`_make_wallet`, `_make_category`, `_create_transaction`, `TRANSACTIONS_URL`)
— the same precedent TM-US-03's own test file already set. Transactions are
always seeded through the real `POST /api/v1/transactions` endpoint
(TM-US-01, already implemented), never inserted directly, so a transaction's
`id` is whatever the server actually assigned.

Stored state is always re-read through `_stored_wallet()`/`_stored_transaction()`,
which expire the test session's identity map first — otherwise a read could
return the test session's own cached copy instead of what the request
actually committed (the `_stored()` technique BM-US-04/CM-US-04 already
established, QF-19/QF-10 there).

TC-94 compares the full response body of the ownership-mismatch case against
the full response body of the corresponding not-found-at-all case (TC-93)
and asserts they match exactly — the identical technique BM-US-04
QF-16/TC-68 established (QF-18 here).

Decimal amounts are always sent as JSON strings, never Python floats,
mirroring every prior story's tests.
"""

from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.category import CategoryType
from app.models.transaction import TransactionModel
from app.models.user import UserModel
from app.models.wallet import WalletModel
from tests.integration.test_tm_us_02_list_transactions import (
    TRANSACTIONS_URL,
    _create_transaction,
    _make_category,
    _make_wallet,
)


def _url(transaction_id: str) -> str:
    return f"{TRANSACTIONS_URL}/{transaction_id}"


def _stored_wallet(db: Session, wallet_id: str) -> WalletModel:
    """The committed `wallets` row, read fresh rather than from the identity
    map (mirrors BM-US-04/CM-US-04's own `_stored()`).
    """
    db.expire_all()
    wallet = db.get(WalletModel, wallet_id)
    assert wallet is not None
    return wallet


def _stored_transaction(db: Session, transaction_id: str) -> TransactionModel:
    """The committed `transactions` row, read fresh rather than from the
    identity map.
    """
    db.expire_all()
    transaction = db.get(TransactionModel, transaction_id)
    assert transaction is not None
    return transaction


def _fields(body: dict[str, object]) -> list[str]:
    details = body["details"]
    assert isinstance(details, dict)
    return [f["location"][-1] for f in details["fields"]]  # type: ignore[index]


# --- TC-83/TC-84: amount-only update of an EXPENSE, net effect only --------


def test_updating_only_the_amount_of_an_expense_recalculates_balance_to_net_effect_up(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-83: wallet 1000.00, EXPENSE 200.00 logged (balance 800.00) -> PATCH
    amount 350.00 only -> 200; amount 350.00; balance exactly 650.00 (1000.00
    minus the new 350.00), never 800.00 minus 350.00.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("1000.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="200.00"
    )

    response = client.patch(_url(str(txn["id"])), json={"amount": "350.00"}, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert Decimal(str(body["amount"])) == Decimal("350.00")
    assert _stored_wallet(db, wallet.id).balance == Decimal("650.00")


def test_updating_only_the_amount_of_an_expense_to_a_smaller_value_frees_the_difference(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-84: wallet 1000.00, EXPENSE 400.00 logged (balance 600.00) -> PATCH
    amount 100.00 only -> 200; amount 100.00; balance exactly 900.00.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("1000.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="400.00"
    )

    response = client.patch(_url(str(txn["id"])), json={"amount": "100.00"}, headers=user_headers)

    assert response.status_code == 200
    assert Decimal(str(response.json()["amount"])) == Decimal("100.00")
    assert _stored_wallet(db, wallet.id).balance == Decimal("900.00")


# --- TC-85: amount-only update of an INCOME, regardless of balance --------


def test_updating_only_the_amount_of_an_income_succeeds_regardless_of_balance(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-85: wallet 50.00, INCOME 20.00 logged (balance 70.00) -> PATCH
    amount 500.00 only -> 200; amount 500.00; balance exactly 550.00
    (70.00 minus the reversed 20.00, plus the new 500.00).
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("50.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.INCOME)
    txn = _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=category.id,
        amount="20.00",
        type="INCOME",
    )

    response = client.patch(_url(str(txn["id"])), json={"amount": "500.00"}, headers=user_headers)

    assert response.status_code == 200
    assert Decimal(str(response.json()["amount"])) == Decimal("500.00")
    assert _stored_wallet(db, wallet.id).balance == Decimal("550.00")


# --- TC-86: type flip EXPENSE -> INCOME always succeeds --------------------


def test_changing_type_from_expense_to_income_always_succeeds(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-86: wallet 1000.00, EXPENSE 300.00 logged (balance 700.00) -> PATCH
    type INCOME + an INCOME-typed category, no new amount -> 200; type
    INCOME; balance exactly 1300.00 (700.00 + reversed 300.00 + reapplied
    300.00 as income).
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("1000.00"))
    expense_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE
    )
    income_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.INCOME, name="Salary"
    )
    txn = _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=expense_category.id,
        amount="300.00",
    )

    response = client.patch(
        _url(str(txn["id"])),
        json={"type": "INCOME", "category_id": income_category.id},
        headers=user_headers,
    )

    assert response.status_code == 200
    assert response.json()["type"] == "INCOME"
    assert _stored_wallet(db, wallet.id).balance == Decimal("1300.00")


# --- TC-87/TC-88: type flip INCOME -> EXPENSE, success and refusal ---------


def test_changing_type_from_income_to_expense_succeeds_when_the_wallet_can_support_it(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-87 (numbers corrected — see handback report finding on test_cases.md's
    own TC-87 arithmetic): wallet 500.00, INCOME 400.00 logged (balance
    900.00) -> PATCH type EXPENSE + an EXPENSE-typed category, no new
    amount -> 200; type EXPENSE; reversal brings the balance to 500.00
    (>= the 400.00 effective amount, so the wallet "can support" the new
    expense, per AC-04's own precondition); balance exactly 100.00
    (900.00 - reversed 400.00 - reapplied 400.00 as expense).
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("500.00"))
    income_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.INCOME, name="Salary"
    )
    expense_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE
    )
    txn = _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=income_category.id,
        amount="400.00",
        type="INCOME",
    )

    response = client.patch(
        _url(str(txn["id"])),
        json={"type": "EXPENSE", "category_id": expense_category.id},
        headers=user_headers,
    )

    assert response.status_code == 200
    assert response.json()["type"] == "EXPENSE"
    assert _stored_wallet(db, wallet.id).balance == Decimal("100.00")


def test_changing_type_from_income_to_expense_refused_for_insufficient_balance(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-88: wallet 50.00, INCOME 400.00 logged (balance 450.00) -> PATCH
    type EXPENSE + an EXPENSE category + amount 1000.00 -> 409
    TRANSACTION_INSUFFICIENT_BALANCE; a direct DB read shows the transaction's
    type still INCOME, amount still 400.00, category_id still the original,
    and the wallet's balance still exactly 450.00 (QF-16 DB-level technique).
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("50.00"))
    income_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.INCOME, name="Salary"
    )
    expense_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE
    )
    txn = _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=income_category.id,
        amount="400.00",
        type="INCOME",
    )

    response = client.patch(
        _url(str(txn["id"])),
        json={"type": "EXPENSE", "category_id": expense_category.id, "amount": "1000.00"},
        headers=user_headers,
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "TRANSACTION_INSUFFICIENT_BALANCE"

    stored_txn = _stored_transaction(db, str(txn["id"]))
    assert stored_txn.type.value == "INCOME"
    assert stored_txn.amount == Decimal("400.00")
    assert stored_txn.category_id == income_category.id
    assert _stored_wallet(db, wallet.id).balance == Decimal("450.00")


# --- TC-89: category-only update leaves amount/type/balance alone ---------


def test_updating_only_the_category_leaves_amount_type_and_balance_unchanged(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-89: wallet 800.00, EXPENSE 150.00 logged under "Groceries" (balance
    650.00); a second EXPENSE-typed category "Transport" exists -> PATCH
    category_id "Transport" only -> 200; category_id updated; amount still
    150.00, type still EXPENSE; balance still exactly 650.00.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("800.00"))
    groceries = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name="Groceries"
    )
    transport = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name="Transport"
    )
    txn = _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=groceries.id, amount="150.00"
    )

    response = client.patch(
        _url(str(txn["id"])), json={"category_id": transport.id}, headers=user_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["category_id"] == transport.id
    assert Decimal(str(body["amount"])) == Decimal("150.00")
    assert body["type"] == "EXPENSE"
    assert _stored_wallet(db, wallet.id).balance == Decimal("650.00")


# --- TC-90: note-only update leaves everything else alone -----------------


def test_updating_only_the_note_leaves_amount_type_category_and_balance_unchanged(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-90: wallet 800.00, EXPENSE 150.00 logged -> PATCH note only ->
    200; note updated; amount, type, category_id all unchanged; balance
    still exactly 650.00.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("800.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="150.00"
    )

    response = client.patch(
        _url(str(txn["id"])), json={"note": "Corrected merchant name"}, headers=user_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["note"] == "Corrected merchant name"
    assert Decimal(str(body["amount"])) == Decimal("150.00")
    assert body["type"] == "EXPENSE"
    assert body["category_id"] == category.id
    assert _stored_wallet(db, wallet.id).balance == Decimal("650.00")


# --- TC-91: all four fields together ---------------------------------------


def test_updating_category_amount_type_and_note_together_recalculates_to_net_effect(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-91: wallet 1000.00, EXPENSE 200.00 logged (balance 800.00), an
    INCOME-typed category "Salary" exists -> PATCH category_id "Salary",
    amount 600.00, type INCOME, note "Bonus" together -> 200; all four
    submitted exactly; balance exactly 1600.00 (800.00 + reversed 200.00
    expense + reapplied 600.00 income).
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("1000.00"))
    expense_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE
    )
    salary = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.INCOME, name="Salary"
    )
    txn = _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=expense_category.id,
        amount="200.00",
    )

    response = client.patch(
        _url(str(txn["id"])),
        json={
            "category_id": salary.id,
            "amount": "600.00",
            "type": "INCOME",
            "note": "Bonus",
        },
        headers=user_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["category_id"] == salary.id
    assert Decimal(str(body["amount"])) == Decimal("600.00")
    assert body["type"] == "INCOME"
    assert body["note"] == "Bonus"
    assert _stored_wallet(db, wallet.id).balance == Decimal("1600.00")


# --- TC-92: authentication --------------------------------------------------


def test_an_unauthenticated_caller_is_denied_with_401(
    client: TestClient, admin_headers: dict[str, str], admin_user: UserModel, db: Session
) -> None:
    """TC-92: no Authorization header, against an existing transaction
    belonging to some other, real User -> 401 NOT_AUTHENTICATED; the
    transaction and its wallet's balance are unchanged.
    """
    wallet = _make_wallet(db, user_id=admin_user.id)
    category = _make_category(db, user_id=admin_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(client, admin_headers, wallet_id=wallet.id, category_id=category.id)

    response = client.patch(_url(str(txn["id"])), json={"note": "nope"})

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"
    assert _stored_transaction(db, str(txn["id"])).note is None
    assert _stored_wallet(db, wallet.id).balance == Decimal("990.00")


# --- TC-93/TC-94: not found and not owned, collapsed (QF-18) ---------------


def test_a_transaction_id_matching_no_transaction_is_rejected_with_404(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-93: an id matching no transaction in the system -> 404
    TRANSACTION_NOT_FOUND.
    """
    response = client.patch(_url(str(uuid4())), json={"note": "anything"}, headers=user_headers)

    assert response.status_code == 404
    assert response.json()["error_code"] == "TRANSACTION_NOT_FOUND"


def test_another_users_transaction_is_refused_with_a_body_identical_to_not_found(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-94: B owns a transaction, A owns nothing of the kind -> A's PATCH
    against B's transaction is 404, and error_code/message/details are all
    identical to a well-formed-but-nonexistent id's body (QF-18); B's
    transaction and wallet balance are unchanged.
    """
    b_wallet = _make_wallet(db, user_id=admin_user.id)
    b_category = _make_category(db, user_id=admin_user.id, category_type=CategoryType.EXPENSE)
    b_txn = _create_transaction(
        client, admin_headers, wallet_id=b_wallet.id, category_id=b_category.id
    )

    not_owned = client.patch(
        _url(str(b_txn["id"])), json={"note": "intruding edit"}, headers=user_headers
    )
    not_found = client.patch(
        _url(str(uuid4())), json={"note": "intruding edit"}, headers=user_headers
    )

    assert not_owned.status_code == 404
    assert not_owned.json()["error_code"] == "TRANSACTION_NOT_FOUND"
    assert not_owned.json() == not_found.json()
    assert _stored_transaction(db, str(b_txn["id"])).note is None
    assert _stored_wallet(db, b_wallet.id).balance == Decimal("990.00")


# --- TC-95: no field submitted at all ---------------------------------------


def test_a_request_naming_no_editable_field_at_all_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-95: PATCH body names none of category_id/amount/type/note -> 422
    VALIDATION_ERROR; the transaction and its wallet's balance are unchanged.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(client, user_headers, wallet_id=wallet.id, category_id=category.id)

    response = client.patch(_url(str(txn["id"])), json={}, headers=user_headers)

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"
    assert _stored_wallet(db, wallet.id).balance == Decimal("990.00")


# --- TC-96: unresolvable category reference ---------------------------------


def test_a_submitted_category_reference_that_does_not_resolve_is_rejected_with_404(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-96: category_id matches no category at all -> 404
    TRANSACTION_CATEGORY_NOT_FOUND; the transaction and its wallet's balance
    are unchanged.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(client, user_headers, wallet_id=wallet.id, category_id=category.id)

    response = client.patch(
        _url(str(txn["id"])), json={"category_id": str(uuid4())}, headers=user_headers
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "TRANSACTION_CATEGORY_NOT_FOUND"
    assert _stored_wallet(db, wallet.id).balance == Decimal("990.00")


# --- TC-97/TC-98/TC-99: invalid amount --------------------------------------


def test_a_submitted_amount_of_exactly_zero_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-97: amount 0.00 -> 422 VALIDATION_ERROR naming amount; unchanged."""
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(client, user_headers, wallet_id=wallet.id, category_id=category.id)

    response = client.patch(_url(str(txn["id"])), json={"amount": "0.00"}, headers=user_headers)

    assert response.status_code == 422
    assert "amount" in _fields(response.json())


def test_a_negative_submitted_amount_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-98: amount -50.00 -> 422 VALIDATION_ERROR naming amount; unchanged."""
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(client, user_headers, wallet_id=wallet.id, category_id=category.id)

    response = client.patch(_url(str(txn["id"])), json={"amount": "-50.00"}, headers=user_headers)

    assert response.status_code == 422
    assert "amount" in _fields(response.json())


def test_a_submitted_amount_with_three_decimal_places_is_rejected_not_rounded(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-99: amount 99.999 -> 422 VALIDATION_ERROR naming amount; a direct
    DB read shows the transaction's amount unchanged, and the wallet's
    balance unchanged.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("1000.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="10.00"
    )

    response = client.patch(_url(str(txn["id"])), json={"amount": "99.999"}, headers=user_headers)

    assert response.status_code == 422
    assert "amount" in _fields(response.json())
    assert _stored_transaction(db, str(txn["id"])).amount == Decimal("10.00")
    assert _stored_wallet(db, wallet.id).balance == Decimal("990.00")


# --- TC-100: invalid type ----------------------------------------------------


def test_a_submitted_type_other_than_income_or_expense_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-100: type "TRANSFER" -> 422 VALIDATION_ERROR naming type; unchanged."""
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(client, user_headers, wallet_id=wallet.id, category_id=category.id)

    response = client.patch(_url(str(txn["id"])), json={"type": "TRANSFER"}, headers=user_headers)

    assert response.status_code == 422
    assert "type" in _fields(response.json())


# --- TC-101: over-long note ---------------------------------------------------


def test_a_submitted_note_longer_than_the_supported_length_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-101: a note of 501 characters -> 422 VALIDATION_ERROR naming note;
    unchanged, and the note is not truncated and saved.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(client, user_headers, wallet_id=wallet.id, category_id=category.id)

    response = client.patch(_url(str(txn["id"])), json={"note": "x" * 501}, headers=user_headers)

    assert response.status_code == 422
    assert "note" in _fields(response.json())
    assert _stored_transaction(db, str(txn["id"])).note is None


# --- TC-102/TC-103: effective category/type mismatch -----------------------


def test_category_only_change_whose_new_category_disagrees_with_unchanged_type_is_rejected(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-102: EXPENSE transaction, a second category typed INCOME exists ->
    PATCH category_id to the INCOME category only, no new type -> 409
    TRANSACTION_CATEGORY_TYPE_MISMATCH; category_id, amount, type, and
    balance all unchanged.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("1000.00"))
    expense_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE
    )
    income_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.INCOME, name="Salary"
    )
    txn = _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=expense_category.id,
        amount="50.00",
    )

    response = client.patch(
        _url(str(txn["id"])), json={"category_id": income_category.id}, headers=user_headers
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "TRANSACTION_CATEGORY_TYPE_MISMATCH"
    stored_txn = _stored_transaction(db, str(txn["id"]))
    assert stored_txn.category_id == expense_category.id
    assert stored_txn.amount == Decimal("50.00")
    assert stored_txn.type.value == "EXPENSE"
    assert _stored_wallet(db, wallet.id).balance == Decimal("950.00")


def test_type_only_change_where_existing_unresubmitted_category_no_longer_matches_is_rejected(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-103: EXPENSE transaction logged under an EXPENSE-typed category ->
    PATCH type INCOME only, no new category_id -> 409
    TRANSACTION_CATEGORY_TYPE_MISMATCH; type still EXPENSE, category_id
    unchanged, balance unchanged — the existing, unresubmitted category is
    still re-fetched and re-validated.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("1000.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="50.00"
    )

    response = client.patch(_url(str(txn["id"])), json={"type": "INCOME"}, headers=user_headers)

    assert response.status_code == 409
    assert response.json()["error_code"] == "TRANSACTION_CATEGORY_TYPE_MISMATCH"
    stored_txn = _stored_transaction(db, str(txn["id"]))
    assert stored_txn.type.value == "EXPENSE"
    assert stored_txn.category_id == category.id
    assert _stored_wallet(db, wallet.id).balance == Decimal("950.00")


# --- TC-104: a submitted wallet reference is silently ignored --------------


def test_a_submitted_wallet_reference_is_silently_ignored(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-104: transaction against wallet W1, a second wallet W2 of the same
    owner exists -> PATCH note + a wallet_id-shaped key naming W2 -> 200;
    wallet_id still W1's id; W2's balance entirely unaffected; the response
    carries no echo of the submitted wallet_id value.
    """
    w1 = _make_wallet(db, user_id=normal_user.id, name="W1", balance=Decimal("500.00"))
    w2 = _make_wallet(db, user_id=normal_user.id, name="W2", balance=Decimal("300.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(client, user_headers, wallet_id=w1.id, category_id=category.id)

    response = client.patch(
        _url(str(txn["id"])),
        json={"note": "Updated", "wallet_id": w2.id},
        headers=user_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["wallet_id"] == w1.id
    assert body["wallet_id"] != w2.id
    assert _stored_wallet(db, w2.id).balance == Decimal("300.00")


# --- TC-105/TC-106: resubmitting an identical value succeeds --------------


def test_resubmitting_the_notes_own_current_value_succeeds_as_an_ordinary_update(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-105: note "Groceries run" already stored -> PATCH note "Groceries
    run" again -> 200, not rejected as a no-op.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=category.id,
        note="Groceries run",
    )

    response = client.patch(
        _url(str(txn["id"])), json={"note": "Groceries run"}, headers=user_headers
    )

    assert response.status_code == 200
    assert response.json()["note"] == "Groceries run"


def test_resubmitting_the_amounts_own_current_value_succeeds_and_leaves_balance_unaffected(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-106: EXPENSE amount 75.00 against a wallet of balance 500.00 ->
    PATCH amount 75.00 again -> 200; amount still 75.00; balance still
    exactly 500.00, unaffected by the reverse-then-reapply round trip.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("575.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="75.00"
    )
    assert _stored_wallet(db, wallet.id).balance == Decimal("500.00")

    response = client.patch(_url(str(txn["id"])), json={"amount": "75.00"}, headers=user_headers)

    assert response.status_code == 200
    assert Decimal(str(response.json()["amount"])) == Decimal("75.00")
    assert _stored_wallet(db, wallet.id).balance == Decimal("500.00")


# --- TC-107: EXPENSE amount updated to exactly the post-reversal balance ---


def test_expense_amount_updated_to_exactly_the_post_reversal_balance_drives_balance_to_zero(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-107: wallet 300.00, EXPENSE 100.00 logged (balance 200.00) -> PATCH
    amount 300.00 (exactly 200.00 + 100.00 reversed) -> 200; amount 300.00;
    balance exactly 0.00.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("300.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="100.00"
    )

    response = client.patch(_url(str(txn["id"])), json={"amount": "300.00"}, headers=user_headers)

    assert response.status_code == 200
    assert Decimal(str(response.json()["amount"])) == Decimal("300.00")
    assert _stored_wallet(db, wallet.id).balance == Decimal("0.00")


# --- TC-108: the mathematical safety proof (QF-19) -------------------------


def test_note_only_update_succeeds_even_when_wallet_balance_has_been_driven_to_zero(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-108: wallet 500.00; T1 EXPENSE 500.00 (balance 0.00); T2 INCOME
    200.00 (balance 200.00); T3 EXPENSE 200.00 (balance 0.00 again) ->
    PATCH only T1's note -> 200; T1's note updated, amount/type unchanged;
    the wallet's balance is still exactly 0.00, unaffected — proving an
    amount/type-unchanged update can never be refused for insufficient
    balance, regardless of intervening activity (plan.md A3).
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("500.00"))
    expense_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE
    )
    income_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.INCOME, name="Salary"
    )

    t1 = _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=expense_category.id,
        amount="500.00",
    )
    assert _stored_wallet(db, wallet.id).balance == Decimal("0.00")

    _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=income_category.id,
        amount="200.00",
        type="INCOME",
    )
    assert _stored_wallet(db, wallet.id).balance == Decimal("200.00")

    _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=expense_category.id,
        amount="200.00",
    )
    assert _stored_wallet(db, wallet.id).balance == Decimal("0.00")

    response = client.patch(
        _url(str(t1["id"])), json={"note": "Reclassified later"}, headers=user_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["note"] == "Reclassified later"
    assert Decimal(str(body["amount"])) == Decimal("500.00")
    assert body["type"] == "EXPENSE"
    assert _stored_wallet(db, wallet.id).balance == Decimal("0.00")


# --- TC-109/TC-110: fixed check order ---------------------------------------


def test_unresolvable_category_outranks_a_separately_insufficient_amount(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-109: EXPENSE transaction against a low-balance wallet -> PATCH an
    unresolvable category_id together with an amount far larger than the
    wallet could support -> 404 TRANSACTION_CATEGORY_NOT_FOUND, never 409
    TRANSACTION_INSUFFICIENT_BALANCE.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("10.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="5.00"
    )

    response = client.patch(
        _url(str(txn["id"])),
        json={"category_id": str(uuid4()), "amount": "999999.00"},
        headers=user_headers,
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "TRANSACTION_CATEGORY_NOT_FOUND"


def test_category_type_mismatch_outranks_a_separately_insufficient_amount(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-110: EXPENSE transaction against a low-balance wallet, an
    INCOME-typed category exists -> PATCH that category_id (no new type, so
    the effective type stays EXPENSE) together with an amount far larger
    than the wallet could support -> 409 TRANSACTION_CATEGORY_TYPE_MISMATCH,
    never 409 TRANSACTION_INSUFFICIENT_BALANCE.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("10.00"))
    expense_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE
    )
    income_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.INCOME, name="Salary"
    )
    txn = _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=expense_category.id,
        amount="5.00",
    )

    response = client.patch(
        _url(str(txn["id"])),
        json={"category_id": income_category.id, "amount": "999999.00"},
        headers=user_headers,
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "TRANSACTION_CATEGORY_TYPE_MISMATCH"


# --- TC-111: response shape --------------------------------------------------


def test_a_successful_updates_response_exposes_exactly_the_seven_documented_fields(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-111: a successful note update -> the response body's keys are
    exactly id, wallet_id, category_id, amount, type, timestamp, note — no
    more, and in particular no user_id and no second "previous value" echo.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(client, user_headers, wallet_id=wallet.id, category_id=category.id)

    response = client.patch(_url(str(txn["id"])), json={"note": "Final note"}, headers=user_headers)

    assert response.status_code == 200
    assert set(response.json().keys()) == {
        "id",
        "wallet_id",
        "category_id",
        "amount",
        "type",
        "timestamp",
        "note",
    }


# --- TC-112: unconditional INCOME reversal under a negative intermediate --


def test_reversing_a_stored_income_always_succeeds_even_through_a_negative_intermediate(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-112: wallet 50.00, INCOME 500.00 logged (balance 550.00); other,
    later EXPENSE activity has since brought the balance down to 30.00 ->
    PATCH only a new note for that INCOME transaction (amount/type
    unchanged) -> 200; the reversal (unconditionally subtracting 500.00,
    intermediate balance -470.00) and the reapplication (unconditionally
    adding 500.00 back) both succeed; the wallet's final balance is exactly
    30.00, unaffected — proving decrement_balance_unconditional() never
    refuses a reversal regardless of intermediate negativity (BR-04).
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("50.00"))
    income_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.INCOME, name="Salary"
    )
    expense_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE
    )

    income_txn = _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=income_category.id,
        amount="500.00",
        type="INCOME",
    )
    assert _stored_wallet(db, wallet.id).balance == Decimal("550.00")

    _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=expense_category.id,
        amount="520.00",
    )
    assert _stored_wallet(db, wallet.id).balance == Decimal("30.00")

    response = client.patch(
        _url(str(income_txn["id"])), json={"note": "Year-end bonus"}, headers=user_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["note"] == "Year-end bonus"
    assert Decimal(str(body["amount"])) == Decimal("500.00")
    assert body["type"] == "INCOME"
    assert _stored_wallet(db, wallet.id).balance == Decimal("30.00")
