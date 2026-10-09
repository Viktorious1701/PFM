"""Wallet Management endpoints (SDS §6.3 WM-API-01, WM-API-02)."""

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUserDep, DbDep
from app.schemas.wallet import (
    WalletArchiveRead,
    WalletCreate,
    WalletListRead,
    WalletRead,
    WalletUpdate,
)
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


@router.get(
    "/{wallet_id}",
    response_model=WalletRead,
    status_code=status.HTTP_200_OK,
    summary="View a wallet",
    description=(
        "Returns the full detail -- identifier, owner, name, type, currency, "
        "and current balance -- of one of the authenticated caller's own "
        "wallets, identified by its own id. A wallet's transaction history is "
        "retrieved separately, through GET /api/v1/transactions?wallet_id={id}."
    ),
    responses={
        401: {"description": "NOT_AUTHENTICATED"},
        404: {"description": "WALLET_NOT_FOUND"},
    },
)
def get_wallet(
    wallet_id: str,
    db: DbDep,
    current_user: CurrentUserDep,
) -> WalletRead:
    """Pure read -- no db.commit() (plan.md A6)."""
    return wallet_service.get_wallet(db, owner=current_user, wallet_id=wallet_id)


@router.delete(
    "/{wallet_id}",
    response_model=WalletArchiveRead,
    status_code=status.HTTP_200_OK,
    summary="Archive (delete) a wallet",
    description=(
        "Archives one of the authenticated caller's own wallets, identified "
        "by its own id. The wallet's row, name, type, currency, and balance "
        "are left unchanged, and it remains viewable through "
        "GET /wallets/{wallet_id}; it is excluded from GET /wallets by "
        "default, and can no longer be referenced by a new Transaction or "
        "Budget. Archiving an already-archived wallet succeeds again "
        "without changing the recorded archive time."
    ),
    responses={
        401: {"description": "NOT_AUTHENTICATED"},
        404: {"description": "WALLET_NOT_FOUND"},
    },
)
def archive_wallet(
    wallet_id: str,
    db: DbDep,
    current_user: CurrentUserDep,
) -> WalletArchiveRead:
    result = wallet_service.archive_wallet(db, owner=current_user, wallet_id=wallet_id)
    db.commit()
    return result
