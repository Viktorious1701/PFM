"""TM-US-03 — View a Transaction.

One test per test case in specs/006-transaction-management/test_cases.md
(TC-73..TC-82). Names state what the test proves, not what it calls.

Wallet/category/transaction seeding reuses TM-US-02's own helpers by import
(`_make_wallet`, `_make_category`, `_create_transaction`, `TRANSACTIONS_URL`,
`MALFORMED_ID`) — the same precedent BM-US-04 set by importing its
prerequisites from BM-US-02's own test file. Transactions are always seeded
through the real `POST /api/v1/transactions` endpoint (TM-US-01, already
implemented), never inserted directly, so a viewed transaction's `id` is
whatever the server actually assigned.

TC-76/TC-78/TC-80 each assert full-response-body equality between a freshly
computed not-found-at-all response and the case under test, both computed
inside the same test function — the same QF-14-style "identical, not merely
both 404" technique TM-US-01 TC-08/TC-11, TM-US-02 TC-58/TC-61, and BM-US-04
TC-68/TC-69 each already established for their own ownership-collapse cases.

Decimal amounts are always sent as JSON strings, never Python floats,
mirroring every prior story's tests.
"""

from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.category import CategoryType
from app.models.user import UserModel
from tests.integration.test_tm_us_02_list_transactions import (
    MALFORMED_ID,
    TRANSACTIONS_URL,
    _create_transaction,
    _make_category,
    _make_wallet,
)


def _url(transaction_id: str) -> str:
    return f"{TRANSACTIONS_URL}/{transaction_id}"


# --- TC-73/TC-74: the happy path ---------------------------------------------


