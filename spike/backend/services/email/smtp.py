"""Gmail SMTP delivery.

Gmail requires 2FA on the account plus a 16-character App Password; the normal
account password is rejected with 535. Submission port 587 + STARTTLS.
"""

import logging
import smtplib
from email.message import EmailMessage as MimeMessage

from app.core.config import Settings
from app.core.errors import EmailDeliveryError
from app.services.email.sender import EmailMessage

logger = logging.getLogger(__name__)


class GmailSmtpSender:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send(self, message: EmailMessage) -> None:
        settings = self._settings
        if not settings.smtp_configured:
            raise EmailDeliveryError(
                "SMTP credentials are not configured. Set SMTP_USER and SMTP_PASSWORD "
                "in backend/.env (Gmail needs a 16-char App Password, not your login "
                "password).",
                details={"smtp_host": settings.smtp_host},
            )

        mime = MimeMessage()
        mime["From"] = settings.email_from
        mime["To"] = message.to
        mime["Subject"] = message.subject
        mime.set_content(message.text_body)
        mime.add_alternative(message.html_body, subtype="html")

        try:
            with smtplib.SMTP(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_seconds,
            ) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(mime)
        except smtplib.SMTPAuthenticationError as exc:
            raise EmailDeliveryError(
                "Gmail rejected the SMTP credentials. Confirm 2FA is enabled and that "
                "SMTP_PASSWORD is an App Password.",
                details={"smtp_code": exc.smtp_code},
            ) from exc
        except (smtplib.SMTPException, OSError) as exc:
            raise EmailDeliveryError(
                f"SMTP delivery to {message.to} failed: {exc}",
            ) from exc

        logger.info("invitation email sent", extra={"recipient": message.to})
