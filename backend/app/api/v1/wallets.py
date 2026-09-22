"""Wallet Management endpoints (SDS §6.3 WM-API-01)."""

from fastapi import APIRouter, status

from app.core.deps import CurrentUserDep, DbDep
from app.schemas.wallet import WalletCreate, WalletRead
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
