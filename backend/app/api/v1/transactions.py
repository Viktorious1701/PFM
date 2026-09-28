"""Transaction Management endpoints (SDS §5.6.1 TM-US-01, §5.6.2 TM-US-02)."""

from datetime import datetime

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUserDep, DbDep
from app.schemas.transaction import TransactionCreate, TransactionListRead, TransactionRead
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


@router.get(
    "",
    response_model=TransactionListRead,
    status_code=status.HTTP_200_OK,
    summary="List the caller's transactions",
    description=(
        "Returns every transaction belonging to a wallet owned by the "
        "authenticated caller, optionally narrowed by wallet, category, or "
        "date range, paginated, with an accurate total scoped to the caller "
        "and to every filter supplied."
    ),
    responses={
        401: {"description": "NOT_AUTHENTICATED"},
        422: {"description": "VALIDATION_ERROR"},
    },
)
def list_transactions(
    db: DbDep,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    wallet_id: str | None = Query(None),
    category_id: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
) -> TransactionListRead:
    """Pure read — no `db.commit()` (plan.md A9)."""
    return transaction_service.list_transactions(
        db,
        owner=current_user,
        page=page,
        page_size=page_size,
        wallet_id=wallet_id,
        category_id=category_id,
        date_from=date_from,
        date_to=date_to,
    )
