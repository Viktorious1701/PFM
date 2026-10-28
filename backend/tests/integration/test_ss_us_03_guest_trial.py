"""SS-US-03 — Guest trial.

One test per test case in specs/002-system-security/test_cases.md (TC-58..TC-85).
Names state what the test proves, not what it calls.

Time (test_cases QF-03): PyJWT checks a token's `exp` against the real wall
clock, not the `app.core.clock` seam. So these tests freeze the seam *near real
time* (`trial_clock`), and every trial-end boundary is moved on the seam or on
the stored `expires_at` — never on the token. The token's own lifetime is
asserted separately by decoding it (TC-62).
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.errors import InvalidCredentialsError, ValidationError
from app.models.budget import BudgetModel
from app.models.category import CategoryModel
from app.models.invitation import InvitationModel
from app.models.transaction import TransactionModel
from app.models.user import UserModel, UserRole, UserStatus
from app.models.wallet import WalletModel
from app.services import auth_service, invitation_service
from app.services.email.sender import RecordingEmailSender

GUEST_URL = "/api/v1/auth/guest"
LOGIN_URL = "/api/v1/auth/login"
LOGOUT_URL = "/api/v1/auth/logout"
WALLETS_URL = "/api/v1/wallets"
CATEGORIES_URL = "/api/v1/categories"
TRANSACTIONS_URL = "/api/v1/transactions"
BUDGETS_URL = "/api/v1/budgets"
REPORT_URL = "/api/v1/reports/summary"
INVITE_URL = "/api/v1/users/invite"
USERS_URL = "/api/v1/users"

TRIAL = timedelta(days=7)
PLACEHOLDER = re.compile(
    r"^guest-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}@guest\.invalid$"
)
# auth_service's timing-parity dummy password — public in the source (plan.md F1).
DUMMY_PASSWORD = "dummy-placeholder-for-timing-parity"


# --- Helpers ------------------------------------------------------------------


@dataclass
class TrialClock:
    """The clock seam, frozen near real time (QF-03), movable per test."""

    start: datetime
    _monkeypatch: pytest.MonkeyPatch

    def set(self, moment: datetime) -> None:
        self._monkeypatch.setattr("app.core.clock.utcnow", lambda: moment)


@pytest.fixture
def trial_clock(monkeypatch: pytest.MonkeyPatch) -> TrialClock:
    start = datetime.now(UTC).replace(microsecond=0)
    clock = TrialClock(start, monkeypatch)
    clock.set(start)
    return clock


@dataclass
class Guest:
    id: str
    token: str
    body: dict[str, Any]

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


def _start(client: TestClient, settings: Settings) -> Guest:
    response = client.post(GUEST_URL)
    assert response.status_code == 201, response.text
    body = response.json()
    claims = jwt.decode(
        body["access_token"], settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    return Guest(id=claims["sub"], token=body["access_token"], body=body)


def _row(db: Session, user_id: str) -> UserModel | None:
    db.expire_all()
    return db.get(UserModel, user_id)


def _end_trial(db: Session, guest: Guest, moment: datetime) -> None:
    """Move a guest's stored trial end — the authoritative check (plan.md A5)."""
    row = _row(db, guest.id)
    assert row is not None
    row.expires_at = moment
    db.commit()


def _count(db: Session, model: type, *where: Any) -> int:
    db.expire_all()
    return db.scalar(select(func.count()).select_from(model).where(*where)) or 0


def _owned_counts(db: Session, user_id: str) -> dict[str, int]:
    wallet_ids = select(WalletModel.id).where(WalletModel.user_id == user_id)
    category_ids = select(CategoryModel.id).where(CategoryModel.user_id == user_id)
    return {
        "users": _count(db, UserModel, UserModel.id == user_id),
        "wallets": _count(db, WalletModel, WalletModel.user_id == user_id),
        "categories": _count(db, CategoryModel, CategoryModel.user_id == user_id),
        "budgets": _count(db, BudgetModel, BudgetModel.wallet_id.in_(wallet_ids)),
        "transactions": _count(db, TransactionModel, TransactionModel.wallet_id.in_(wallet_ids))
        + _count(
            db,
            TransactionModel,
            TransactionModel.category_id.in_(category_ids),
            TransactionModel.wallet_id.not_in(wallet_ids),
        ),
    }


