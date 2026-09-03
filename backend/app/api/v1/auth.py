"""System Security endpoints (SDS §6.3 SS-API-01).

Constitution AR-02 — a thin router. It binds the payload, calls the service,
and formats the response. No queries and no business rules live here.
"""

from fastapi import APIRouter, status

from app.core.deps import CurrentUserDep, DbDep, SettingsDep
from app.schemas.auth import LoginRequest, LogoutResult, TokenResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and issue a JWT (Public)",
    description=(
        "Authenticates an ACTIVE account by email and password and returns a "
        "signed bearer token. No credentials are required to call this route."
    ),
    responses={
        401: {"description": "INVALID_CREDENTIALS — unknown email, wrong password, or deactivated"},
        403: {"description": "ACCOUNT_NOT_ACTIVATED — the account is still PENDING"},
        422: {"description": "VALIDATION_ERROR — malformed or missing email/password"},
    },
)
def login(
    payload: LoginRequest,
    db: DbDep,
    settings: SettingsDep,
) -> TokenResponse:
    return auth_service.authenticate(
        db,
        raw_email=payload.email,
        password=payload.password,
        settings=settings,
    )


@router.post(
    "/logout",
    response_model=LogoutResult,
    status_code=status.HTTP_200_OK,
    summary="End the caller's session",
    description=(
        "Confirms the caller's session has ended. Requires a currently valid "
        "bearer token — any Authenticated User, not only ADMIN, may call this. "
        "Performs no server-side revocation: the presented token continues to "
        "authenticate normally until its own natural expiry."
    ),
    responses={
        401: {
            "description": "NOT_AUTHENTICATED — no bearer token, or one that is malformed, "
            "has an invalid signature, or has expired"
        },
    },
)
def logout(current_user: CurrentUserDep) -> LogoutResult:
    return auth_service.logout(current_user)
