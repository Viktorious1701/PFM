"""User model — SRS §3 domain model, with invitation-status tracking."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.db.base import Base


class UserStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"


class User(Base):
    __tablename__ = "users"

    # String(36) rather than a native UUID type so the same schema runs on both
    # SQLite (dev) and Postgres (later) without a dialect-specific column.
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Always stored lowercased (see repositories.user_repo.normalize_email) so
    # the unique constraint is genuinely case-insensitive.
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)

    # Both nullable: an invited user has neither until they activate (US-01-02).
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[UserStatus] = mapped_column(
        SAEnum(UserStatus, native_enum=False, length=16, validate_strings=True),
        default=UserStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Only the SHA-256 of the token is persisted; the raw value lives in the email.
    invitation_token_hash: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    preferred_currency: Mapped[str] = mapped_column(String(3), default="VND", nullable=False)

    invited_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    @property
    def is_active(self) -> bool:
        return self.status is UserStatus.ACTIVE

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<User {self.email} {self.status.value}>"
