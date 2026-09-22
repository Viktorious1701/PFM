"""BM-US-01 — Create a Budget.

One test per test case in specs/005-budget-management/test_cases.md
(TC-01..TC-26). Names state what the test proves, not what it calls.

`_budget_count` mirrors the existing `select(func.count()).select_from(...)`
idiom already used by `test_wm_us_01_create_wallet.py`/
`test_cm_us_01_create_category.py` for "nothing was persisted" assertions.

Every budget-creation request needs a real wallet and a real category
already owned by the caller (spec Assumptions & Dependencies). `_make_wallet`
and `_make_category` construct those directly against the `db` session — the
same "arrange via direct model construction" style `conftest.py`'s own
`_make_user` uses for `admin_user`/`normal_user` — rather than routing
prerequisite setup through `POST /api/v1/wallets`/`POST /api/v1/categories`,
which would make every budget test also an implicit wallet/category-creation
test.

Decimal values in request bodies are sent as JSON strings, never Python
floats, matching `test_wm_us_01_create_wallet.py`'s own convention, so a test
itself never introduces the binary floating-point rounding AC-09/TC-17 exists
to rule out on the server side.

`_current_month_start()` reads `datetime.now(UTC)` rather than `date.today()`
so the unfrozen happy-path tests (TC-01/TC-02) compare against exactly the
same notion of "now" the application's own `clock.utcnow()` uses, regardless
of the test machine's local timezone.
"""

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.budget import BudgetModel
from app.models.category import CategoryModel, CategoryType
from app.models.user import UserModel
from app.models.wallet import WalletModel

BUDGETS_URL = "/api/v1/budgets"

NONEXISTENT_WALLET_ID = "00000000-0000-0000-0000-000000000000"
NONEXISTENT_CATEGORY_ID = "00000000-0000-0000-0000-000000000001"
MALFORMED_ID = "not-a-real-id"


# --- helpers ----------------------------------------------------------------


def _current_month_start() -> date:
    return datetime.now(UTC).date().replace(day=1)


def _budget_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(BudgetModel)) or 0


def _make_wallet(db: Session, *, user_id: str, name: str = "Main Checking") -> WalletModel:
    wallet = WalletModel(
        user_id=user_id, name=name, type="BANK", currency="USD", balance=Decimal("1000.00")
    )
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return wallet


def _make_category(db: Session, *, user_id: str, name: str = "Dining Out") -> CategoryModel:
    category = CategoryModel(user_id=user_id, name=name, type=CategoryType.EXPENSE)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def _valid_payload(*, wallet_id: str, category_id: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "wallet_id": wallet_id,
        "category_id": category_id,
        "amount_limit": "200.00",
    }
    payload.update(overrides)
    return payload


def _fields(body: dict[str, object]) -> list[str]:
    details = body["details"]
    assert isinstance(details, dict)
    return [f["location"][-1] for f in details["fields"]]  # type: ignore[index]


def _wallet_not_found_body(
    client: TestClient, headers: dict[str, str], category_id: str
) -> dict[str, object]:
    response = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id=NONEXISTENT_WALLET_ID, category_id=category_id),
        headers=headers,
    )
    assert response.status_code == 404
    body: dict[str, object] = response.json()
    assert body["error_code"] == "BUDGET_WALLET_NOT_FOUND"
    return body


def _category_not_found_body(
    client: TestClient, headers: dict[str, str], wallet_id: str
) -> dict[str, object]:
    response = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id=wallet_id, category_id=NONEXISTENT_CATEGORY_ID),
        headers=headers,
    )
    assert response.status_code == 404
    body: dict[str, object] = response.json()
    assert body["error_code"] == "BUDGET_CATEGORY_NOT_FOUND"
    return body


# --- TC-01/TC-02: the happy path --------------------------------------------


