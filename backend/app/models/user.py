"""User account model (SDS §2.4.1, §4.3.3).

An account is created by invitation in `PENDING` status with no credentials and
becomes usable only through activation (UM-US-02).

Constitution: NC-02 (UserModel), NC-04 (snake_case columns), NC-05 (enum
literals), PF-02 (indexed lookups).
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core import clock
from app.db.base import Base


class UserStatus(enum.StrEnum):
    """SDS §2.4.1 as aligned to the SRS.

    `PENDING` — SRS §6 US-01-01 wins over the SDS's original
    `PENDING_INVITATION` (see CLAUDE.md resolved contradictions).
    Only `PENDING` is written by UM-US-01. There is no `EXPIRED`: token expiry
    is a property of the *invitation*, and leaves the user `PENDING`.
    """

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    DEACTIVATED = "DEACTIVATED"


class UserRole(enum.StrEnum):
    """SDS §5.2. Invited accounts always get USER (spec FR-06, BR-05)."""

    ADMIN = "ADMIN"
    USER = "USER"


def new_uuid() -> str:
    """UUID as text.

    `String(36)` rather than a native UUID column so the same schema runs on
    SQLite locally and PostgreSQL in deployment (ADR-0001 rationale, ENV-03).
    """
    return str(uuid.uuid4())


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)

    # spec FR-03 / BR-01 / A7: stored normalised (trimmed, case-folded) and
    # uniquely indexed. The index is the second half of VL-05's two-level
    # uniqueness — it catches the concurrent duplicate the service check misses.
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)

    # spec AC-07 / FR-05: both NULL for an invited account. A row with no hash
    # cannot authenticate, which is what makes BR-06 true by construction.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, native_enum=False, length=20),
        nullable=False,
        default=UserStatus.PENDING,
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=10),
        nullable=False,
        default=UserRole.USER,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=clock.utcnow
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<UserModel id={self.id} email={self.email} status={self.status}>"
