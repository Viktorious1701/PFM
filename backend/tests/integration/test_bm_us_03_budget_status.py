"""BM-US-03 — View Budget Status & Alerts.

One test per test case in specs/005-budget-management/test_cases.md
(TC-52..TC-63). Names state what the test proves, not what it calls.

Wallet/category/budget/transaction seeding reuses BM-US-02's own helpers
(`_make_wallet`, `_make_category`, `_create_budget`, `_create_transaction`)
by import — the same precedent `test_um_us_02_activate.py` already set by
importing `token_from` from `test_um_us_01_invite.py`.

TC-55/TC-56 (exact `75.00%`/`100.00%` boundaries) and TC-57/TC-58 (adjacent
`75.01%`/`99.99%` values) each construct an `amount_limit`/expense pair that
divides out to exactly the target percentage, not an approximate value
(QF-13).

TC-62's gap (plan.md A10): no `DELETE /api/v1/transactions` endpoint exists
this round — TM-US-05 (Delete a Transaction) is out of scope. The
transaction that must be removed to prove status recomputes fresh is
therefore deleted directly through the `db` session fixture, the same
established idiom `test_bm_us_02_list_budgets.py`'s own helpers use for
state no public endpoint can produce. This does not imply or require
building that endpoint.
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import audit
from app.models.budget import BudgetModel
from app.models.transaction import TransactionModel
from app.models.user import UserModel
from tests.integration.test_bm_us_02_list_budgets import (
    BUDGETS_URL,
    _create_budget,
    _create_transaction,
    _make_category,
    _make_wallet,
)


def _status_by_id(body: dict[str, object]) -> dict[str, str]:
    items = body["items"]  # type: ignore[index]
    return {item["id"]: item["status"] for item in items}  # type: ignore[index]


# --- TC-52: comfortably under NORMAL -----------------------------------------


def test_a_budget_spent_comfortably_under_the_normal_threshold_is_classified_normal(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-52: amount_limit 200.00, expense 100.00 (progress 50.00) -> 200;
    status "NORMAL".
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)
    budget = _create_budget(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount_limit="200.00"
    )
    _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="100.00"
    )

    response = client.get(BUDGETS_URL, headers=user_headers)

    assert response.status_code == 200
    assert _status_by_id(response.json())[budget["id"]] == "NORMAL"


# --- TC-53: strictly between 75% and 100% -------------------------------------


def test_a_budget_spent_strictly_between_75_and_100_percent_is_classified_warning(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-53: amount_limit 100.00, expense 85.00 (progress 85.00) -> 200;
    status "WARNING".
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)
    budget = _create_budget(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount_limit="100.00"
    )
    _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="85.00"
    )

    response = client.get(BUDGETS_URL, headers=user_headers)

    assert response.status_code == 200
    assert _status_by_id(response.json())[budget["id"]] == "WARNING"


# --- TC-54: at or above 100% --------------------------------------------------


def test_a_budget_spent_at_or_above_100_percent_is_classified_exceeded(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-54: amount_limit 100.00, expense 120.00 (progress 120.00) -> 200;
    status "EXCEEDED".
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)
    budget = _create_budget(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount_limit="100.00"
    )
    _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="120.00"
    )

    response = client.get(BUDGETS_URL, headers=user_headers)

    assert response.status_code == 200
    assert _status_by_id(response.json())[budget["id"]] == "EXCEEDED"


# --- TC-55: zero spend and the exact 75.00% boundary, both NORMAL ------------


def test_zero_spend_and_the_exact_75_boundary_are_both_classified_normal(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-55: B1 with no transaction (progress 0.00) and B2 with amount_limit
    100.00 / expense exactly 75.00 (progress exactly 75.00) -> both 200;
    both statuses "NORMAL" — B2 proves the upper bound is inclusive
    (QF-13).
    """
    wallet_1 = _make_wallet(db, user_id=normal_user.id, name="W1")
    category_1 = _make_category(db, user_id=normal_user.id, name="C1")
    budget_1 = _create_budget(
        client, user_headers, wallet_id=wallet_1.id, category_id=category_1.id
    )

    wallet_2 = _make_wallet(db, user_id=normal_user.id, name="W2")
    category_2 = _make_category(db, user_id=normal_user.id, name="C2")
    budget_2 = _create_budget(
        client,
        user_headers,
        wallet_id=wallet_2.id,
        category_id=category_2.id,
        amount_limit="100.00",
    )
    _create_transaction(
        client, user_headers, wallet_id=wallet_2.id, category_id=category_2.id, amount="75.00"
    )

    response = client.get(BUDGETS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    statuses = _status_by_id(body)
    assert statuses[budget_1["id"]] == "NORMAL"
    assert statuses[budget_2["id"]] == "NORMAL"
    items = {item["id"]: item for item in body["items"]}
    assert Decimal(str(items[budget_2["id"]]["progress_percentage"])) == Decimal("75.00")


# --- TC-56: the exact 100.00% boundary, EXCEEDED ------------------------------


def test_the_exact_100_boundary_is_classified_exceeded(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-56: amount_limit 100.00, expense exactly 100.00 (progress exactly
    100.00) -> 200; status "EXCEEDED" — the lower bound is inclusive
    (QF-13).
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)
    budget = _create_budget(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount_limit="100.00"
    )
    _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="100.00"
    )

    response = client.get(BUDGETS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert _status_by_id(body)[budget["id"]] == "EXCEEDED"
    items = {item["id"]: item for item in body["items"]}
    assert Decimal(str(items[budget["id"]]["progress_percentage"])) == Decimal("100.00")


# --- TC-57: just above the NORMAL boundary ------------------------------------


def test_a_progress_percentage_just_above_75_percent_is_classified_warning_not_normal(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-57: amount_limit 10000.00, expense 7501.00 (progress 75.01) -> 200;
    status "WARNING" — the TC-55 boundary is not widened in NORMAL's favor
    (QF-13).
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("10000.00"))
    category = _make_category(db, user_id=normal_user.id)
    budget = _create_budget(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=category.id,
        amount_limit="10000.00",
    )
    _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="7501.00"
    )

    response = client.get(BUDGETS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert _status_by_id(body)[budget["id"]] == "WARNING"
    items = {item["id"]: item for item in body["items"]}
    assert Decimal(str(items[budget["id"]]["progress_percentage"])) == Decimal("75.01")


# --- TC-58: just below the EXCEEDED boundary ----------------------------------


def test_a_progress_percentage_just_below_100_percent_is_classified_warning_not_exceeded(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-58: amount_limit 10000.00, expense 9999.00 (progress 99.99) -> 200;
    status "WARNING" — the TC-56 boundary is not widened in EXCEEDED's
    favor (QF-13).
    """
    wallet = _make_wallet(db, user_id=normal_user.id, balance=Decimal("10000.00"))
    category = _make_category(db, user_id=normal_user.id)
    budget = _create_budget(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=category.id,
        amount_limit="10000.00",
    )
    _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="9999.00"
    )

    response = client.get(BUDGETS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert _status_by_id(body)[budget["id"]] == "WARNING"
    items = {item["id"]: item for item in body["items"]}
    assert Decimal(str(items[budget["id"]]["progress_percentage"])) == Decimal("99.99")


# --- TC-59: stable NORMAL across repeated requests with no change ------------


def test_a_budget_deep_in_normal_territory_stays_normal_across_repeated_requests(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-59: progress percentage 10.00, requested twice with nothing
    changed in between -> both responses report "NORMAL" for that budget.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)
    budget = _create_budget(
        client,
        user_headers,
        wallet_id=wallet.id,
        category_id=category.id,
        amount_limit="1000.00",
    )
    _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="100.00"
    )

    first = client.get(BUDGETS_URL, headers=user_headers)
    second = client.get(BUDGETS_URL, headers=user_headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert _status_by_id(first.json())[budget["id"]] == "NORMAL"
    assert _status_by_id(second.json())[budget["id"]] == "NORMAL"


# --- TC-60: exactly eight fields, including status ----------------------------


def test_the_response_item_exposes_exactly_eight_fields_including_status(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-60: the top-level body exposes exactly items, total, page,
    page_size (unchanged from BM-US-02 TC-28); each item in items exposes
    exactly the eight documented fields, including status with a value
    from the three reachable states. Supersedes BM-US-02 TC-28's
    seven-field count for this story onward without altering TC-28's own
    text (plan.md A4; QF-15).
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)
    _create_budget(client, user_headers, wallet_id=wallet.id, category_id=category.id)

    response = client.get(BUDGETS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"items", "total", "page", "page_size"}
    assert set(body["items"][0].keys()) == {
        "id",
        "wallet_id",
        "category_id",
        "amount_limit",
        "period",
        "amount_spent",
        "progress_percentage",
        "status",
    }
    assert body["items"][0]["status"] in {"NORMAL", "WARNING", "EXCEEDED"}


# --- TC-61: every status is reachable, and budgets carries no status column --


def test_every_status_is_one_of_the_three_reachable_states_and_budgets_has_no_status_column(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-61: several budgets spanning NORMAL/WARNING/EXCEEDED -> every
    item's status is one of exactly "NORMAL"/"WARNING"/"EXCEEDED" — never
    "DRAFT" or "ARCHIVED" — and BudgetModel's own table definition carries
    no `status` column (plan.md A1, A2, A9; assertion technique per
    QF-14).
    """
    wallet_normal = _make_wallet(db, user_id=normal_user.id, name="W-normal")
    category_normal = _make_category(db, user_id=normal_user.id, name="C-normal")
    _create_budget(
        client,
        user_headers,
        wallet_id=wallet_normal.id,
        category_id=category_normal.id,
        amount_limit="200.00",
    )

    wallet_warning = _make_wallet(db, user_id=normal_user.id, name="W-warning")
    category_warning = _make_category(db, user_id=normal_user.id, name="C-warning")
    _create_budget(
        client,
        user_headers,
        wallet_id=wallet_warning.id,
        category_id=category_warning.id,
        amount_limit="100.00",
    )
    _create_transaction(
        client,
        user_headers,
        wallet_id=wallet_warning.id,
        category_id=category_warning.id,
        amount="85.00",
    )

    wallet_exceeded = _make_wallet(db, user_id=normal_user.id, name="W-exceeded")
    category_exceeded = _make_category(db, user_id=normal_user.id, name="C-exceeded")
    _create_budget(
        client,
        user_headers,
        wallet_id=wallet_exceeded.id,
        category_id=category_exceeded.id,
        amount_limit="100.00",
    )
    _create_transaction(
        client,
        user_headers,
        wallet_id=wallet_exceeded.id,
        category_id=category_exceeded.id,
        amount="150.00",
    )

    response = client.get(BUDGETS_URL, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    statuses = {item["status"] for item in body["items"]}
    assert statuses == {"NORMAL", "WARNING", "EXCEEDED"}
    assert statuses.isdisjoint({"DRAFT", "ARCHIVED"})

    column_names = {column.name for column in BudgetModel.__table__.columns}
    assert "status" not in column_names


# --- TC-62: status recomputes fresh after the underlying transaction is removed


def test_status_moves_from_exceeded_back_to_normal_once_the_causing_transaction_is_deleted(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-62: amount_limit 100.00, expense 150.00 -> first confirmed
    "EXCEEDED"; the transaction is then deleted and the budget list
    requested again -> status is now "NORMAL" (progress 0.00), computed
    fresh from the data as it now stands, not the earlier "EXCEEDED"
    value.

    plan.md A10 (gap closure): no `DELETE /api/v1/transactions` endpoint
    exists this round (TM-US-05 is out of scope), so the transaction is
    removed directly through the `db` session fixture rather than a
    public API call — this does not imply or require building that
    endpoint.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)
    budget = _create_budget(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount_limit="100.00"
    )
    transaction = _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="150.00"
    )

    before = client.get(BUDGETS_URL, headers=user_headers)
    assert before.status_code == 200
    assert _status_by_id(before.json())[budget["id"]] == "EXCEEDED"

    transaction_model = db.get(TransactionModel, transaction["id"])
    assert transaction_model is not None
    db.delete(transaction_model)
    db.commit()

    after = client.get(BUDGETS_URL, headers=user_headers)

    assert after.status_code == 200
    after_body = after.json()
    assert _status_by_id(after_body)[budget["id"]] == "NORMAL"
    items = {item["id"]: item for item in after_body["items"]}
    assert Decimal(str(items[budget["id"]]["progress_percentage"])) == Decimal("0.00")


# --- TC-63: no alert/notification/audit record as a side effect --------------


def test_no_alert_notification_or_audit_record_is_created_when_a_budget_becomes_exceeded(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-63: a budget that newly qualifies for EXCEEDED on this request ->
    200 with status "EXCEEDED"; no notification, alert, or audit-log row
    of any kind is created as a side effect. `audit.record` is this
    codebase's only audit-emission path (app/core/audit.py); no
    notification service exists to call at all (plan.md A5, A8) — spying
    on `audit.record` is therefore a complete check, not a partial one.
    """
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(audit, "record", lambda *args, **kwargs: calls.append((args, kwargs)))

    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)
    budget = _create_budget(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount_limit="100.00"
    )
    _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="150.00"
    )
    calls.clear()  # discard any audit calls from the seeding requests above

    response = client.get(BUDGETS_URL, headers=user_headers)

    assert response.status_code == 200
    assert _status_by_id(response.json())[budget["id"]] == "EXCEEDED"
    assert calls == []
