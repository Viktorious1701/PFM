"""TM-US-01 — Create a Transaction.

One test per test case in specs/006-transaction-management/test_cases.md
(TC-01..TC-36). Names state what the test proves, not what it calls.

`_transaction_count` mirrors the existing `select(func.count()).select_from(...)`
idiom already used by `test_bm_us_01_create_budget.py` for "nothing was
persisted" assertions.

Every transaction-creation request needs a real wallet and a real category
already owned by the caller (spec Assumptions & Dependencies). `_make_wallet`
and `_make_category` construct those directly against the `db` session — the
same "arrange via direct model construction" style `test_bm_us_01_create_budget.py`
itself uses — rather than routing prerequisite setup through
`POST /api/v1/wallets`/`POST /api/v1/categories`, which would make every
transaction test also an implicit wallet/category-creation test.

Decimal values in request bodies are sent as JSON strings, never Python
floats, matching every prior story's tests, so a test itself never introduces
the binary floating-point rounding AC-11/TC-17 exists to rule out on the
server side.

A wallet's balance is re-read via `db.refresh(wallet)` on the same ORM
instance the test already holds — the app's own request uses a *different*
session (see `conftest.py`'s `app` fixture override), so without an explicit
refresh the test session's identity map would keep returning the
pre-request, stale value.

Timestamps are asserted with `datetime.fromisoformat()` plus an explicit
`tzinfo is not None` check, exactly the idiom `test_um_us_01_invite.py`'s
`test_the_invitation_expires_exactly_24_hours_after_creation` already
established — CLAUDE.md records a serialization defect (a naive-looking
timestamp) as a prior story's real, live-walkthrough-caught bug, so this is
asserted directly rather than assumed.
"""

from datetime import datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import CategoryModel, CategoryType
from app.models.transaction import TransactionModel, TransactionType
from app.models.user import UserModel
from app.models.wallet import WalletModel

TRANSACTIONS_URL = "/api/v1/transactions"

NONEXISTENT_WALLET_ID = "00000000-0000-0000-0000-000000000000"
NONEXISTENT_CATEGORY_ID = "00000000-0000-0000-0000-000000000001"
MALFORMED_ID = "not-a-real-id"


# --- helpers ----------------------------------------------------------------


def _transaction_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(TransactionModel)) or 0


def _make_wallet(
    db: Session, *, user_id: str, name: str = "Main Checking", balance: Decimal = Decimal("1000.00")
) -> WalletModel:
    wallet = WalletModel(user_id=user_id, name=name, type="BANK", currency="USD", balance=balance)
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return wallet


def _make_category(
    db: Session, *, user_id: str, category_type: CategoryType, name: str = "Groceries"
) -> CategoryModel:
    category = CategoryModel(user_id=user_id, name=name, type=category_type)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def _valid_payload(
    *,
    wallet_id: str,
    category_id: str,
    amount: str = "50.00",
    txn_type: str = "EXPENSE",
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "wallet_id": wallet_id,
        "category_id": category_id,
        "amount": amount,
        "type": txn_type,
    }
    payload.update(overrides)
    return payload


def _fields(body: dict[str, object]) -> list[str]:
    details = body["details"]
    assert isinstance(details, dict)
    return [f["location"][-1] for f in details["fields"]]  # type: ignore[index]


def _wallet_not_found_body(
    client: TestClient, headers: dict[str, str], category_id: str
) -> dict[str, object]:
    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(wallet_id=NONEXISTENT_WALLET_ID, category_id=category_id),
        headers=headers,
    )
    assert response.status_code == 404
    body: dict[str, object] = response.json()
    assert body["error_code"] == "TRANSACTION_WALLET_NOT_FOUND"
    return body


def _category_not_found_body(
    client: TestClient, headers: dict[str, str], wallet_id: str
) -> dict[str, object]:
    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(wallet_id=wallet_id, category_id=NONEXISTENT_CATEGORY_ID),
        headers=headers,
    )
    assert response.status_code == 404
    body: dict[str, object] = response.json()
    assert body["error_code"] == "TRANSACTION_CATEGORY_NOT_FOUND"
    return body


