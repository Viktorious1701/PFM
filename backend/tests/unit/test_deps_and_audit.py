"""Unit tests for dependency wiring and the audit guard.

Supporting coverage, not test_cases.md TCs.
"""

import logging

import pytest

from app.core import audit
from app.core.config import Settings
from app.core.deps import get_email_sender
from app.services.email.sender import RecordingEmailSender
from app.services.email.smtp import GmailSmtpSender


def test_a_real_smtp_sender_is_used_once_credentials_exist() -> None:
    settings = Settings(smtp_user="u@example.com", smtp_password="app-password")
    assert settings.smtp_configured

    assert isinstance(get_email_sender(settings), GmailSmtpSender)


@pytest.mark.parametrize(
    ("user", "password"),
    [("", ""), ("u@example.com", ""), ("", "app-password")],
)
def test_the_recording_double_is_used_when_credentials_are_incomplete(
    user: str, password: str, caplog: pytest.LogCaptureFixture
) -> None:
    """A half-configured SMTP block is not configured.

    Falling back keeps the invite flow working for a developer without a Gmail
    App Password. It warns loudly so the fallback is never mistaken for delivery.
    """
    settings = Settings(smtp_user=user, smtp_password=password)
    assert not settings.smtp_configured

    with caplog.at_level(logging.WARNING):
        sender = get_email_sender(settings)

    assert isinstance(sender, RecordingEmailSender)
    assert "SMTP is not configured" in caplog.text


def test_an_audit_record_carries_the_five_required_fields(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """LA-02: actor, timestamp, action, target, result."""
    with caplog.at_level(logging.INFO, logger="app.audit"):
        audit.record(
            action="USER_INVITED",
            actor_id="admin-1",
            target="invitee@example.com",
            result="SUCCESS",
        )

    message = caplog.text
    for expected in ("USER_INVITED", "admin-1", "invitee@example.com", "SUCCESS", "timestamp"):
        assert expected in message


@pytest.mark.parametrize(
    "field", ["token", "raw_token", "password", "password_hash", "token_hash", "client_secret"]
)
def test_audit_refuses_a_field_that_looks_like_a_secret(field: str) -> None:
    """LA-01 as an executable guard, not a code-review convention.

    A future caller widening `extra` to include a token gets an exception rather
    than a quiet leak into the log.
    """
    with pytest.raises(ValueError, match="LA-01"):
        audit.record(
            action="USER_INVITED",
            actor_id="admin-1",
            target="invitee@example.com",
            result="SUCCESS",
            **{field: "sensitive"},
        )


def test_a_failure_result_is_recordable_without_an_actor(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Background delivery failure has no request context, so no actor (spec EC-06)."""
    with caplog.at_level(logging.INFO, logger="app.audit"):
        audit.record(
            action="INVITATION_EMAIL_FAILED",
            actor_id=None,
            target="invitee@example.com",
            result="FAILURE",
        )

    assert "INVITATION_EMAIL_FAILED" in caplog.text
    assert "FAILURE" in caplog.text
