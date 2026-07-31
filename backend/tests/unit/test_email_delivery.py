"""Unit tests for the SMTP sender and the email body.

Supporting coverage, not test_cases.md TCs. The real network path is TC-22's job
(opt-in). What is asserted here is the failure mapping — the part that decides
whether spec EC-07 produces a 502 or an unhandled 500.
"""

import smtplib
from unittest.mock import MagicMock, patch

import pytest

from app.services.email.sender import (
    EmailDeliveryFailed,
    EmailMessage,
    RecordingEmailSender,
)
from app.services.email.smtp import GmailSmtpSender
from app.services.email.templates import build_activation_url, build_invitation_email

MESSAGE = EmailMessage(to="x@example.com", subject="s", text_body="t", html_body="<p>h</p>")


def sender(**overrides: object) -> GmailSmtpSender:
    kwargs: dict[str, object] = {
        "host": "smtp.example.com",
        "port": 587,
        "user": "u@example.com",
        "password": "app-password",
        "from_address": "PFM <u@example.com>",
    }
    kwargs.update(overrides)
    return GmailSmtpSender(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize("missing", ["user", "password"])
def test_absent_credentials_fail_before_connecting(missing: str) -> None:
    """spec EC-07: no credentials is a delivery failure, not a silent success.

    Checked before opening a socket so the error names the real cause instead of
    an opaque auth rejection.
    """
    with patch("smtplib.SMTP") as smtp:
        with pytest.raises(EmailDeliveryFailed, match="not configured"):
            sender(**{missing: ""}).send(MESSAGE)
        smtp.assert_not_called()


def test_an_smtp_error_becomes_a_delivery_failure() -> None:
    """The service layer only knows EmailDeliveryFailed; smtplib types stop here."""
    with patch("smtplib.SMTP") as smtp:
        smtp.return_value.__enter__.return_value.login.side_effect = (
            smtplib.SMTPAuthenticationError(535, b"bad credentials")
        )
        with pytest.raises(EmailDeliveryFailed):
            sender().send(MESSAGE)


def test_a_network_error_becomes_a_delivery_failure() -> None:
    """OSError covers an unreachable host, which is not an SMTPException."""
    with (
        patch("smtplib.SMTP", side_effect=OSError("unreachable")),
        pytest.raises(EmailDeliveryFailed),
    ):
        sender().send(MESSAGE)


def test_a_successful_send_uses_starttls_and_both_alternatives() -> None:
    """STARTTLS on 587 is what Gmail requires; plain SMTP is rejected."""
    with patch("smtplib.SMTP") as smtp:
        connection = MagicMock()
        smtp.return_value.__enter__.return_value = connection

        sender().send(MESSAGE)

        connection.starttls.assert_called_once()
        connection.login.assert_called_once_with("u@example.com", "app-password")
        connection.send_message.assert_called_once()

        mime = connection.send_message.call_args[0][0]
        assert mime["To"] == "x@example.com"
        # Multipart: a text-only client must still be able to activate.
        assert mime.is_multipart()


def test_the_activation_url_substitutes_the_token_without_format_parsing() -> None:
    """`replace`, not `format` — a real URL may contain braces `format` would choke on."""
    url = build_activation_url("https://app.example/activate?token={token}&next={a}", "abc123")
    assert url == "https://app.example/activate?token=abc123&next={a}"


def test_the_invitation_body_carries_the_link_in_both_alternatives() -> None:
    message = build_invitation_email(
        to_email="invitee@example.com",
        raw_token="TOK",
        activation_url_template="https://app.example/activate?token={token}",
        expires_in_hours=24,
    )

    expected = "https://app.example/activate?token=TOK"
    assert expected in message.text_body
    assert expected in message.html_body
    assert "24 hours" in message.text_body
    assert message.to == "invitee@example.com"


def test_the_recording_sender_can_be_told_to_fail() -> None:
    """The double drives spec EC-06 and EC-07 in the integration tests."""
    recorder = RecordingEmailSender()
    recorder.send(MESSAGE)
    assert recorder.last == MESSAGE

    failing = RecordingEmailSender(fail=True)
    with pytest.raises(EmailDeliveryFailed):
        failing.send(MESSAGE)
    assert failing.sent == []
    assert failing.last is None
