"""BM-US-02 — List Budgets.

One test per test case in specs/005-budget-management/test_cases.md
(TC-27..TC-51). Names state what the test proves, not what it calls.

Wallets and categories are prerequisites, not the entity under test, so they
are constructed directly against the `db` session (`_make_wallet`,
`_make_category`) — the same style `test_bm_us_01_create_budget.py` itself
uses for its own prerequisites. Budgets and transactions, however, ARE
entities this endpoint's computation depends on, so they are seeded through
the real `POST /api/v1/budgets` (BM-US-01) and `POST /api/v1/transactions`
(TM-US-01) endpoints via `_create_budget`/`_create_transaction` — mirroring
`test_wm_us_02_list_wallets.py`'s own `_create_wallet` precedent, and it is
what lets a budget's `id` be whatever the server actually assigned, which the
ordering assertions below (TC-39, TC-50) depend on.

`_create_transaction_at` monkeypatches `app.core.clock.utcnow` to an explicit
instant immediately before a single creation call, the same technique
`test_tm_us_02_list_transactions.py`'s own helper of the same name already
established; TC-46 uses it to place transactions exactly at the current
period's boundaries. TC-40 instead uses the shared `frozen_now`/`advance_clock`
fixtures from `conftest.py` — the same clock-seam technique BM-US-01 TC-23
already used — because that test needs the *budget's own period* to move to
a different month, not just a transaction's timestamp.

Decimal amounts are always compared via `Decimal(str(...))`, never as floats,
matching `test_bm_us_01_create_budget.py`'s own convention
(`Decimal(str(body["amount_limit"])) == Decimal("200.00")`).
"""

from datetime import UTC, datetime, time, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import Settings
from app.models.category import CategoryModel, CategoryType
from app.models.user import UserModel
from app.models.wallet import WalletModel

