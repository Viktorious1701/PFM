"""Transaction Management endpoints (SDS §5.6.1 TM-US-01)."""

from fastapi import APIRouter, status

from app.core.deps import CurrentUserDep, DbDep
from app.schemas.transaction import TransactionCreate, TransactionRead
from app.services import transaction_service

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post(
    "",
    response_model=TransactionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a transaction",
    description=(
        "Creates a new income or expense transaction against one of the "
        "authenticated caller's own wallets and one of their own categories, "
        "and atomically updates the wallet's balance. The timestamp is always "
        "the moment of creation, computed by the system."
    ),
    responses={
        401: {"description": "NOT_AUTHENTICATED"},
        404: {"description": "TRANSACTION_WALLET_NOT_FOUND / TRANSACTION_CATEGORY_NOT_FOUND"},
        409: {
            "description": ("TRANSACTION_CATEGORY_TYPE_MISMATCH / TRANSACTION_INSUFFICIENT_BALANCE")
        },
        422: {"description": "VALIDATION_ERROR"},
    },
)
def create_transaction(
    payload: TransactionCreate,
    db: DbDep,
    current_user: CurrentUserDep,
) -> TransactionRead:
    result = transaction_service.create_transaction(
        db,
        owner=current_user,
        wallet_id=payload.wallet_id,
        category_id=payload.category_id,
        amount=payload.amount,
        type=payload.type,
        note=payload.note,
    )
    db.commit()
    return result