# --- TC-01/TC-02: EXPENSE happy path -----------------------------------------


def test_authenticated_user_creates_expense_transaction_201_with_created_transaction_and_note(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-01: 201; body carries id, wallet_id, category_id, amount 50.00,
    type EXPENSE, a timestamp, and note equal to exactly the submitted
    string — proving a submitted note round-trips unchanged (distinct from
    TC-23's omitted-note case).
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("1000.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(
            wallet_id=wallet.id,
            category_id=category.id,
            amount="50.00",
            txn_type="EXPENSE",
            note="Weekly grocery run",
        ),
        headers=user_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body.get("id")
    assert body["wallet_id"] == wallet.id
    assert body["category_id"] == category.id
    assert Decimal(str(body["amount"])) == Decimal("50.00")
    assert body["type"] == "EXPENSE"
    assert body.get("timestamp")
    assert body["note"] == "Weekly grocery run"


def test_creating_expense_transaction_persists_one_row_and_decreases_balance_by_exact_amount(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-02: exactly one `transactions` row carries the submitted fields;
    the wallet's `balance` row (inspected directly — no GET endpoint exists
    yet) now reads `950.00`.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("1000.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id, amount="50.00"),
        headers=user_headers,
    )

    assert response.status_code == 201
    assert _transaction_count(db) == 1
    row = db.scalars(select(TransactionModel)).one()
    assert row.wallet_id == wallet.id
    assert row.category_id == category.id
    assert row.amount == Decimal("50.00")
    assert row.type == TransactionType.EXPENSE
    db.refresh(wallet)
    assert wallet.balance == Decimal("950.00")


# --- TC-03/TC-04: INCOME happy path ------------------------------------------


def test_authenticated_user_creates_income_transaction_201_with_created_transaction(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-03: 201; body carries id, wallet_id, category_id, amount 500.00,
    type INCOME, a timestamp, and note.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.INCOME)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(
            wallet_id=wallet.id, category_id=category.id, amount="500.00", txn_type="INCOME"
        ),
        headers=user_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body.get("id")
    assert body["wallet_id"] == wallet.id
    assert body["category_id"] == category.id
    assert Decimal(str(body["amount"])) == Decimal("500.00")
    assert body["type"] == "INCOME"
    assert body.get("timestamp")
    assert "note" in body


def test_creating_income_transaction_persists_one_row_and_increases_balance_by_exact_amount(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-04: exactly one `transactions` row carries the submitted fields;
    the wallet's `balance` row now reads `600.00`.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("100.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.INCOME)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(
            wallet_id=wallet.id, category_id=category.id, amount="500.00", txn_type="INCOME"
        ),
        headers=user_headers,
    )

    assert response.status_code == 201
    assert _transaction_count(db) == 1
    row = db.scalars(select(TransactionModel)).one()
    assert row.wallet_id == wallet.id
    assert row.category_id == category.id
    assert row.amount == Decimal("500.00")
    assert row.type == TransactionType.INCOME
    db.refresh(wallet)
    assert wallet.balance == Decimal("600.00")


# --- TC-05: authentication ----------------------------------------------------


def test_unauthenticated_caller_is_denied_with_401(client: TestClient, db: Session) -> None:
    """TC-05: no `Authorization` header -> 401 NOT_AUTHENTICATED; nothing
    persisted.
    """
    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(wallet_id="irrelevant-wallet", category_id="irrelevant-category"),
    )

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"
    assert _transaction_count(db) == 0


# --- TC-06/TC-07/TC-08: wallet presence and ownership -------------------------


def test_a_missing_wallet_reference_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-06: `wallet_id` absent -> 422 VALIDATION_ERROR naming `wallet_id`;
    nothing persisted.
    """
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    payload = _valid_payload(wallet_id="placeholder", category_id=category.id)
    del payload["wallet_id"]

    response = client.post(TRANSACTIONS_URL, json=payload, headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "wallet_id" in _fields(body)
    assert _transaction_count(db) == 0


def test_a_wallet_reference_matching_no_wallet_at_all_is_rejected_with_404(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-07: `wallet_id` matches no wallet in the system -> 404
    TRANSACTION_WALLET_NOT_FOUND; nothing persisted.
    """
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    _wallet_not_found_body(client, user_headers, category.id)

    assert _transaction_count(db) == 0