def _only(client: TestClient, url: str, headers: dict[str, str]) -> dict[str, Any]:
    response = client.get(url, headers=headers)
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert len(items) == 1, items
    item: dict[str, Any] = items[0]
    return item


def _add_owned_data(client: TestClient, headers: dict[str, str], tag: str) -> dict[str, str]:
    """A wallet, an EXPENSE category, a budget and an expense — through the API."""
    wallet = client.post(
        WALLETS_URL,
        headers=headers,
        json={
            "name": f"{tag} wallet",
            "type": "Bank",
            "currency": "VND",
            "initial_balance": "1000.00",
        },
    )
    assert wallet.status_code == 201, wallet.text
    category = client.post(
        CATEGORIES_URL, headers=headers, json={"name": f"{tag} category", "type": "EXPENSE"}
    )
    assert category.status_code == 201, category.text
    budget = client.post(
        BUDGETS_URL,
        headers=headers,
        json={
            "wallet_id": wallet.json()["id"],
            "category_id": category.json()["id"],
            "amount_limit": "500.00",
        },
    )
    assert budget.status_code == 201, budget.text
    transaction = client.post(
        TRANSACTIONS_URL,
        headers=headers,
        json={
            "wallet_id": wallet.json()["id"],
            "category_id": category.json()["id"],
            "amount": "100.00",
            "type": "EXPENSE",
            "note": f"{tag} expense",
        },
    )
    assert transaction.status_code == 201, transaction.text
    return {
        "wallet": wallet.json()["id"],
        "category": category.json()["id"],
        "budget": budget.json()["id"],
        "transaction": transaction.json()["id"],
    }


def _purge(db: Session) -> Any:
    """Run the purge directly and commit, as startup and the CLI do (plan.md A9)."""
    from app.services import guest_service

    result = guest_service.purge_expired(db)
    db.commit()
    return result


def _audit_events(caplog: pytest.LogCaptureFixture, action: str) -> list[dict[str, Any]]:
    """The structured event dict `audit.record()` passes as its third log arg."""
    events = []
    for record in caplog.records:
        if record.name == "app.audit" and isinstance(record.args, tuple):
            event = record.args[2]
            if isinstance(event, dict) and event.get("action") == action:
                events.append(event)
    return events


@pytest.fixture
def cli_db(
    db_session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> sessionmaker[Session]:
    """Point the CLI's SessionLocal at the same database the app uses."""
    monkeypatch.setattr("app.cli.SessionLocal", db_session_factory)
    return db_session_factory


# --- AC-01, AC-07: the trial and its account --------------------------------


def test_starting_a_trial_needs_no_credentials_and_returns_a_guest_session(
    client: TestClient, trial_clock: TrialClock
) -> None:
    """TC-58: no Authorization header, no body -> 201 with exactly the five
    session fields, a 7-day trial end carrying a UTC offset, and nothing that
    could be an email, a password or a hash.
    """
    response = client.post(GUEST_URL)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"access_token", "token_type", "expires_in", "role", "expires_at"}
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 604800
    assert body["role"] == "GUEST"
    expires_at = datetime.fromisoformat(body["expires_at"])
    assert expires_at.utcoffset() == timedelta(0)
    assert expires_at == trial_clock.start + TRIAL
    assert "guest.invalid" not in response.text
    assert "password" not in response.text
    assert "hash" not in response.text


def test_guest_account_has_placeholder_address_no_password_and_seven_day_end(
    client: TestClient, db: Session, settings: Settings, trial_clock: TrialClock
) -> None:
    """TC-59: ACTIVE, GUEST, `guest-<uuid4>@guest.invalid`, no password hash,
    no full name, trial end exactly the frozen time plus 7 days.
    """
    guest = _start(client, settings)

    row = _row(db, guest.id)
    assert row is not None
    assert row.status is UserStatus.ACTIVE
    assert row.role is UserRole.GUEST
    assert PLACEHOLDER.match(row.email), row.email
    assert row.password_hash is None
    assert row.full_name is None
    assert row.expires_at is not None
    assert row.expires_at.replace(tzinfo=UTC) == trial_clock.start + TRIAL


# --- AC-02: the example ------------------------------------------------------


