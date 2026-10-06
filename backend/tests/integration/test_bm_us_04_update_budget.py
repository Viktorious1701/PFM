"""BM-US-04 — Update a Budget.

One test per live test case in specs/005-budget-management/test_cases.md
(TC-64..TC-75, TC-77..TC-84). TC-76 is withdrawn (plan.md A8) and has no
test. Names state what the test proves, not what it calls.

Wallet/category/budget/transaction seeding reuses BM-US-02's own helpers by
import, the same precedent `test_bm_us_03_budget_status.py` set. The second
User in the ownership cases is the conftest `admin_user`, the same "other
owner" BM-US-02 TC-37 already used. Budgets have no role restriction
(plan.md A9), so an ADMIN owning a budget is an ordinary owner here.

Past-period budgets (TC-83, TC-84) are inserted directly through the `db`
session. No public endpoint can create a budget outside the current month
(BM-US-01 BR-04), so this is state only the `db` fixture can produce.

Stored state is always re-read through `_stored()`, which expires the test
session's identity map first. Otherwise a read could return the test
session's own cached copy instead of what the request actually committed
(QF-19).
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.budget import BudgetModel
from app.models.user import UserModel
from tests.integration.test_bm_us_02_list_budgets import (
    BUDGETS_URL,
    _create_budget,
    _create_transaction,
    _expired_token,
    _fields,
    _make_category,
    _make_wallet,
)

PAST_PERIOD = date(2020, 1, 1)


# --- helpers ----------------------------------------------------------------


def _url(budget_id: str) -> str:
    return f"{BUDGETS_URL}/{budget_id}"


def _stored(db: Session, budget_id: str) -> BudgetModel:
    """The committed `budgets` row, read fresh rather than from the identity map."""
    db.expire_all()
    budget = db.get(BudgetModel, budget_id)
    assert budget is not None
    return budget


def _seed_budget(
    client: TestClient,
    headers: dict[str, str],
    db: Session,
    user: UserModel,
    *,
    amount_limit: str = "200.00",
    name: str = "W1",
) -> dict[str, object]:
    """A current-month budget created through the real BM-US-01 endpoint."""
    wallet = _make_wallet(db, user_id=user.id, name=name)
    category = _make_category(db, user_id=user.id, name=f"{name}-cat")
    return _create_budget(
        client, headers, wallet_id=wallet.id, category_id=category.id, amount_limit=amount_limit
    )


def _seed_past_budget(db: Session, user: UserModel) -> BudgetModel:
    """A budget whose period is an earlier calendar month, inserted directly."""
    wallet = _make_wallet(db, user_id=user.id, name="Past-W")
    category = _make_category(db, user_id=user.id, name="Past-C")
    budget = BudgetModel(
        wallet_id=wallet.id,
        category_id=category.id,
        amount_limit=Decimal("200.00"),
        period=PAST_PERIOD,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


# --- TC-64/TC-65: the happy path ---------------------------------------------


def test_owner_updates_a_budgets_amount_limit_and_receives_the_updated_budget(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-64: current-month budget at 200.00, PATCH amount_limit 350.00 ->
    200; id, wallet_id, category_id and period unchanged; amount_limit 350.00.
    """
    budget = _seed_budget(client, user_headers, db, normal_user)

    response = client.patch(
        _url(str(budget["id"])), json={"amount_limit": "350.00"}, headers=user_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == budget["id"]
    assert body["wallet_id"] == budget["wallet_id"]
    assert body["category_id"] == budget["category_id"]
    assert body["period"] == budget["period"]
    assert Decimal(str(body["amount_limit"])) == Decimal("350.00")


def test_updating_a_budget_persists_the_new_amount_limit_on_the_same_single_row(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-65: a successful update -> the stored row carries the new
    amount_limit, and exactly one row still exists for that budget id.
    """
    budget = _seed_budget(client, user_headers, db, normal_user)

    response = client.patch(
        _url(str(budget["id"])), json={"amount_limit": "275.50"}, headers=user_headers
    )

    assert response.status_code == 200
    assert _stored(db, str(budget["id"])).amount_limit == Decimal("275.50")
    count = db.scalar(
        select(func.count()).select_from(BudgetModel).where(BudgetModel.id == budget["id"])
    )
    assert count == 1


# --- TC-66: authentication ---------------------------------------------------


def test_an_unauthenticated_or_expired_caller_is_denied_and_nothing_changes(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    settings: Settings,
) -> None:
    """TC-66: no Authorization header, and separately an expired token ->
    401 NOT_AUTHENTICATED both times; the stored amount_limit is unchanged.
    """
    budget = _seed_budget(client, user_headers, db, normal_user)

    no_auth = client.patch(_url(str(budget["id"])), json={"amount_limit": "999.00"})
    expired = client.patch(
        _url(str(budget["id"])),
        json={"amount_limit": "999.00"},
        headers={"Authorization": f"Bearer {_expired_token(normal_user, settings)}"},
    )

    assert no_auth.status_code == 401
    assert no_auth.json()["error_code"] == "NOT_AUTHENTICATED"
    assert expired.status_code == 401
    assert expired.json()["error_code"] == "NOT_AUTHENTICATED"
    assert _stored(db, str(budget["id"])).amount_limit == Decimal("200.00")


# --- TC-67/TC-68/TC-69: not found and not owned, collapsed (QF-16) -----------


def test_a_budget_id_matching_no_budget_is_rejected_with_404_budget_not_found(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-67: a well-formed id matching no budget -> 404 BUDGET_NOT_FOUND;
    the caller's own existing budget is untouched.
    """
    own = _seed_budget(client, user_headers, db, normal_user)

    response = client.patch(
        _url(str(uuid4())), json={"amount_limit": "50.00"}, headers=user_headers
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "BUDGET_NOT_FOUND"
    assert _stored(db, str(own["id"])).amount_limit == Decimal("200.00")


def test_another_users_budget_is_refused_with_a_body_identical_to_not_found(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-68: A patches B's budget -> 404, and error_code, message and
    details are all identical to TC-67's not-found-at-all body (QF-16);
    B's budget is unchanged.
    """
    b_budget = _seed_budget(client, admin_headers, db, admin_user, name="B")

    not_owned = client.patch(
        _url(str(b_budget["id"])), json={"amount_limit": "50.00"}, headers=user_headers
    )
    not_found = client.patch(
        _url(str(uuid4())), json={"amount_limit": "50.00"}, headers=user_headers
    )

    assert not_owned.status_code == 404
    assert not_owned.json()["error_code"] == "BUDGET_NOT_FOUND"
    assert not_owned.json() == not_found.json()
    assert _stored(db, str(b_budget["id"])).amount_limit == Decimal("200.00")


def test_a_malformed_budget_id_gets_the_same_404_as_a_well_formed_unknown_one(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-69: PATCH /budgets/not-a-real-id with a valid payload -> 404
    BUDGET_NOT_FOUND, identical to TC-67's body. No separate
    malformed-identifier error exists (spec EC-03).
    """
    malformed = client.patch(
        _url("not-a-real-id"), json={"amount_limit": "50.00"}, headers=user_headers
    )
    unknown = client.patch(_url(str(uuid4())), json={"amount_limit": "50.00"}, headers=user_headers)

    assert malformed.status_code == 404
    assert malformed.json()["error_code"] == "BUDGET_NOT_FOUND"
    assert malformed.json() == unknown.json()


# --- TC-70..TC-75: amount_limit validation -----------------------------------


def _assert_rejected(
    client: TestClient,
    headers: dict[str, str],
    db: Session,
    budget: dict[str, object],
    payload: dict[str, object],
) -> None:
    response = client.patch(_url(str(budget["id"])), json=payload, headers=headers)
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "amount_limit" in _fields(body)
    assert _stored(db, str(budget["id"])).amount_limit == Decimal("200.00")


def test_a_missing_amount_limit_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-70: empty body -> 422 VALIDATION_ERROR naming amount_limit;
    stored value unchanged. An absent field is a failure, never a no-op 200
    (plan.md A6).
    """
    budget = _seed_budget(client, user_headers, db, normal_user)
    _assert_rejected(client, user_headers, db, budget, {})


def test_an_amount_limit_of_exactly_zero_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-71: amount_limit 0.00 -> 422 VALIDATION_ERROR naming amount_limit;
    stored value unchanged.
    """
    budget = _seed_budget(client, user_headers, db, normal_user)
    _assert_rejected(client, user_headers, db, budget, {"amount_limit": "0.00"})


def test_a_negative_amount_limit_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-72: amount_limit -50.00 -> 422 VALIDATION_ERROR naming
    amount_limit; stored value unchanged.
    """
    budget = _seed_budget(client, user_headers, db, normal_user)
    _assert_rejected(client, user_headers, db, budget, {"amount_limit": "-50.00"})


def test_the_smallest_positive_amount_limit_is_accepted(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-73: amount_limit 0.01 -> 200; the updated amount_limit is 0.01."""
    budget = _seed_budget(client, user_headers, db, normal_user)

    response = client.patch(
        _url(str(budget["id"])), json={"amount_limit": "0.01"}, headers=user_headers
    )

    assert response.status_code == 200
    assert Decimal(str(response.json()["amount_limit"])) == Decimal("0.01")
    assert _stored(db, str(budget["id"])).amount_limit == Decimal("0.01")


def test_an_amount_limit_with_three_decimal_places_is_rejected_not_rounded(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-74: amount_limit 100.005 -> 422 naming amount_limit; the stored
    value stays 200.00, neither a rounded 100.01 nor a truncated 100.00.
    """
    budget = _seed_budget(client, user_headers, db, normal_user)
    _assert_rejected(client, user_headers, db, budget, {"amount_limit": "100.005"})


def test_an_amount_limit_wider_than_fifteen_digits_is_rejected(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-75: 14 integer digits + 2 decimals (16 digits) -> 422; stored
    value unchanged.
    """
    budget = _seed_budget(client, user_headers, db, normal_user)
    _assert_rejected(client, user_headers, db, budget, {"amount_limit": "12345678901234.00"})


# --- TC-77/TC-78/TC-79: only amount_limit changes; exact response shape ------


def test_a_successful_update_leaves_wallet_category_and_period_unchanged_in_storage(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-77: after a successful update, both the response and the stored
    row read independently through `db` carry the pre-update wallet_id,
    category_id and period (assertion technique per QF-19).
    """
    budget = _seed_budget(client, user_headers, db, normal_user)
    before = _stored(db, str(budget["id"]))
    wallet_id, category_id, period = before.wallet_id, before.category_id, before.period

    response = client.patch(
        _url(str(budget["id"])), json={"amount_limit": "123.45"}, headers=user_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["wallet_id"], body["category_id"], body["period"]) == (
        wallet_id,
        category_id,
        period.isoformat(),
    )
    after = _stored(db, str(budget["id"]))
    assert (after.wallet_id, after.category_id, after.period) == (wallet_id, category_id, period)


def test_wallet_category_and_period_submitted_alongside_the_amount_limit_are_ignored(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-78: a valid amount_limit plus a different real wallet_id, a
    different real category_id and period 2020-01-01 -> 200; the budget
    keeps its original W1/C1/period in both the response and storage.
    """
    budget = _seed_budget(client, user_headers, db, normal_user)
    other_wallet = _make_wallet(db, user_id=normal_user.id, name="W2")
    other_category = _make_category(db, user_id=normal_user.id, name="C2")

    response = client.patch(
        _url(str(budget["id"])),
        json={
            "amount_limit": "300.00",
            "wallet_id": other_wallet.id,
            "category_id": other_category.id,
            "period": "2020-01-01",
        },
        headers=user_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["wallet_id"] == budget["wallet_id"]
    assert body["category_id"] == budget["category_id"]
    assert body["period"] == budget["period"]
    stored = _stored(db, str(budget["id"]))
    assert stored.wallet_id == budget["wallet_id"]
    assert stored.category_id == budget["category_id"]
    assert stored.period.isoformat() == budget["period"]
    assert stored.amount_limit == Decimal("300.00")


def test_the_update_response_exposes_exactly_the_five_documented_fields(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-79: response keys are exactly id, wallet_id, category_id,
    amount_limit, period. No amount_spent, progress_percentage or status.
    """
    budget = _seed_budget(client, user_headers, db, normal_user)

    response = client.patch(
        _url(str(budget["id"])), json={"amount_limit": "210.00"}, headers=user_headers
    )

    assert response.status_code == 200
    assert set(response.json().keys()) == {
        "id",
        "wallet_id",
        "category_id",
        "amount_limit",
        "period",
    }


# --- TC-80/TC-81: composition with BM-US-02/03; same-value update ------------


def test_lowering_the_limit_below_spending_is_accepted_and_the_next_list_shows_exceeded(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-80: limit 200.00, expense 150.00, PATCH down to 100.00 -> 200 with
    amount_limit 100.00; the next GET /budgets shows amount_spent 150.00,
    progress_percentage 150.00 and status EXCEEDED.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)
    budget = _create_budget(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount_limit="200.00"
    )
    _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="150.00"
    )

    patched = client.patch(
        _url(str(budget["id"])), json={"amount_limit": "100.00"}, headers=user_headers
    )
    listed = client.get(BUDGETS_URL, headers=user_headers)

    assert patched.status_code == 200
    assert Decimal(str(patched.json()["amount_limit"])) == Decimal("100.00")
    assert listed.status_code == 200
    item = next(i for i in listed.json()["items"] if i["id"] == budget["id"])
    assert Decimal(str(item["amount_spent"])) == Decimal("150.00")
    assert Decimal(str(item["progress_percentage"])) == Decimal("150.00")
    assert item["status"] == "EXCEEDED"


def test_updating_to_the_value_already_held_is_an_ordinary_successful_update(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-81: limit 200.00, PATCH 200.00 -> 200 with amount_limit 200.00.
    Not a no-op error.
    """
    budget = _seed_budget(client, user_headers, db, normal_user)

    response = client.patch(
        _url(str(budget["id"])), json={"amount_limit": "200.00"}, headers=user_headers
    )

    assert response.status_code == 200
    assert Decimal(str(response.json()["amount_limit"])) == Decimal("200.00")
    assert _stored(db, str(budget["id"])).amount_limit == Decimal("200.00")


# --- TC-82/TC-83: owning budgets never grants access to someone else's -------


def test_owning_a_budget_does_not_let_a_caller_update_another_users_budget(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    normal_user: UserModel,
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-82: A owns BA, B owns BB; A patches BB -> 404 BUDGET_NOT_FOUND,
    identical to the not-found body; BB and BA both unchanged.
    """
    ba = _seed_budget(client, user_headers, db, normal_user, name="A")
    bb = _seed_budget(client, admin_headers, db, admin_user, name="B")

    response = client.patch(
        _url(str(bb["id"])), json={"amount_limit": "1.00"}, headers=user_headers
    )
    not_found = client.patch(
        _url(str(uuid4())), json={"amount_limit": "1.00"}, headers=user_headers
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "BUDGET_NOT_FOUND"
    assert response.json() == not_found.json()
    assert _stored(db, str(bb["id"])).amount_limit == Decimal("200.00")
    assert _stored(db, str(ba["id"])).amount_limit == Decimal("200.00")


def test_a_non_owner_updating_another_users_past_period_budget_gets_404(
    client: TestClient, user_headers: dict[str, str], admin_user: UserModel, db: Session
) -> None:
    """TC-83: B owns a past-period budget at 200.00; A patches it -> 404
    BUDGET_NOT_FOUND; B's stored budget is unchanged.
    """
    b_budget = _seed_past_budget(db, admin_user)

    response = client.patch(
        _url(b_budget.id), json={"amount_limit": "500.00"}, headers=user_headers
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "BUDGET_NOT_FOUND"
    stored = _stored(db, b_budget.id)
    assert stored.amount_limit == Decimal("200.00")
    assert stored.period == PAST_PERIOD


# --- TC-84: budgets are not time-boxed (plan.md A8) --------------------------


def test_an_owner_can_update_a_budget_whose_period_is_an_earlier_month(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-84: the caller's own past-period budget at 200.00, PATCH 500.00 ->
    200 with amount_limit 500.00 and the original period; storage agrees.
    Supersedes withdrawn TC-76 (plan.md A8).
    """
    budget = _seed_past_budget(db, normal_user)

    response = client.patch(_url(budget.id), json={"amount_limit": "500.00"}, headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert Decimal(str(body["amount_limit"])) == Decimal("500.00")
    assert body["period"] == PAST_PERIOD.isoformat()
    stored = _stored(db, budget.id)
    assert stored.amount_limit == Decimal("500.00")
    assert stored.period == PAST_PERIOD