def test_a_wallet_reference_belonging_to_a_different_user_is_rejected_identically_to_not_found(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-08 / EC-05: User A submits User B's `wallet_id` with A's own
    `category_id` -> 404; `error_code`, `message`, `details` identical to
    TC-07's response; nothing persisted (assertion technique per QF-01).
    """
    category_a = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    wallet_b = _make_wallet(db, user_id=admin_user.id)

    not_found_body = _wallet_not_found_body(client, user_headers, category_a.id)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(wallet_id=wallet_b.id, category_id=category_a.id),
        headers=user_headers,
    )

    assert response.status_code == 404
    assert response.json() == not_found_body
    assert _transaction_count(db) == 0


# --- TC-09/TC-10/TC-11: category presence and ownership -----------------------


def test_a_missing_category_reference_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-09: `category_id` absent -> 422 VALIDATION_ERROR naming
    `category_id`; nothing persisted.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    payload = _valid_payload(wallet_id=wallet.id, category_id="placeholder")
    del payload["category_id"]

    response = client.post(TRANSACTIONS_URL, json=payload, headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "category_id" in _fields(body)
    assert _transaction_count(db) == 0


def test_a_category_reference_matching_no_category_at_all_is_rejected_with_404(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-10: `category_id` matches no category in the system -> 404
    TRANSACTION_CATEGORY_NOT_FOUND; nothing persisted.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)

    _category_not_found_body(client, user_headers, wallet.id)

    assert _transaction_count(db) == 0


def test_a_category_reference_belonging_to_a_different_user_is_rejected_identically_to_not_found(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-11 / EC-06: User A submits A's own `wallet_id` with User B's
    `category_id` -> 404; `error_code`, `message`, `details` identical to
    TC-10's response; nothing persisted (assertion technique per QF-01).
    """
    wallet_a = _make_wallet(db, user_id=normal_user.id)
    category_b = _make_category(db, user_id=admin_user.id, category_type=CategoryType.EXPENSE)

    not_found_body = _category_not_found_body(client, user_headers, wallet_a.id)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(wallet_id=wallet_a.id, category_id=category_b.id),
        headers=user_headers,
    )

    assert response.status_code == 404
    assert response.json() == not_found_body
    assert _transaction_count(db) == 0


# --- TC-12/TC-13: category-type consistency -----------------------------------


