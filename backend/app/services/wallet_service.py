"""Wallet business rules (spec WM-US-01, SDS §5.3.1).

Constitution:
  AR-01  the owner-assignment rule lives here, not in the router
  AR-05  no framework objects — plain values only
  AR-06  this module flushes; the router commits. One request, one transaction

No audit call (plan.md A9) — wallet creation is not one of constitution
LA-04's three named audited events, and no AC or FR in spec.md asks for one.
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import WalletNotFoundError
from app.models.user import UserModel
from app.repositories import wallet_repo
from app.schemas.wallet import WalletListRead, WalletRead


def create_wallet(
    db: Session,
    *,
    owner: UserModel,
    name: str,
    wallet_type: str,
    currency: str,
    initial_balance: Decimal,
) -> WalletRead:
    """Create a wallet owned by `owner` (spec AC-01, AC-10, FR-08, FR-09,
    BR-01).

    The owner is read from `owner.id` — the authenticated caller resolved by
    `CurrentUserDep` — never from any value in the request payload
    (`WalletCreate` declares no `user_id` field to read from instead;
    plan.md A7).

    `initial_balance` maps to the stored `balance` column (spec FR-09,
    SDS §6.2.1 vs §2.2 — the create-time input and the stored column are
    distinct names for the same value).
    """
    wallet = wallet_repo.add_wallet(
        db,
        user_id=owner.id,
        name=name,
        wallet_type=wallet_type,
        currency=currency,
        balance=initial_balance,
    )
    return WalletRead(
        id=wallet.id,
        user_id=wallet.user_id,
        name=wallet.name,
        type=wallet.type,
        currency=wallet.currency,
        balance=wallet.balance,
    )


def list_wallets(db: Session, *, owner: UserModel, page: int, page_size: int) -> WalletListRead:
    """Assemble a page of the caller's own wallets into the `WalletListRead`
    envelope (spec WM-US-02 AC-01, AC-04, AC-05, AC-07, AC-09; plan.md A2,
    A3).

    Unlike `user_service.list_users`, this calls no `clock.ensure_aware()` —
    `WalletRead` carries no datetime field to normalise (WM-US-01 A5).
    """
    items, total = wallet_repo.list_owned(db, user_id=owner.id, page=page, page_size=page_size)
    return WalletListRead(
        items=[
            WalletRead(
                id=w.id,
                user_id=w.user_id,
                name=w.name,
                type=w.type,
                currency=w.currency,
                balance=w.balance,
            )
            for w in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


def update_wallet(
    db: Session,
    *,
    owner: UserModel,
    wallet_id: str,
    name: str | None,
    wallet_type: str | None,
) -> WalletRead:
    """spec AC-01, FR-03 (plan.md A1, A3, A4). Looks up the wallet scoped to
    the caller, then updates whichever of name/type was actually submitted
    -- no further precondition follows ownership, the same shape BM-US-04's
    own update_budget() already established.
    """
    wallet = wallet_repo.get_owned_by_id(db, wallet_id=wallet_id, user_id=owner.id)
    if wallet is None:
        raise WalletNotFoundError()

    wallet = wallet_repo.update_wallet(db, wallet=wallet, name=name, wallet_type=wallet_type)
    return WalletRead(
        id=wallet.id,
        user_id=wallet.user_id,
        name=wallet.name,
        type=wallet.type,
        currency=wallet.currency,
        balance=wallet.balance,
    )


def get_wallet(db: Session, *, owner: UserModel, wallet_id: str) -> WalletRead:
    """spec AC-01, FR-03 (plan.md A2, A3). Looks up the wallet scoped to the
    caller; no further precondition follows ownership -- a view changes
    nothing, the same shape transaction_service.get_transaction() (TM-US-03)
    already established for its own single-resource read, and the same
    ownership-scoped lookup wallet_service.update_wallet() (WM-US-04) already
    uses before mutating.
    """
    wallet = wallet_repo.get_owned_by_id(db, wallet_id=wallet_id, user_id=owner.id)
    if wallet is None:
        raise WalletNotFoundError()

    return WalletRead(
        id=wallet.id,
        user_id=wallet.user_id,
        name=wallet.name,
        type=wallet.type,
        currency=wallet.currency,
        balance=wallet.balance,
    )