def test_new_trial_holds_exactly_one_example_wallet_with_one_example_expense(
    client: TestClient, settings: Settings
) -> None:
    """TC-60: one wallet "Example wallet", VND, 450000.00; one category "Food",
    EXPENSE; one transaction 50000.00 EXPENSE "Example: lunch" against them;
    no budgets.
    """
    guest = _start(client, settings)

    wallet = _only(client, WALLETS_URL, guest.headers)
    assert wallet["name"] == "Example wallet"
    assert wallet["currency"] == "VND"
    assert Decimal(wallet["balance"]) == Decimal("450000.00")

    category = _only(client, CATEGORIES_URL, guest.headers)
    assert category["name"] == "Food"
    assert category["type"] == "EXPENSE"

    transaction = _only(client, TRANSACTIONS_URL, guest.headers)
    assert Decimal(transaction["amount"]) == Decimal("50000.00")
    assert transaction["type"] == "EXPENSE"
    assert transaction["note"] == "Example: lunch"
    assert transaction["wallet_id"] == wallet["id"]
    assert transaction["category_id"] == category["id"]

    budgets = client.get(BUDGETS_URL, headers=guest.headers)
    assert budgets.status_code == 200
    assert budgets.json()["items"] == []
    assert budgets.json()["total"] == 0


# --- AC-03, EC-05, EC-06: a guest is a member, with its own data -------------


def test_guest_can_do_everything_a_member_can_including_removing_the_example(
    client: TestClient, settings: Settings, user_headers: dict[str, str]
) -> None:
    """TC-61: every creation, the edit, the deletion, the archive and the
    report answer exactly as for a member, and the report is the guest's own.

    TC-61's text names `200` for the deletion; the member's own route answers
    `204` (TM-US-05). "Exactly as for a member" is what is asserted.
    """
    # A member with data of its own, so "only the guest's own" can be seen.
    member_wallet = client.post(
        WALLETS_URL,
        headers=user_headers,
        json={"name": "Member", "type": "Bank", "currency": "VND", "initial_balance": "0.00"},
    ).json()
    member_income = client.post(
        CATEGORIES_URL, headers=user_headers, json={"name": "Salary", "type": "INCOME"}
    ).json()
    assert (
        client.post(
            TRANSACTIONS_URL,
            headers=user_headers,
            json={
                "wallet_id": member_wallet["id"],
                "category_id": member_income["id"],
                "amount": "9999.00",
                "type": "INCOME",
            },
        ).status_code
        == 201
    )

    guest = _start(client, settings)
    example_wallet = _only(client, WALLETS_URL, guest.headers)
    example_category = _only(client, CATEGORIES_URL, guest.headers)
    example_tx = _only(client, TRANSACTIONS_URL, guest.headers)

    wallet = client.post(
        WALLETS_URL,
        headers=guest.headers,
        json={"name": "Savings", "type": "Bank", "currency": "VND", "initial_balance": "0.00"},
    )
    assert wallet.status_code == 201
    income = client.post(
        CATEGORIES_URL, headers=guest.headers, json={"name": "Gift", "type": "INCOME"}
    )
    assert income.status_code == 201
    created_tx = client.post(
        TRANSACTIONS_URL,
        headers=guest.headers,
        json={
            "wallet_id": wallet.json()["id"],
            "category_id": income.json()["id"],
            "amount": "1234.00",
            "type": "INCOME",
        },
    )
    assert created_tx.status_code == 201
    budget = client.post(
        BUDGETS_URL,
        headers=guest.headers,
        json={
            "wallet_id": wallet.json()["id"],
            "category_id": example_category["id"],
            "amount_limit": "100000.00",
        },
    )
    assert budget.status_code == 201

    edited = client.patch(
        f"{TRANSACTIONS_URL}/{example_tx['id']}", headers=guest.headers, json={"note": "edited"}
    )
    assert edited.status_code == 200
    assert edited.json()["note"] == "edited"

    deleted = client.delete(f"{TRANSACTIONS_URL}/{example_tx['id']}", headers=guest.headers)
    member_delete_status = 204  # TM-US-05: the member's route answers 204
    assert deleted.status_code == member_delete_status

    archived = client.delete(f"{WALLETS_URL}/{example_wallet['id']}", headers=guest.headers)
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None

    # Per currency since FR-US-03 (plan.md FR-US-03 A14): every guest wallet
    # here is VND, so the report carries exactly one entry.
    report = client.get(REPORT_URL, headers=guest.headers)
    assert report.status_code == 200
    entries = report.json()["currencies"]
    assert [e["currency"] for e in entries] == ["VND"]
    assert Decimal(entries[0]["total_income"]) == Decimal("1234.00")
    assert Decimal(entries[0]["total_expenses"]) == Decimal("0")


