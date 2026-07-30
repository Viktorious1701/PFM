"""US-01-01 request/response shapes."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_serializer

from app.core.clock import ensure_aware
from app.models.user import UserStatus


class InvitationCreate(BaseModel):
    """AC-1: EmailStr does the format validation, so a malformed address is a 422."""

    email: EmailStr


class InvitationRead(BaseModel):
    """AC-6: invitation metadata, deliberately excluding the token.

    The raw token exists only in the email body. Returning it here would let any
    authenticated caller activate an account they were merely inviting.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    status: UserStatus
    token_expires_at: datetime
    created_at: datetime
    email_dispatched: bool = True

    @field_serializer("token_expires_at", "created_at")
    def _serialize_datetimes(self, value: datetime) -> str:
        return ensure_aware(value).isoformat()
