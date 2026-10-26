"""System Security endpoints (SDS §6.3 SS-API-01, SS-API-02, SS-API-03).

Constitution AR-02 — a thin router. It binds the payload, calls the service,
and formats the response. No queries and no business rules live here.
"""

from fastapi import APIRouter, Request, status

from app.core.deps import CurrentUserDep, DbDep, SettingsDep
from app.core.rate_limit import guest_rate_limit, limiter
from app.schemas.auth import GuestSessionRead, LoginRequest, LogoutResult, TokenResponse
from app.services import auth_service, guest_service

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


@router.post(
    "/guest",
    response_model=GuestSessionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Start a guest trial (Public)",
    description=(
        "Creates a temporary guest account holding one example wallet with one "
        "example expense, and signs the caller in as that guest until the trial "
        "ends 7 days from now. No credentials and no body. The guest has no real "
        "email and no password, is never upgraded, and is deleted with all its "
        "data when the trial ends; signing out does not delete it."
    ),
    responses={
        429: {"description": "RATE_LIMIT_EXCEEDED — too many trials started from this address"},
        503: {"description": "GUEST_LIMIT_REACHED — the number of live trials is at its cap"},
    },
)
@limiter.limit(guest_rate_limit)
def start_guest_trial(request: Request, db: DbDep, settings: SettingsDep) -> GuestSessionRead:
    """Public by necessity: a visitor holds no credential (constitution API-08,
    plan.md A3). `request` is read only by the limiter's decorator (AR-05)."""
    result = guest_service.start(db, settings=settings)
    db.commit()
    return result
