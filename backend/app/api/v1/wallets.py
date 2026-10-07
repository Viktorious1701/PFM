"""Wallet Management endpoints (SDS §6.3 WM-API-01, WM-API-02)."""

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUserDep, DbDep
from app.schemas.wallet import WalletCreate, WalletListRead, WalletRead, WalletUpdate
from app.services import wallet_service

router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.post(
    "",
    response_model=WalletRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a wallet",
    description=(
        "Creates a new wallet owned by the authenticated caller, with a name, "
        "type, currency, and initial balance."
    ),
    responses={
        401: {"description": "NOT_AUTHENTICATED"},
        422: {"description": "VALIDATION_ERROR"},
    },
)
def create_wallet(
    payload: WalletCreate,
    db: DbDep,
    current_user: CurrentUserDep,
) -> WalletRead:
    result = wallet_service.create_wallet(
        db,
        owner=current_user,
        name=payload.name,
        wallet_type=payload.type,
        currency=payload.currency,
        initial_balance=payload.initial_balance,
    )
    db.commit()
    return result


@router.get(
    "",
    response_model=WalletListRead,
    status_code=status.HTTP_200_OK,
    summary="List the caller's wallets",
    description=(
        "Returns every wallet owned by the authenticated caller, paginated, "
        "with an accurate total scoped to that caller."
    ),
    responses={
        401: {"description": "NOT_AUTHENTICATED"},
        422: {"description": "VALIDATION_ERROR"},
    },
)
def list_wallets(
    db: DbDep,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> WalletListRead:
    """Pure read — no `db.commit()` (plan.md A4)."""
    return wallet_service.list_wallets(db, owner=current_user, page=page, page_size=page_size)


@router.patch(
    "/{wallet_id}",
    response_model=WalletRead,
    status_code=status.HTTP_200_OK,
    summary="Update a wallet",
    description=(
        "Updates the name, the type, or both, of one of the authenticated "
        "caller's own wallets, identified by its own id. The wallet's "
        "currency and balance are immutable through this endpoint."
    ),
    responses={
        401: {"description": "NOT_AUTHENTICATED"},
        404: {"description": "WALLET_NOT_FOUND"},
        422: {"description": "VALIDATION_ERROR"},
    },
)
def update_wallet(
    wallet_id: str,
    payload: WalletUpdate,
    db: DbDep,
    current_user: CurrentUserDep,
) -> WalletRead:
    result = wallet_service.update_wallet(
        db,
        owner=current_user,
        wallet_id=wallet_id,
        name=payload.name,
        wallet_type=payload.type,
    )
    db.commit()
    return result
