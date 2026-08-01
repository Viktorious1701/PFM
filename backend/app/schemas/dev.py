"""Dev-only outbox DTOs. Never mounted in production (see api/v1/dev.py)."""

from pydantic import BaseModel


class OutboxMessage(BaseModel):
    to: str
    sent_at: str
    activation_url: str | None


class OutboxList(BaseModel):
    messages: list[OutboxMessage]