BUDGETS_URL = "/api/v1/budgets"
TRANSACTIONS_URL = "/api/v1/transactions"


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
    db: Session,
    *,
    user_id: str,
    name: str = "Dining Out",
    category_type: CategoryType = CategoryType.EXPENSE,
) -> CategoryModel:
    category = CategoryModel(user_id=user_id, name=name, type=category_type)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def _create_budget(
    client: TestClient,
    headers: dict[str, str],
    *,
    wallet_id: str,
    category_id: str,
    **overrides: object,
) -> dict[str, object]:
    """POST a budget through the real BM-US-01 endpoint and return its body.

    Asserts 201 itself so a seeding failure fails loudly at the seeding
    line, not as a confusing downstream assertion.
    """
    payload: dict[str, object] = {
        "wallet_id": wallet_id,
        "category_id": category_id,
        "amount_limit": "200.00",
    }
    payload.update(overrides)
    response = client.post(BUDGETS_URL, json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


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
    seeding line.
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
    this one call only — the created transaction's `timestamp` is always
    `app.core.clock.utcnow()` at the moment the service runs, so this is how
    a test controls it (mirrors test_tm_us_02_list_transactions.py).
    """
    monkeypatch.setattr("app.core.clock.utcnow", lambda: instant)
    return _create_transaction(
        client, headers, wallet_id=wallet_id, category_id=category_id, **overrides
    )


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


# --- TC-27: the happy path envelope, with computed progress ------------------


def test_authenticated_user_lists_every_active_budget_they_own_with_computed_progress(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-27: two current-month budgets, one with a recorded expense -> 200;
    items contains both, the one with an expense reports nonzero
    amount_spent; total is 2.
    """
    wallet_1 = _make_wallet(db, user_id=normal_user.id, name="W1")
    category_1 = _make_category(db, user_id=normal_user.id, name="C1")
    wallet_2 = _make_wallet(db, user_id=normal_user.id, name="W2")
    category_2 = _make_category(db, user_id=normal_user.id, name="C2")

    budget_1 = _create_budget(
        client, user_headers, wallet_id=wallet_1.id, category_id=category_1.id
    )
    budget_2 = _create_budget(
        client, user_headers, wallet_id=wallet_2.id, category_id=category_2.id
    )
    _create_transaction(
        client, user_headers, wallet_id=wallet_1.id, category_id=category_1.id, amount="50.00"
    )

    response = client.get(BUDGETS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    items = {item["id"]: item for item in body["items"]}
    assert set(items.keys()) == {budget_1["id"], budget_2["id"]}
    for item in items.values():
        assert set(item.keys()) == {
            "id",
            "wallet_id",
            "category_id",
            "amount_limit",
            "period",
            "amount_spent",
            "progress_percentage",
        }
    assert Decimal(str(items[budget_1["id"]]["amount_spent"])) == Decimal("50.00")


# --- TC-28: exact response shape ---------------------------------------------


def test_response_item_exposes_exactly_seven_fields_wrapped_in_paginated_envelope(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-28: top-level body exposes exactly items, total, page, page_size;
    each entry in items exposes exactly the seven documented fields — no
    more, and in particular no `user_id` and no `status`.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)
    _create_budget(client, user_headers, wallet_id=wallet.id, category_id=category.id)

    response = client.get(BUDGETS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"items", "total", "page", "page_size"}
    assert len(body["items"]) == 1
    assert set(body["items"][0].keys()) == {
        "id",
        "wallet_id",
        "category_id",
        "amount_limit",
        "period",
        "amount_spent",
        "progress_percentage",
    }


# --- TC-29: the empty case ----------------------------------------------------


def test_user_with_no_active_budgets_receives_empty_list_and_zero_total(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-29: no budgets owned -> 200, not an error; items is empty, total
    is 0.
    """
    response = client.get(BUDGETS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


# --- TC-30/TC-31: authentication ---------------------------------------------


def test_unauthenticated_or_invalid_credential_caller_is_denied_with_401(
    client: TestClient, normal_user: UserModel, settings: Settings
) -> None:
    """TC-30: no `Authorization` header, and separately an expired token,
    both -> 401 NOT_AUTHENTICATED; no items returned either way.
    """
    no_auth = client.get(BUDGETS_URL)
    assert no_auth.status_code == 401
    assert no_auth.json()["error_code"] == "NOT_AUTHENTICATED"
    assert "items" not in no_auth.json()

    expired = client.get(
        BUDGETS_URL,
        headers={"Authorization": f"Bearer {_expired_token(normal_user, settings)}"},
    )
    assert expired.status_code == 401
    assert expired.json()["error_code"] == "NOT_AUTHENTICATED"
    assert "items" not in expired.json()


def test_credentials_are_evaluated_before_any_query_parameter(client: TestClient) -> None:
    """TC-31: an out-of-range `page` from an unauthenticated caller still
    answers 401, not 422.
    """
    response = client.get(BUDGETS_URL, params={"page": 0})

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"


# --- TC-32/TC-33: pagination defaults and explicit values --------------------


def test_default_page_is_1_of_size_25_with_accurate_total(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-32: no page/page_size supplied -> page 1, page_size 25, all three
    budgets returned, total 3.
    """
    for i in range(3):
        wallet = _make_wallet(db, user_id=normal_user.id, name=f"W{i}")
        category = _make_category(db, user_id=normal_user.id, name=f"C{i}")
        _create_budget(client, user_headers, wallet_id=wallet.id, category_id=category.id)

    response = client.get(BUDGETS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 25
    assert len(body["items"]) == 3
    assert body["total"] == 3


def test_explicit_page_and_page_size_within_range_return_that_page_and_accurate_total(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-33: page=2, page_size=2 over 5 budgets -> that page's two budgets
    and total=5.
    """
    for i in range(5):
        wallet = _make_wallet(db, user_id=normal_user.id, name=f"W{i}")
        category = _make_category(db, user_id=normal_user.id, name=f"C{i}")
        _create_budget(client, user_headers, wallet_id=wallet.id, category_id=category.id)

    response = client.get(BUDGETS_URL, params={"page": 2, "page_size": 2}, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 2
    assert body["page_size"] == 2
    assert body["total"] == 5
    assert len(body["items"]) == 2


# --- TC-34/TC-35/TC-36: pagination boundary validation -----------------------


@pytest.mark.parametrize("bad_page", [0, -1, "abc"])
def test_a_non_positive_or_non_integer_page_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], bad_page: object
) -> None:
    """TC-34: page in {0, -1, "abc"} -> 422 VALIDATION_ERROR naming `page`;
    no items returned.
    """
    response = client.get(BUDGETS_URL, params={"page": bad_page}, headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "page" in _fields(body)
    assert "items" not in body


@pytest.mark.parametrize("bad_page_size", [0, -1, "abc"])
def test_a_non_positive_or_non_integer_page_size_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], bad_page_size: object
) -> None:
    """TC-35: page_size in {0, -1, "abc"} -> 422 VALIDATION_ERROR naming
    `page_size`; no items returned.
    """
    response = client.get(BUDGETS_URL, params={"page_size": bad_page_size}, headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "page_size" in _fields(body)
    assert "items" not in body


def test_a_page_size_above_the_maximum_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-36: page_size=101 -> 422 VALIDATION_ERROR naming `page_size`; the
    request is not silently capped at 100.
    """
    response = client.get(BUDGETS_URL, params={"page_size": 101}, headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "page_size" in _fields(body)


# --- TC-37/TC-38: ownership scoping, items and total alike (QF-07/QF-08) -----


def test_a_user_only_ever_sees_their_own_budgets_never_another_users(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    normal_user: UserModel,
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-37: A (two budgets) and B (three budgets) -> A's request returns
    exactly A's two budgets, none of B's three; total is 2, not 5
    (assertion technique per QF-07/QF-08).
    """
    wallet_a = _make_wallet(db, user_id=normal_user.id, name="A-Wallet")
    cat_a1 = _make_category(db, user_id=normal_user.id, name="A-1")
    cat_a2 = _make_category(db, user_id=normal_user.id, name="A-2")
    budget_a1 = _create_budget(client, user_headers, wallet_id=wallet_a.id, category_id=cat_a1.id)
    budget_a2 = _create_budget(client, user_headers, wallet_id=wallet_a.id, category_id=cat_a2.id)

    wallet_b = _make_wallet(db, user_id=admin_user.id, name="B-Wallet")
    for i in range(3):
        cat_b = _make_category(db, user_id=admin_user.id, name=f"B-{i}")
        _create_budget(client, admin_headers, wallet_id=wallet_b.id, category_id=cat_b.id)

    response = client.get(BUDGETS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {item["id"] for item in body["items"]} == {budget_a1["id"], budget_a2["id"]}


def test_reported_total_counts_only_callers_own_active_budgets_even_when_smaller(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    normal_user: UserModel,
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-38: A (no budgets) and B (four budgets) -> A's request returns an
    empty list and total 0 — not 4, and not any count reflecting B's
    budgets (assertion technique per QF-07).
    """
    wallet_b = _make_wallet(db, user_id=admin_user.id, name="B-Wallet")
    for i in range(4):
        cat_b = _make_category(db, user_id=admin_user.id, name=f"B-{i}")
        _create_budget(client, admin_headers, wallet_id=wallet_b.id, category_id=cat_b.id)

    response = client.get(BUDGETS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


# --- TC-39: stable order ------------------------------------------------------


def test_list_is_returned_in_stable_order_matching_ids_sorted_ascending(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-39: five budgets created in an order that does not already match
    ascending id order -> both of two successive requests return the same
    order, which equals the five ids sorted ascending as strings
    (assertion technique per QF-12).
    """
    ids = []
    for i in range(5):
        wallet = _make_wallet(db, user_id=normal_user.id, name=f"W{i}")
        category = _make_category(db, user_id=normal_user.id, name=f"C{i}")
        budget = _create_budget(client, user_headers, wallet_id=wallet.id, category_id=category.id)
        ids.append(budget["id"])

    expected_order = sorted(ids)
    assert expected_order != ids, (
        "fixture coincidence: creation order already matches ascending id "
        "order — this run cannot distinguish id-order from insertion-order"
    )

    first = client.get(BUDGETS_URL, headers=user_headers)
    second = client.get(BUDGETS_URL, headers=user_headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert [item["id"] for item in first.json()["items"]] == expected_order
    assert [item["id"] for item in second.json()["items"]] == expected_order


# --- TC-40: period restricted to the current calendar month (QF-10) ----------


def test_a_budget_whose_period_is_a_past_month_is_excluded_while_current_month_one_appears(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
    advance_clock,  # type: ignore[no-untyped-def]
) -> None:
    """TC-40: a budget created while the clock is frozen, then the clock
    advanced a full calendar month and a second budget created -> the list,
    requested at the later month, contains only the second budget; total
    is 1; the first budget's row still exists in storage but appears in
    neither items nor total (assertion technique per QF-10).
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)

    first_budget = _create_budget(
        client, user_headers, wallet_id=wallet.id, category_id=category.id
    )

    advance_clock(timedelta(days=32))
    second_budget = _create_budget(
        client, user_headers, wallet_id=wallet.id, category_id=category.id
    )
    assert second_budget["period"] != first_budget["period"]

    response = client.get(BUDGETS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert [item["id"] for item in body["items"]] == [second_budget["id"]]


# --- TC-41: amount spent, happy path -----------------------------------------


def test_amount_spent_sums_only_expense_transactions_against_the_budgets_own_wallet_and_category(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-41: two expense transactions against the budget's own wallet and
    category, totalling 75.50 -> that budget's amount_spent is exactly
    75.50.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)
    budget = _create_budget(client, user_headers, wallet_id=wallet.id, category_id=category.id)
    _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="30.00"
    )
    _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="45.50"
    )

    response = client.get(BUDGETS_URL, headers=user_headers)

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["id"] == budget["id"]
    assert Decimal(str(item["amount_spent"])) == Decimal("75.50")


# --- TC-42: no matching expense (QF-09) ---------------------------------------


def test_a_budget_with_no_matching_expense_transactions_reports_zero_spent_and_zero_progress(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-42: a budget with no transaction recorded at all -> still appears
    in items with amount_spent exactly "0.00" and progress_percentage
    exactly "0.00" — not omitted, not null, not an error (assertion
    technique per QF-09).
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)
    budget = _create_budget(client, user_headers, wallet_id=wallet.id, category_id=category.id)

    response = client.get(BUDGETS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id"] == budget["id"]
    assert Decimal(str(item["amount_spent"])) == Decimal("0.00")
    assert Decimal(str(item["progress_percentage"])) == Decimal("0.00")


# --- TC-43: progress may exceed 100 -------------------------------------------


def test_progress_percentage_may_exceed_100_when_spending_surpasses_the_limit(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-43: amount_limit 100.00, an expense of 150.00 -> amount_spent is
    150.00 and progress_percentage is 150.00 — not capped or clamped to
    100.00.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("1000.00"))
    category = _make_category(db, user_id=normal_user.id)
    budget = _create_budget(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount_limit="100.00"
    )
    _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="150.00"
    )

    response = client.get(BUDGETS_URL, headers=user_headers)

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["id"] == budget["id"]
    assert Decimal(str(item["amount_spent"])) == Decimal("150.00")
    assert Decimal(str(item["progress_percentage"])) == Decimal("150.00")


# --- TC-44: different wallet/category never contributes (QF-11) --------------


def test_a_transaction_against_a_different_wallet_or_category_never_contributes_to_a_budgets_spend(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-44: two budgets sharing wallet W1 but different categories C1/C2,
    an expense against W1/C1 only -> the C1 budget reflects the
    transaction; the C2 budget remains exactly "0.00" (assertion technique
    per QF-11).
    """
    wallet = _make_wallet(db, user_id=normal_user.id, name="W1")
    category_1 = _make_category(db, user_id=normal_user.id, name="C1")
    category_2 = _make_category(db, user_id=normal_user.id, name="C2")
    budget_1 = _create_budget(client, user_headers, wallet_id=wallet.id, category_id=category_1.id)
    budget_2 = _create_budget(client, user_headers, wallet_id=wallet.id, category_id=category_2.id)
    _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category_1.id, amount="20.00"
    )

    response = client.get(BUDGETS_URL, headers=user_headers)

    assert response.status_code == 200
    items = {item["id"]: item for item in response.json()["items"]}
    assert Decimal(str(items[budget_1["id"]]["amount_spent"])) == Decimal("20.00")
    assert Decimal(str(items[budget_2["id"]]["amount_spent"])) == Decimal("0.00")


# --- TC-45: income never contributes ------------------------------------------


def test_an_income_transaction_never_contributes_to_a_budgets_amount_spent(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-45: an income transaction against the same wallet/category as a
    budget -> that budget's amount_spent remains exactly "0.00".
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.INCOME)
    budget = _create_budget(client, user_headers, wallet_id=wallet.id, category_id=category.id)
    _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=category.id,
        amount="500.00",
        txn_type="INCOME",
    )

    response = client.get(BUDGETS_URL, headers=user_headers)

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["id"] == budget["id"]
    assert Decimal(str(item["amount_spent"])) == Decimal("0.00")


# --- TC-46: month-boundary transactions excluded -----------------------------


def test_a_transaction_at_the_month_boundary_is_excluded_from_amount_spent(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-46: one expense transaction timestamped at the first instant of
    the immediately preceding calendar month, and one at the first instant
    of the immediately following calendar month, both against the budget's
    own wallet/category -> amount_spent remains exactly "0.00"; neither
    boundary transaction is counted.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)
    budget = _create_budget(client, user_headers, wallet_id=wallet.id, category_id=category.id)

    period_start = frozen_now.date().replace(day=1)
    if period_start.month == 1:
        prev_month_start = period_start.replace(year=period_start.year - 1, month=12)
    else:
        prev_month_start = period_start.replace(month=period_start.month - 1)
    if period_start.month == 12:
        next_month_start = period_start.replace(year=period_start.year + 1, month=1)
    else:
        next_month_start = period_start.replace(month=period_start.month + 1)

    prev_boundary = datetime.combine(prev_month_start, time.min, tzinfo=UTC)
    next_boundary = datetime.combine(next_month_start, time.min, tzinfo=UTC)

    _create_transaction_at(
        client,
        user_headers,
        monkeypatch,
        prev_boundary,
        wallet_id=wallet.id,
        category_id=category.id,
        amount="10.00",
    )
    _create_transaction_at(
        client,
        user_headers,
        monkeypatch,
        next_boundary,
        wallet_id=wallet.id,
        category_id=category.id,
        amount="10.00",
    )
    # Restore the clock to the frozen "current" instant before listing — the
    # two creation calls above each moved it to a boundary instant.
    monkeypatch.setattr("app.core.clock.utcnow", lambda: frozen_now)

    response = client.get(BUDGETS_URL, headers=user_headers)

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["id"] == budget["id"]
    assert Decimal(str(item["amount_spent"])) == Decimal("0.00")


# --- TC-47: sharing exactly one dimension (QF-11) -----------------------------


def test_budgets_sharing_exactly_one_of_wallet_or_category_have_independently_computed_spend(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-47: a budget for W1/C1 and a second for W2/C1 (same category,
    different wallet), an expense against W1/C1 only -> the W1/C1 budget
    reflects the transaction; the W2/C1 budget remains exactly "0.00"
    (assertion technique per QF-11).
    """
    wallet_1 = _make_wallet(db, user_id=normal_user.id, name="W1")
    wallet_2 = _make_wallet(db, user_id=normal_user.id, name="W2")
    category = _make_category(db, user_id=normal_user.id, name="C1")
    budget_1 = _create_budget(client, user_headers, wallet_id=wallet_1.id, category_id=category.id)
    budget_2 = _create_budget(client, user_headers, wallet_id=wallet_2.id, category_id=category.id)
    _create_transaction(
        client, user_headers, wallet_id=wallet_1.id, category_id=category.id, amount="25.00"
    )

    response = client.get(BUDGETS_URL, headers=user_headers)

    assert response.status_code == 200
    items = {item["id"]: item for item in response.json()["items"]}
    assert Decimal(str(items[budget_1["id"]]["amount_spent"])) == Decimal("25.00")
    assert Decimal(str(items[budget_2["id"]]["amount_spent"])) == Decimal("0.00")


# --- TC-48/TC-49: boundary values that ARE accepted --------------------------


def test_a_page_beyond_the_last_available_page_returns_an_empty_list_with_accurate_total(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-48: page=5, page_size=25 over 3 budgets -> 200, not 404; items is
    empty and total is still 3.
    """
    for i in range(3):
        wallet = _make_wallet(db, user_id=normal_user.id, name=f"W{i}")
        category = _make_category(db, user_id=normal_user.id, name=f"C{i}")
        _create_budget(client, user_headers, wallet_id=wallet.id, category_id=category.id)

    response = client.get(BUDGETS_URL, params={"page": 5, "page_size": 25}, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 3


def test_a_page_size_of_exactly_100_is_accepted(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-49: page_size=100 -> 200; the request is not rejected."""
    response = client.get(BUDGETS_URL, params={"page_size": 100}, headers=user_headers)

    assert response.status_code == 200
    assert response.json()["page_size"] == 100


# --- TC-50: cross-page completeness (QF-12) -----------------------------------


def test_paging_through_every_page_returns_every_active_budget_exactly_once_in_stable_order(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-50: five budgets, page_size=2, every page requested in sequence ->
    the concatenation of all three pages' items contains every one of the
    five budgets exactly once, no duplicate and no gap, in the same order
    TC-39 establishes (assertion technique per QF-12).
    """
    ids = []
    for i in range(5):
        wallet = _make_wallet(db, user_id=normal_user.id, name=f"W{i}")
        category = _make_category(db, user_id=normal_user.id, name=f"C{i}")
        budget = _create_budget(client, user_headers, wallet_id=wallet.id, category_id=category.id)
        ids.append(budget["id"])

    expected_order = sorted(ids)
    assert expected_order != ids

    collected: list[str] = []
    for page in (1, 2, 3):
        response = client.get(
            BUDGETS_URL, params={"page": page, "page_size": 2}, headers=user_headers
        )
        assert response.status_code == 200
        collected.extend(item["id"] for item in response.json()["items"])

    assert collected == expected_order


# --- TC-51: ADMIN role carries no elevated visibility ------------------------


def test_admin_role_caller_who_also_owns_a_budget_sees_only_their_own(
    client: TestClient,
    admin_headers: dict[str, str],
    user_headers: dict[str, str],
    admin_user: UserModel,
    normal_user: UserModel,
    db: Session,
) -> None:
    """TC-51: an ADMIN-role caller with one budget, alongside another User's
    budgets -> items contains exactly the ADMIN's own budget — never the
    other User's — despite the elevated role.
    """
    admin_wallet = _make_wallet(db, user_id=admin_user.id, name="Admin-Wallet")
    admin_category = _make_category(db, user_id=admin_user.id, name="Admin-Cat")
    admin_budget = _create_budget(
        client, admin_headers, wallet_id=admin_wallet.id, category_id=admin_category.id
    )

    user_wallet = _make_wallet(db, user_id=normal_user.id, name="User-Wallet")
    user_category = _make_category(db, user_id=normal_user.id, name="User-Cat")
    _create_budget(client, user_headers, wallet_id=user_wallet.id, category_id=user_category.id)

    response = client.get(BUDGETS_URL, headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert [item["id"] for item in body["items"]] == [admin_budget["id"]]
