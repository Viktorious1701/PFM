"""BM-US-05 — Delete a Budget.

One test per test case in specs/005-budget-management/test_cases.md
(TC-85..TC-96). Names state what the test proves, not what it calls.

Wallet/category/budget/transaction seeding reuses BM-US-02's own helpers by
import, the same precedent test_bm_us_03_budget_status.py and
test_bm_us_04_update_budget.py already set. The second User in the
ownership cases is the conftest `admin_user`, the same "other owner"
BM-US-02 TC-37 already used -- budgets have no role restriction (plan.md
A9), so an ADMIN owning a budget is an ordinary owner here.

The past-period budget (TC-92) is inserted directly through the `db`
session, the same technique test_bm_us_04_update_budget.py's own
`_seed_past_budget` already established -- no public endpoint can create a
budget outside the current month (BM-US-01 BR-04).

Stored state is always re-read through `_stored()`, which expires the test
session's identity map first -- otherwise a read could return the test
session's own cached copy instead of what the request actually committed.
After a successful delete, `_stored()` returns `None`: this is the
assertion technique QF-21 calls for -- the response carries no body at all
(plan.md A5), so only a direct storage read proves anything was actually
removed.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.budget import BudgetModel
from app.models.category import CategoryModel
from app.models.transaction import TransactionModel
from app.models.user import UserModel
from app.models.wallet import WalletModel
from tests.integration.test_bm_us_02_list_budgets import (
    BUDGETS_URL,
    _create_budget,
    _create_transaction,
    _expired_token,
    _make_category,
    _make_wallet,
)

PAST_PERIOD = date(2020, 1, 1)


# --- helpers ----------------------------------------------------------------


def _url(budget_id: str) -> str:
    return f"{BUDGETS_URL}/{budget_id}"


def _stored(db: Session, budget_id: str) -> BudgetModel | None:
    """The committed `budgets` row, read fresh rather than from the identity
    map -- `None` once the row has genuinely been removed.
    """
    db.expire_all()
    return db.get(BudgetModel, budget_id)


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


# --- TC-85/TC-86: the happy path, and proof storage actually changed (QF-21) -


def test_an_authenticated_user_deletes_a_budget_they_own(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-85: DELETE on a budget the caller owns -> 204, with an empty body."""
    budget = _seed_budget(client, user_headers, db, normal_user)

    response = client.delete(_url(str(budget["id"])), headers=user_headers)

    assert response.status_code == 204
    assert response.content == b""