def test_authenticated_user_creates_a_budget_201_with_created_budget(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-01: 201; body carries id, wallet_id, category_id, amount_limit
    200.00, and period equal to the first day of the current calendar month.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)

    response = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id),
        headers=user_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body.get("id")
    assert body["wallet_id"] == wallet.id
    assert body["category_id"] == category.id
    assert Decimal(str(body["amount_limit"])) == Decimal("200.00")
    assert body["period"] == _current_month_start().isoformat()


def test_creating_a_budget_persists_exactly_one_row_with_submitted_fields_and_computed_period(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-02: exactly one `budgets` row exists carrying the submitted
    `wallet_id`, `category_id`, `amount_limit`, with `period` equal to the
    first day of the current calendar month.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)

    response = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id),
        headers=user_headers,
    )

    assert response.status_code == 201
    assert _budget_count(db) == 1
    row = db.scalars(select(BudgetModel)).one()
    assert row.wallet_id == wallet.id
    assert row.category_id == category.id
    assert row.amount_limit == Decimal("200.00")
    assert row.period == _current_month_start()


# --- TC-03: period is computed from the clock seam --------------------------


def test_created_budget_period_is_first_day_of_current_month_from_frozen_clock(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-03: with the clock frozen, the created budget's `period` equals the
    first day of the frozen instant's calendar month (assertion technique
    per QF-03).
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)

    response = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id),
        headers=user_headers,
    )

    assert response.status_code == 201
    expected_period = frozen_now.date().replace(day=1)
    assert response.json()["period"] == expected_period.isoformat()


# --- TC-04: authentication ---------------------------------------------------


def test_unauthenticated_caller_is_denied_with_401(client: TestClient, db: Session) -> None:
    """TC-04: no `Authorization` header -> 401 NOT_AUTHENTICATED; nothing
    persisted.
    """
    response = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id="irrelevant-wallet", category_id="irrelevant-category"),
    )

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"
    assert _budget_count(db) == 0


# --- TC-05: missing wallet_id -------------------------------------------------


def test_a_missing_wallet_reference_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-05: `wallet_id` absent -> 422 VALIDATION_ERROR naming `wallet_id`;
    nothing persisted.
    """
    payload = _valid_payload(wallet_id="placeholder", category_id="placeholder")
    del payload["wallet_id"]

    response = client.post(BUDGETS_URL, json=payload, headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "wallet_id" in _fields(body)
    assert _budget_count(db) == 0


# --- TC-06/TC-07: wallet ownership --------------------------------------------


def test_a_wallet_reference_matching_no_wallet_at_all_is_rejected_with_404(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-06: `wallet_id` matches no wallet in the system -> 404
    BUDGET_WALLET_NOT_FOUND; nothing persisted.
    """
    category = _make_category(db, user_id=normal_user.id)

    _wallet_not_found_body(client, user_headers, category.id)

    assert _budget_count(db) == 0


