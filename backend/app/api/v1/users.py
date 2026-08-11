"""User Management endpoints (SDS §6.3 UM-API-01, UM-API-02, UM-API-04)."""

from fastapi import APIRouter, BackgroundTasks, Query, status

from app.core import clock
from app.core.deps import AdminDep, DbDep, EmailSenderDep, SettingsDep
from app.schemas.activation import ActivateRequest, ActivationResult, TokenStateRead
from app.schemas.invitation import InvitationRead, InviteCreate
from app.schemas.user import UserListRead
from app.services import activation_service, invitation_service, user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/invite",
    response_model=InvitationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Send an email invitation (ADMIN)",
    description=(
        "Creates a PENDING account and an invitation carrying a token that expires "
        "24 hours from creation, then emails the activation link to the address."
    ),
    responses={
        401: {"description": "NOT_AUTHENTICATED"},
        403: {"description": "FORBIDDEN"},
        409: {"description": "USER_EMAIL_ALREADY_ACTIVE or USER_EMAIL_DEACTIVATED"},
        422: {"description": "VALIDATION_ERROR"},
        502: {"description": "EMAIL_DELIVERY_FAILED"},
    },
)
def invite_user(
    payload: InviteCreate,
    background_tasks: BackgroundTasks,
    db: DbDep,
    settings: SettingsDep,
    sender: EmailSenderDep,
    admin: AdminDep,
) -> InvitationRead:
    result = invitation_service.create_invitation(
        db,
        raw_email=payload.email,
        invited_by=admin,
        settings=settings,
    )

    db.commit()
    db.refresh(result.user)
    db.refresh(result.invitation)

    if settings.email_send_mode == "sync":
        invitation_service.send_invitation_email(
            sender=sender,
            settings=settings,
            to_email=result.user.email,
            raw_token=result.raw_token,
        )
    else:
        background_tasks.add_task(
            invitation_service.send_invitation_email_safely,
            sender=sender,
            settings=settings,
            to_email=result.user.email,
            raw_token=result.raw_token,
        )

    return InvitationRead(
        id=result.user.id,
        email=result.user.email,
        status=result.user.status,
        token_expires_at=clock.ensure_aware(result.invitation.expires_at),
        created_at=clock.ensure_aware(result.user.created_at),
        message=result.message,
    )


@router.get(
    "/activate",
    response_model=TokenStateRead,
    status_code=status.HTTP_200_OK,
    summary="Check invitation token state (Public)",
    description=(
        "Reports whether an invitation token is usable, expired, or not usable "
        "without consuming it. Used by the activation form to guide the user (UXR-04)."
    ),
)
def check_activation_token_state(
    token: str,
    db: DbDep,
) -> TokenStateRead:
    return activation_service.check_token_state(db, raw_token=token)


@router.post(
    "/activate",
    response_model=ActivationResult,
    status_code=status.HTTP_200_OK,
    summary="Activate user account with token (Public)",
    description=(
        "Activates a PENDING user account using a valid invitation token, "
        "storing their full name and a hashed password. Sets status to ACTIVE "
        "and marks the invitation ACCEPTED."
    ),
    responses={
        400: {"description": "INVITATION_TOKEN_EXPIRED or INVITATION_TOKEN_INVALID"},
        422: {"description": "VALIDATION_ERROR — malformed password or full name"},
    },
)
def activate_user(
    payload: ActivateRequest,
    db: DbDep,
) -> ActivationResult:
    result = activation_service.activate_account(
        db,
        raw_token=payload.token,
        full_name=payload.full_name,
        password=payload.password,
    )
    db.commit()
    return result


@router.get(
    "",
    response_model=UserListRead,
    status_code=status.HTTP_200_OK,
    summary="List all users (ADMIN)",
    description=(
        "Returns every invited and active account's email, full name, status, "
        "and creation date, newest first, paginated with an accurate total count."
    ),
    responses={
        401: {"description": "NOT_AUTHENTICATED"},
        403: {"description": "FORBIDDEN"},
        422: {"description": "VALIDATION_ERROR — page or page_size out of range"},
    },
)
def list_users(
    db: DbDep,
    admin: AdminDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> UserListRead:
    """Pure read — no `db.commit()` (plan.md A4)."""
    return user_service.list_users(db, page=page, page_size=page_size)
