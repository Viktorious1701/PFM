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

from app.models.user import UserModel
from app.repositories import wallet_repo
from app.schemas.wallet import WalletRead


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