def test_authenticated_user_views_a_transaction_they_own_with_note_included(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-73: a transaction created with amount 50.00, type EXPENSE, and a
    note -> GET by id -> 200; id, wallet_id, category_id, amount, type, the
    exact timestamp recorded at creation, and the note all round-trip
    unchanged.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    created = _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=category.id,
        amount="50.00",
        note="Weekly grocery run",
    )

    response = client.get(_url(str(created["id"])), headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["wallet_id"] == wallet.id
    assert body["category_id"] == category.id
    assert Decimal(str(body["amount"])) == Decimal("50.00")
    assert body["type"] == "EXPENSE"
    assert body["timestamp"] == created["timestamp"]
    assert body["note"] == "Weekly grocery run"


def test_viewing_a_transaction_created_with_no_note_returns_note_as_exactly_null(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-74: a transaction created with the note field entirely absent ->
    GET by id -> 200; the note key is present and exactly null — not an
    empty string and not the key omitted, the same distinction TM-US-01
    TC-23 already proved at creation, now proved again through the read
    path.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    created = _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id
    )

    response = client.get(_url(str(created["id"])), headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert "note" in body
    assert body["note"] is None


# --- TC-75/TC-76: not found and not owned, collapsed (QF-14) -----------------


def test_a_transaction_id_matching_no_transaction_is_rejected_with_404(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-75: an id matching no transaction in the system -> 404
    TRANSACTION_NOT_FOUND.
    """
    response = client.get(_url(str(uuid4())), headers=user_headers)

    assert response.status_code == 404
    assert response.json()["error_code"] == "TRANSACTION_NOT_FOUND"


def test_another_users_transaction_is_refused_with_a_body_identical_to_not_found(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-76: B owns a transaction, A owns nothing of the kind -> A's
    request for B's transaction is 404, and error_code, message and details
    are all identical to a well-formed-but-nonexistent id's body (QF-14).
    """
    b_wallet = _make_wallet(db, user_id=admin_user.id)
    b_category = _make_category(db, user_id=admin_user.id, category_type=CategoryType.EXPENSE)
    b_txn = _create_transaction(
        client, admin_headers, wallet_id=b_wallet.id, category_id=b_category.id
    )

    not_owned = client.get(_url(str(b_txn["id"])), headers=user_headers)
    not_found = client.get(_url(str(uuid4())), headers=user_headers)

    assert not_owned.status_code == 404
    assert not_owned.json()["error_code"] == "TRANSACTION_NOT_FOUND"
    assert not_owned.json() == not_found.json()


# --- TC-77: authentication ---------------------------------------------------


def test_an_unauthenticated_caller_is_denied_with_401(
    client: TestClient, admin_headers: dict[str, str], admin_user: UserModel, db: Session
) -> None:
    """TC-77: no Authorization header, against an existing transaction
    belonging to some other, real User -> 401 NOT_AUTHENTICATED.
    """
    wallet = _make_wallet(db, user_id=admin_user.id)
    category = _make_category(db, user_id=admin_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(client, admin_headers, wallet_id=wallet.id, category_id=category.id)

    response = client.get(_url(str(txn["id"])))

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"


# --- TC-78: malformed reference -----------------------------------------------


def test_a_malformed_transaction_id_gets_the_same_404_as_a_well_formed_unknown_one(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-78: GET /transactions/not-a-real-id -> 404 TRANSACTION_NOT_FOUND,
    identical to a well-formed-but-nonexistent id's body. No separate
    malformed-identifier error exists (spec EC-01).
    """
    malformed = client.get(_url(MALFORMED_ID), headers=user_headers)
    unknown = client.get(_url(str(uuid4())), headers=user_headers)

    assert malformed.status_code == 404
    assert malformed.json()["error_code"] == "TRANSACTION_NOT_FOUND"
    assert malformed.json() == unknown.json()


# --- TC-79: response shape ----------------------------------------------------


def test_response_exposes_exactly_the_seven_documented_fields(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-79: the response body's keys are exactly id, wallet_id,
    category_id, amount, type, timestamp, note — no more, and in particular
    no user_id, no embedded wallet or category name (QF-15).
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    created = _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id
    )

    response = client.get(_url(str(created["id"])), headers=user_headers)

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


# --- TC-80: owning one transaction grants no access to another's ------------


def test_a_caller_who_owns_a_transaction_of_their_own_cannot_view_a_different_users(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    admin_headers: dict[str, str],
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-80: A owns a transaction of their own; B owns a separate one. A's
    request for B's transaction is 404, identical to a not-found-at-all
    body — owning a transaction of their own gives A no access to B's.
    """
    a_wallet = _make_wallet(db, user_id=normal_user.id, name="A-Wallet")
    a_category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    _create_transaction(client, user_headers, wallet_id=a_wallet.id, category_id=a_category.id)

    b_wallet = _make_wallet(db, user_id=admin_user.id, name="B-Wallet")
    b_category = _make_category(db, user_id=admin_user.id, category_type=CategoryType.EXPENSE)
    b_txn = _create_transaction(
        client, admin_headers, wallet_id=b_wallet.id, category_id=b_category.id
    )

    response = client.get(_url(str(b_txn["id"])), headers=user_headers)
    not_found = client.get(_url(str(uuid4())), headers=user_headers)

    assert response.status_code == 404
    assert response.json()["error_code"] == "TRANSACTION_NOT_FOUND"
    assert response.json() == not_found.json()


# --- TC-81: no role-based visibility override --------------------------------


def test_an_admin_role_caller_cannot_view_another_users_transaction(
    client: TestClient,
    admin_headers: dict[str, str],
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
) -> None:
    """TC-81: an ADMIN-role caller requesting a transaction they do not own
    -> 404 TRANSACTION_NOT_FOUND, the same outcome any non-ADMIN caller
    would get; no role grants visibility through this endpoint.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    txn = _create_transaction(client, user_headers, wallet_id=wallet.id, category_id=category.id)

    response = client.get(_url(str(txn["id"])), headers=admin_headers)

    assert response.status_code == 404
    assert response.json()["error_code"] == "TRANSACTION_NOT_FOUND"


# --- TC-82: credentials checked before the reference is looked up ------------


def test_credentials_are_evaluated_before_the_transaction_reference_is_looked_up(
    client: TestClient,
) -> None:
    """TC-82: no credentials, against an id that matches no transaction
    either -> 401 NOT_AUTHENTICATED, not 404 — mirrors TM-US-02
    TC-41/UM-US-03 TC-61's own ordering.
    """
    response = client.get(_url(str(uuid4())))

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"