def test_a_wallet_reference_belonging_to_a_different_user_is_rejected_identically_to_not_found(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    normal_user: UserModel,
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-07: User A submits User B's `wallet_id` with A's own `category_id`
    -> 404; `error_code`, `message`, `details` identical to TC-06's response;
    nothing persisted (assertion technique per QF-01).
    """
    category_a = _make_category(db, user_id=normal_user.id)
    wallet_b = _make_wallet(db, user_id=admin_user.id)

    not_found_body = _wallet_not_found_body(client, user_headers, category_a.id)

    response = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id=wallet_b.id, category_id=category_a.id),
        headers=user_headers,
    )

    assert response.status_code == 404
    assert response.json() == not_found_body
    assert _budget_count(db) == 0


# --- TC-08/TC-09/TC-10: category presence and ownership -----------------------


def test_a_missing_category_reference_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-08: `category_id` absent -> 422 VALIDATION_ERROR naming
    `category_id`; nothing persisted.
    """
    payload = _valid_payload(wallet_id="placeholder", category_id="placeholder")
    del payload["category_id"]

    response = client.post(BUDGETS_URL, json=payload, headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "category_id" in _fields(body)
    assert _budget_count(db) == 0


def test_a_category_reference_matching_no_category_at_all_is_rejected_with_404(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-09: `category_id` matches no category in the system -> 404
    BUDGET_CATEGORY_NOT_FOUND; nothing persisted.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)

    _category_not_found_body(client, user_headers, wallet.id)

    assert _budget_count(db) == 0


def test_a_category_reference_belonging_to_a_different_user_is_rejected_identically_to_not_found(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    normal_user: UserModel,
    admin_user: UserModel,
    db: Session,
) -> None:
    """TC-10: User A submits A's own `wallet_id` with User B's `category_id`
    -> 404; `error_code`, `message`, `details` identical to TC-09's response;
    nothing persisted (assertion technique per QF-01).
    """
    wallet_a = _make_wallet(db, user_id=normal_user.id)
    category_b = _make_category(db, user_id=admin_user.id)

    not_found_body = _category_not_found_body(client, user_headers, wallet_a.id)

    response = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id=wallet_a.id, category_id=category_b.id),
        headers=user_headers,
    )

    assert response.status_code == 404
    assert response.json() == not_found_body
    assert _budget_count(db) == 0


# --- TC-11/TC-12: malformed references are refused identically ---------------


