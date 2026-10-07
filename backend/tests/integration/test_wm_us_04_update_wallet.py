"""WM-US-04 — Update a Wallet.

One test per test case in specs/003-wallet-management/test_cases.md
(TC-40..TC-59). Names state what the test proves, not what it calls.

`WALLETS_URL`/`_create_wallet`/`_fields`/`_expired_token` are reused by
import from test_wm_us_02_list_wallets.py, the same precedent
test_bm_us_04_update_budget.py set for its own BM-US-02 imports — wallets
are seeded through the real POST /api/v1/wallets endpoint (WM-US-01,
already implemented), never inserted directly, so every TC in this file
describes a wallet "created via POST /api/v1/wallets" and its id is
whatever the server actually assigned.

Stored state is always re-read through `_stored()`, which expires the test
session's identity map first — otherwise a read could return the test
session's own cached copy instead of what the request actually committed
(QF-09).
"""

from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.user import UserModel
from app.models.wallet import WalletModel
from tests.integration.test_wm_us_02_list_wallets import (
    WALLETS_URL,
    _create_wallet,
    _expired_token,
    _fields,
)

# --- helpers ----------------------------------------------------------------


def _url(wallet_id: str) -> str:
    return f"{WALLETS_URL}/{wallet_id}"


def _stored(db: Session, wallet_id: str) -> WalletModel:
    """The committed `wallets` row, read fresh rather than from the identity map."""
    db.expire_all()
    wallet = db.get(WalletModel, wallet_id)
    assert wallet is not None
    return wallet


# --- TC-40/TC-41/TC-42: the happy path, partial and full updates ------------


