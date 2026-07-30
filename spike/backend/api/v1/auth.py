"""Login + whoami."""

from fastapi import APIRouter

from app.core.deps import CurrentUserDep, DbDep, SettingsDep
from app.core.security import create_access_token
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserRead
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Exchange email + password for a bearer token",
)
def login(payload: LoginRequest, db: DbDep, settings: SettingsDep) -> TokenResponse:
    user = auth_service.authenticate(db, email=payload.email, password=payload.password)
    token, expires_in = create_access_token(user.id, settings)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=UserRead, summary="The authenticated caller")
def me(current_user: CurrentUserDep) -> UserRead:
    return UserRead.model_validate(current_user)
