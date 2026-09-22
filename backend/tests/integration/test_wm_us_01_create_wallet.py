"""WM-US-01 — Create a Wallet.

One test per test case in specs/003-wallet-management/test_cases.md
(TC-01..TC-22). Names state what the test proves, not what it calls.

`_wallet_count` mirrors the existing `select(func.count()).select_from(...)`
idiom already used by `test_um_us_01_invite.py` for "nothing was persisted"
assertions.

Decimal values in request bodies are sent as JSON strings, never Python
floats, so a test itself never introduces the binary floating-point rounding
that AC-09/TC-13 exists to rule out on the server side. Response balances are
compared via `Decimal(str(...))` so the assertion is immune to whether the
server happens to serialise `1000.00` as the JSON number `1000.0` or the
string `"1000.00"` — both carry the same value.
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import UserModel
from app.models.wallet import WalletModel

WALLETS_URL = "/api/v1/wallets"


# --- helpers --------------------------------------------------------------


def _wallet_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(WalletModel)) or 0


def _valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Main Checking",
        "type": "BANK",
        "currency": "USD",
        "initial_balance": "1000.00",
    }
    payload.update(overrides)
    return payload


def _fields(body: dict[str, object]) -> list[str]:
    details = body["details"]
    assert isinstance(details, dict)
    return [f["location"][-1] for f in details["fields"]]  # type: ignore[index]


# --- TC-01/TC-02: the happy path -------------------------------------------


def test_authenticated_user_creates_a_wallet_201_with_created_wallet(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel
) -> None:
    """TC-01: 201, body carries id, user_id (caller's), name, type, currency,
    balance exactly as submitted.
    """
    response = client.post(WALLETS_URL, json=_valid_payload(), headers=user_headers)

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == normal_user.id
    assert body["name"] == "Main Checking"
    assert body["type"] == "BANK"
    assert body["currency"] == "USD"
    assert Decimal(str(body["balance"])) == Decimal("1000.00")
    assert body.get("id")


def test_creating_a_wallet_persists_exactly_one_row_with_submitted_fields(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-02: exactly one `wallets` row exists carrying the submitted fields,
    owned by the caller.
    """
    response = client.post(WALLETS_URL, json=_valid_payload(), headers=user_headers)

    assert response.status_code == 201
    assert _wallet_count(db) == 1
    row = db.scalars(select(WalletModel)).one()
    assert row.user_id == normal_user.id
    assert row.name == "Main Checking"
    assert row.type == "BANK"
    assert row.currency == "USD"
    assert row.balance == Decimal("1000.00")


# --- TC-03: authentication ---------------------------------------------------


def test_unauthenticated_caller_is_denied_with_401(client: TestClient, db: Session) -> None:
    """TC-03: no `Authorization` header -> 401 NOT_AUTHENTICATED; nothing
    persisted.
    """
    response = client.post(WALLETS_URL, json=_valid_payload())

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"
    assert _wallet_count(db) == 0


# --- TC-04/TC-05/TC-06: name validation --------------------------------------


def test_a_missing_wallet_name_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-04: `name` absent -> 422 VALIDATION_ERROR naming `name`; nothing
    persisted.
    """
    payload = _valid_payload()
    del payload["name"]

    response = client.post(WALLETS_URL, json=payload, headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "name" in _fields(body)
    assert _wallet_count(db) == 0


def test_empty_or_whitespace_only_wallet_name_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-05: `name` `""` and, separately, `"   "` -> each 422 naming `name`;
    nothing persisted.
    """
    for bad_name in ("", "   "):
        response = client.post(
            WALLETS_URL, json=_valid_payload(name=bad_name), headers=user_headers
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error_code"] == "VALIDATION_ERROR"
        assert "name" in _fields(body)

    assert _wallet_count(db) == 0


def test_a_wallet_name_exceeding_100_characters_is_rejected_not_truncated(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-06: `name` of 101 characters -> 422; not truncated, nothing
    persisted.
    """
    response = client.post(WALLETS_URL, json=_valid_payload(name="x" * 101), headers=user_headers)

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"
    assert _wallet_count(db) == 0


# --- TC-07/TC-08/TC-09: type validation --------------------------------------


def test_a_missing_wallet_type_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-07: `type` absent -> 422 VALIDATION_ERROR naming `type`; nothing
    persisted.
    """
    payload = _valid_payload()
    del payload["type"]

    response = client.post(WALLETS_URL, json=payload, headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "type" in _fields(body)
    assert _wallet_count(db) == 0


def test_an_empty_wallet_type_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-08: `type` `""` -> 422 VALIDATION_ERROR naming `type`; nothing
    persisted.
    """
    response = client.post(WALLETS_URL, json=_valid_payload(type=""), headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "type" in _fields(body)
    assert _wallet_count(db) == 0


def test_a_wallet_type_exceeding_50_characters_is_rejected_not_truncated(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-09: `type` of 51 characters -> 422; not truncated, nothing
    persisted.
    """
    response = client.post(WALLETS_URL, json=_valid_payload(type="x" * 51), headers=user_headers)

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"
    assert _wallet_count(db) == 0


# --- TC-10/TC-11: currency validation -----------------------------------------


@pytest.mark.parametrize("bad_currency", ["US", "USDD", "12A", ""])
def test_a_malformed_currency_value_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], db: Session, bad_currency: str
) -> None:
    """TC-10: `currency` in turn `"US"`, `"USDD"`, `"12A"`, `""` -> each 422
    VALIDATION_ERROR naming `currency`; nothing persisted.
    """
    response = client.post(
        WALLETS_URL, json=_valid_payload(currency=bad_currency), headers=user_headers
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "currency" in _fields(body)
    assert _wallet_count(db) == 0


@pytest.mark.parametrize("bad_currency", ["usd", "Usd"])
def test_a_lowercase_or_mixed_case_currency_is_rejected_not_folded_to_uppercase(
    client: TestClient, user_headers: dict[str, str], db: Session, bad_currency: str
) -> None:
    """TC-11: `currency` `"usd"` and, separately, `"Usd"` -> each 422; no
    wallet is created with `currency` `"USD"` — not case-folded and accepted.
    """
    response = client.post(
        WALLETS_URL, json=_valid_payload(currency=bad_currency), headers=user_headers
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"
    assert _wallet_count(db) == 0


# --- TC-12/TC-13/TC-14: initial_balance validation ---------------------------


def test_a_missing_initial_balance_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-12: `initial_balance` absent -> 422 VALIDATION_ERROR naming
    `initial_balance`; nothing persisted.
    """
    payload = _valid_payload()
    del payload["initial_balance"]

    response = client.post(WALLETS_URL, json=payload, headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "initial_balance" in _fields(body)
    assert _wallet_count(db) == 0


def test_an_initial_balance_with_three_decimal_places_is_rejected_not_rounded(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-13: `initial_balance` `"100.005"` -> 422 whose `details` names
    `initial_balance`; no row created — so there is no rounded `100.01` or
    truncated `100.00` value to find (assertion technique per QF-02).
    """
    response = client.post(
        WALLETS_URL, json=_valid_payload(initial_balance="100.005"), headers=user_headers
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "initial_balance" in _fields(body)
    assert _wallet_count(db) == 0


def test_an_initial_balance_exceeding_15_total_digits_is_rejected(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-14: `initial_balance` with 14 integer digits and 2 decimal places
    (16 significant digits total) -> 422; nothing persisted.
    """
    response = client.post(
        WALLETS_URL,
        json=_valid_payload(initial_balance="12345678901234.12"),
        headers=user_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "initial_balance" in _fields(body)
    assert _wallet_count(db) == 0


# --- TC-15/TC-16: sign of the initial balance ---------------------------------


def test_an_initial_balance_of_exactly_zero_is_accepted(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-15: `initial_balance` `"0.00"` -> 201; created wallet's `balance`
    is `0.00`.
    """
    response = client.post(
        WALLETS_URL, json=_valid_payload(initial_balance="0.00"), headers=user_headers
    )

    assert response.status_code == 201
    assert Decimal(str(response.json()["balance"])) == Decimal("0.00")


def test_a_negative_initial_balance_is_accepted(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-16: `type` `"CREDIT"`, `initial_balance` `"-250.00"` -> 201;
    created wallet's `balance` is `-250.00`.
    """
    response = client.post(
        WALLETS_URL,
        json=_valid_payload(type="CREDIT", initial_balance="-250.00"),
        headers=user_headers,
    )

    assert response.status_code == 201
    assert Decimal(str(response.json()["balance"])) == Decimal("-250.00")


# --- TC-17: ownership cannot be overridden by the payload ---------------------


def test_created_wallet_is_always_owned_by_caller_never_by_payload_value(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    normal_user: UserModel,
    admin_user: UserModel,
) -> None:
    """TC-17: caller A (`normal_user`) submits an otherwise valid payload that
    additionally includes an unrecognised `"user_id"` key naming caller B
    (`admin_user`) -> 201; the created wallet's `user_id` equals A's id,
    never B's — the extra key is ignored, not honoured (assertion technique
    per QF-01).
    """
    payload = _valid_payload()
    payload["user_id"] = admin_user.id

    response = client.post(WALLETS_URL, json=payload, headers=user_headers)

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == normal_user.id
    assert body["user_id"] != admin_user.id


# --- TC-18: exact response shape ----------------------------------------------


def test_response_exposes_exactly_the_six_documented_fields(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-18: response body's keys are exactly id, user_id, name, type,
    currency, balance — no more, and in particular no `created_at`
    (plan.md A5, QF-04).
    """
    response = client.post(WALLETS_URL, json=_valid_payload(), headers=user_headers)

    assert response.status_code == 201
    expected_keys = {"id", "user_id", "name", "type", "currency", "balance"}
    assert set(response.json().keys()) == expected_keys


# --- TC-19: no uniqueness constraint on name ----------------------------------


def test_two_wallets_with_the_same_name_for_the_same_user_both_succeed(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-19: a User with one existing wallet named `"Savings"` submits
    another also named `"Savings"` -> 201; two rows exist, both named
    `"Savings"`, with distinct ids.
    """
    first = client.post(WALLETS_URL, json=_valid_payload(name="Savings"), headers=user_headers)
    assert first.status_code == 201

    second = client.post(WALLETS_URL, json=_valid_payload(name="Savings"), headers=user_headers)
    assert second.status_code == 201

    assert first.json()["id"] != second.json()["id"]
    assert _wallet_count(db) == 2
    names = {row.name for row in db.scalars(select(WalletModel)).all()}
    assert names == {"Savings"}


# --- TC-20: grouped validation failures ---------------------------------------


def test_multiple_validation_failures_in_one_submission_are_reported_together(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-20: `name` `""` and `currency` `"usd"` in the same request -> a
    single 422 whose `details` identifies both fields, not just the first
    one encountered.
    """
    response = client.post(
        WALLETS_URL,
        json=_valid_payload(name="", currency="usd"),
        headers=user_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    fields = _fields(body)
    assert "name" in fields
    assert "currency" in fields
    assert _wallet_count(db) == 0


# --- TC-21: whitespace trimming -----------------------------------------------


def test_a_wallet_name_with_surrounding_whitespace_is_stored_trimmed(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-21: `name` `"  Main Checking  "` -> 201; persisted `name` is
    `"Main Checking"` — interior spacing preserved, surrounding whitespace
    removed.
    """
    response = client.post(
        WALLETS_URL, json=_valid_payload(name="  Main Checking  "), headers=user_headers
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Main Checking"


# --- TC-22: no closed vocabulary for type -------------------------------------


def test_a_wallet_type_outside_either_reference_documents_examples_is_accepted(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-22: `type` `"Piggy Bank"` — neither the Gherkin's `"BANK"` nor SDS
    §5.3.1's `"Checking, Cash, Credit Card"` examples -> 201; created
    wallet's `type` is `"Piggy Bank"` exactly, demonstrating the bound is
    length-only, not a closed vocabulary (plan.md A1, QF-03).
    """
    response = client.post(
        WALLETS_URL, json=_valid_payload(type="Piggy Bank"), headers=user_headers
    )

    assert response.status_code == 201
    assert response.json()["type"] == "Piggy Bank"