def test_updating_only_the_name_returns_200_with_other_fields_unchanged(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-40: name "Main Checking"/type "BANK"/currency "USD"/balance
    500.00, PATCH name "Primary Checking" only -> 200; id unchanged, name
    "Primary Checking", type/currency/balance unchanged.
    """
    wallet = _create_wallet(
        client,
        user_headers,
        name="Main Checking",
        type="BANK",
        currency="USD",
        initial_balance="500.00",
    )

    response = client.patch(
        _url(str(wallet["id"])), json={"name": "Primary Checking"}, headers=user_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == wallet["id"]
    assert body["name"] == "Primary Checking"
    assert body["type"] == "BANK"
    assert body["currency"] == "USD"
    assert Decimal(str(body["balance"])) == Decimal("500.00")


def test_updating_only_the_type_returns_200_with_other_fields_unchanged(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-41: name "Main Checking"/type "BANK"/currency "USD"/balance
    500.00, PATCH type "CREDIT" only -> 200; type "CREDIT",
    name/currency/balance unchanged.
    """
    wallet = _create_wallet(
        client,
        user_headers,
        name="Main Checking",
        type="BANK",
        currency="USD",
        initial_balance="500.00",
    )

    response = client.patch(_url(str(wallet["id"])), json={"type": "CREDIT"}, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "CREDIT"
    assert body["name"] == "Main Checking"
    assert body["currency"] == "USD"
    assert Decimal(str(body["balance"])) == Decimal("500.00")


def test_updating_both_name_and_type_together_changes_both_leaves_currency_and_balance(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-42: PATCH name "Primary Checking" and type "CREDIT" together ->
    200; both change, currency/balance unchanged.
    """
    wallet = _create_wallet(
        client,
        user_headers,
        name="Main Checking",
        type="BANK",
        currency="USD",
        initial_balance="500.00",
    )

    response = client.patch(
        _url(str(wallet["id"])),
        json={"name": "Primary Checking", "type": "CREDIT"},
        headers=user_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Primary Checking"
    assert body["type"] == "CREDIT"
    assert body["currency"] == "USD"
    assert Decimal(str(body["balance"])) == Decimal("500.00")


# --- TC-43: persistence on the same single row ------------------------------


def test_updating_a_wallet_persists_the_new_values_on_the_same_single_row(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-43: after a successful name+type update, direct inspection of the
    `wallets` row for that id shows the new values; exactly one row still
    exists for that wallet id.
    """
    wallet = _create_wallet(client, user_headers)

    response = client.patch(
        _url(str(wallet["id"])),
        json={"name": "Primary Checking", "type": "CREDIT"},
        headers=user_headers,
    )

    assert response.status_code == 200
    stored = _stored(db, str(wallet["id"]))
    assert stored.name == "Primary Checking"
    assert stored.type == "CREDIT"
    count = db.scalar(
        select(func.count()).select_from(WalletModel).where(WalletModel.id == wallet["id"])
    )
    assert count == 1


# --- TC-44: authentication ---------------------------------------------------


def test_an_unauthenticated_or_expired_caller_is_denied_and_nothing_changes(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    settings: Settings,
) -> None:
    """TC-44: no Authorization header, and separately an expired token ->
    401 NOT_AUTHENTICATED both times; the stored name/type are unchanged.
    """
    wallet = _create_wallet(client, user_headers, name="Main Checking", type="BANK")

    no_auth = client.patch(_url(str(wallet["id"])), json={"name": "Hacked"})
    expired = client.patch(
        _url(str(wallet["id"])),
        json={"name": "Hacked"},
        headers={"Authorization": f"Bearer {_expired_token(normal_user, settings)}"},
    )

    assert no_auth.status_code == 401
    assert no_auth.json()["error_code"] == "NOT_AUTHENTICATED"
    assert expired.status_code == 401
    assert expired.json()["error_code"] == "NOT_AUTHENTICATED"
    stored = _stored(db, str(wallet["id"]))
    assert stored.name == "Main Checking"
    assert stored.type == "BANK"


# --- TC-45/TC-46/TC-47: not found, not owned, malformed — collapsed (QF-08) --


def test_a_wallet_id_matching_no_wallet_is_rejected_with_404_wallet_not_found(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-45: a well-formed id matching no wallet -> 404 WALLET_NOT_FOUND;
    nothing changes.
    """
    own = _create_wallet(client, user_headers, name="Mine")

    response = client.patch(_url(str(uuid4())), json={"name": "Hacked"}, headers=user_headers)

    assert response.status_code == 404
    assert response.json()["error_code"] == "WALLET_NOT_FOUND"
    assert _stored(db, str(own["id"])).name == "Mine"


def test_another_users_wallet_is_refused_with_a_body_identical_to_not_found(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-46: A patches B's wallet -> 404, and error_code/message/details
    are all identical to TC-45's not-found-at-all body (QF-08); B's wallet
    is unchanged.
    """
    b_wallet = _create_wallet(client, admin_headers, name="B's Wallet")

    not_owned = client.patch(
        _url(str(b_wallet["id"])), json={"name": "Hacked"}, headers=user_headers
    )
    not_found = client.patch(_url(str(uuid4())), json={"name": "Hacked"}, headers=user_headers)

    assert not_owned.status_code == 404
    assert not_owned.json()["error_code"] == "WALLET_NOT_FOUND"
    assert not_owned.json() == not_found.json()
    assert _stored(db, str(b_wallet["id"])).name == "B's Wallet"


def test_a_malformed_wallet_id_gets_the_same_404_as_a_well_formed_unknown_one(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-47: PATCH /wallets/not-a-real-id with a valid payload -> 404
    WALLET_NOT_FOUND, identical to TC-45's body.
    """
    malformed = client.patch(_url("not-a-real-id"), json={"name": "Hacked"}, headers=user_headers)
    unknown = client.patch(_url(str(uuid4())), json={"name": "Hacked"}, headers=user_headers)

    assert malformed.status_code == 404
    assert malformed.json()["error_code"] == "WALLET_NOT_FOUND"
    assert malformed.json() == unknown.json()


# --- TC-48: neither field submitted is a 422, never a no-op 200 (QF-10) -----


def test_a_submission_naming_neither_name_nor_type_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-48: empty body -> 422 VALIDATION_ERROR, not 200; stored name/type
    are unchanged (assertion technique per QF-10).
    """
    wallet = _create_wallet(client, user_headers, name="Mine", type="BANK")

    response = client.patch(_url(str(wallet["id"])), json={}, headers=user_headers)

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"
    stored = _stored(db, str(wallet["id"]))
    assert stored.name == "Mine"
    assert stored.type == "BANK"


# --- TC-49/TC-50: name validation --------------------------------------------


def test_a_blank_or_whitespace_only_name_when_submitted_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-49: name "" and, separately, "   " -> each 422 VALIDATION_ERROR
    naming `name`; the stored name is unchanged.
    """
    wallet = _create_wallet(client, user_headers, name="Mine")

    for bad_name in ("", "   "):
        response = client.patch(
            _url(str(wallet["id"])), json={"name": bad_name}, headers=user_headers
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error_code"] == "VALIDATION_ERROR"
        assert "name" in _fields(body)

    assert _stored(db, str(wallet["id"])).name == "Mine"


def test_a_name_exceeding_100_characters_is_rejected_not_truncated(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-50: name of 101 characters -> 422; not truncated, stored name
    unchanged.
    """
    wallet = _create_wallet(client, user_headers, name="Mine")

    response = client.patch(_url(str(wallet["id"])), json={"name": "x" * 101}, headers=user_headers)

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"
    assert _stored(db, str(wallet["id"])).name == "Mine"


# --- TC-51/TC-52: type validation --------------------------------------------


def test_an_empty_type_when_submitted_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-51: type "" -> 422 VALIDATION_ERROR naming `type`; stored type
    unchanged (scope bounded by QF-11 — no whitespace-only case asserted).
    """
    wallet = _create_wallet(client, user_headers, type="BANK")

    response = client.patch(_url(str(wallet["id"])), json={"type": ""}, headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "type" in _fields(body)
    assert _stored(db, str(wallet["id"])).type == "BANK"


def test_a_type_exceeding_50_characters_is_rejected_not_truncated(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-52: type of 51 characters -> 422; not truncated, stored type
    unchanged.
    """
    wallet = _create_wallet(client, user_headers, type="BANK")

    response = client.patch(_url(str(wallet["id"])), json={"type": "x" * 51}, headers=user_headers)

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"
    assert _stored(db, str(wallet["id"])).type == "BANK"


# --- TC-53: no closed vocabulary for type, on update either ------------------


def test_a_wallet_type_outside_either_reference_documents_examples_is_accepted_on_update(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-53: type "Piggy Bank" — neither the Gherkin's "BANK" nor SDS
    §5.3.1's own examples -> 200; updated type is "Piggy Bank" exactly.
    """
    wallet = _create_wallet(client, user_headers, type="BANK")

    response = client.patch(
        _url(str(wallet["id"])), json={"type": "Piggy Bank"}, headers=user_headers
    )

    assert response.status_code == 200
    assert response.json()["type"] == "Piggy Bank"


# --- TC-54: whitespace trimming -----------------------------------------------


def test_a_name_with_surrounding_whitespace_is_stored_trimmed(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-54: name "  Primary Checking  " -> 200; persisted name is
    "Primary Checking" — interior spacing preserved, surrounding whitespace
    removed.
    """
    wallet = _create_wallet(client, user_headers, name="Main Checking")

    response = client.patch(
        _url(str(wallet["id"])), json={"name": "  Primary Checking  "}, headers=user_headers
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Primary Checking"


# --- TC-55/TC-56: currency and balance are immutable through this story -----


def test_a_successful_update_leaves_currency_and_balance_unchanged_verified_against_storage(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-55: currency "USD"/balance 750.25, update name successfully ->
    response currency/balance match pre-update values; a direct read of the
    `wallets` row confirms the stored columns are unchanged too (assertion
    technique per QF-09).
    """
    wallet = _create_wallet(client, user_headers, currency="USD", initial_balance="750.25")

    response = client.patch(_url(str(wallet["id"])), json={"name": "Renamed"}, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["currency"] == "USD"
    assert Decimal(str(body["balance"])) == Decimal("750.25")
    stored = _stored(db, str(wallet["id"]))
    assert stored.currency == "USD"
    assert stored.balance == Decimal("750.25")


def test_a_currency_or_balance_value_submitted_alongside_name_or_type_is_silently_ignored(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-56: valid name plus the extra keys currency ("EUR") and
    initial_balance (9999.00) -> 200; updated currency/balance remain
    "USD"/500.00 — never the submitted extra values.
    """
    wallet = _create_wallet(client, user_headers, currency="USD", initial_balance="500.00")

    response = client.patch(
        _url(str(wallet["id"])),
        json={"name": "Renamed", "currency": "EUR", "initial_balance": "9999.00"},
        headers=user_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["currency"] == "USD"
    assert Decimal(str(body["balance"])) == Decimal("500.00")
    stored = _stored(db, str(wallet["id"]))
    assert stored.currency == "USD"
    assert stored.balance == Decimal("500.00")


# --- TC-57: exact response shape ---------------------------------------------


def test_the_response_exposes_exactly_the_six_documented_fields(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-57: response body's keys are exactly id, user_id, name, type,
    currency, balance — no more, no invented field.
    """
    wallet = _create_wallet(client, user_headers)

    response = client.patch(_url(str(wallet["id"])), json={"name": "Renamed"}, headers=user_headers)

    assert response.status_code == 200
    assert set(response.json().keys()) == {
        "id",
        "user_id",
        "name",
        "type",
        "currency",
        "balance",
    }


# --- TC-58: grouped validation failures ---------------------------------------


def test_multiple_validation_failures_in_one_submission_are_reported_together(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-58: name "" and a type of 51 characters in the same request -> a
    single 422 whose details identifies both fields, not just the first one
    encountered.
    """
    wallet = _create_wallet(client, user_headers, name="Mine", type="BANK")

    response = client.patch(
        _url(str(wallet["id"])),
        json={"name": "", "type": "x" * 51},
        headers=user_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    fields = _fields(body)
    assert "name" in fields
    assert "type" in fields
    stored = _stored(db, str(wallet["id"]))
    assert stored.name == "Mine"
    assert stored.type == "BANK"


# --- TC-59: owning a wallet never grants access to someone else's -----------


def test_a_caller_who_owns_a_different_wallet_cannot_update_another_users_wallet(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    db: Session,
) -> None:
    """TC-59: A owns WA, B owns WB; A patches WB -> 404 WALLET_NOT_FOUND,
    identical to TC-45/TC-46's responses; WB's stored name/type are
    unchanged, and A's own WA is also unaffected.
    """
    wa = _create_wallet(client, user_headers, name="A's Wallet", type="BANK")
    wb = _create_wallet(client, admin_headers, name="B's Wallet", type="CASH")

    response = client.patch(_url(str(wb["id"])), json={"name": "Hacked"}, headers=user_headers)
    not_found = client.patch(_url(str(uuid4())), json={"name": "Hacked"}, headers=user_headers)

    assert response.status_code == 404
    assert response.json()["error_code"] == "WALLET_NOT_FOUND"
    assert response.json() == not_found.json()
    stored_b = _stored(db, str(wb["id"]))
    assert stored_b.name == "B's Wallet"
    assert stored_b.type == "CASH"
    stored_a = _stored(db, str(wa["id"]))
    assert stored_a.name == "A's Wallet"
    assert stored_a.type == "BANK"