def test_deleting_a_budget_permanently_removes_its_row_from_storage(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-86 (QF-21): after a 204, a direct read of the `budgets` table for
    that id finds no row at all -- not a row carrying a deleted flag, no row
    of any kind. A router that returned 204 unconditionally, without ever
    deleting, would fool a status-only assertion; this one does not.
    """
    budget = _seed_budget(client, user_headers, db, normal_user)

    response = client.delete(_url(str(budget["id"])), headers=user_headers)

    assert response.status_code == 204
    assert _stored(db, str(budget["id"])) is None
    count = db.scalar(
        select(func.count()).select_from(BudgetModel).where(BudgetModel.id == budget["id"])
    )
    assert count == 0


# --- TC-87: authentication ----------------------------------------------------


def test_an_unauthenticated_or_expired_caller_is_denied_and_nothing_is_deleted(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    settings: Settings,
) -> None:
    """TC-87: no Authorization header, and separately an expired token ->
    401 NOT_AUTHENTICATED both times; the budget's row is unchanged in
    storage.
    """
    budget = _seed_budget(client, user_headers, db, normal_user)

    no_auth = client.delete(_url(str(budget["id"])))
    expired = client.delete(
        _url(str(budget["id"])),
        headers={"Authorization": f"Bearer {_expired_token(normal_user, settings)}"},
    )

    assert no_auth.status_code == 401
    assert no_auth.json()["error_code"] == "NOT_AUTHENTICATED"
    assert expired.status_code == 401
    assert expired.json()["error_code"] == "NOT_AUTHENTICATED"
    assert _stored(db, str(budget["id"])) is not None


# --- TC-88/TC-89/TC-90: not found and not owned, collapsed (QF-20) -----------


def test_a_budget_id_matching_no_budget_at_all_is_rejected_with_404(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-88: a well-formed id matching no budget -> 404 BUDGET_NOT_FOUND;
    the caller's own existing budget is untouched.
    """
    own = _seed_budget(client, user_headers, db, normal_user)

    response = client.delete(_url(str(uuid4())), headers=user_headers)

    assert response.status_code == 404
    assert response.json()["error_code"] == "BUDGET_NOT_FOUND"
    assert _stored(db, str(own["id"])) is not None


def test_a_budget_belonging_to_a_different_user_is_rejected_identically_to_never_existed(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-89: A deletes B's budget -> 404, and error_code, message and
    details are all identical to TC-88's not-found-at-all body (QF-20); B's
    budget is unchanged.
    """
    b_budget = _seed_budget(client, admin_headers, db, admin_user, name="B")

    not_owned = client.delete(_url(str(b_budget["id"])), headers=user_headers)
    not_found = client.delete(_url(str(uuid4())), headers=user_headers)

    assert not_owned.status_code == 404
    assert not_owned.json()["error_code"] == "BUDGET_NOT_FOUND"
    assert not_owned.json() == not_found.json()
    assert _stored(db, str(b_budget["id"])) is not None


def test_a_malformed_budget_id_gets_the_same_404_as_a_well_formed_unknown_one(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """TC-90: DELETE /budgets/not-a-real-id -> 404 BUDGET_NOT_FOUND,
    identical to TC-88's body. No separate malformed-identifier error exists
    (spec EC-01).
    """
    malformed = client.delete(_url("not-a-real-id"), headers=user_headers)
    unknown = client.delete(_url(str(uuid4())), headers=user_headers)

    assert malformed.status_code == 404
    assert malformed.json()["error_code"] == "BUDGET_NOT_FOUND"
    assert malformed.json() == unknown.json()


# --- TC-91: deleting a budget touches nothing else (QF-22) -------------------


def test_deleting_a_budget_leaves_its_wallet_category_and_transactions_unaffected(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-91 (QF-22): record the wallet, category, and a transaction tied to
    a budget's own wallet/category before deleting it, then re-read all
    three directly from storage after deletion -- every one is still
    present, unchanged. Guards against an accidental cascade (e.g. a
    careless ORM relationship) that plan.md A3 says cannot exist, but that a
    "the budget is gone" assertion alone would never catch.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, name="W1")
    category = _make_category(db, user_id=normal_user.id, name="C1")
    budget = _create_budget(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount_limit="200.00"
    )
    transaction = _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="50.00"
    )

    db.expire_all()
    wallet_before = db.get(WalletModel, wallet.id)
    category_before = db.get(CategoryModel, category.id)
    transaction_before = db.get(TransactionModel, str(transaction["id"]))
    assert wallet_before is not None
    assert category_before is not None
    assert transaction_before is not None
    wallet_snapshot = (
        wallet_before.user_id,
        wallet_before.name,
        wallet_before.type,
        wallet_before.currency,
        wallet_before.balance,
    )
    category_snapshot = (category_before.user_id, category_before.name, category_before.type)
    transaction_snapshot = (
        transaction_before.wallet_id,
        transaction_before.category_id,
        transaction_before.amount,
        transaction_before.type,
        transaction_before.timestamp,
        transaction_before.note,
    )

    response = client.delete(_url(str(budget["id"])), headers=user_headers)

    assert response.status_code == 204
    db.expire_all()
    wallet_after = db.get(WalletModel, wallet.id)
    category_after = db.get(CategoryModel, category.id)
    transaction_after = db.get(TransactionModel, str(transaction["id"]))
    assert wallet_after is not None
    assert category_after is not None
    assert transaction_after is not None
    assert (
        wallet_after.user_id,
        wallet_after.name,
        wallet_after.type,
        wallet_after.currency,
        wallet_after.balance,
    ) == wallet_snapshot
    assert (category_after.user_id, category_after.name, category_after.type) == category_snapshot
    assert (
        transaction_after.wallet_id,
        transaction_after.category_id,
        transaction_after.amount,
        transaction_after.type,
        transaction_after.timestamp,
        transaction_after.note,
    ) == transaction_snapshot
    assert _stored(db, str(budget["id"])) is None


# --- TC-92: budgets are not time-boxed (plan.md A1) --------------------------


def test_a_budget_whose_period_is_an_earlier_month_is_deleted_like_any_other(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-92: a budget whose period is an earlier calendar month, inserted
    directly since no API path creates one outside the current month
    (BM-US-01 BR-04) -- deleted the same way as a current-month budget
    (plan.md A1, carried forward from BM-US-04's own settled reading).
    """
    budget = _seed_past_budget(db, normal_user)

    response = client.delete(_url(budget.id), headers=user_headers)

    assert response.status_code == 204
    assert _stored(db, budget.id) is None


# --- TC-93/TC-94: status and spending history never gate a deletion ---------


def test_a_budget_currently_classified_exceeded_is_deleted_like_any_other(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-93 (EC-03): a budget whose recorded spending already exceeds its
    amount limit, confirmed `status` `"EXCEEDED"` via GET /budgets before
    deletion -- deleted the same way as any other budget. Status is a
    read-time computation, never a stored precondition that could block a
    deletion.
    """
    wallet = _make_wallet(db, user_id=normal_user.id, name="Exceeded-W")
    category = _make_category(db, user_id=normal_user.id, name="Exceeded-C")
    budget = _create_budget(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount_limit="50.00"
    )
    _create_transaction(
        client, user_headers, wallet_id=wallet.id, category_id=category.id, amount="100.00"
    )
    listed = client.get(BUDGETS_URL, headers=user_headers)
    item = next(i for i in listed.json()["items"] if i["id"] == budget["id"])
    assert item["status"] == "EXCEEDED"

    response = client.delete(_url(str(budget["id"])), headers=user_headers)

    assert response.status_code == 204
    assert _stored(db, str(budget["id"])) is None


def test_a_budget_with_no_transaction_recorded_against_it_is_deleted_normally(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-94 (EC-04): a budget against which no transaction of any kind has
    ever been recorded -- deleted the same way as a budget with an active
    spending history.
    """
    budget = _seed_budget(client, user_headers, db, normal_user, name="NoTxn")
    count = db.scalar(
        select(func.count())
        .select_from(TransactionModel)
        .where(TransactionModel.wallet_id == budget["wallet_id"])
    )
    assert count == 0

    response = client.delete(_url(str(budget["id"])), headers=user_headers)

    assert response.status_code == 204
    assert _stored(db, str(budget["id"])) is None


# --- TC-95: a repeated deletion is refused identically to never-existed (QF-23)


def test_deleting_a_budget_a_second_time_is_rejected_identically_to_never_existed(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-95 (QF-23): delete a budget (204), then delete the same id again
    -> the second response is 404, with error_code, message, and details
    identical to a never-existed id's response -- not a distinct
    "already deleted" error (plan.md A8).
    """
    budget = _seed_budget(client, user_headers, db, normal_user)

    first = client.delete(_url(str(budget["id"])), headers=user_headers)
    second = client.delete(_url(str(budget["id"])), headers=user_headers)
    never_existed = client.delete(_url(str(uuid4())), headers=user_headers)

    assert first.status_code == 204
    assert second.status_code == 404
    assert second.json()["error_code"] == "BUDGET_NOT_FOUND"
    assert second.json() == never_existed.json()


# --- TC-96: owning a budget never grants access to someone else's -----------


def test_a_caller_who_owns_a_different_budget_cannot_delete_another_users_budget(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    normal_user: UserModel,
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-96 (EC-02): A owns BA, B owns BB; A deletes BB -> 404
    BUDGET_NOT_FOUND, identical to TC-88/TC-89's responses; BB is unchanged,
    and A's own BA is also unaffected.
    """
    ba = _seed_budget(client, user_headers, db, normal_user, name="A")
    bb = _seed_budget(client, admin_headers, db, admin_user, name="B")

    response = client.delete(_url(str(bb["id"])), headers=user_headers)
    not_found = client.delete(_url(str(uuid4())), headers=user_headers)

    assert response.status_code == 404
    assert response.json()["error_code"] == "BUDGET_NOT_FOUND"
    assert response.json() == not_found.json()
    assert _stored(db, str(bb["id"])) is not None
    assert _stored(db, str(ba["id"])) is not None