def test_guest_and_member_cannot_see_each_others_data(
    client: TestClient, settings: Settings, user_headers: dict[str, str]
) -> None:
    """TC-63: the guest lists only its example and gets 404 for the member's
    wallet; the member's list holds none of the guest's wallets.
    """
    member_wallet = client.post(
        WALLETS_URL,
        headers=user_headers,
        json={"name": "Member", "type": "Bank", "currency": "VND", "initial_balance": "10.00"},
    ).json()
    guest = _start(client, settings)

    example = _only(client, WALLETS_URL, guest.headers)
    assert example["name"] == "Example wallet"

    peek = client.get(f"{WALLETS_URL}/{member_wallet['id']}", headers=guest.headers)
    assert peek.status_code == 404
    assert peek.json()["error_code"] == "WALLET_NOT_FOUND"

    member_ids = {w["id"] for w in client.get(WALLETS_URL, headers=user_headers).json()["items"]}
    assert example["id"] not in member_ids
    assert member_ids == {member_wallet["id"]}


def test_two_trials_are_two_separate_guests_each_with_a_fresh_example(
    client: TestClient, settings: Settings
) -> None:
    """TC-64: different accounts, one example wallet each with different ids,
    and neither can read the other's wallet (404).
    """
    first = _start(client, settings)
    second = _start(client, settings)

    assert first.id != second.id
    first_wallet = _only(client, WALLETS_URL, first.headers)
    second_wallet = _only(client, WALLETS_URL, second.headers)
    assert first_wallet["id"] != second_wallet["id"]
    assert first_wallet["name"] == second_wallet["name"] == "Example wallet"

    first_peeks = client.get(f"{WALLETS_URL}/{second_wallet['id']}", headers=first.headers)
    second_peeks = client.get(f"{WALLETS_URL}/{first_wallet['id']}", headers=second.headers)
    assert first_peeks.status_code == second_peeks.status_code == 404


# --- AC-04: the session lasts the trial -------------------------------------


