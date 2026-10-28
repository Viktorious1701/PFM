"""FR-US-03 — Summary Report per Currency.

One test per integration test case in specs/007-financial-reporting/
test_cases.md (TC-29..TC-49). Names state what the test proves.

Same arrangement style as test_fr_us_01_view_summary_report.py: wallets and
categories are prerequisites built directly on the `db` session; transactions
are the data this endpoint aggregates, so they go through the real
`POST /api/v1/transactions`; archiving goes through the real
`DELETE /api/v1/wallets/{id}` and `DELETE /api/v1/categories/{id}`. The clock is
frozen (`frozen_now`, 2026-07-31) so "this month" is deterministic
(constitution TST-06); TC-41 freezes its own instants.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.category import CategoryModel, CategoryType
from app.models.user import UserModel
from app.models.wallet import WalletModel

REPORTS_URL = "/api/v1/reports/summary"
TRANSACTIONS_URL = "/api/v1/transactions"
WALLETS_URL = "/api/v1/wallets"
CATEGORIES_URL = "/api/v1/categories"


# --- helpers ----------------------------------------------------------------


def _make_wallet(
    db: Session, *, user_id: str, currency: str, name: str | None = None
) -> WalletModel:
    wallet = WalletModel(
        user_id=user_id,
        name=name or f"{currency} wallet",
        type="BANK",
        currency=currency,
        balance=Decimal("100000000.00"),
    )
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return wallet


def _make_category(
    db: Session,
    *,
    user_id: str,
    name: str = "Groceries",
    category_type: CategoryType = CategoryType.EXPENSE,
) -> CategoryModel:
    category = CategoryModel(user_id=user_id, name=name, type=category_type)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def _spend(
    client: TestClient,
    headers: dict[str, str],
    wallet: WalletModel,
    category: CategoryModel,
    amount: str,
    txn_type: str = "EXPENSE",
) -> None:
    """POST one transaction through the real TM-US-01 endpoint; asserts 201
    so a seeding failure fails here, not as a confusing report assertion."""
    response = client.post(
        TRANSACTIONS_URL,
        json={
            "wallet_id": wallet.id,
            "category_id": category.id,
            "amount": amount,
            "type": txn_type,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text


def _earn(
    client: TestClient,
    headers: dict[str, str],
    wallet: WalletModel,
    category: CategoryModel,
    amount: str,
) -> None:
    _spend(client, headers, wallet, category, amount, txn_type="INCOME")


def _freeze(monkeypatch: pytest.MonkeyPatch, instant: datetime) -> None:
    monkeypatch.setattr("app.core.clock.utcnow", lambda: instant)


def _report(client: TestClient, headers: dict[str, str]) -> dict[str, Any]:
    response = client.get(REPORTS_URL, headers=headers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _entry(body: dict[str, Any], currency: str) -> dict[str, Any]:
    """The one entry for `currency`; fails if absent or duplicated."""
    matches = [e for e in body["currencies"] if e["currency"] == currency]
    assert len(matches) == 1, f"expected one {currency} entry, got {body['currencies']}"
    return matches[0]


def _codes(body: dict[str, Any]) -> list[str]:
    return [e["currency"] for e in body["currencies"]]


def _all_values(node: Any) -> list[Any]:
    """Every scalar anywhere in the response, for "no value equals X" checks."""
    if isinstance(node, dict):
        return [v for value in node.values() for v in _all_values(value)]
    if isinstance(node, list):
        return [v for item in node for v in _all_values(item)]
    return [node]


# --- TC-29 ----------------------------------------------------------------


def test_figures_are_reported_separately_for_vnd_and_usd(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-29 / AC-01, FR-01, FR-03: VND and USD wallets each with income and
    an expense -> two entries, each with only its own currency's figures and
    categories."""
    vnd = _make_wallet(db, user_id=normal_user.id, currency="VND")
    usd = _make_wallet(db, user_id=normal_user.id, currency="USD")
    salary = _make_category(
        db, user_id=normal_user.id, name="Salary", category_type=CategoryType.INCOME
    )
    food = _make_category(db, user_id=normal_user.id, name="Food")
    travel = _make_category(db, user_id=normal_user.id, name="Travel")
    _earn(client, user_headers, vnd, salary, "15000000.00")
    _spend(client, user_headers, vnd, food, "100000.00")
    _earn(client, user_headers, usd, salary, "500.00")
    _spend(client, user_headers, usd, travel, "20.00")

    body = _report(client, user_headers)

    assert len(body["currencies"]) == 2
    vnd_entry = _entry(body, "VND")
    assert vnd_entry["total_income"] == "15000000.00"
    assert vnd_entry["total_expenses"] == "100000.00"
    assert vnd_entry["net_savings"] == "14900000.00"
    assert [c["category_name"] for c in vnd_entry["top_categories"]] == ["Food"]
    usd_entry = _entry(body, "USD")
    assert usd_entry["total_income"] == "500.00"
    assert usd_entry["total_expenses"] == "20.00"
    assert usd_entry["net_savings"] == "480.00"
    assert [c["category_name"] for c in usd_entry["top_categories"]] == ["Travel"]