def test_a_malformed_wallet_reference_is_rejected_with_same_outcome_as_not_found(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-11: `wallet_id` `"not-a-real-id"` -> 404 BUDGET_WALLET_NOT_FOUND,
    identical to TC-06's response; nothing persisted.
    """
    category = _make_category(db, user_id=normal_user.id)
    not_found_body = _wallet_not_found_body(client, user_headers, category.id)

    response = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id=MALFORMED_ID, category_id=category.id),
        headers=user_headers,
    )

    assert response.status_code == 404
    assert response.json() == not_found_body
    assert _budget_count(db) == 0


def test_a_malformed_category_reference_is_rejected_with_same_outcome_as_not_found(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-12: `category_id` `"not-a-real-id"` -> 404 BUDGET_CATEGORY_NOT_FOUND,
    identical to TC-09's response; nothing persisted.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    not_found_body = _category_not_found_body(client, user_headers, wallet.id)

    response = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=MALFORMED_ID),
        headers=user_headers,
    )

    assert response.status_code == 404
    assert response.json() == not_found_body
    assert _budget_count(db) == 0


# --- TC-13/TC-14/TC-15: amount_limit presence and sign ------------------------


def test_a_missing_amount_limit_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-13: `amount_limit` absent -> 422 VALIDATION_ERROR naming
    `amount_limit`; nothing persisted.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)
    payload = _valid_payload(wallet_id=wallet.id, category_id=category.id)
    del payload["amount_limit"]

    response = client.post(BUDGETS_URL, json=payload, headers=user_headers)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "amount_limit" in _fields(body)
    assert _budget_count(db) == 0


def test_an_amount_limit_of_exactly_zero_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-14: `amount_limit` `"0.00"` -> 422 VALIDATION_ERROR naming
    `amount_limit`; nothing persisted.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)

    response = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id, amount_limit="0.00"),
        headers=user_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "amount_limit" in _fields(body)
    assert _budget_count(db) == 0


def test_a_negative_amount_limit_is_rejected_with_422(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-15: `amount_limit` `"-50.00"` -> 422 VALIDATION_ERROR naming
    `amount_limit`; nothing persisted.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)

    response = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id, amount_limit="-50.00"),
        headers=user_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "amount_limit" in _fields(body)
    assert _budget_count(db) == 0


# --- TC-16: smallest positive amount_limit ------------------------------------


def test_an_amount_limit_of_exactly_0_01_is_accepted(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-16: `amount_limit` `"0.01"` -> 201; created budget's
    `amount_limit` is `0.01`.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)

    response = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id, amount_limit="0.01"),
        headers=user_headers,
    )

    assert response.status_code == 201
    assert Decimal(str(response.json()["amount_limit"])) == Decimal("0.01")


# --- TC-17: over-precise amount_limit is rejected, not rounded ---------------


def test_an_amount_limit_with_three_decimal_places_is_rejected_not_rounded(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-17: `amount_limit` `"100.005"` -> 422 whose `details` names
    `amount_limit`; no `budgets` row created — so there is no rounded
    `100.01` or truncated `100.00` value to find (assertion technique per
    QF-02).
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)

    response = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id, amount_limit="100.005"),
        headers=user_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "amount_limit" in _fields(body)
    assert _budget_count(db) == 0


# --- TC-18: amount_limit exceeding 15 total digits ----------------------------


def test_an_amount_limit_exceeding_15_total_digits_is_rejected(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-18: `amount_limit` with 14 integer digits and 2 decimal places (16
    significant digits total) -> 422; nothing persisted — constitution
    VL-07's `DECIMAL(15,2)` bound is enforced by the DTO before the service
    runs.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)

    response = client.post(
        BUDGETS_URL,
        json=_valid_payload(
            wallet_id=wallet.id, category_id=category.id, amount_limit="12345678901234.12"
        ),
        headers=user_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "amount_limit" in _fields(body)
    assert _budget_count(db) == 0


# --- TC-19: a submitted period is silently ignored ----------------------------


def test_a_period_submitted_in_the_request_body_is_silently_ignored(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-19: an otherwise valid payload additionally includes
    `"period": "2020-01-01"` -> 201; created budget's `period` equals the
    first day of the frozen instant's calendar month, never `"2020-01-01"`.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)

    response = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id, period="2020-01-01"),
        headers=user_headers,
    )

    assert response.status_code == 201
    expected_period = frozen_now.date().replace(day=1)
    assert response.json()["period"] == expected_period.isoformat()
    assert response.json()["period"] != "2020-01-01"


# --- TC-20: duplicate wallet+category+period is refused -----------------------


def test_a_duplicate_budget_for_same_wallet_category_period_is_rejected_with_409(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-20: a second budget for the same wallet, category, and period ->
    409 BUDGET_ALREADY_EXISTS; exactly one `budgets` row exists for that
    combination — the original, unchanged.
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)

    first = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id, amount_limit="200.00"),
        headers=user_headers,
    )
    assert first.status_code == 201

    second = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id, amount_limit="999.00"),
        headers=user_headers,
    )

    assert second.status_code == 409
    assert second.json()["error_code"] == "BUDGET_ALREADY_EXISTS"
    assert _budget_count(db) == 1
    row = db.scalars(select(BudgetModel)).one()
    assert row.id == first.json()["id"]
    assert row.amount_limit == Decimal("200.00")


# --- TC-21/TC-22/TC-23: uniqueness scope is exactly the three-column tuple ---


def test_a_second_budget_same_category_and_period_different_wallet_is_accepted(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-21: a second budget for the same category and period against a
    different wallet -> 201; two rows exist, one per wallet, both against
    the same category and period (assertion technique per QF-04).
    """
    wallet_1 = _make_wallet(db, user_id=normal_user.id, name="Wallet One")
    wallet_2 = _make_wallet(db, user_id=normal_user.id, name="Wallet Two")
    category = _make_category(db, user_id=normal_user.id)

    first = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id=wallet_1.id, category_id=category.id),
        headers=user_headers,
    )
    assert first.status_code == 201

    second = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id=wallet_2.id, category_id=category.id),
        headers=user_headers,
    )

    assert second.status_code == 201
    assert _budget_count(db) == 2
    wallets_used = {row.wallet_id for row in db.scalars(select(BudgetModel)).all()}
    assert wallets_used == {wallet_1.id, wallet_2.id}


