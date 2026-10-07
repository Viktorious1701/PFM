"""WM-US-03 — View a Wallet.

One test per test case in specs/003-wallet-management/test_cases.md
(TC-60..TC-70). Names state what the test proves, not what it calls.

`WALLETS_URL`/`_create_wallet`/`_expired_token` are reused by import from
test_wm_us_02_list_wallets.py, the same precedent test_wm_us_04_update_wallet.py
already set for its own WM-US-02 imports — wallets are seeded through the real
POST /api/v1/wallets endpoint (WM-US-01, already implemented), never inserted
directly, so every TC in this file describes a wallet "created via POST
/api/v1/wallets" and its id is whatever the server actually assigned.

A transaction's effect on a wallet's `balance` (TC-61, TC-68) is proven
through the real `POST /api/v1/transactions` endpoint (TM-US-01, already
implemented), not by writing to `WalletModel.balance` directly — otherwise
the test would only prove this endpoint echoes back whatever a test wrote,
not that it reads the wallet's genuinely current, Transaction-adjusted
balance. The category each transaction references is a prerequisite, not the
entity under test, so it is constructed directly against the `db` session —
the same style `test_tm_us_01_create_transaction.py`/
`test_tm_us_02_list_transactions.py` already use for their own prerequisites.
"""

from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.category import CategoryModel, CategoryType
from app.models.user import UserModel
from tests.integration.test_wm_us_02_list_wallets import (
    WALLETS_URL,
    _create_wallet,
    _expired_token,
)

TRANSACTIONS_URL = "/api/v1/transactions"


# --- helpers ----------------------------------------------------------------


def _url(wallet_id: str) -> str:
    return f"{WALLETS_URL}/{wallet_id}"