def test_expense_transaction_against_income_typed_category_is_rejected_with_409(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-12: `EXPENSE` against an `INCOME`-typed category -> 409
    TRANSACTION_CATEGORY_TYPE_MISMATCH; the wallet's balance is unchanged
    and nothing is persisted.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("1000.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.INCOME)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(
            wallet_id=wallet.id, category_id=category.id, amount="50.00", txn_type="EXPENSE"
        ),
        headers=user_headers,
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "TRANSACTION_CATEGORY_TYPE_MISMATCH"
    db.refresh(wallet)
    assert wallet.balance == Decimal("1000.00")
    assert _transaction_count(db) == 0


def test_income_transaction_against_expense_typed_category_is_rejected_with_409(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-13: `INCOME` against an `EXPENSE`-typed category -> 409
    TRANSACTION_CATEGORY_TYPE_MISMATCH; the wallet's balance is unchanged
    and nothing is persisted.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("1000.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(
            wallet_id=wallet.id, category_id=category.id, amount="50.00", txn_type="INCOME"
        ),
        headers=user_headers,
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "TRANSACTION_CATEGORY_TYPE_MISMATCH"
    db.refresh(wallet)
    assert wallet.balance == Decimal("1000.00")
    assert _transaction_count(db) == 0


# --- TC-14/TC-15/TC-16: amount presence and sign ------------------------------


def test_a_missing_amount_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-14: `amount` absent -> 422 VALIDATION_ERROR naming `amount`;
    nothing persisted.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    payload = _valid_payload(wallet_id=wallet.id, category_id=category.id)
    del payload["amount"]

    response = client.post(TRANSACTIONS_URL, json=payload, headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "amount" in _fields(body)
    assert _transaction_count(db) == 0


def test_an_amount_of_exactly_zero_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-15: `amount` `"0.00"` -> 422 VALIDATION_ERROR naming `amount`;
    nothing persisted.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id, amount="0.00"),
        headers=user_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "amount" in _fields(body)
    assert _transaction_count(db) == 0


def test_a_negative_amount_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-16: `amount` `"-50.00"` -> 422 VALIDATION_ERROR naming `amount`;
    nothing persisted.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id, amount="-50.00"),
        headers=user_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "amount" in _fields(body)
    assert _transaction_count(db) == 0


# --- TC-17: over-precise amount is rejected, not rounded ---------------------


def test_an_amount_with_three_decimal_places_is_rejected_not_rounded(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-17: `amount` `"100.005"` -> 422 whose `details` names `amount`;
    no `transactions` row is created and the wallet's balance is unchanged
    (assertion technique per QF-02).
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("1000.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id, amount="100.005"),
        headers=user_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "amount" in _fields(body)
    assert _transaction_count(db) == 0
    db.refresh(wallet)
    assert wallet.balance == Decimal("1000.00")


# --- TC-18/TC-19: type presence and closed vocabulary -------------------------


def test_a_missing_transaction_type_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-18: `type` absent -> 422 VALIDATION_ERROR naming `type`; nothing
    persisted.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    payload = _valid_payload(wallet_id=wallet.id, category_id=category.id)
    del payload["type"]

    response = client.post(TRANSACTIONS_URL, json=payload, headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "type" in _fields(body)
    assert _transaction_count(db) == 0


def test_a_transaction_type_other_than_income_or_expense_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-19: `type` `"TRANSFER"` -> 422 VALIDATION_ERROR naming `type`;
    nothing persisted.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id, txn_type="TRANSFER"),
        headers=user_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "type" in _fields(body)
    assert _transaction_count(db) == 0


# --- TC-20: insufficient balance ----------------------------------------------


def test_expense_amount_exceeding_wallet_balance_is_rejected_with_409_and_nothing_persists(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-20: `EXPENSE` `1500.00` against a `1000.00` balance -> 409
    TRANSACTION_INSUFFICIENT_BALANCE; the wallet's `balance` row is still
    exactly `1000.00`, and no `transactions` row exists for this attempt
    (also the load-bearing atomicity witness, QF-07).
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("1000.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id, amount="1500.00"),
        headers=user_headers,
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "TRANSACTION_INSUFFICIENT_BALANCE"
    db.refresh(wallet)
    assert wallet.balance == Decimal("1000.00")
    assert _transaction_count(db) == 0


# --- TC-21: timestamp is the moment of creation, from the clock seam --------


def test_created_transactions_timestamp_is_moment_of_creation_from_frozen_clock(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-21: with the clock frozen, the created transaction's `timestamp`
    equals the frozen instant exactly (assertion technique per QF-03).
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("1000.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id, amount="50.00"),
        headers=user_headers,
    )

    assert response.status_code == 201
    parsed = datetime.fromisoformat(response.json()["timestamp"])
    assert parsed.tzinfo is not None, "timestamp was serialised without a timezone"
    assert parsed == frozen_now


# --- TC-22/TC-23: note bounds and optionality --------------------------------


def test_a_note_longer_than_500_characters_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-22: a `note` of 501 characters -> 422 VALIDATION_ERROR naming
    `note`; nothing persisted.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id, note="x" * 501),
        headers=user_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "note" in _fields(body)
    assert _transaction_count(db) == 0


def test_transaction_created_with_no_note_succeeds_and_returned_note_is_null(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-23 / EC-13: the `note` field is entirely absent from the request
    body -> 201; the body's `note` key is present and its value is exactly
    `null` — not an empty string and not the key omitted (assertion
    technique per QF-08).
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    payload = _valid_payload(wallet_id=wallet.id, category_id=category.id)
    assert "note" not in payload

    response = client.post(TRANSACTIONS_URL, json=payload, headers=user_headers)

    assert response.status_code == 201
    body = response.json()
    assert "note" in body
    assert body["note"] is None


# --- TC-24: exact response shape ---------------------------------------------


def test_response_exposes_exactly_the_seven_documented_fields(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-24: response body's keys are exactly id, wallet_id, category_id,
    amount, type, timestamp, note — no more, and in particular no
    `user_id` (plan.md A11, QF-05).
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id),
        headers=user_headers,
    )

    assert response.status_code == 201
    expected_keys = {"id", "wallet_id", "category_id", "amount", "type", "timestamp", "note"}
    body_keys = set(response.json().keys())
    assert body_keys == expected_keys
    assert "user_id" not in body_keys


# --- TC-25/TC-26: amount digit-width boundaries ------------------------------


def test_an_amount_of_exactly_0_01_is_accepted(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-25 / EC-01: `amount` `"0.01"` -> 201; created transaction's
    `amount` is `0.01`.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id, amount="0.01"),
        headers=user_headers,
    )

    assert response.status_code == 201
    assert Decimal(str(response.json()["amount"])) == Decimal("0.01")


def test_an_amount_exceeding_15_total_digits_is_rejected(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-26 / EC-02: an `amount` of 14 integer digits and 2 decimal places
    (16 significant digits total) -> 422; nothing persisted — constitution
    VL-07's `DECIMAL(15,2)` bound is enforced by the DTO before the service
    runs.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(
            wallet_id=wallet.id, category_id=category.id, amount="12345678901234.12"
        ),
        headers=user_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "amount" in _fields(body)
    assert _transaction_count(db) == 0


# --- TC-27: grouped validation failures --------------------------------------


def test_multiple_validation_failures_in_one_submission_are_reported_together(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-27 / EC-03: `wallet_id` absent and `amount` `"-50.00"` in the same
    request -> a single 422 whose `details` identifies both fields, not just
    the first one encountered.
    """
    response = client.post(
        TRANSACTIONS_URL,
        json={"category_id": "placeholder-category", "amount": "-50.00", "type": "EXPENSE"},
        headers=user_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    fields = _fields(body)
    assert "wallet_id" in fields
    assert "amount" in fields


# --- TC-28: a submitted timestamp is silently ignored ------------------------


def test_a_timestamp_submitted_in_the_request_body_is_silently_ignored(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-28 / EC-04: an otherwise valid payload additionally includes a
    timestamp-shaped key -> 201; the created transaction's `timestamp`
    equals the frozen instant, never the submitted value.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(
            wallet_id=wallet.id,
            category_id=category.id,
            timestamp="2020-01-01T00:00:00Z",
        ),
        headers=user_headers,
    )

    assert response.status_code == 201
    parsed = datetime.fromisoformat(response.json()["timestamp"])
    assert parsed == frozen_now
    assert response.json()["timestamp"] != "2020-01-01T00:00:00Z"


# --- TC-29/TC-30: malformed references are refused identically ---------------


def test_a_malformed_wallet_reference_is_rejected_with_same_outcome_as_not_found(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-29 / EC-07: `wallet_id` `"not-a-real-id"` -> 404
    TRANSACTION_WALLET_NOT_FOUND, identical to TC-07's response; nothing
    persisted.
    """
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    not_found_body = _wallet_not_found_body(client, user_headers, category.id)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(wallet_id=MALFORMED_ID, category_id=category.id),
        headers=user_headers,
    )

    assert response.status_code == 404
    assert response.json() == not_found_body
    assert _transaction_count(db) == 0


def test_a_malformed_category_reference_is_rejected_with_same_outcome_as_not_found(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-30 / EC-07: `category_id` `"not-a-real-id"` -> 404
    TRANSACTION_CATEGORY_NOT_FOUND, identical to TC-10's response; nothing
    persisted.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    not_found_body = _category_not_found_body(client, user_headers, wallet.id)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=MALFORMED_ID),
        headers=user_headers,
    )

    assert response.status_code == 404
    assert response.json() == not_found_body
    assert _transaction_count(db) == 0


# --- TC-31/TC-32/TC-33: balance boundaries ------------------------------------


def test_expense_amount_exactly_equal_to_balance_is_accepted_leaving_balance_at_zero(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-31 / EC-08: an `EXPENSE` amount exactly equal to the wallet's
    current balance -> 201; the wallet's `balance` row now reads exactly
    `0.00`.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("1000.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id, amount="1000.00"),
        headers=user_headers,
    )

    assert response.status_code == 201
    db.refresh(wallet)
    assert wallet.balance == Decimal("0.00")


def test_income_transaction_accepted_even_when_wallet_balance_is_negative(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-32 / EC-09: an `INCOME` transaction is accepted unconditionally
    even when the wallet's current balance is negative (reachable per
    WM-US-01 EC-02).
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("-50.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.INCOME)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(
            wallet_id=wallet.id, category_id=category.id, amount="20.00", txn_type="INCOME"
        ),
        headers=user_headers,
    )

    assert response.status_code == 201
    db.refresh(wallet)
    assert wallet.balance == Decimal("-30.00")


def test_expense_against_wallet_already_at_zero_balance_is_rejected_regardless_of_amount(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-33 / EC-10: an `EXPENSE` of `0.01` (the smallest possible positive
    amount) against a wallet already at `0.00` -> 409
    TRANSACTION_INSUFFICIENT_BALANCE; the wallet's balance is still `0.00`.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("0.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id, amount="0.01"),
        headers=user_headers,
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "TRANSACTION_INSUFFICIENT_BALANCE"
    db.refresh(wallet)
    assert wallet.balance == Decimal("0.00")


# --- TC-34: fixed check order — type before balance --------------------------


def test_category_type_mismatch_takes_priority_over_independently_failing_balance_check(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-34 / EC-11: a request that would independently fail both the
    type-consistency check and the balance-sufficiency check -> 409
    TRANSACTION_CATEGORY_TYPE_MISMATCH — never
    TRANSACTION_INSUFFICIENT_BALANCE, and never both; the wallet's balance
    is unchanged (assertion technique per QF-06).
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("10.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.INCOME)

    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(
            wallet_id=wallet.id, category_id=category.id, amount="500.00", txn_type="EXPENSE"
        ),
        headers=user_headers,
    )

    assert response.status_code == 409
    body = response.json()
    assert body["error_code"] == "TRANSACTION_CATEGORY_TYPE_MISMATCH"
    assert body["error_code"] != "TRANSACTION_INSUFFICIENT_BALANCE"
    db.refresh(wallet)
    assert wallet.balance == Decimal("10.00")


# --- TC-35: no uniqueness constraint ------------------------------------------


def test_two_identical_transactions_are_both_accepted_as_independent_ledger_entries(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-35 / EC-12: the same `EXPENSE` transaction submitted twice,
    back-to-back -> both `201`, each with its own distinct `id`; two
    separate `transactions` rows exist, and the wallet's balance reflects
    both decrements.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("1000.00"))
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    payload = _valid_payload(wallet_id=wallet.id, category_id=category.id, amount="25.00")

    first = client.post(TRANSACTIONS_URL, json=payload, headers=user_headers)
    second = client.post(TRANSACTIONS_URL, json=payload, headers=user_headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    assert _transaction_count(db) == 2
    db.refresh(wallet)
    assert wallet.balance == Decimal("950.00")


# --- TC-36: fixed check order — wallet before category ------------------------


def test_wallet_ownership_is_checked_before_category_ownership_when_both_invalid(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-36 / EC-14: `wallet_id` matching no wallet and `category_id`
    matching no category, in the same request -> 404
    TRANSACTION_WALLET_NOT_FOUND — never TRANSACTION_CATEGORY_NOT_FOUND, and
    never both (assertion technique per QF-06).
    """
    response = client.post(
        TRANSACTIONS_URL,
        json=_valid_payload(wallet_id=NONEXISTENT_WALLET_ID, category_id=NONEXISTENT_CATEGORY_ID),
        headers=user_headers,
    )

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "TRANSACTION_WALLET_NOT_FOUND"
    assert body["error_code"] != "TRANSACTION_CATEGORY_NOT_FOUND"
    assert _transaction_count(db) == 0
