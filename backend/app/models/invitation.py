"""Invitation model (SDS §2.4.2, §4.3.3).

One row per invitation *attempt*, distinct from the account, so the history of
attempts survives and an expired attempt leaves the account untouched
(spec FR-10, plan.md A1/A3, ADR-0002 rationale).
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core import clock
from app.db.base import Base
from app.models.user import new_uuid


class InvitationStatus(enum.StrEnum):
    """SDS §2.4.2.

    UM-US-01 writes `PENDING` and `SUPERSEDED` only. `ACCEPTED` belongs to
    UM-US-02.

    `EXPIRED` is **derived** — never written. A reader compares `expires_at`
    against the clock (spec BR-04, plan.md A5). There is no sweeper job, so the
    value exists in this enum for readers to compute, not for writers to set.
    """

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    EXPIRED = "EXPIRED"
    SUPERSEDED = "SUPERSEDED"


class InvitationModel(Base):
    __tablename__ = "invitations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)

    # plan.md A7: indexed for lookup but deliberately NOT unique — uniqueness
    # lives on the account, not the attempt, so an address can be re-invited.
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)

    # spec AC-08 / BR-07 / SEC-03: only the SHA-256 hex digest is stored. The
    # raw token exists solely in the delivered email. 64 chars of hex.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    # spec FR-09: exactly INVITATION_TTL_HOURS after creation.
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    status: Mapped[InvitationStatus] = mapped_column(
        Enum(InvitationStatus, native_enum=False, length=20),
        nullable=False,
        default=InvitationStatus.PENDING,
    )

    # spec FR-07 / AC-09: which ADMIN issued this invitation.
    invited_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=clock.utcnow
    )

    def is_expired(self, now: datetime | None = None) -> bool:
        """Derive expiry by comparison (spec BR-04).

        `ensure_aware` is required, not defensive: SQLite drops tzinfo, so
        `expires_at` reads back naive and comparing it to an aware `utcnow()`
        raises TypeError (spike finding 4, ADR-0004 rationale).
        """
        moment = now or clock.utcnow()
        return clock.ensure_aware(self.expires_at) <= clock.ensure_aware(moment)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<InvitationModel id={self.id} email={self.email} status={self.status}>"