def _make_category(
    db: Session, *, user_id: str, category_type: CategoryType = CategoryType.EXPENSE
) -> CategoryModel:
    category = CategoryModel(user_id=user_id, name="Groceries", type=category_type)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def _record_expense(
    client: TestClient,
    headers: dict[str, str],
    db: Session,
    *,
    user_id: str,
    wallet_id: str,
    amount: str = "100.00",
) -> dict[str, object]:
    """Record a real EXPENSE transaction against `wallet_id`, through the
    real TM-US-01 endpoint, so the wallet's stored `balance` genuinely
    reflects it (TC-61, TC-68).
    """
    category = _make_category(db, user_id=user_id)
    response = client.post(
        TRANSACTIONS_URL,
        json={
            "wallet_id": wallet_id,
            "category_id": category.id,
            "amount": amount,
            "type": "EXPENSE",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


# --- TC-60: the happy path, full detail --------------------------------------


def test_an_authenticated_user_views_a_wallet_they_own(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel
) -> None:
    """TC-60: name "Main Checking"/type "BANK"/currency "USD"/balance 750.25
    -> 200; body carries id, user_id (caller's own), name, type, currency,
    balance exactly as created.
    """
    wallet = _create_wallet(
        client,
        user_headers,
        name="Main Checking",
        type="BANK",
        currency="USD",
        initial_balance="750.25",
    )

    response = client.get(_url(str(wallet["id"])), headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == wallet["id"]
    assert body["user_id"] == normal_user.id
    assert body["name"] == "Main Checking"
    assert body["type"] == "BANK"
    assert body["currency"] == "USD"
    assert Decimal(str(body["balance"])) == Decimal("750.25")


# --- TC-61: balance reflects Transaction activity, not initial_balance -------


def test_viewing_a_wallet_reflects_its_current_transaction_adjusted_balance(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-61: initial_balance 500.00, one EXPENSE transaction of 100.00
    recorded against it (TM-US-01) -> 200; balance is 400.00 — the current,
    adjusted value, not the original initial_balance — and the response
    carries exactly the six documented fields.
    """
    wallet = _create_wallet(client, user_headers, initial_balance="500.00")
    _record_expense(
        client,
        user_headers,
        db,
        user_id=normal_user.id,
        wallet_id=str(wallet["id"]),
        amount="100.00",
    )

    response = client.get(_url(str(wallet["id"])), headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert Decimal(str(body["balance"])) == Decimal("400.00")
    assert set(body.keys()) == {"id", "user_id", "name", "type", "currency", "balance"}


# --- TC-62: no such wallet at all --------------------------------------------


def test_a_wallet_id_matching_no_wallet_at_all_is_rejected_with_404(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-62: a well-formed id matching no wallet -> 404 WALLET_NOT_FOUND."""
    response = client.get(_url(str(uuid4())), headers=user_headers)

    assert response.status_code == 404
    assert response.json()["error_code"] == "WALLET_NOT_FOUND"


# --- TC-63: another User's wallet collapses to the identical outcome (QF-12) -


def test_another_users_wallet_is_refused_with_a_body_identical_to_not_found(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    """TC-63: B owns a wallet, A owns nothing of the kind; A requests B's
    wallet -> 404, and error_code/message/details are all identical to a
    genuinely nonexistent id's response (QF-12).
    """
    b_wallet = _create_wallet(client, admin_headers, name="B's Wallet")

    not_owned = client.get(_url(str(b_wallet["id"])), headers=user_headers)
    not_found = client.get(_url(str(uuid4())), headers=user_headers)

    assert not_owned.status_code == 404
    assert not_owned.json()["error_code"] == "WALLET_NOT_FOUND"
    assert not_owned.json() == not_found.json()


# --- TC-64: authentication ----------------------------------------------------


def test_an_unauthenticated_or_expired_caller_is_denied_with_401(
    client: TestClient,
    admin_headers: dict[str, str],
    normal_user: UserModel,
    settings: Settings,
) -> None:
    """TC-64: no Authorization header, and separately an expired token, each
    against an existing wallet belonging to some other, real User -> 401
    NOT_AUTHENTICATED both times.
    """
    other_wallet = _create_wallet(client, admin_headers, name="Someone Else's Wallet")

    no_auth = client.get(_url(str(other_wallet["id"])))
    expired = client.get(
        _url(str(other_wallet["id"])),
        headers={"Authorization": f"Bearer {_expired_token(normal_user, settings)}"},
    )

    assert no_auth.status_code == 401
    assert no_auth.json()["error_code"] == "NOT_AUTHENTICATED"
    assert expired.status_code == 401
    assert expired.json()["error_code"] == "NOT_AUTHENTICATED"


# --- TC-65: malformed reference gets the same outcome as unknown-but-well-formed


def test_a_malformed_wallet_id_gets_the_same_404_as_a_well_formed_unknown_one(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-65: GET /wallets/not-a-real-id -> 404 WALLET_NOT_FOUND, identical
    to a well-formed but nonexistent id's response.
    """
    malformed = client.get(_url("not-a-real-id"), headers=user_headers)
    unknown = client.get(_url(str(uuid4())), headers=user_headers)

    assert malformed.status_code == 404
    assert malformed.json()["error_code"] == "WALLET_NOT_FOUND"
    assert malformed.json() == unknown.json()


# --- TC-66: no role elevation for ADMIN --------------------------------------


def test_an_admin_role_caller_cannot_view_another_users_wallet(
    client: TestClient,
    admin_headers: dict[str, str],
    user_headers: dict[str, str],
) -> None:
    """TC-66: an ADMIN caller requests a wallet owned by a different, real
    User -> 404 WALLET_NOT_FOUND — the same outcome any non-ADMIN caller
    would get; no role grants visibility through this endpoint.
    """
    others_wallet = _create_wallet(client, user_headers, name="Member's Wallet")

    response = client.get(_url(str(others_wallet["id"])), headers=admin_headers)

    assert response.status_code == 404
    assert response.json()["error_code"] == "WALLET_NOT_FOUND"


# --- TC-67: an empty transaction history is not an error ---------------------


def test_a_wallet_with_no_transactions_logged_still_views_successfully(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-67: a wallet created with initial_balance 250.00 and no
    transaction ever recorded against it -> 200; balance is exactly 250.00.
    """
    wallet = _create_wallet(client, user_headers, initial_balance="250.00")

    response = client.get(_url(str(wallet["id"])), headers=user_headers)

    assert response.status_code == 200
    assert Decimal(str(response.json()["balance"])) == Decimal("250.00")


# --- TC-68: exact response shape, even with transactions present ------------


def test_the_response_exposes_exactly_the_six_documented_fields(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-68: a wallet with one or more transactions logged against it ->
    response body's keys are exactly id, user_id, name, type, currency,
    balance — no more, and in particular no transactions/transaction_count/
    history key of any kind.
    """
    wallet = _create_wallet(client, user_headers, initial_balance="300.00")
    _record_expense(
        client,
        user_headers,
        db,
        user_id=normal_user.id,
        wallet_id=str(wallet["id"]),
        amount="25.00",
    )

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


# --- TC-69: owning a wallet never grants access to someone else's -----------


def test_a_caller_who_owns_a_different_wallet_cannot_view_another_users_wallet(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    """TC-69: A owns WA, B owns WB; A requests B's wallet -> 404, identical
    to a genuinely nonexistent id's response (QF-12) — owning a wallet of
    their own gives A no access to B's.
    """
    _wa = _create_wallet(client, user_headers, name="A's Wallet")
    wb = _create_wallet(client, admin_headers, name="B's Wallet")

    response = client.get(_url(str(wb["id"])), headers=user_headers)
    not_found = client.get(_url(str(uuid4())), headers=user_headers)

    assert response.status_code == 404
    assert response.json()["error_code"] == "WALLET_NOT_FOUND"
    assert response.json() == not_found.json()


# --- TC-70: credentials are checked before the lookup ------------------------


def test_credentials_are_evaluated_before_the_wallet_reference_is_looked_up(
    client: TestClient,
) -> None:
    """TC-70: an unauthenticated caller requests a wallet id that matches no
    wallet in the system -> 401 NOT_AUTHENTICATED, not 404.
    """
    response = client.get(_url(str(uuid4())))

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"
