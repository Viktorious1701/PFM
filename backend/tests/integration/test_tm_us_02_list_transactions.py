"""TM-US-02 — List Transactions.

One test per test case in specs/006-transaction-management/test_cases.md
(TC-37..TC-72). Names state what the test proves, not what it calls.

Wallets and categories are prerequisites, not the entity under test, so they
are constructed directly against the `db` session (`_make_wallet`,
`_make_category`) — the same style `test_tm_us_01_create_transaction.py`
itself uses for its own prerequisites. Transactions, however, ARE the entity
this endpoint lists, so they are seeded through the real
`POST /api/v1/transactions` endpoint (TM-US-01, already implemented) via
`_create_transaction`/`_create_transaction_at` — mirroring
`test_wm_us_02_list_wallets.py`'s own `_create_wallet` precedent ("seeds
preconditions through the real endpoint... rather than inserting rows
directly"), and it is what lets a transaction's `id` be whatever the server
actually assigned, which the ordering assertions below (TC-50..TC-52, TC-55)
depend on.

`_create_transaction_at` monkeypatches `app.core.clock.utcnow` to an explicit
instant immediately before a single creation call, then restores nothing
itself — each call sets a fresh instant, so a test that needs several
distinct, known timestamps just calls it several times with different
instants. This is the out-of-creation-order technique QF-09 requires: TC-50
deliberately creates the *middle* instant first, the *earliest* second, and
the *latest* third, so a test that returned rows in insertion order rather
than genuine `timestamp` order could not accidentally pass.

TC-58/TC-61/TC-70/TC-71 each assert full-response-body equality against a
`_empty_wallet_filter_body`/`_empty_category_filter_body` call computed fresh
inside the same test (never a nonexistent-id response captured in a
*different* test function) — the same QF-01-style "identical, not merely
both empty" technique TM-US-01's own TC-08/TC-11 already established for a
create-time reference, applied here to a list filter (QF-11).

Decimal amounts are always sent as JSON strings, never Python floats, mirroring
every prior story's tests.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import Settings
from app.models.category import CategoryModel, CategoryType
from app.models.user import UserModel
from app.models.wallet import WalletModel

TRANSACTIONS_URL = "/api/v1/transactions"

NONEXISTENT_WALLET_ID = "00000000-0000-0000-0000-000000000000"
NONEXISTENT_CATEGORY_ID = "00000000-0000-0000-0000-000000000001"
MALFORMED_ID = "not-a-real-id"

# A fixed base instant, distinct from conftest's own FROZEN_NOW, so ordering
# tests below can derive several distinct, known instants from it without
# colliding with any other fixture's notion of "now".
BASE_INSTANT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


# --- helpers ----------------------------------------------------------------


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


def _create_transaction(
    client: TestClient,
    headers: dict[str, str],
    *,
    wallet_id: str,
    category_id: str,
    amount: str = "10.00",
    txn_type: str = "EXPENSE",
    **overrides: object,
) -> dict[str, object]:
    """POST a transaction through the real TM-US-01 endpoint and return its
    body. Asserts 201 itself so a seeding failure fails loudly at the
    seeding line, not as a confusing downstream assertion.
    """
    payload: dict[str, object] = {
        "wallet_id": wallet_id,
        "category_id": category_id,
        "amount": amount,
        "type": txn_type,
    }
    payload.update(overrides)
    response = client.post(TRANSACTIONS_URL, json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


def _create_transaction_at(
    client: TestClient,
    headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    instant: datetime,
    *,
    wallet_id: str,
    category_id: str,
    **overrides: object,
) -> dict[str, object]:
    """`_create_transaction`, with the clock seam patched to `instant` for
    this one call only (QF-09) — the created transaction's `timestamp` is
    always `app.core.clock.utcnow()` at the moment the service runs
    (TM-US-01 A5), so this is how a test controls it.
    """
    monkeypatch.setattr("app.core.clock.utcnow", lambda: instant)
    return _create_transaction(
        client, headers, wallet_id=wallet_id, category_id=category_id, **overrides
    )


def _empty_wallet_filter_body(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    response = client.get(
        TRANSACTIONS_URL, params={"wallet_id": NONEXISTENT_WALLET_ID}, headers=headers
    )
    assert response.status_code == 200
    body: dict[str, object] = response.json()
    return body


def _empty_category_filter_body(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    response = client.get(
        TRANSACTIONS_URL, params={"category_id": NONEXISTENT_CATEGORY_ID}, headers=headers
    )
    assert response.status_code == 200
    body: dict[str, object] = response.json()
    return body


def _fields(body: dict[str, object]) -> list[str]:
    details = body["details"]
    assert isinstance(details, dict)
    return [f["location"][-1] for f in details["fields"]]  # type: ignore[index]


def _expired_token(user: UserModel, settings: Settings) -> str:
    return security.encode_jwt(
        subject=user.id,
        role=user.role.value,
        secret=settings.jwt_secret,
        ttl_minutes=-1,  # already past
        algorithm=settings.jwt_algorithm,
    )


# --- TC-37/TC-38: the happy path envelope ------------------------------------


def test_authenticated_user_lists_every_transaction_belonging_to_every_wallet_they_own(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-37: three transactions logged via POST against one owned wallet ->
    200; items contains all three (by id), each referencing the caller's
    own wallet and category; total is 3.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    created_ids = {
        _create_transaction(client, user_headers, wallet_id=wallet.id, category_id=category.id)[
            "id"
        ]
        for _ in range(3)
    }

    response = client.get(TRANSACTIONS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3
    assert {item["id"] for item in body["items"]} == created_ids
    for item in body["items"]:
        assert item["wallet_id"] == wallet.id
        assert item["category_id"] == category.id


def test_response_item_exposes_exactly_seven_fields_wrapped_in_paginated_envelope(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-38: top-level body exposes exactly items, total, page, page_size;
    each entry in items exposes exactly id, wallet_id, category_id, amount,
    type, timestamp, note — no more, no field this story invents.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    _create_transaction(client, user_headers, wallet_id=wallet.id, category_id=category.id)

    response = client.get(TRANSACTIONS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"items", "total", "page", "page_size"}
    assert len(body["items"]) == 1
    assert set(body["items"][0].keys()) == {
        "id",
        "wallet_id",
        "category_id",
        "amount",
        "type",
        "timestamp",
        "note",
    }


# --- TC-39: the empty case ----------------------------------------------------


def test_user_with_no_transactions_yet_receives_empty_list_and_zero_total(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-39: owns a wallet and a category but no transactions -> 200, not an
    error; items is empty, total is 0.
    """
    _make_wallet(db, user_id=normal_user.id)
    _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    response = client.get(TRANSACTIONS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


# --- TC-40/TC-41: authentication ---------------------------------------------


def test_unauthenticated_or_invalid_credential_caller_is_denied_with_401(
    client: TestClient, normal_user: UserModel, settings: Settings
) -> None:
    """TC-40: no Authorization header, and separately an expired token, both
    -> 401 NOT_AUTHENTICATED; no items returned either way.
    """
    no_auth = client.get(TRANSACTIONS_URL)
    assert no_auth.status_code == 401
    assert no_auth.json()["error_code"] == "NOT_AUTHENTICATED"
    assert "items" not in no_auth.json()

    expired = client.get(
        TRANSACTIONS_URL,
        headers={"Authorization": f"Bearer {_expired_token(normal_user, settings)}"},
    )
    assert expired.status_code == 401
    assert expired.json()["error_code"] == "NOT_AUTHENTICATED"
    assert "items" not in expired.json()


def test_credentials_are_evaluated_before_any_query_parameter(client: TestClient) -> None:
    """TC-41: an out-of-range `page` from an unauthenticated caller still
    answers 401, not 422 — mirrors WM-US-02 TC-27/UM-US-03 TC-61's ordering.
    """
    response = client.get(TRANSACTIONS_URL, params={"page": 0})

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"


# --- TC-42/TC-43: pagination defaults and explicit values --------------------


def test_default_page_is_1_of_size_25_with_accurate_total(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-42: no page/page_size supplied -> page 1, page_size 25, all three
    transactions returned, total 3.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    for _ in range(3):
        _create_transaction(client, user_headers, wallet_id=wallet.id, category_id=category.id)

    response = client.get(TRANSACTIONS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 25
    assert len(body["items"]) == 3
    assert body["total"] == 3


def test_explicit_page_and_page_size_within_range_return_that_page_and_accurate_total(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-43: page=2, page_size=2 over 5 transactions -> that page's two
    transactions and total=5.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    for _ in range(5):
        _create_transaction(client, user_headers, wallet_id=wallet.id, category_id=category.id)

    response = client.get(
        TRANSACTIONS_URL, params={"page": 2, "page_size": 2}, headers=user_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 2
    assert body["page_size"] == 2
    assert body["total"] == 5
    assert len(body["items"]) == 2


# --- TC-44/TC-45/TC-46/TC-47: pagination boundary validation -----------------


@pytest.mark.parametrize("bad_page", [0, -1, "abc"])
def test_a_non_positive_or_non_integer_page_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], bad_page: object
) -> None:
    """TC-44: page in {0, -1, "abc"} -> 422 VALIDATION_ERROR naming `page`;
    no items returned.
    """
    response = client.get(TRANSACTIONS_URL, params={"page": bad_page}, headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "page" in _fields(body)
    assert "items" not in body


@pytest.mark.parametrize("bad_page_size", [0, -1, "abc"])
def test_a_non_positive_or_non_integer_page_size_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], bad_page_size: object
) -> None:
    """TC-45: page_size in {0, -1, "abc"} -> 422 VALIDATION_ERROR naming
    `page_size`; no items returned.
    """
    response = client.get(
        TRANSACTIONS_URL, params={"page_size": bad_page_size}, headers=user_headers
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "page_size" in _fields(body)
    assert "items" not in body


def test_a_page_size_above_the_maximum_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-46 / EC-02: page_size=101 -> 422 VALIDATION_ERROR naming
    `page_size`; the request is not silently capped at 100.
    """
    response = client.get(TRANSACTIONS_URL, params={"page_size": 101}, headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "page_size" in _fields(body)


def test_a_page_size_of_exactly_100_is_accepted(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-47 / EC-02: page_size=100 -> 200. The cap is a ceiling, not a
    target: only 101 (TC-46) is rejected.
    """
    response = client.get(TRANSACTIONS_URL, params={"page_size": 100}, headers=user_headers)

    assert response.status_code == 200
    assert response.json()["page_size"] == 100


# --- TC-48/TC-49: ownership scoping, items and total alike (QF-10) ----------


def test_a_user_only_ever_sees_transactions_belonging_to_wallets_they_own(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    normal_user: UserModel,
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-48: A (one wallet, two transactions) and B (one wallet, three
    transactions) -> A's request returns exactly A's two transactions, none
    of B's three; total is 2, not 5 (assertion technique per QF-10).
    """
    wallet_a = _make_wallet(db, user_id=normal_user.id)
    category_a = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    ids_a = {
        _create_transaction(client, user_headers, wallet_id=wallet_a.id, category_id=category_a.id)[
            "id"
        ]
        for _ in range(2)
    }

    wallet_b = _make_wallet(db, user_id=admin_user.id)
    category_b = _make_category(db, user_id=admin_user.id, category_type=CategoryType.EXPENSE)
    for _ in range(3):
        _create_transaction(client, admin_headers, wallet_id=wallet_b.id, category_id=category_b.id)

    response = client.get(TRANSACTIONS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert {item["id"] for item in body["items"]} == ids_a


def test_reported_total_counts_only_callers_own_transactions_even_when_smaller(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    normal_user: UserModel,
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-49: A (a wallet with no transactions) and B (a wallet with four
    transactions) -> A's request returns items empty and total 0 — not 4,
    and not any count reflecting B's transactions (assertion technique per
    QF-10).
    """
    _make_wallet(db, user_id=normal_user.id)
    wallet_b = _make_wallet(db, user_id=admin_user.id)
    category_b = _make_category(db, user_id=admin_user.id, category_type=CategoryType.EXPENSE)
    for _ in range(4):
        _create_transaction(client, admin_headers, wallet_id=wallet_b.id, category_id=category_b.id)

    response = client.get(TRANSACTIONS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


# --- TC-50/TC-51/TC-52: ordering and cross-page completeness (QF-09) --------


def test_list_is_returned_most_recently_recorded_first_proven_against_out_of_order_creation(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-50: three transactions created while the clock is monkeypatched to
    three distinct instants in non-chronological creation order (middle
    first, earliest second, latest third) -> items are ordered
    latest-instant, middle-instant, earliest-instant — matching the frozen
    timestamps' own chronological order, not creation-call order (assertion
    technique per QF-09).
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    earliest = BASE_INSTANT
    middle = BASE_INSTANT + timedelta(hours=1)
    latest = BASE_INSTANT + timedelta(hours=2)

    mid_id = _create_transaction_at(
        client, user_headers, monkeypatch, middle, wallet_id=wallet.id, category_id=category.id
    )["id"]
    early_id = _create_transaction_at(
        client, user_headers, monkeypatch, earliest, wallet_id=wallet.id, category_id=category.id
    )["id"]
    late_id = _create_transaction_at(
        client, user_headers, monkeypatch, latest, wallet_id=wallet.id, category_id=category.id
    )["id"]

    response = client.get(TRANSACTIONS_URL, headers=user_headers)

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [late_id, mid_id, early_id]


def test_two_transactions_recorded_at_the_same_instant_have_deterministic_relative_order(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-51 / EC-08: two transactions created while the clock returns the
    identical instant for both -> both list requests place the tied
    transactions in the identical relative order — the lexicographically
    smaller id first — on both requests.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    id_1 = _create_transaction_at(
        client,
        user_headers,
        monkeypatch,
        BASE_INSTANT,
        wallet_id=wallet.id,
        category_id=category.id,
    )["id"]
    id_2 = _create_transaction_at(
        client,
        user_headers,
        monkeypatch,
        BASE_INSTANT,
        wallet_id=wallet.id,
        category_id=category.id,
    )["id"]
    expected_order = sorted([id_1, id_2])

    first = client.get(TRANSACTIONS_URL, headers=user_headers)
    second = client.get(TRANSACTIONS_URL, headers=user_headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert [item["id"] for item in first.json()["items"]] == expected_order
    assert [item["id"] for item in second.json()["items"]] == expected_order


def test_paging_through_every_page_returns_every_transaction_exactly_once_in_stable_order(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-52 / EC-03: five transactions recorded at five distinct, known
    instants, paged with page_size=2 across page=1,2,3 -> the concatenation
    of all three pages' items contains every one of the five transactions
    exactly once, no duplicate, no gap, in the same most-recent-first order
    TC-50 established.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    instants = [BASE_INSTANT + timedelta(hours=i) for i in range(5)]
    created_ids = [
        _create_transaction_at(
            client, user_headers, monkeypatch, instant, wallet_id=wallet.id, category_id=category.id
        )["id"]
        for instant in instants
    ]
    expected_order = list(reversed(created_ids))  # latest instant (created last) first

    seen: list[str] = []
    for page in (1, 2, 3):
        response = client.get(
            TRANSACTIONS_URL, params={"page": page, "page_size": 2}, headers=user_headers
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 5
        seen.extend(item["id"] for item in body["items"])

    assert len(seen) == 5
    assert len(set(seen)) == 5
    assert seen == expected_order


# --- TC-53: page beyond the last page ----------------------------------------


def test_a_page_beyond_the_last_available_page_returns_empty_list_with_accurate_total(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-53 / EC-01: page=5, page_size=25 over 3 transactions -> 200, not
    404; items empty, total still 3.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    for _ in range(3):
        _create_transaction(client, user_headers, wallet_id=wallet.id, category_id=category.id)

    response = client.get(
        TRANSACTIONS_URL, params={"page": 5, "page_size": 25}, headers=user_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 3


# --- TC-54: ADMIN role grants no extra visibility here (EC-04) --------------


def test_admin_role_caller_who_also_owns_transactions_sees_only_their_own(
    client: TestClient,
    admin_headers: dict[str, str],
    user_headers: dict[str, str],
    admin_user: UserModel,
    normal_user: UserModel,
    db: Session,
) -> None:
    """TC-54 / EC-04: an ADMIN who owns one wallet with one transaction, and
    a second User (role USER) who owns a wallet with two of their own -> the
    ADMIN's request returns exactly the ADMIN's own one transaction, never
    either of the other User's; total is 1.
    """
    wallet_admin = _make_wallet(db, user_id=admin_user.id)
    category_admin = _make_category(db, user_id=admin_user.id, category_type=CategoryType.EXPENSE)
    admin_txn_id = _create_transaction(
        client, admin_headers, wallet_id=wallet_admin.id, category_id=category_admin.id
    )["id"]

    wallet_user = _make_wallet(db, user_id=normal_user.id)
    category_user = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    for _ in range(2):
        _create_transaction(
            client, user_headers, wallet_id=wallet_user.id, category_id=category_user.id
        )

    response = client.get(TRANSACTIONS_URL, headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == admin_txn_id


# --- TC-55: cross-wallet aggregation (EC-11) --------------------------------


def test_transactions_from_every_wallet_the_caller_owns_appear_together_correctly_ordered(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-55 / EC-11: caller owns two wallets, with transactions recorded
    against each at interleaved instants (not grouped by wallet) -> items
    contains every transaction from both wallets, ordered
    most-recently-recorded first across the combined set — not grouped by
    wallet and not limited to one wallet.
    """
    wallet_1 = _make_wallet(db, user_id=normal_user.id, name="Wallet 1")
    wallet_2 = _make_wallet(db, user_id=normal_user.id, name="Wallet 2")
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    t1, t2, t3, t4 = (BASE_INSTANT + timedelta(hours=i) for i in range(4))
    id_1 = _create_transaction_at(
        client, user_headers, monkeypatch, t1, wallet_id=wallet_1.id, category_id=category.id
    )["id"]
    id_2 = _create_transaction_at(
        client, user_headers, monkeypatch, t2, wallet_id=wallet_2.id, category_id=category.id
    )["id"]
    id_3 = _create_transaction_at(
        client, user_headers, monkeypatch, t3, wallet_id=wallet_1.id, category_id=category.id
    )["id"]
    id_4 = _create_transaction_at(
        client, user_headers, monkeypatch, t4, wallet_id=wallet_2.id, category_id=category.id
    )["id"]

    response = client.get(TRANSACTIONS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 4
    assert [item["id"] for item in body["items"]] == [id_4, id_3, id_2, id_1]


# --- TC-56/TC-57/TC-58: wallet filter (QF-10, QF-11) ------------------------


def test_a_wallet_filter_narrows_the_list_to_exactly_that_wallets_transactions(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-56: caller owns two wallets, each with transactions logged against
    it -> naming one wallet's id returns only that wallet's transactions,
    and the reported total counts only that wallet's transactions.
    """
    wallet_1 = _make_wallet(db, user_id=normal_user.id, name="Wallet 1")
    wallet_2 = _make_wallet(db, user_id=normal_user.id, name="Wallet 2")
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    ids_1 = {
        _create_transaction(client, user_headers, wallet_id=wallet_1.id, category_id=category.id)[
            "id"
        ]
        for _ in range(2)
    }
    for _ in range(3):
        _create_transaction(client, user_headers, wallet_id=wallet_2.id, category_id=category.id)

    response = client.get(TRANSACTIONS_URL, params={"wallet_id": wallet_1.id}, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {item["id"] for item in body["items"]} == ids_1


def test_a_wallet_filter_matching_no_wallet_at_all_returns_an_empty_result_not_an_error(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-57 / EC-09: a wallet_id matching no wallet in the system -> 200,
    not 404; items empty, total 0 — even though the caller has existing
    transactions of their own.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    _create_transaction(client, user_headers, wallet_id=wallet.id, category_id=category.id)

    body = _empty_wallet_filter_body(client, user_headers)

    assert body["items"] == []
    assert body["total"] == 0


def test_a_wallet_filter_naming_a_different_users_real_wallet_matches_tc_57(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    normal_user: UserModel,
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-58: A names B's real wallet_id -> identical outcome to TC-57's
    response — not merely both empty (assertion technique per QF-11).
    """
    wallet_a = _make_wallet(db, user_id=normal_user.id)
    category_a = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    _create_transaction(client, user_headers, wallet_id=wallet_a.id, category_id=category_a.id)

    wallet_b = _make_wallet(db, user_id=admin_user.id)
    category_b = _make_category(db, user_id=admin_user.id, category_type=CategoryType.EXPENSE)
    _create_transaction(client, admin_headers, wallet_id=wallet_b.id, category_id=category_b.id)

    not_found_equivalent = _empty_wallet_filter_body(client, user_headers)

    response = client.get(TRANSACTIONS_URL, params={"wallet_id": wallet_b.id}, headers=user_headers)

    assert response.status_code == 200
    assert response.json() == not_found_equivalent


# --- TC-59/TC-60/TC-61: category filter (QF-11, QF-12) ----------------------


def test_a_category_filter_narrows_the_list_to_exactly_that_categorys_transactions(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-59: caller owns transactions logged under two categories -> naming
    one category's id returns only that category's transactions, and the
    reported total counts only that category's transactions.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category_1 = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name="Groceries"
    )
    category_2 = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.INCOME, name="Salary"
    )
    ids_1 = {
        _create_transaction(
            client,
            user_headers,
            wallet_id=wallet.id,
            category_id=category_1.id,
            txn_type="EXPENSE",
        )["id"]
        for _ in range(2)
    }
    for _ in range(3):
        _create_transaction(
            client,
            user_headers,
            wallet_id=wallet.id,
            category_id=category_2.id,
            txn_type="INCOME",
        )

    response = client.get(
        TRANSACTIONS_URL, params={"category_id": category_1.id}, headers=user_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {item["id"] for item in body["items"]} == ids_1


def test_a_category_filter_matching_no_category_at_all_returns_an_empty_result_not_an_error(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-60 / EC-10: a category_id matching no category in the system ->
    200, not 404; items empty, total 0.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    _create_transaction(client, user_headers, wallet_id=wallet.id, category_id=category.id)

    body = _empty_category_filter_body(client, user_headers)

    assert body["items"] == []
    assert body["total"] == 0


def test_a_category_filter_naming_a_different_users_real_category_matches_tc_60(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    normal_user: UserModel,
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-61: A names B's real category_id -> identical outcome to TC-60's
    response, even though B's own transactions (combining B's own wallet and
    B's own category) genuinely exist under it — proving the wallet-ownership
    join alone already excludes them, with no second join to `categories`
    needed (assertion technique per QF-11, QF-12).
    """
    wallet_a = _make_wallet(db, user_id=normal_user.id)
    category_a = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    _create_transaction(client, user_headers, wallet_id=wallet_a.id, category_id=category_a.id)

    wallet_b = _make_wallet(db, user_id=admin_user.id)
    category_b = _make_category(db, user_id=admin_user.id, category_type=CategoryType.EXPENSE)
    _create_transaction(client, admin_headers, wallet_id=wallet_b.id, category_id=category_b.id)

    not_found_equivalent = _empty_category_filter_body(client, user_headers)

    response = client.get(
        TRANSACTIONS_URL, params={"category_id": category_b.id}, headers=user_headers
    )

    assert response.status_code == 200
    assert response.json() == not_found_equivalent


# --- TC-62..TC-67: date-range filter (QF-13) --------------------------------


def test_a_date_range_filter_with_both_bounds_narrows_to_transactions_recorded_within_it(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-62: three transactions recorded at three distinct, known instants,
    only the middle one falling inside a chosen range -> items contains only
    that one transaction; total is 1.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    before, inside, after = (BASE_INSTANT + timedelta(hours=i) for i in (0, 1, 2))
    _create_transaction_at(
        client, user_headers, monkeypatch, before, wallet_id=wallet.id, category_id=category.id
    )
    inside_id = _create_transaction_at(
        client, user_headers, monkeypatch, inside, wallet_id=wallet.id, category_id=category.id
    )["id"]
    _create_transaction_at(
        client, user_headers, monkeypatch, after, wallet_id=wallet.id, category_id=category.id
    )

    range_start = inside - timedelta(minutes=1)
    range_end = inside + timedelta(minutes=1)
    response = client.get(
        TRANSACTIONS_URL,
        params={"date_from": range_start.isoformat(), "date_to": range_end.isoformat()},
        headers=user_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == inside_id


def test_a_date_range_with_only_a_start_bound_includes_every_transaction_from_it_onward(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-63 / EC-05: only date_from is named -> every transaction recorded
    at or after that instant is included, none recorded before it.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    before, boundary, after = (BASE_INSTANT + timedelta(hours=i) for i in (0, 1, 2))
    _create_transaction_at(
        client, user_headers, monkeypatch, before, wallet_id=wallet.id, category_id=category.id
    )
    boundary_id = _create_transaction_at(
        client, user_headers, monkeypatch, boundary, wallet_id=wallet.id, category_id=category.id
    )["id"]
    after_id = _create_transaction_at(
        client, user_headers, monkeypatch, after, wallet_id=wallet.id, category_id=category.id
    )["id"]

    response = client.get(
        TRANSACTIONS_URL, params={"date_from": boundary.isoformat()}, headers=user_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {item["id"] for item in body["items"]} == {boundary_id, after_id}


def test_a_date_range_with_only_an_end_bound_includes_every_transaction_up_to_it(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-64 / EC-06: only date_to is named -> every transaction recorded at
    or before that instant is included, none recorded after it.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    before, boundary, after = (BASE_INSTANT + timedelta(hours=i) for i in (0, 1, 2))
    before_id = _create_transaction_at(
        client, user_headers, monkeypatch, before, wallet_id=wallet.id, category_id=category.id
    )["id"]
    boundary_id = _create_transaction_at(
        client, user_headers, monkeypatch, boundary, wallet_id=wallet.id, category_id=category.id
    )["id"]
    _create_transaction_at(
        client, user_headers, monkeypatch, after, wallet_id=wallet.id, category_id=category.id
    )

    response = client.get(
        TRANSACTIONS_URL, params={"date_to": boundary.isoformat()}, headers=user_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {item["id"] for item in body["items"]} == {before_id, boundary_id}


def test_a_date_range_whose_start_equals_its_end_includes_the_transaction_at_that_instant(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-65 / EC-07: date_from and date_to both name the same instant ->
    the transaction recorded at exactly that instant is included — the
    range is not treated as empty or invalid.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    txn_id = _create_transaction_at(
        client,
        user_headers,
        monkeypatch,
        BASE_INSTANT,
        wallet_id=wallet.id,
        category_id=category.id,
    )["id"]

    response = client.get(
        TRANSACTIONS_URL,
        params={"date_from": BASE_INSTANT.isoformat(), "date_to": BASE_INSTANT.isoformat()},
        headers=user_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == txn_id


def test_a_date_range_whose_start_is_after_its_end_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-66 / AC-15: date_from later than date_to -> 422 VALIDATION_ERROR
    with a details.fields entry locating date_to; no items returned.
    """
    later = BASE_INSTANT + timedelta(hours=2)
    earlier = BASE_INSTANT

    response = client.get(
        TRANSACTIONS_URL,
        params={"date_from": later.isoformat(), "date_to": earlier.isoformat()},
        headers=user_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "date_to" in _fields(body)
    assert "items" not in body


def test_a_date_bound_with_no_explicit_time_zone_is_interpreted_as_utc(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-67: the same date-range boundary submitted twice — once with no
    offset, once with an explicit UTC (Z) offset for the identical instant
    -> both requests return the identical items and total (assertion
    technique per QF-13).
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    _create_transaction_at(
        client,
        user_headers,
        monkeypatch,
        BASE_INSTANT,
        wallet_id=wallet.id,
        category_id=category.id,
    )

    naive = BASE_INSTANT.replace(tzinfo=None).isoformat()
    explicit_utc = BASE_INSTANT.isoformat().replace("+00:00", "Z")

    naive_response = client.get(
        TRANSACTIONS_URL, params={"date_from": naive, "date_to": naive}, headers=user_headers
    )
    explicit_response = client.get(
        TRANSACTIONS_URL,
        params={"date_from": explicit_utc, "date_to": explicit_utc},
        headers=user_headers,
    )

    assert naive_response.status_code == 200
    assert explicit_response.status_code == 200
    assert naive_response.json() == explicit_response.json()
    assert naive_response.json()["total"] == 1


# --- TC-68/TC-69: filters combine with AND semantics ------------------------


def test_a_wallet_filter_and_a_category_filter_combine_to_narrow_to_matching_both(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-68: caller owns two wallets and two categories, with one
    transaction matching one wallet and one category, and other transactions
    matching only one of the two -> naming both filters returns only the
    transaction matching both — never one matching only the wallet or only
    the category.
    """
    wallet_1 = _make_wallet(db, user_id=normal_user.id, name="Wallet 1")
    wallet_2 = _make_wallet(db, user_id=normal_user.id, name="Wallet 2")
    category_1 = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name="Category 1"
    )
    category_2 = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name="Category 2"
    )

    matching_id = _create_transaction(
        client, user_headers, wallet_id=wallet_1.id, category_id=category_1.id
    )["id"]
    _create_transaction(client, user_headers, wallet_id=wallet_1.id, category_id=category_2.id)
    _create_transaction(client, user_headers, wallet_id=wallet_2.id, category_id=category_1.id)
    _create_transaction(client, user_headers, wallet_id=wallet_2.id, category_id=category_2.id)

    response = client.get(
        TRANSACTIONS_URL,
        params={"wallet_id": wallet_1.id, "category_id": category_1.id},
        headers=user_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == matching_id


def test_a_wallet_filter_and_a_date_range_filter_combine_to_narrow_to_matching_both(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-69: caller owns two wallets, with transactions recorded at various
    instants against each -> naming one wallet together with a date range
    that would separately match a transaction in the OTHER wallet too
    returns only the named wallet's own transaction inside the range —
    never a transaction from the other wallet, even one recorded inside the
    same range.
    """
    wallet_1 = _make_wallet(db, user_id=normal_user.id, name="Wallet 1")
    wallet_2 = _make_wallet(db, user_id=normal_user.id, name="Wallet 2")
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)

    inside_id = _create_transaction_at(
        client,
        user_headers,
        monkeypatch,
        BASE_INSTANT,
        wallet_id=wallet_1.id,
        category_id=category.id,
    )["id"]
    _create_transaction_at(
        client,
        user_headers,
        monkeypatch,
        BASE_INSTANT,
        wallet_id=wallet_2.id,
        category_id=category.id,
    )

    range_start = BASE_INSTANT - timedelta(minutes=1)
    range_end = BASE_INSTANT + timedelta(minutes=1)
    response = client.get(
        TRANSACTIONS_URL,
        params={
            "wallet_id": wallet_1.id,
            "date_from": range_start.isoformat(),
            "date_to": range_end.isoformat(),
        },
        headers=user_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == inside_id


# --- TC-70/TC-71: malformed filter values (QF-11) ---------------------------


def test_a_malformed_wallet_filter_value_matches_tc_57(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-70 / EC-09: wallet_id "not-a-real-id" -> identical outcome to
    TC-57's response (assertion technique per QF-11).
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    _create_transaction(client, user_headers, wallet_id=wallet.id, category_id=category.id)

    not_found_equivalent = _empty_wallet_filter_body(client, user_headers)

    response = client.get(
        TRANSACTIONS_URL, params={"wallet_id": MALFORMED_ID}, headers=user_headers
    )

    assert response.status_code == 200
    assert response.json() == not_found_equivalent


def test_a_malformed_category_filter_value_matches_tc_60(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-71 / EC-10: category_id "not-a-real-id" -> identical outcome to
    TC-60's response (assertion technique per QF-11).
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    _create_transaction(client, user_headers, wallet_id=wallet.id, category_id=category.id)

    not_found_equivalent = _empty_category_filter_body(client, user_headers)

    response = client.get(
        TRANSACTIONS_URL, params={"category_id": MALFORMED_ID}, headers=user_headers
    )

    assert response.status_code == 200
    assert response.json() == not_found_equivalent


# --- TC-72: the count query applies the same filter as the item query (QF-10)


def test_a_wallet_filter_scopes_the_total_to_that_wallet_not_the_callers_full_total(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-72: caller owns two wallets, one with two transactions and the
    other with three -> naming the two-transaction wallet returns total=2 —
    not 5, the caller's combined cross-wallet total — proving the count
    query applies the same wallet filter the item query does (assertion
    technique per QF-10).
    """
    wallet_1 = _make_wallet(db, user_id=normal_user.id, name="Wallet 1")
    wallet_2 = _make_wallet(db, user_id=normal_user.id, name="Wallet 2")
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    for _ in range(2):
        _create_transaction(client, user_headers, wallet_id=wallet_1.id, category_id=category.id)
    for _ in range(3):
        _create_transaction(client, user_headers, wallet_id=wallet_2.id, category_id=category.id)

    response = client.get(TRANSACTIONS_URL, params={"wallet_id": wallet_1.id}, headers=user_headers)

    assert response.status_code == 200
    assert response.json()["total"] == 2
