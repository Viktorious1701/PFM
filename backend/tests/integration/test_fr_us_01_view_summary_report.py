"""FR-US-01 — View Summary Report.

One test per test case in specs/007-financial-reporting/test_cases.md
(TC-01..TC-28). Names state what the test proves, not what it calls.

Wallets and categories are prerequisites, not the entity under test, so they
are constructed directly against the `db` session (`_make_wallet`,
`_make_category`) — the same style `test_tm_us_02_list_transactions.py` uses
for its own prerequisites. Transactions ARE data this endpoint aggregates, so
they are seeded through the real `POST /api/v1/transactions` endpoint
(TM-US-01, already implemented) via `_create_transaction`/
`_create_transaction_at`, mirroring that same file's precedent.

This endpoint's period is always the current calendar month, read from
`app.core.clock.utcnow()` at request time (plan.md A2, A12) — never from the
request. Most tests below therefore freeze the clock via the shared
`frozen_now` fixture (`conftest.py`, pinned to 2026-07-31) for the entire
test, so both the seeded transactions' timestamps (when created through the
real endpoint, unfrozen writes still land "now") and the report's own
"current month" agree deterministically (constitution TST-06) — no test
depends on the real wall-clock date. The month-boundary tests (TC-16, TC-23,
TC-24, TC-25, TC-26) instead freeze the clock explicitly to their own,
different chosen instants via `_freeze`/`_create_transaction_at`, because
their entire point is to control which calendar month a transaction and the
report's own "now" each fall into independently.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.category import CategoryModel, CategoryType
from app.models.user import UserModel
from app.models.wallet import WalletModel

REPORTS_URL = "/api/v1/reports/summary"
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
    this one call — the created transaction's `timestamp` is always
    `app.core.clock.utcnow()` at the moment the service runs, so this is how
    a test controls it (mirrors test_tm_us_02_list_transactions.py).
    """
    monkeypatch.setattr("app.core.clock.utcnow", lambda: instant)
    return _create_transaction(
        client, headers, wallet_id=wallet_id, category_id=category_id, **overrides
    )


def _freeze(monkeypatch: pytest.MonkeyPatch, instant: datetime) -> None:
    """Pin `app.core.clock.utcnow()` to `instant` from this call forward,
    independent of any transaction creation — used to control what the
    report itself treats as "now" (plan.md A2), separately from whatever
    instant a prerequisite transaction was created at.
    """
    monkeypatch.setattr("app.core.clock.utcnow", lambda: instant)


# --- TC-01: the happy-path envelope ------------------------------------------


def test_authenticated_user_retrieves_a_populated_summary_report(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-01: a wallet with one income and one expense transaction this
    month -> 200; body carries period, total_income, total_expenses,
    net_savings, and a non-empty top_categories list.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    income_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.INCOME, name="Salary"
    )
    expense_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name="Groceries"
    )
    _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=income_category.id,
        amount="1000.00",
        txn_type="INCOME",
    )
    _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=expense_category.id,
        amount="200.00",
        txn_type="EXPENSE",
    )

    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "period",
        "total_income",
        "total_expenses",
        "net_savings",
        "top_categories",
    }
    assert body["top_categories"] != []


# --- TC-02: authentication ----------------------------------------------------


def test_unauthenticated_caller_is_denied_with_401_and_nothing_computed(
    client: TestClient,
) -> None:
    """TC-02: no Authorization header -> 401 NOT_AUTHENTICATED; no report
    field returned.
    """
    response = client.get(REPORTS_URL)

    assert response.status_code == 401
    body = response.json()
    assert body["error_code"] == "NOT_AUTHENTICATED"
    assert "total_income" not in body


# --- TC-03: cross-wallet aggregation ------------------------------------------