def test_a_second_budget_same_wallet_and_period_different_category_is_accepted(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-22: a second budget for the same wallet and period against a
    different category -> 201; two rows exist, one per category, both
    against the same wallet and period (assertion technique per QF-04).
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category_1 = _make_category(db, user_id=normal_user.id, name="Category One")
    category_2 = _make_category(db, user_id=normal_user.id, name="Category Two")

    first = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category_1.id),
        headers=user_headers,
    )
    assert first.status_code == 201

    second = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category_2.id),
        headers=user_headers,
    )

    assert second.status_code == 201
    assert _budget_count(db) == 2
    categories_used = {row.category_id for row in db.scalars(select(BudgetModel)).all()}
    assert categories_used == {category_1.id, category_2.id}


def test_a_second_budget_same_wallet_and_category_different_period_is_accepted(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
    advance_clock: Callable[[timedelta], datetime],
) -> None:
    """TC-23: a second budget for the same wallet and category, with the
    clock advanced to a later calendar month -> 201; two rows exist for the
    same wallet+category, one per period (assertion technique per QF-03,
    QF-04).
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)

    first = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id),
        headers=user_headers,
    )
    assert first.status_code == 201
    first_period = frozen_now.date().replace(day=1)

    later_instant = advance_clock(timedelta(days=32))
    second_period = later_instant.date().replace(day=1)
    assert second_period != first_period

    second = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id),
        headers=user_headers,
    )

    assert second.status_code == 201
    assert _budget_count(db) == 2
    periods_used = {row.period for row in db.scalars(select(BudgetModel)).all()}
    assert periods_used == {first_period, second_period}


# --- TC-24: exact response shape ----------------------------------------------


def test_response_exposes_exactly_the_five_documented_fields(
    client: TestClient, user_headers: dict[str, str], normal_user: UserModel, db: Session
) -> None:
    """TC-24: response body's keys are exactly id, wallet_id, category_id,
    amount_limit, period — no more, and in particular no `user_id` and no
    `status` (plan.md A7, A8, QF-05).
    """
    wallet = _make_wallet(db, user_id=normal_user.id)
    category = _make_category(db, user_id=normal_user.id)

    response = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id=wallet.id, category_id=category.id),
        headers=user_headers,
    )

    assert response.status_code == 201
    expected_keys = {"id", "wallet_id", "category_id", "amount_limit", "period"}
    body_keys = set(response.json().keys())
    assert body_keys == expected_keys
    assert "user_id" not in body_keys
    assert "status" not in body_keys


# --- TC-25: grouped validation failures ---------------------------------------


def test_multiple_validation_failures_in_one_submission_are_reported_together(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-25: `wallet_id` absent and `amount_limit` `"-50.00"` in the same
    request -> a single 422 whose `details` identifies both fields, not just
    the first one encountered.
    """
    response = client.post(
        BUDGETS_URL,
        json={"category_id": "placeholder-category", "amount_limit": "-50.00"},
        headers=user_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    fields = _fields(body)
    assert "wallet_id" in fields
    assert "amount_limit" in fields
    assert _budget_count(db) == 0


# --- TC-26: fixed check order — wallet before category ------------------------


def test_wallet_ownership_is_checked_before_category_ownership_when_both_invalid(
    client: TestClient, user_headers: dict[str, str], db: Session
) -> None:
    """TC-26: `wallet_id` matching no wallet and `category_id` matching no
    category, in the same request -> 404 BUDGET_WALLET_NOT_FOUND — never
    BUDGET_CATEGORY_NOT_FOUND, and never both (assertion technique per
    QF-06).
    """
    response = client.post(
        BUDGETS_URL,
        json=_valid_payload(wallet_id=NONEXISTENT_WALLET_ID, category_id=NONEXISTENT_CATEGORY_ID),
        headers=user_headers,
    )

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "BUDGET_WALLET_NOT_FOUND"
    assert body["error_code"] != "BUDGET_CATEGORY_NOT_FOUND"
    assert _budget_count(db) == 0
