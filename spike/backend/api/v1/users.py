"""Feature-01 endpoints: invite (US-01-01), activate (US-01-02), list (US-01-03)."""

from fastapi import APIRouter, BackgroundTasks, Query, status

from app.core.deps import CurrentUserDep, DbDep, EmailSenderDep, SettingsDep
from app.models.user import UserStatus
from app.repositories import user_repo
from app.schemas.invitation import InvitationCreate, InvitationRead
from app.schemas.user import ActivationPreflight, ActivationRequest, UserRead
from app.services import activation_service, invitation_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/invitations",
    response_model=InvitationRead,
    status_code=status.HTTP_201_CREATED,
    summary="US-01-01 — invite a family member by email",
)
def create_invitation(
    payload: InvitationCreate,
    db: DbDep,
    settings: SettingsDep,
    sender: EmailSenderDep,
    current_user: CurrentUserDep,
    background_tasks: BackgroundTasks,
) -> InvitationRead:
    invitation = invitation_service.create_invitation(
        db,
        email=payload.email,
        settings=settings,
        invited_by_id=current_user.id,
    )
    # Commit before dispatch: an email must never advertise a token that was
    # rolled back. The reverse order can hand out an unusable link.
    db.commit()
    db.refresh(invitation.user)

    dispatch_kwargs = {
        "sender": sender,
        "settings": settings,
        "recipient": invitation.user.email,
        "raw_token": invitation.raw_token,
    }

    if settings.email_send_mode == "sync":
        # Surfaces EmailDeliveryError as a 502 — useful while first wiring Gmail up.
        invitation_service.send_invitation_email(**dispatch_kwargs)  # type: ignore[arg-type]
    else:
        background_tasks.add_task(
            invitation_service.send_invitation_email_safely, **dispatch_kwargs
        )

    return InvitationRead.model_validate(invitation.user)


@router.get(
    "/activate",
    response_model=ActivationPreflight,
    summary="US-01-02 pre-flight — is this invitation token still usable?",
)
def check_activation_token(db: DbDep, token: str = Query(min_length=1)) -> ActivationPreflight:
    user = activation_service.resolve_invitation(db, token)
    assert user.token_expires_at is not None  # guaranteed by resolve_invitation
    return ActivationPreflight(email=user.email, token_expires_at=user.token_expires_at)


@router.post(
    "/activate",
    response_model=UserRead,
    summary="US-01-02 — set name + password and activate the account",
)
def activate_account(payload: ActivationRequest, db: DbDep) -> UserRead:
    user = activation_service.activate(
        db,
        raw_token=payload.token,
        full_name=payload.full_name,
        password=payload.password,
    )
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)


@router.get(
    "",
    response_model=list[UserRead],
    summary="US-01-03 — list family users and their onboarding state",
)
def list_users(
    db: DbDep,
    current_user: CurrentUserDep,
    user_status: UserStatus | None = Query(default=None, alias="status"),
) -> list[UserRead]:
    users = user_repo.list_users(db, user_status)
    return [UserRead.model_validate(u) for u in users]
