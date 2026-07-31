"""User Management endpoints (SDS §6.3 UM-API-01).

Constitution AR-02 — a thin router. It binds the payload, resolves dependencies,
calls the service, **commits once**, schedules the background send, and formats
the response. No queries and no business rules live here.
"""

from fastapi import APIRouter, BackgroundTasks, status

from app.core import clock
from app.core.deps import AdminDep, DbDep, EmailSenderDep, SettingsDep
from app.schemas.invitation import InvitationRead, InviteCreate
from app.services import invitation_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/invite",
    response_model=InvitationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Send an email invitation (ADMIN)",
    description=(
        "Creates a PENDING account and an invitation carrying a token that expires "
        "24 hours from creation, then emails the activation link to the address. "
        "The invitation token is never returned — it reaches only the invited "
        "mailbox. Requires an ADMIN bearer token."
    ),
    responses={
        401: {"description": "NOT_AUTHENTICATED — credentials absent, invalid or expired"},
        403: {"description": "FORBIDDEN — authenticated, but not an ADMIN"},
        409: {"description": "USER_EMAIL_ALREADY_ACTIVE — the address already has an account"},
        422: {"description": "VALIDATION_ERROR — malformed, missing or over-long email"},
        502: {"description": "EMAIL_DELIVERY_FAILED — sync mode only; the mail was not sent"},
    },
)
def invite_user(
    payload: InviteCreate,
    background_tasks: BackgroundTasks,
    db: DbDep,
    settings: SettingsDep,
    sender: EmailSenderDep,
    # AdminDep chains through get_current_user, so 401 is raised before 403
    # (plan.md A8) and both before this function body runs (spec FR-15).
    admin: AdminDep,
) -> InvitationRead:
    result = invitation_service.create_invitation(
        db,
        raw_email=payload.email,
        invited_by=admin,
        settings=settings,
    )

    # AR-06 / spec BR-08: one commit covers both inserts. Nothing is emailed
    # before this line — an activation link for a rolled-back token would be a
    # promise the database never made.
    db.commit()
    db.refresh(result.user)
    db.refresh(result.invitation)

    if settings.email_send_mode == "sync":
        # spec EC-07 / FR-20: inline send, so a misconfiguration surfaces as 502
        # instead of being reported as success.
        invitation_service.send_invitation_email(
            sender=sender,
            settings=settings,
            to_email=result.user.email,
            raw_token=result.raw_token,
        )
    else:
        # plan.md A4 / spec FR-19: Gmail costs 1-3s, well past NFR-01's 300 ms
        # p95, so delivery runs after the response. A failure there is logged and
        # leaves the invitation re-invitable (spec EC-06, FR-21).
        background_tasks.add_task(
            invitation_service.send_invitation_email_safely,
            sender=sender,
            settings=settings,
            to_email=result.user.email,
            raw_token=result.raw_token,
        )

    # ensure_aware is required, not defensive. SQLite has no timestamp type, so a
    # column written as aware reads back *naive* after the refresh above — and
    # serialising that would emit "2026-08-01T02:58:56" with no offset, leaving
    # the client to guess the timezone of an expiry deadline (ADR-0004 rationale,
    # spike finding 4, CLAUDE.md §4).
    return InvitationRead(
        id=result.user.id,
        email=result.user.email,
        status=result.user.status,
        token_expires_at=clock.ensure_aware(result.invitation.expires_at),
        created_at=clock.ensure_aware(result.user.created_at),
        message=result.message,
    )
