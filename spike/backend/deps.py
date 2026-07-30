"""Shared FastAPI dependencies."""

from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import NotAuthenticatedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserStatus
from app.repositories import user_repo
from app.services.email.sender import EmailSender
from app.services.email.smtp import GmailSmtpSender

# auto_error=False so a missing header raises our own enveloped error rather than
# FastAPI's bare {"detail": ...} shape.
_bearer = HTTPBearer(auto_error=False)

SettingsDep = Annotated[Settings, Depends(get_settings)]
DbDep = Annotated[Session, Depends(get_db)]


def get_email_sender(settings: SettingsDep) -> EmailSender:
    """Overridden in tests with a recorder — the only place SMTP is constructed."""
    return GmailSmtpSender(settings)


EmailSenderDep = Annotated[EmailSender, Depends(get_email_sender)]


def get_current_user(
    db: DbDep,
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> User:
    """Enforces 'Caller is authenticated' for US-01-01 and US-01-03."""
    if credentials is None or not credentials.credentials:
        raise NotAuthenticatedError()

    try:
        payload = decode_access_token(credentials.credentials, settings)
    except jwt.ExpiredSignatureError as exc:
        raise NotAuthenticatedError("Access token has expired.") from exc
    except jwt.PyJWTError as exc:
        raise NotAuthenticatedError("Access token is invalid.") from exc

    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise NotAuthenticatedError("Access token is missing a subject.")

    user = user_repo.get_by_id(db, subject)
    if user is None or user.status is not UserStatus.ACTIVE:
        # Covers a token minted for an account that was since removed.
        raise NotAuthenticatedError("Account for this token is no longer active.")

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
