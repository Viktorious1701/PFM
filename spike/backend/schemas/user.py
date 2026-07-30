"""Response/request shapes for users."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_serializer, field_validator

from app.core.clock import ensure_aware
from app.models.user import UserStatus


class UserRead(BaseModel):
    """US-01-03 AC-1: id, email, full_name, status, created_at."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str | None
    status: UserStatus
    created_at: datetime

    @field_serializer("created_at")
    def _serialize_created_at(self, value: datetime) -> str:
        return ensure_aware(value).isoformat()


class ActivationRequest(BaseModel):
    """US-01-02 AC-3."""

    token: str = Field(min_length=1)
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _within_bcrypt_limit(cls, value: str) -> str:
        """bcrypt ignores everything past 72 *bytes* — reject rather than truncate.

        Character count is not byte count: 30 emoji or accented characters can
        exceed 72 bytes, which would make part of the password meaningless.
        """
        if len(value.encode("utf-8")) > 72:
            raise ValueError("password must be at most 72 bytes when UTF-8 encoded")
        return value


class ActivationPreflight(BaseModel):
    """Lets a client tell 'expired invite' from 'bad token' before asking for a password."""

    email: EmailStr
    token_expires_at: datetime

    @field_serializer("token_expires_at")
    def _serialize_expiry(self, value: datetime) -> str:
        return ensure_aware(value).isoformat()
