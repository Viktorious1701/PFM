"""Model package.

Every model must be imported here. Alembic autogenerate only sees tables that
are registered on `Base.metadata`, and that registration happens at import time
— a model this module forgets is a table the next migration silently drops.
"""

from app.models.budget import BudgetModel
from app.models.category import CategoryModel, CategoryType
from app.models.invitation import InvitationModel, InvitationStatus
from app.models.user import UserModel, UserRole, UserStatus, new_uuid
from app.models.wallet import WalletModel

__all__ = [
    "BudgetModel",
    "CategoryModel",
    "CategoryType",
    "InvitationModel",
    "InvitationStatus",
    "UserModel",
    "UserRole",
    "UserStatus",
    "WalletModel",
    "new_uuid",
]