# --- TC-30 ----------------------------------------------------------------


def test_amounts_in_different_currencies_are_never_added_together(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-30 / AC-02, FR-02, BR-02 (QF-10): 100000.00 VND + 20.00 USD -> each
    entry has its own figure, and "100020.00" appears nowhere."""
    vnd = _make_wallet(db, user_id=normal_user.id, currency="VND")
    usd = _make_wallet(db, user_id=normal_user.id, currency="USD")
    food = _make_category(db, user_id=normal_user.id, name="Food")
    travel = _make_category(db, user_id=normal_user.id, name="Travel")
    _spend(client, user_headers, vnd, food, "100000.00")
    _spend(client, user_headers, usd, travel, "20.00")

    body = _report(client, user_headers)

    assert _entry(body, "VND")["total_expenses"] == "100000.00"
    assert _entry(body, "USD")["total_expenses"] == "20.00"
    assert "100020.00" not in _all_values(body)
    assert "-100020.00" not in _all_values(body)


# --- TC-31 ----------------------------------------------------------------


def test_two_wallets_in_the_same_currency_form_one_entry(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-31 / AC-03, FR-01: two VND wallets, 30000.00 + 70000.00 -> exactly
    one VND entry with 100000.00."""
    cash = _make_wallet(db, user_id=normal_user.id, currency="VND", name="Cash")
    bank = _make_wallet(db, user_id=normal_user.id, currency="VND", name="Bank")
    food = _make_category(db, user_id=normal_user.id, name="Food")
    _spend(client, user_headers, cash, food, "30000.00")
    _spend(client, user_headers, bank, food, "70000.00")

    body = _report(client, user_headers)

    assert _codes(body) == ["VND"]
    assert body["currencies"][0]["total_expenses"] == "100000.00"


# --- TC-32 ----------------------------------------------------------------


def test_currency_entries_are_ordered_by_code_the_same_on_every_request(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-32 / AC-04, FR-06, BR-04 (QF-08): wallets created VND, EUR, USD --
    deliberately not alphabetical -> ["EUR", "USD", "VND"] on two requests."""
    food = _make_category(db, user_id=normal_user.id, name="Food")
    for currency, amount in (("VND", "50000.00"), ("EUR", "10.00"), ("USD", "20.00")):
        wallet = _make_wallet(db, user_id=normal_user.id, currency=currency)
        _spend(client, user_headers, wallet, food, amount)

    first = _report(client, user_headers)
    second = _report(client, user_headers)

    assert _codes(first) == ["EUR", "USD", "VND"]
    assert _codes(second) == ["EUR", "USD", "VND"]


# --- TC-33 ----------------------------------------------------------------


def test_each_currency_has_its_own_top_five_never_crowded_out_by_another(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-33 / AC-05, FR-04 (QF-09): six VND categories all larger than
    USD's two -> VND has its top five (sixth absent), USD keeps both of its
    own, unpadded. A global LIMIT 5 would return VND rows only."""
    vnd = _make_wallet(db, user_id=normal_user.id, currency="VND")
    usd = _make_wallet(db, user_id=normal_user.id, currency="USD")
    vnd_amounts = ["600000.00", "500000.00", "400000.00", "300000.00", "200000.00", "100000.00"]
    vnd_categories = [_make_category(db, user_id=normal_user.id, name=f"V{i}") for i in range(6)]
    for category, amount in zip(vnd_categories, vnd_amounts, strict=True):
        _spend(client, user_headers, vnd, category, amount)
    usd_big = _make_category(db, user_id=normal_user.id, name="U-big")
    usd_small = _make_category(db, user_id=normal_user.id, name="U-small")
    _spend(client, user_headers, usd, usd_small, "10.00")
    _spend(client, user_headers, usd, usd_big, "50.00")

    body = _report(client, user_headers)

    vnd_top = _entry(body, "VND")["top_categories"]
    assert [c["category_id"] for c in vnd_top] == [c.id for c in vnd_categories[:5]]
    assert [c["total_amount"] for c in vnd_top] == vnd_amounts[:5]
    assert vnd_categories[5].id not in {c["category_id"] for c in vnd_top}
    usd_top = _entry(body, "USD")["top_categories"]
    assert [c["category_id"] for c in usd_top] == [usd_big.id, usd_small.id]
    assert [c["total_amount"] for c in usd_top] == ["50.00", "10.00"]


# --- TC-34 ----------------------------------------------------------------


def test_tied_categories_within_one_currency_are_ordered_by_identifier(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-34 / AC-05, FR-04: two USD categories at exactly 40.00 -> both
    present, smaller category_id first."""
    usd = _make_wallet(db, user_id=normal_user.id, currency="USD")
    a = _make_category(db, user_id=normal_user.id, name="Tie A")
    b = _make_category(db, user_id=normal_user.id, name="Tie B")
    _spend(client, user_headers, usd, a, "40.00")
    _spend(client, user_headers, usd, b, "40.00")

    body = _report(client, user_headers)

    top = _entry(body, "USD")["top_categories"]
    assert [c["category_id"] for c in top] == sorted([a.id, b.id])


# --- TC-35 ----------------------------------------------------------------


def test_a_category_spent_in_two_currencies_ranks_in_each_with_its_own_total(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-35 / AC-06, FR-02, FR-04, VL-07 (QF-10): "Food" 0.10 + 0.20 USD and
    50000.00 VND -> "0.30" in USD, "50000.00" in VND, exact strings."""
    usd = _make_wallet(db, user_id=normal_user.id, currency="USD")
    vnd = _make_wallet(db, user_id=normal_user.id, currency="VND")
    food = _make_category(db, user_id=normal_user.id, name="Food")
    _spend(client, user_headers, usd, food, "0.10")
    _spend(client, user_headers, usd, food, "0.20")
    _spend(client, user_headers, vnd, food, "50000.00")

    body = _report(client, user_headers)

    usd_top = _entry(body, "USD")["top_categories"]
    vnd_top = _entry(body, "VND")["top_categories"]
    assert [(c["category_name"], c["total_amount"]) for c in usd_top] == [("Food", "0.30")]
    assert [(c["category_name"], c["total_amount"]) for c in vnd_top] == [("Food", "50000.00")]


# --- TC-36 ----------------------------------------------------------------


def test_a_held_currency_with_no_activity_this_month_is_a_zero_entry(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-36 / AC-07, FR-05, BR-03 (QF-07): an active EUR wallet with no
    transactions at all, beside a VND wallet with an expense -> EUR entry with
    every figure exactly "0.00" and no categories."""
    _make_wallet(db, user_id=normal_user.id, currency="EUR")
    vnd = _make_wallet(db, user_id=normal_user.id, currency="VND")
    food = _make_category(db, user_id=normal_user.id, name="Food")
    _spend(client, user_headers, vnd, food, "100000.00")

    body = _report(client, user_headers)

    assert _codes(body) == ["EUR", "VND"]
    eur = _entry(body, "EUR")
    assert eur["total_income"] == "0.00"
    assert eur["total_expenses"] == "0.00"
    assert eur["net_savings"] == "0.00"
    assert eur["top_categories"] == []


# --- TC-37 ----------------------------------------------------------------


def test_a_user_with_no_wallets_receives_an_empty_report(
    client: TestClient, user_headers: dict[str, str], frozen_now: datetime
) -> None:
    """TC-37 / AC-09, FR-07 (supersedes FR-US-01 TC-18): no wallets -> 200,
    period is the first of the current month, currencies exactly []."""
    body = _report(client, user_headers)

    assert body["period"] == frozen_now.date().replace(day=1).isoformat()
    assert body["currencies"] == []


# --- TC-38 ----------------------------------------------------------------


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer not-a-real-token"}],
    ids=["no-header", "invalid-bearer"],
)
def test_an_unauthenticated_caller_is_denied_with_401(
    client: TestClient, headers: dict[str, str]
) -> None:
    """TC-38 / AC-10, FR-08, SEC-07: no Authorization header, and an invalid
    bearer token -> 401 NOT_AUTHENTICATED, no currencies field."""
    response = client.get(REPORTS_URL, headers=headers)

    assert response.status_code == 401
    body = response.json()
    assert body["error_code"] == "NOT_AUTHENTICATED"
    assert "currencies" not in body


# --- TC-39 ----------------------------------------------------------------


def test_another_users_currency_and_amounts_never_appear(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    normal_user: UserModel,
    admin_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-39 / AC-11, FR-08, SEC-08: A has VND 100000.00; B has VND
    100000.00 against a same-named category and EUR 30.00 -> A sees only VND
    at 100000.00 (not 200000.00), no EUR."""
    a_vnd = _make_wallet(db, user_id=normal_user.id, currency="VND")
    a_food = _make_category(db, user_id=normal_user.id, name="Food")
    _spend(client, user_headers, a_vnd, a_food, "100000.00")
    b_vnd = _make_wallet(db, user_id=admin_user.id, currency="VND")
    b_eur = _make_wallet(db, user_id=admin_user.id, currency="EUR")
    b_food = _make_category(db, user_id=admin_user.id, name="Food")
    _spend(client, admin_headers, b_vnd, b_food, "100000.00")
    _spend(client, admin_headers, b_eur, b_food, "30.00")

    body = _report(client, user_headers)

    assert _codes(body) == ["VND"]
    vnd = _entry(body, "VND")
    assert vnd["total_expenses"] == "100000.00"
    assert [c["category_id"] for c in vnd["top_categories"]] == [a_food.id]


# --- TC-40 ----------------------------------------------------------------


def test_the_response_carries_exactly_the_documented_fields_at_every_level(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-40 / AC-12, FR-09, PF-03 (supersedes FR-US-01 TC-17): exact key
    sets at the top level, per currency entry, and per ranked category."""
    usd = _make_wallet(db, user_id=normal_user.id, currency="USD")
    food = _make_category(db, user_id=normal_user.id, name="Food")
    _spend(client, user_headers, usd, food, "30.00")

    body = _report(client, user_headers)

    assert set(body.keys()) == {"period", "currencies"}
    assert len(body["currencies"]) == 1
    entry = body["currencies"][0]
    assert set(entry.keys()) == {
        "currency",
        "total_income",
        "total_expenses",
        "net_savings",
        "top_categories",
    }
    assert len(entry["top_categories"]) == 1
    assert set(entry["top_categories"][0].keys()) == {
        "category_id",
        "category_name",
        "total_amount",
    }


# --- TC-41 ----------------------------------------------------------------


def test_the_period_applies_to_every_currency_alike(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-41 / AC-13, FR-08: in each of VND and USD, one expense this month
    and one last month, clock frozen mid-month -> period is the frozen month
    and each entry counts only its this-month expense."""
    vnd = _make_wallet(db, user_id=normal_user.id, currency="VND")
    usd = _make_wallet(db, user_id=normal_user.id, currency="USD")
    food = _make_category(db, user_id=normal_user.id, name="Food")
    _freeze(monkeypatch, datetime(2026, 2, 10, 9, 0, 0, tzinfo=UTC))
    _spend(client, user_headers, vnd, food, "999000.00")
    _spend(client, user_headers, usd, food, "99.00")
    _freeze(monkeypatch, datetime(2026, 3, 15, 12, 0, 0, tzinfo=UTC))
    _spend(client, user_headers, vnd, food, "100000.00")
    _spend(client, user_headers, usd, food, "20.00")

    body = _report(client, user_headers)

    assert body["period"] == "2026-03-01"
    assert _entry(body, "VND")["total_expenses"] == "100000.00"
    assert _entry(body, "USD")["total_expenses"] == "20.00"


# --- TC-42 ----------------------------------------------------------------


def test_archived_wallet_still_counts_this_month_but_archived_unused_currency_is_absent(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-42 / AC-08, FR-05, BR-03: a USD wallet spent 20.00 then archived ->
    USD entry with 20.00; an unused EUR wallet archived -> no EUR entry."""
    usd = _make_wallet(db, user_id=normal_user.id, currency="USD")
    eur = _make_wallet(db, user_id=normal_user.id, currency="EUR")
    food = _make_category(db, user_id=normal_user.id, name="Food")
    _spend(client, user_headers, usd, food, "20.00")
    for wallet in (usd, eur):
        archived = client.delete(f"{WALLETS_URL}/{wallet.id}", headers=user_headers)
        assert archived.status_code == 200

    body = _report(client, user_headers)

    assert _codes(body) == ["USD"]
    assert _entry(body, "USD")["total_expenses"] == "20.00"


# --- TC-43 ----------------------------------------------------------------


def test_a_user_with_only_archived_unused_wallets_receives_an_empty_report(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-43 / AC-09, FR-05, FR-07: the only wallet is archived and unused ->
    200, currencies exactly []."""
    wallet = _make_wallet(db, user_id=normal_user.id, currency="VND")
    archived = client.delete(f"{WALLETS_URL}/{wallet.id}", headers=user_headers)
    assert archived.status_code == 200

    body = _report(client, user_headers)

    assert body["currencies"] == []


# --- TC-44 ----------------------------------------------------------------


def test_a_currency_with_income_only_reports_zero_expenses(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-44 / EC-01, FR-03 (QF-07): USD income 500.00 only -> expenses
    "0.00", net "500.00", no categories."""
    usd = _make_wallet(db, user_id=normal_user.id, currency="USD")
    salary = _make_category(
        db, user_id=normal_user.id, name="Salary", category_type=CategoryType.INCOME
    )
    _earn(client, user_headers, usd, salary, "500.00")

    body = _report(client, user_headers)

    entry = _entry(body, "USD")
    assert entry["total_income"] == "500.00"
    assert entry["total_expenses"] == "0.00"
    assert entry["net_savings"] == "500.00"
    assert entry["top_categories"] == []


# --- TC-45 ----------------------------------------------------------------


def test_a_currency_with_expenses_only_reports_zero_income_and_negative_net_savings(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-45 / EC-02, FR-03 (QF-07): VND expense 100000.00 only -> income
    "0.00", net "-100000.00"."""
    vnd = _make_wallet(db, user_id=normal_user.id, currency="VND")
    food = _make_category(db, user_id=normal_user.id, name="Food")
    _spend(client, user_headers, vnd, food, "100000.00")

    body = _report(client, user_headers)

    entry = _entry(body, "VND")
    assert entry["total_income"] == "0.00"
    assert entry["net_savings"] == "-100000.00"


# --- TC-46 ----------------------------------------------------------------


def test_net_savings_carry_their_own_sign_per_currency(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-46 / EC-03, FR-02, FR-03: VND +200000/-50000, USD +10/-40 -> VND
    net "150000.00", USD net "-30.00", neither offset by the other."""
    vnd = _make_wallet(db, user_id=normal_user.id, currency="VND")
    usd = _make_wallet(db, user_id=normal_user.id, currency="USD")
    salary = _make_category(
        db, user_id=normal_user.id, name="Salary", category_type=CategoryType.INCOME
    )
    food = _make_category(db, user_id=normal_user.id, name="Food")
    _earn(client, user_headers, vnd, salary, "200000.00")
    _spend(client, user_headers, vnd, food, "50000.00")
    _earn(client, user_headers, usd, salary, "10.00")
    _spend(client, user_headers, usd, food, "40.00")

    body = _report(client, user_headers)

    assert _entry(body, "VND")["net_savings"] == "150000.00"
    assert _entry(body, "USD")["net_savings"] == "-30.00"


# --- TC-47 ----------------------------------------------------------------


def test_a_category_archived_after_being_spent_against_still_ranks_in_its_currency(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-47 / EC-04, FR-04: 25.00 USD against "Gifts", then "Gifts"
    archived -> still ranked in USD with "25.00"."""
    usd = _make_wallet(db, user_id=normal_user.id, currency="USD")
    gifts = _make_category(db, user_id=normal_user.id, name="Gifts")
    _spend(client, user_headers, usd, gifts, "25.00")
    archived = client.delete(f"{CATEGORIES_URL}/{gifts.id}", headers=user_headers)
    assert archived.status_code == 200

    body = _report(client, user_headers)

    top = _entry(body, "USD")["top_categories"]
    assert [(c["category_name"], c["total_amount"]) for c in top] == [("Gifts", "25.00")]


# --- TC-48 ----------------------------------------------------------------


def test_a_user_holding_only_eur_gets_exactly_one_eur_entry_and_nothing_invented(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-48 / EC-05, EC-06, FR-05: the only wallet is EUR -> exactly one
    entry, EUR; no VND (the client's default) is invented."""
    eur = _make_wallet(db, user_id=normal_user.id, currency="EUR")
    food = _make_category(db, user_id=normal_user.id, name="Food")
    _spend(client, user_headers, eur, food, "15.00")

    body = _report(client, user_headers)

    assert _codes(body) == ["EUR"]


# --- TC-49 ----------------------------------------------------------------


def test_two_currencies_with_identical_figures_stay_two_entries(
    client: TestClient,
    user_headers: dict[str, str],
    normal_user: UserModel,
    db: Session,
    frozen_now: datetime,
) -> None:
    """TC-49 / EC-07, FR-02: 100.00 USD and 100.00 EUR -> two entries, EUR
    then USD, each 100.00."""
    usd = _make_wallet(db, user_id=normal_user.id, currency="USD")
    eur = _make_wallet(db, user_id=normal_user.id, currency="EUR")
    food = _make_category(db, user_id=normal_user.id, name="Food")
    _spend(client, user_headers, usd, food, "100.00")
    _spend(client, user_headers, eur, food, "100.00")

    body = _report(client, user_headers)

    assert _codes(body) == ["EUR", "USD"]
    assert [e["total_expenses"] for e in body["currencies"]] == ["100.00", "100.00"]
