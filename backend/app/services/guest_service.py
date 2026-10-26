"""Guest trial business rules (spec SS-US-03, SDS §5.1.3).

Constitution:
  AR-01  the cap, the seeding, the trial end and the purge order live here
  AR-05  no framework objects — plain values only; the limiter stays in the router
  AR-06  this module flushes; the router (or startup, or the CLI) commits
  AR-07  guest_service -> other services -> repositories, never router -> repo
  SEC-12 a guest has no real email and no password, is never upgraded, and is
         deleted with all its data when its trial ends — never on sign-out
"""

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core import audit, clock, security
from app.core.config import Settings
from app.core.errors import GuestLimitReachedError
from app.models.category import CategoryType
from app.models.transaction import TransactionType
from app.models.user import UserRole
from app.repositories import (
    budget_repo,
    category_repo,
    transaction_repo,
    user_repo,
    wallet_repo,
)
from app.schemas.auth import GuestSessionRead
from app.services import category_service, transaction_service, wallet_service

# plan.md A2: `.invalid` is reserved (RFC 2606, RFC 6761) — it can never
# resolve, so a guest is never mailable, and pydantic's EmailStr rejects it in
# every request body, so no login or invite can even name one.
GUEST_EMAIL_DOMAIN = "guest.invalid"

# spec AC-02 / FR-03: exactly one example, nothing else.
EXAMPLE_WALLET_NAME = "Example wallet"
# plan.md A6: chosen from the client's own wallet types; no rule names one.
EXAMPLE_WALLET_TYPE = "Cash"
EXAMPLE_CURRENCY = "VND"
EXAMPLE_OPENING_BALANCE = Decimal("500000.00")
EXAMPLE_CATEGORY_NAME = "Food"
EXAMPLE_EXPENSE = Decimal("50000.00")
EXAMPLE_NOTE = "Example: lunch"


@dataclass(frozen=True)
class PurgeResult:
    """How much one purge removed, per kind (spec AC-13, plan.md A14)."""

    guests: int = 0
    wallets: int = 0
    categories: int = 0
    budgets: int = 0
    transactions: int = 0


def start(db: Session, *, settings: Settings) -> GuestSessionRead:
    """Start a guest trial (spec AC-01, AC-02, AC-04, AC-11, AC-12, AC-13).

    1. Purge ended trials first, in this same transaction, so an ended trial
       never holds a place under the cap (EC-03, plan.md A7).
    2. Refuse at the cap (A12) — before anything is written.
    3. Create the guest and its example through the members' own services, so
       ownership, type agreement and the balance decrement are their rules and
       the balance reads 450,000.00 for the same reason a member's would (A6).
    4. Issue a token that lasts the whole trial (A4) and audit the creation.

    Flushes only: the router commits once, so the account and its example
    reach the database together or not at all (AC-12, NFR-05).
    """
    purge_expired(db)

    if user_repo.count_guests(db) >= settings.guest_max_active:
        raise GuestLimitReachedError()

    now = clock.utcnow()
    trial = timedelta(days=settings.guest_ttl_days)
    expires_at = now + trial
    guest = user_repo.add_guest_user(
        db, email=f"guest-{uuid4()}@{GUEST_EMAIL_DOMAIN}", expires_at=expires_at
    )

    wallet = wallet_service.create_wallet(
        db,
        owner=guest,
        name=EXAMPLE_WALLET_NAME,
        wallet_type=EXAMPLE_WALLET_TYPE,
        currency=EXAMPLE_CURRENCY,
        initial_balance=EXAMPLE_OPENING_BALANCE,
    )
    category = category_service.create_category(
        db, owner=guest, name=EXAMPLE_CATEGORY_NAME, category_type=CategoryType.EXPENSE
    )
    transaction_service.create_transaction(
        db,
        owner=guest,
        wallet_id=wallet.id,
        category_id=category.id,
        amount=EXAMPLE_EXPENSE,
        type=TransactionType.EXPENSE,
        note=EXAMPLE_NOTE,
    )

    # SEC-12's one exception to SEC-06's 60 minutes: the session lasts the
    # trial, because a guest holds no password to sign back in with (AC-04).
    token = security.encode_jwt(
        subject=guest.id,
        role=UserRole.GUEST.value,
        secret=settings.jwt_secret,
        ttl_minutes=settings.guest_ttl_days * 24 * 60,
        algorithm=settings.jwt_algorithm,
    )

    # LA-01: the guest's id, never the token and never the placeholder address.
    audit.record(
        action="GUEST_CREATED",
        actor_id=guest.id,
        target=guest.id,
        result="SUCCESS",
        expires_at=expires_at.isoformat(),
    )

    return GuestSessionRead(
        access_token=token,
        expires_in=int(trial.total_seconds()),
        role="GUEST",
        expires_at=clock.ensure_aware(expires_at),
    )


def purge_expired(db: Session) -> PurgeResult:
    """Delete every ended trial with everything it owns, and nothing else
    (spec AC-06, FR-06, plan.md A8).

    Child-first, per ended guest: transactions, budgets, categories, wallets,
    then the account — nothing cascades, SQLite does not enforce the foreign
    keys here, and PostgreSQL would refuse any other order (ENV-03). Every
    predicate is ownership by an *ended* guest's id, so no member's row and no
    live guest's row can match.

    Called at startup, at the start of every trial, and by the `purge-guests`
    command (A9). Flushes only; the caller commits.
    """
    totals = PurgeResult()
    for guest in user_repo.list_ended_guests(db, now=clock.utcnow()):
        transactions = transaction_repo.delete_all_for_owner(db, user_id=guest.id)
        budgets = budget_repo.delete_all_for_owner(db, user_id=guest.id)
        categories = category_repo.delete_all_for_owner(db, user_id=guest.id)
        wallets = wallet_repo.delete_all_for_owner(db, user_id=guest.id)
        guest_id = guest.id
        user_repo.delete_user(db, guest)

        audit.record(
            action="GUEST_PURGED",
            actor_id=None,
            target=guest_id,
            result="SUCCESS",
            wallets=wallets,
            categories=categories,
            budgets=budgets,
            transactions=transactions,
        )
        totals = PurgeResult(
            guests=totals.guests + 1,
            wallets=totals.wallets + wallets,
            categories=totals.categories + categories,
            budgets=totals.budgets + budgets,
            transactions=totals.transactions + transactions,
        )
    return totals
