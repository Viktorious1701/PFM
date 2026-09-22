"""Wallet model (SDS §2.2, §4.3.3; spec WM-US-01).

A named store of liquid money a User holds — cash, a bank account, a credit
line (SRS §1.5). First story to persist money in this codebase (constitution
VL-07): `balance` is `Numeric(15, 2)`, matching `Decimal(max_digits=15,
decimal_places=2)` on `WalletCreate` exactly, so the DTO bound and the column
bound cannot silently drift apart (plan.md A3).

No `created_at` column (plan.md A5) — SDS §4.3.3's ERD lists `wallets` with
exactly `id`, `user_id`, `name`, `type`, `balance`, `currency`, and adding a
column the ERD does not list is a domain-model change this story may not make
unilaterally. Flagged, not silently patched — see spec.md Assumptions.

`type` and `currency` are plain bounded strings, not `Enum` columns (plan.md
A1, A2) — no closed vocabulary exists in either reference document for either
field.
"""

from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import new_uuid


class WalletModel(Base):
    __tablename__ = "wallets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)

    # spec BR-01 / AC-10 / constitution SEC-08: every future query on this
    # table filters by owner, so the FK carries an index now (PF-02), even
    # though this story only ever writes one row per request.
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )

    # spec AC-03/AC-04/FR-03: required, trimmed by the DTO, bounded at 100.
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # spec AC-05/AC-06/FR-04, plan.md A1: free text, no enum — no closed
    # vocabulary exists in either reference document.
    type: Mapped[str] = mapped_column(String(50), nullable=False)

    # spec AC-07/FR-05, plan.md A2: ISO-4217 shape only, no case-folding.
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    # spec FR-06/FR-09, constitution VL-07: Decimal(15,2), never float.
    balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<WalletModel id={self.id} user_id={self.user_id} name={self.name}>"
