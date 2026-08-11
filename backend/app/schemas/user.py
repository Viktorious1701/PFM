"""User DTOs (SDS §6.2.1 `UserRead`, plan.md UM-US-03 A6).

Constitution: PF-03 (DTO projection, never an ORM graph), SEC-01 (never a
password hash), NC-02.
"""

from datetime import datetime

from pydantic import BaseModel

from app.models.user import UserStatus


class UserRead(BaseModel):
    """SDS §6.2.1 `UserRead`. Restored per UM-US-01 plan.md F2 — it "returns
    with UM-US-03", this story.

    **Exactly five fields, never `password_hash`** (spec FR-10, constitution
    PF-03, SEC-01). `full_name` is nullable — an invited account that has
    never activated carries no name yet (spec EC-03, QF-01: serialises as
    JSON `null`, matching the nullable storage column rather than coercing to
    an empty string).
    """

    id: str
    email: str
    full_name: str | None
    status: UserStatus
    created_at: datetime


class UserListRead(BaseModel):
    """New envelope (plan.md A6). Not in SDS's DTO registry — designed here to
    satisfy constitution API-06's pagination contract (page, page_size, total
    count alongside every page).
    """

    items: list[UserRead]
    total: int
    page: int
    page_size: int
