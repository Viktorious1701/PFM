"""Import models so Alembic autogenerate and create_all see every table."""

from app.db.base import Base
from app.models.user import User, UserStatus

__all__ = ["Base", "User", "UserStatus"]