def test_guest_token_lasts_the_whole_trial_not_sixty_minutes(
    client: TestClient, settings: Settings, trial_clock: TrialClock
) -> None:
    """TC-62: `exp - iat` is 604800 and the role claim is GUEST; 61 minutes
    later the guest is still served.
    """
    guest = _start(client, settings)

    claims = jwt.decode(guest.token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert claims["exp"] - claims["iat"] == 604800
    assert claims["role"] == "GUEST"

    trial_clock.set(trial_clock.start + timedelta(minutes=61))
    assert client.get(WALLETS_URL, headers=guest.headers).status_code == 200


# --- AC-05, EC-01, EC-02: access ends with the trial ------------------------


def test_guest_whose_trial_has_ended_is_refused_even_before_deletion(
    client: TestClient, db: Session, settings: Settings, trial_clock: TrialClock
) -> None:
    """TC-65: trial end one minute in the past, row and data still present,
    token still valid -> 401 byte-identical to a request with no token.
    """
    guest = _start(client, settings)
    _end_trial(db, guest, trial_clock.start - timedelta(minutes=1))

    refused = client.get(WALLETS_URL, headers=guest.headers)
    anonymous = client.get(WALLETS_URL)

    assert refused.status_code == 401
    assert refused.json()["error_code"] == "NOT_AUTHENTICATED"
    assert refused.status_code == anonymous.status_code
    assert refused.content == anonymous.content
    assert _owned_counts(db, guest.id)["wallets"] == 1  # not deleted yet


def test_trial_ends_exactly_at_its_end_time(
    client: TestClient, settings: Settings, trial_clock: TrialClock
) -> None:
    """TC-66: one second before the end -> 200; exactly at the end -> 401."""
    guest = _start(client, settings)
    end = trial_clock.start + TRIAL

    trial_clock.set(end - timedelta(seconds=1))
    assert client.get(WALLETS_URL, headers=guest.headers).status_code == 200

    trial_clock.set(end)
    at_end = client.get(WALLETS_URL, headers=guest.headers)
    assert at_end.status_code == 401
    assert at_end.json()["error_code"] == "NOT_AUTHENTICATED"


def test_deleted_guests_token_is_refused(
    client: TestClient, db: Session, settings: Settings, trial_clock: TrialClock
) -> None:
    """TC-67: an ended and purged guest's token -> 401 on a protected route."""
    guest = _start(client, settings)
    _end_trial(db, guest, trial_clock.start - timedelta(seconds=1))
    _purge(db)
    assert _row(db, guest.id) is None

    response = client.get(CATEGORIES_URL, headers=guest.headers)
    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"


# --- AC-06, AC-13, EC-03, EC-04: deletion -----------------------------------


def test_purge_removes_an_ended_trial_with_all_its_data_and_nothing_else(
    client: TestClient,
    db: Session,
    settings: Settings,
    trial_clock: TrialClock,
    normal_user: UserModel,
    user_headers: dict[str, str],
) -> None:
    """TC-68: the ended guest and everything it owns is gone; the live guest's
    and the member's rows are untouched; the purge reports per-kind counts.
    """
    ended = _start(client, settings)
    _add_owned_data(client, ended.headers, "ended")
    live = _start(client, settings)
    member_ids = _add_owned_data(client, user_headers, "member")

    live_before = _owned_counts(db, live.id)
    member_before = _owned_counts(db, normal_user.id)
    live_balance = _only(client, WALLETS_URL, live.headers)["balance"]
    member_balance = client.get(
        f"{WALLETS_URL}/{member_ids['wallet']}", headers=user_headers
    ).json()["balance"]

    _end_trial(db, ended, trial_clock.start - timedelta(seconds=1))
    result = _purge(db)

    assert (result.guests, result.wallets, result.categories, result.budgets) == (1, 2, 2, 1)
    assert result.transactions == 2
    assert _owned_counts(db, ended.id) == {
        "users": 0,
        "wallets": 0,
        "categories": 0,
        "budgets": 0,
        "transactions": 0,
    }
    assert _owned_counts(db, live.id) == live_before
    assert _owned_counts(db, normal_user.id) == member_before
    assert _only(client, WALLETS_URL, live.headers)["balance"] == live_balance
    assert (
        client.get(f"{WALLETS_URL}/{member_ids['wallet']}", headers=user_headers).json()["balance"]
        == member_balance
    )


def test_starting_a_trial_is_audited_without_the_token(
    client: TestClient,
    db: Session,
    settings: Settings,
    caplog: pytest.LogCaptureFixture,
    trial_clock: TrialClock,
) -> None:
    """TC-69: one GUEST_CREATED, SUCCESS, the guest's id as actor and target,
    the trial end; never the token nor the placeholder address.
    """
    with caplog.at_level("INFO", logger="app.audit"):
        guest = _start(client, settings)

    events = _audit_events(caplog, "GUEST_CREATED")
    assert len(events) == 1
    event = events[0]
    assert event["result"] == "SUCCESS"
    assert event["actor_id"] == guest.id
    assert event["target"] == guest.id
    assert datetime.fromisoformat(event["expires_at"]) == trial_clock.start + TRIAL

    row = _row(db, guest.id)
    assert row is not None
    lines = [r.getMessage() for r in caplog.records if r.name == "app.audit"]
    assert all(guest.token not in line and row.email not in line for line in lines)


def test_deleting_an_ended_trial_is_audited_with_counts(
    client: TestClient,
    db: Session,
    settings: Settings,
    caplog: pytest.LogCaptureFixture,
    trial_clock: TrialClock,
) -> None:
    """TC-70: one GUEST_PURGED, SUCCESS, the guest's id as target, counts
    1/1/1/1; no token, password or hash.
    """
    guest = _start(client, settings)
    wallet = _only(client, WALLETS_URL, guest.headers)
    category = _only(client, CATEGORIES_URL, guest.headers)
    assert (
        client.post(
            BUDGETS_URL,
            headers=guest.headers,
            json={"wallet_id": wallet["id"], "category_id": category["id"], "amount_limit": "1.00"},
        ).status_code
        == 201
    )
    _end_trial(db, guest, trial_clock.start - timedelta(seconds=1))

    with caplog.at_level("INFO", logger="app.audit"):
        _purge(db)

    events = _audit_events(caplog, "GUEST_PURGED")
    assert len(events) == 1
    event = events[0]
    assert event["result"] == "SUCCESS"
    assert event["target"] == guest.id
    assert event["actor_id"] is None
    assert (event["wallets"], event["categories"], event["transactions"], event["budgets"]) == (
        1,
        1,
        1,
        1,
    )
    lines = [r.getMessage() for r in caplog.records if r.name == "app.audit"]
    assert all(guest.token not in line for line in lines)
    assert all(word not in line.lower() for line in lines for word in ("password", "hash"))


def test_ended_trials_are_deleted_when_the_server_starts(
    app: FastAPI, db: Session, settings: Settings, trial_clock: TrialClock
) -> None:
    """TC-71: the startup hook deletes the ended guest and its data; the live
    guest is untouched.
    """
    with TestClient(app) as first_run:
        ended = _start(first_run, settings)
        live = _start(first_run, settings)
    _end_trial(db, ended, trial_clock.start - timedelta(seconds=1))
    live_before = _owned_counts(db, live.id)

    with TestClient(app):  # startup runs the lifespan hook
        pass

    assert _owned_counts(db, ended.id) == {
        "users": 0,
        "wallets": 0,
        "categories": 0,
        "budgets": 0,
        "transactions": 0,
    }
    assert _owned_counts(db, live.id) == live_before
    assert live_before["users"] == 1


def test_purge_guests_command_deletes_ended_trials_and_reports_what_it_removed(
    client: TestClient,
    db: Session,
    settings: Settings,
    trial_clock: TrialClock,
    cli_db: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """TC-72: `purge-guests` exits 0, prints what it removed; the ended guest
    and its data are gone; the live guest is untouched.
    """
    from app.cli import main

    ended = _start(client, settings)
    live = _start(client, settings)
    _end_trial(db, ended, trial_clock.start - timedelta(seconds=1))
    live_before = _owned_counts(db, live.id)

    exit_code = main(["purge-guests"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "1 ended guest trial" in out
    assert "1 wallets" in out and "1 categories" in out and "1 transactions" in out
    assert "0 budgets" in out
    assert _owned_counts(db, ended.id)["users"] == 0
    assert _owned_counts(db, ended.id)["wallets"] == 0
    assert _owned_counts(db, live.id) == live_before


def test_an_ended_trial_never_holds_a_place_under_the_cap(
    client: TestClient, db: Session, settings: Settings, trial_clock: TrialClock
) -> None:
    """TC-73: cap 2, one live and one ended -> a new start is 201, the ended
    guest is deleted, two live guests remain.
    """
    settings.guest_max_active = 2
    _start(client, settings)
    ended = _start(client, settings)
    _end_trial(db, ended, trial_clock.start - timedelta(seconds=1))

    response = client.post(GUEST_URL)

    assert response.status_code == 201
    assert _row(db, ended.id) is None
    guests = db.scalars(select(UserModel).where(UserModel.role == UserRole.GUEST)).all()
    assert len(guests) == 2
    assert all(
        g.expires_at is not None and g.expires_at.replace(tzinfo=UTC) > trial_clock.start
        for g in guests
    )


def test_at_the_cap_a_new_trial_is_refused_and_nothing_is_created(
    client: TestClient, db: Session, settings: Settings
) -> None:
    """TC-74: cap 2, two live guests -> 503 GUEST_LIMIT_REACHED in the flat
    envelope; no account, wallet, category or transaction is added.
    """
    settings.guest_max_active = 2
    _start(client, settings)
    _start(client, settings)
    before = [_count(db, m) for m in (UserModel, WalletModel, CategoryModel, TransactionModel)]

    response = client.post(GUEST_URL)

    assert response.status_code == 503
    body = response.json()
    assert set(body) == {"error_code", "message", "details"}
    assert body["error_code"] == "GUEST_LIMIT_REACHED"
    after = [_count(db, m) for m in (UserModel, WalletModel, CategoryModel, TransactionModel)]
    assert after == before


def test_sixth_trial_start_from_one_client_within_an_hour_is_refused(
    client: TestClient, db: Session, settings: Settings
) -> None:
    """TC-75: the production limit (5/hour) -> five 201s, then 429
    RATE_LIMIT_EXCEEDED in the flat envelope; exactly five guests exist.
    """
    assert settings.guest_rate_limit == "5/hour"

    statuses = [client.post(GUEST_URL).status_code for _ in range(5)]
    sixth = client.post(GUEST_URL)

    assert statuses == [201] * 5
    assert sixth.status_code == 429
    body = sixth.json()
    assert set(body) == {"error_code", "message", "details"}
    assert body["error_code"] == "RATE_LIMIT_EXCEEDED"
    assert _count(db, UserModel, UserModel.role == UserRole.GUEST) == 5


def test_failure_while_creating_the_example_leaves_nothing_behind(
    app: FastAPI, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TC-76: the example transaction fails unexpectedly -> 500
    INTERNAL_ERROR, and no guest, wallet, category or transaction remains.
    """

    def _explode(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("seeding failed")

    monkeypatch.setattr("app.services.transaction_service.create_transaction", _explode)

    with TestClient(app, raise_server_exceptions=False) as bare_client:
        response = bare_client.post(GUEST_URL)

    assert response.status_code == 500
    assert response.json()["error_code"] == "INTERNAL_ERROR"
    for model in (UserModel, WalletModel, CategoryModel, TransactionModel):
        assert _count(db, model) == 0, model


# --- AC-07, EC-08, EC-09: no credentials, no email, no upgrade --------------


def test_login_service_never_authenticates_a_guest_whatever_the_password(
    client: TestClient, db: Session, settings: Settings
) -> None:
    """TC-77: called directly with the guest's placeholder address — with the
    timing-parity dummy password, then an arbitrary one — both are refused
    with the generic invalid-credentials error (plan.md F1).
    """
    guest = _start(client, settings)
    row = _row(db, guest.id)
    assert row is not None

    for password in (DUMMY_PASSWORD, "Arbitrary-Passw0rd!"):
        with pytest.raises(InvalidCredentialsError):
            auth_service.authenticate(db, raw_email=row.email, password=password, settings=settings)


def test_login_naming_a_guests_placeholder_address_is_rejected_before_any_lookup(
    client: TestClient, db: Session, settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    """TC-78: 422 VALIDATION_ERROR naming the email field; no token, and no
    login audit record.
    """
    guest = _start(client, settings)
    row = _row(db, guest.id)
    assert row is not None

    with caplog.at_level("INFO", logger="app.audit"):
        response = client.post(LOGIN_URL, json={"email": row.email, "password": DUMMY_PASSWORD})

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert any("email" in field["location"] for field in body["details"]["fields"])
    assert "access_token" not in body
    assert _audit_events(caplog, "LOGIN_SUCCESS") == []
    assert _audit_events(caplog, "LOGIN_FAILED") == []


def test_admin_cannot_invite_a_guests_address_or_any_guest_style_address(
    client: TestClient,
    db: Session,
    settings: Settings,
    admin_headers: dict[str, str],
    email_sender: RecordingEmailSender,
) -> None:
    """TC-79: both invitations are 422; no invitation row, no email, the
    guest unchanged.
    """
    guest = _start(client, settings)
    row = _row(db, guest.id)
    assert row is not None

    exact = client.post(INVITE_URL, headers=admin_headers, json={"email": row.email})
    other = client.post(INVITE_URL, headers=admin_headers, json={"email": "someone@guest.invalid"})

    assert exact.status_code == other.status_code == 422
    assert exact.json()["error_code"] == other.json()["error_code"] == "VALIDATION_ERROR"
    assert _count(db, InvitationModel) == 0
    assert email_sender.sent == []
    after = _row(db, guest.id)
    assert after is not None
    assert (after.role, after.status, after.password_hash) == (
        UserRole.GUEST,
        UserStatus.ACTIVE,
        None,
    )


def test_invitation_service_refuses_a_guest_address_past_the_validation_layer(
    db: Session, settings: Settings, admin_user: UserModel
) -> None:
    """TC-80: the service itself raises the 422 refusal and creates neither a
    user nor an invitation (plan.md A13's defensive layer).
    """
    users_before = _count(db, UserModel)

    with pytest.raises(ValidationError) as refused:
        invitation_service.create_invitation(
            db, raw_email="guest-x@guest.invalid", invited_by=admin_user, settings=settings
        )

    assert refused.value.status_code == 422
    db.rollback()
    assert _count(db, UserModel) == users_before
    assert _count(db, InvitationModel) == 0


def test_promote_admin_refuses_a_guest_account(
    client: TestClient,
    db: Session,
    settings: Settings,
    cli_db: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """TC-81: exit 1 with a message on stderr; still GUEST, ACTIVE, no password."""
    from app.cli import main

    guest = _start(client, settings)
    row = _row(db, guest.id)
    assert row is not None

    exit_code = main(["promote-admin", "--email", row.email, "--password", "Str0ng-Passw0rd!"])

    assert exit_code == 1
    assert capsys.readouterr().err.strip()
    after = _row(db, guest.id)
    assert after is not None
    assert (after.role, after.status, after.password_hash) == (
        UserRole.GUEST,
        UserStatus.ACTIVE,
        None,
    )


def test_former_guests_invitation_starts_an_ordinary_account_with_nothing_from_the_trial(
    client: TestClient, db: Session, settings: Settings, admin_headers: dict[str, str]
) -> None:
    """TC-84: 201; PENDING, USER, no wallets or categories; the guest and its
    example unchanged.
    """
    guest = _start(client, settings)
    guest_before = _owned_counts(db, guest.id)

    response = client.post(
        INVITE_URL, headers=admin_headers, json={"email": "former.guest@example.com"}
    )

    assert response.status_code == 201
    db.expire_all()
    invited = db.scalars(
        select(UserModel).where(UserModel.email == "former.guest@example.com")
    ).one()
    assert (invited.status, invited.role) == (UserStatus.PENDING, UserRole.USER)
    assert invited.expires_at is None
    assert _owned_counts(db, invited.id)["wallets"] == 0
    assert _owned_counts(db, invited.id)["categories"] == 0
    assert _owned_counts(db, guest.id) == guest_before
    assert Decimal(_only(client, WALLETS_URL, guest.headers)["balance"]) == Decimal("450000.00")


# --- AC-08, AC-09: not a family member ---------------------------------------


def test_guests_are_absent_from_the_admins_user_list_and_its_total(
    client: TestClient,
    settings: Settings,
    admin_user: UserModel,
    normal_user: UserModel,
    admin_headers: dict[str, str],
) -> None:
    """TC-82: the list holds the ADMIN, the member and the invitee — no guest —
    and the total counts exactly those three.
    """
    invited = client.post(INVITE_URL, headers=admin_headers, json={"email": "invitee@example.com"})
    assert invited.status_code == 201
    _start(client, settings)
    _start(client, settings)

    response = client.get(USERS_URL, headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert {u["email"] for u in body["items"]} == {
        admin_user.email,
        normal_user.email,
        "invitee@example.com",
    }
    assert body["total"] == 3


def test_guest_cannot_invite_or_list_users(
    client: TestClient, db: Session, settings: Settings
) -> None:
    """TC-83: both 403 FORBIDDEN; no invitation created."""
    guest = _start(client, settings)

    invite = client.post(INVITE_URL, headers=guest.headers, json={"email": "friend@example.com"})
    listing = client.get(USERS_URL, headers=guest.headers)

    assert invite.status_code == listing.status_code == 403
    assert invite.json()["error_code"] == listing.json()["error_code"] == "FORBIDDEN"
    assert _count(db, InvitationModel) == 0


# --- AC-15, AC-16: sign-out keeps the trial ----------------------------------


def test_guests_sign_out_deletes_nothing_and_its_token_keeps_working(
    client: TestClient, db: Session, settings: Settings
) -> None:
    """TC-85: logout 200 with SS-US-02's LogoutResult shape; the account and
    its data stay; the same token then lists both wallets.
    """
    guest = _start(client, settings)
    extra = client.post(
        WALLETS_URL,
        headers=guest.headers,
        json={"name": "Extra", "type": "Bank", "currency": "VND", "initial_balance": "0.00"},
    )
    assert extra.status_code == 201
    before = _owned_counts(db, guest.id)

    logout = client.post(LOGOUT_URL, headers=guest.headers)

    assert logout.status_code == 200
    assert set(logout.json()) == {"status", "message"}
    assert logout.json()["status"] == "SUCCESS"
    assert _owned_counts(db, guest.id) == before
    assert before == {"users": 1, "wallets": 2, "categories": 1, "budgets": 0, "transactions": 1}

    after = client.get(WALLETS_URL, headers=guest.headers)
    assert after.status_code == 200
    assert {w["name"] for w in after.json()["items"]} == {"Example wallet", "Extra"}