def test_report_aggregates_expense_transactions_across_two_wallets_the_same_user_owns(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-03: two wallets, each with an expense transaction this month ->
    total_expenses equals the sum of both, not either wallet's alone.
    """
    wallet_1 = _make_wallet(db, user_id=normal_user.id, name="Wallet 1")
    wallet_2 = _make_wallet(db, user_id=normal_user.id, name="Wallet 2")
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    _create_transaction(
        client, user_headers, wallet_id=wallet_1.id, category_id=category.id, amount="100.00"
    )
    _create_transaction(
        client, user_headers, wallet_id=wallet_2.id, category_id=category.id, amount="150.00"
    )

    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    assert Decimal(response.json()["total_expenses"]) == Decimal("250.00")


# --- TC-04: cross-user isolation ----------------------------------------------


def test_another_users_wallet_and_transactions_are_excluded(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    normal_user: UserModel,
    admin_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-04: A and B each own a wallet with an expense transaction this
    month -> A's total_expenses reflects only A's own transaction
    (constitution SEC-08).
    """
    wallet_a = _make_wallet(db, user_id=normal_user.id)
    category_a = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    _create_transaction(
        client, user_headers, wallet_id=wallet_a.id, category_id=category_a.id, amount="100.00"
    )

    wallet_b = _make_wallet(db, user_id=admin_user.id)
    category_b = _make_category(db, user_id=admin_user.id, category_type=CategoryType.EXPENSE)
    _create_transaction(
        client, admin_headers, wallet_id=wallet_b.id, category_id=category_b.id, amount="999.00"
    )

    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    assert Decimal(response.json()["total_expenses"]) == Decimal("100.00")


# --- TC-05: the period is system-computed, from the frozen clock -------------


def test_reports_period_is_the_first_day_of_the_frozen_instants_calendar_month(
    client: TestClient, user_headers: dict[str, str], frozen_now: datetime
) -> None:
    """TC-05: the clock frozen to a known instant -> returned `period`
    equals the first day of that instant's calendar month.
    """
    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    expected_period = frozen_now.date().replace(day=1).isoformat()
    assert response.json()["period"] == expected_period


# --- TC-06: no transactions this month is a valid, zero-valued report --------


def test_caller_with_no_transactions_this_month_receives_a_zero_valued_report(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-06: owns a wallet but has recorded no transactions at all this
    month -> 200; every figure "0.00"; top_categories empty.
    """
    _make_wallet(db, user_id=normal_user.id)

    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total_income"] == "0.00"
    assert body["total_expenses"] == "0.00"
    assert body["net_savings"] == "0.00"
    assert body["top_categories"] == []


# --- TC-07/TC-08: income and expense totals are independent -------------------


def test_total_income_reflects_only_income_transactions(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-07: one income and one expense transaction of different amounts
    this month -> total_income equals exactly the income amount, not the
    sum of both.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    income_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.INCOME, name="Salary"
    )
    expense_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name="Groceries"
    )
    _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=income_category.id,
        amount="500.00",
        txn_type="INCOME",
    )
    _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=expense_category.id,
        amount="200.00",
        txn_type="EXPENSE",
    )

    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    assert Decimal(response.json()["total_income"]) == Decimal("500.00")


def test_total_expenses_reflects_only_expense_transactions(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-08: one income and one expense transaction of different amounts
    this month -> total_expenses equals exactly the expense amount, not the
    sum of both.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    income_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.INCOME, name="Salary"
    )
    expense_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name="Groceries"
    )
    _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=income_category.id,
        amount="500.00",
        txn_type="INCOME",
    )
    _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=expense_category.id,
        amount="200.00",
        txn_type="EXPENSE",
    )

    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    assert Decimal(response.json()["total_expenses"]) == Decimal("200.00")


# --- TC-09/TC-10/TC-11: net savings sign ---------------------------------------


def test_net_savings_is_negative_when_expenses_exceed_income(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-09 / EC-10: expenses (300.00) exceed income (100.00) this month ->
    net_savings equals total_income - total_expenses exactly, and is
    negative.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    income_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.INCOME, name="Salary"
    )
    expense_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name="Groceries"
    )
    _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=income_category.id,
        amount="100.00",
        txn_type="INCOME",
    )
    _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=expense_category.id,
        amount="300.00",
        txn_type="EXPENSE",
    )

    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    net_savings = Decimal(response.json()["net_savings"])
    assert net_savings == Decimal("-200.00")
    assert net_savings < 0


def test_net_savings_is_positive_when_income_exceeds_expenses(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-10 / EC-11: income (500.00) exceeds expenses (100.00) this month ->
    net_savings equals total_income - total_expenses exactly, and is
    positive.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    income_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.INCOME, name="Salary"
    )
    expense_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name="Groceries"
    )
    _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=income_category.id,
        amount="500.00",
        txn_type="INCOME",
    )
    _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=expense_category.id,
        amount="100.00",
        txn_type="EXPENSE",
    )

    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    net_savings = Decimal(response.json()["net_savings"])
    assert net_savings == Decimal("400.00")
    assert net_savings > 0


def test_net_savings_is_exactly_zero_when_income_equals_expenses(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-11 / EC-12: income and expenses both 250.00 this month ->
    net_savings is exactly "0.00".
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    income_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.INCOME, name="Salary"
    )
    expense_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name="Groceries"
    )
    _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=income_category.id,
        amount="250.00",
        txn_type="INCOME",
    )
    _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=expense_category.id,
        amount="250.00",
        txn_type="EXPENSE",
    )

    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    assert response.json()["net_savings"] == "0.00"


# --- TC-12: top-five selection and ordering out of six (QF-04) ----------------


def test_top_spending_categories_select_and_order_the_highest_five_of_six(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-12 / EC-05: six distinct categories with six distinct totals this
    month -> top_categories contains exactly five entries, ordered highest
    to lowest, and the sixth (lowest-total) category is absent.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    amounts = ["60.00", "50.00", "40.00", "30.00", "20.00", "10.00"]
    categories = [
        _make_category(
            db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name=f"Category {i}"
        )
        for i in range(6)
    ]
    for category, amount in zip(categories, amounts, strict=True):
        _create_transaction(
            client, user_headers, wallet_id=wallet.id, category_id=category.id, amount=amount
        )

    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    top = response.json()["top_categories"]
    assert len(top) == 5
    assert [entry["category_id"] for entry in top] == [c.id for c in categories[:5]]
    assert [entry["total_amount"] for entry in top] == amounts[:5]
    assert categories[5].id not in {entry["category_id"] for entry in top}


# --- TC-13: a category with no activity this period is omitted --------------


def test_a_category_with_no_expense_activity_this_period_is_omitted(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-13: a category with no expense transaction this month, alongside
    another category that does have one -> top_categories includes only the
    active category.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    inactive_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name="Inactive"
    )
    active_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name="Active"
    )
    _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=active_category.id, amount="75.00"
    )

    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    top = response.json()["top_categories"]
    ids = {entry["category_id"] for entry in top}
    assert active_category.id in ids
    assert inactive_category.id not in ids


# --- TC-14: deterministic tie-break (QF-03) -----------------------------------


def test_categories_tied_on_total_expense_amount_are_ordered_by_ascending_category_id(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-14 / AC-12: two categories with exactly equal current-month expense
    totals -> both appear, in ascending category_id order relative to each
    other, not merely both present in some order.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category_a = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name="Category A"
    )
    category_b = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name="Category B"
    )
    _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category_a.id, amount="40.00"
    )
    _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category_b.id, amount="40.00"
    )
    expected_order = sorted([category_a.id, category_b.id])

    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    top = response.json()["top_categories"]
    assert [entry["category_id"] for entry in top] == expected_order


# --- TC-15: each ranked category carries both id and name ---------------------


def test_each_ranked_category_carries_both_an_identifier_and_a_name(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-15: an expense transaction against a named category this month ->
    the top_categories entry carries both category_id and category_name
    matching the category.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name="Groceries"
    )
    _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="50.00"
    )

    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    top = response.json()["top_categories"]
    assert len(top) == 1
    assert top[0]["category_id"] == category.id
    assert top[0]["category_name"] == "Groceries"


# --- TC-16: a transaction outside the current month never affects the report -


def test_a_transaction_dated_in_a_prior_month_never_affects_the_report(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-16 / AC-14: an expense transaction dated in the previous calendar
    month, no transactions this month -> total_expenses "0.00",
    top_categories empty — the prior-month transaction contributes to
    nothing.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    previous_month_instant = datetime(2026, 2, 10, 12, 0, 0, tzinfo=UTC)
    current_instant = datetime(2026, 3, 15, 12, 0, 0, tzinfo=UTC)
    _create_transaction_at(
        client,
        user_headers,
        monkeypatch,
        previous_month_instant,
        wallet_id=wallet.id,
        category_id=category.id,
        amount="50.00",
    )
    _freeze(monkeypatch, current_instant)

    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total_expenses"] == "0.00"
    assert body["top_categories"] == []


# --- TC-17: exactly the documented fields, nothing else -----------------------


def test_response_exposes_exactly_the_documented_fields(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-17 / AC-15: top-level keys are exactly period, total_income,
    total_expenses, net_savings, top_categories; each top_categories entry's
    keys are exactly category_id, category_name, total_amount.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="30.00"
    )

    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "period",
        "total_income",
        "total_expenses",
        "net_savings",
        "top_categories",
    }
    assert len(body["top_categories"]) == 1
    assert set(body["top_categories"][0].keys()) == {
        "category_id",
        "category_name",
        "total_amount",
    }


# --- TC-18: a caller who owns no wallets at all (EC-01) ------------------------


def test_a_caller_who_owns_no_wallets_at_all_still_receives_a_zero_valued_report(
    client: TestClient, user_headers: dict[str, str], frozen_now: datetime
) -> None:
    """TC-18 / EC-01: no wallets owned at all -> 200, not 404; every figure
    zero-valued, top_categories empty.
    """
    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total_income"] == "0.00"
    assert body["total_expenses"] == "0.00"
    assert body["net_savings"] == "0.00"
    assert body["top_categories"] == []


# --- TC-19/TC-20: income-only / expense-only periods (QF-02) -----------------


def test_a_caller_with_only_income_transactions_this_period_reports_zero_expenses(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-19 / EC-02: only income transactions this month -> total_expenses
    exactly "0.00" (the missing-key path, not a coincidental zero sum) and
    top_categories empty.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    income_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.INCOME, name="Salary"
    )
    _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=income_category.id,
        amount="500.00",
        txn_type="INCOME",
    )

    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total_expenses"] == "0.00"
    assert body["top_categories"] == []


def test_a_caller_with_only_expense_transactions_this_period_reports_zero_income(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-20 / EC-03: only expense transactions this month -> total_income
    exactly "0.00" (the missing-key path per QF-02).
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    expense_category = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name="Groceries"
    )
    _create_transaction(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=expense_category.id,
        amount="200.00",
        txn_type="EXPENSE",
    )

    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    assert response.json()["total_income"] == "0.00"


# --- TC-21/TC-22: category-count boundaries (EC-04, EC-06) -------------------


def test_exactly_five_distinct_nonzero_expense_categories_all_appear(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-21 / EC-04: expense transactions across exactly five distinct
    categories this month, each nonzero -> top_categories contains exactly
    those five categories.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    amounts = ["10.00", "20.00", "30.00", "40.00", "50.00"]
    categories = [
        _make_category(
            db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name=f"Category {i}"
        )
        for i in range(5)
    ]
    for category, amount in zip(categories, amounts, strict=True):
        _create_transaction(
            client, user_headers, wallet_id=wallet.id, category_id=category.id, amount=amount
        )

    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    top = response.json()["top_categories"]
    assert len(top) == 5
    assert {entry["category_id"] for entry in top} == {c.id for c in categories}


def test_fewer_than_five_distinct_nonzero_expense_categories_are_never_padded(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-22 / EC-06: expense transactions across exactly two distinct
    categories this month -> top_categories contains exactly those two
    entries, never padded with placeholder or zero-valued entries.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category_1 = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name="Category 1"
    )
    category_2 = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name="Category 2"
    )
    _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category_1.id, amount="10.00"
    )
    _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category_2.id, amount="20.00"
    )

    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    top = response.json()["top_categories"]
    assert len(top) == 2
    assert {entry["category_id"] for entry in top} == {category_1.id, category_2.id}


# --- TC-23/TC-24/TC-25: month-boundary inclusion/exclusion --------------------


def test_a_transaction_at_the_first_instant_of_the_current_month_is_included(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-23 / EC-07: an expense transaction timestamped at exactly the
    first instant of the current calendar month, with the clock frozen to
    that same instant -> included in total_expenses.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    first_instant_of_month = datetime(2026, 3, 1, 0, 0, 0, tzinfo=UTC)
    _create_transaction_at(
        client,
        user_headers,
        monkeypatch,
        first_instant_of_month,
        wallet_id=wallet.id,
        category_id=category.id,
        amount="42.00",
    )

    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    assert Decimal(response.json()["total_expenses"]) == Decimal("42.00")


def test_a_transaction_at_the_first_instant_of_the_following_month_is_excluded(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-24 / EC-08: an expense transaction timestamped at exactly the
    first instant of the *following* calendar month, with the report's own
    "now" in the current month -> not included in total_expenses.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    current_instant = datetime(2026, 3, 15, 12, 0, 0, tzinfo=UTC)
    first_instant_of_following_month = datetime(2026, 4, 1, 0, 0, 0, tzinfo=UTC)
    _create_transaction_at(
        client,
        user_headers,
        monkeypatch,
        first_instant_of_following_month,
        wallet_id=wallet.id,
        category_id=category.id,
        amount="42.00",
    )
    _freeze(monkeypatch, current_instant)

    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    assert response.json()["total_expenses"] == "0.00"


def test_a_transaction_in_the_immediately_preceding_month_is_excluded(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-25 / EC-09: an expense transaction timestamped in the calendar
    month immediately before the report's own "now" -> not included in
    total_expenses.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    current_instant = datetime(2026, 3, 15, 12, 0, 0, tzinfo=UTC)
    preceding_month_instant = datetime(2026, 2, 20, 8, 0, 0, tzinfo=UTC)
    _create_transaction_at(
        client,
        user_headers,
        monkeypatch,
        preceding_month_instant,
        wallet_id=wallet.id,
        category_id=category.id,
        amount="42.00",
    )
    _freeze(monkeypatch, current_instant)

    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    assert response.json()["total_expenses"] == "0.00"


# --- TC-26: December -> January rollover (QF-01) -----------------------------


def test_the_reporting_period_rolls_over_correctly_from_december_into_january(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-26 / AC-05: the clock frozen to a late-December instant, and an
    expense transaction timestamped in the following January -> the
    reported period is the frozen instant's own December, and the
    January-dated transaction is excluded from every figure.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    december_instant = datetime(2026, 12, 20, 10, 0, 0, tzinfo=UTC)
    following_january_instant = datetime(2027, 1, 5, 9, 0, 0, tzinfo=UTC)
    _create_transaction_at(
        client,
        user_headers,
        monkeypatch,
        following_january_instant,
        wallet_id=wallet.id,
        category_id=category.id,
        amount="42.00",
    )
    _freeze(monkeypatch, december_instant)

    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["period"] == "2026-12-01"
    assert body["total_expenses"] == "0.00"
    assert body["top_categories"] == []


# --- TC-27: classic float-trap Decimal amounts sum exactly (QF-06) -----------


def test_classic_float_trap_decimal_amounts_sum_exactly_end_to_end(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-27 / constitution VL-07: expense transactions of 19.99, 0.01,
    0.20, 0.10 against the same category this month -> total_expenses and
    the category's own total_amount both equal exactly "20.30" — an exact
    string/decimal match, not an approximately-equal comparison.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id, category_type=CategoryType.EXPENSE)
    for amount in ("19.99", "0.01", "0.20", "0.10"):
        _create_transaction(
            client, user_headers, wallet_id=wallet.id, category_id=category.id, amount=amount
        )

    response = client.get(REPORTS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total_expenses"] == "20.30"
    assert len(body["top_categories"]) == 1
    assert body["top_categories"][0]["total_amount"] == "20.30"


# --- TC-28: cross-wallet aggregation and cross-user isolation with -----------
# --- maximally overlapping data (QF-05) --------------------------------------


def test_cross_wallet_aggregation_and_cross_user_isolation_with_overlapping_data(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    normal_user: UserModel,
    admin_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-28 / AC-03, AC-04: A and B each own one wallet and one category of
    the identical name, each recording one expense transaction of the
    identical amount this month -> each User's own total_expenses equals
    exactly their own single transaction's amount, never the sum of both
    (assertion technique per QF-05 — a missing ownership filter would
    double at least one of these totals).
    """
    wallet_a = _make_wallet(db, user_id=normal_user.id)
    category_a = _make_category(
        db, user_id=normal_user.id, category_type=CategoryType.EXPENSE, name="Groceries"
    )
    _create_transaction(
        client, user_headers, wallet_id=wallet_a.id, category_id=category_a.id, amount="42.00"
    )

    wallet_b = _make_wallet(db, user_id=admin_user.id)
    category_b = _make_category(
        db, user_id=admin_user.id, category_type=CategoryType.EXPENSE, name="Groceries"
    )
    _create_transaction(
        client, admin_headers, wallet_id=wallet_b.id, category_id=category_b.id, amount="42.00"
    )

    response_a = client.get(REPORTS_URL, headers=user_headers)
    response_b = client.get(REPORTS_URL, headers=admin_headers)

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    assert Decimal(response_a.json()["total_expenses"]) == Decimal("42.00")
    assert Decimal(response_b.json()["total_expenses"]) == Decimal("42.00")
