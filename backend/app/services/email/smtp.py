"""Gmail SMTP sender (SDS §13).

Requires 2FA on the account plus a 16-character App Password — a normal Google
password is rejected by SMTP AUTH.

Constitution SEC-09: credentials come from the environment, never the source.
LA-01: nothing here logs the message body, which contains the raw token.
"""

import logging
import smtplib
from email.message import EmailMessage as MimeMessage

from app.services.email.sender import EmailDeliveryFailed, EmailMessage

logger = logging.getLogger(__name__)


class GmailSmtpSender:
    """Sends over STARTTLS on port 587."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        from_address: str,
        timeout: float = 10.0,
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.from_address = from_address
        self.timeout = timeout

    def send(self, message: EmailMessage) -> None:
        # spec EC-07: absent credentials are a delivery failure, surfaced rather
        # than reported as success. Checked before connecting so the error names
        # the actual cause instead of an opaque auth rejection.
        if not self.user or not self.password:
            raise EmailDeliveryFailed(
                "SMTP credentials are not configured (SMTP_USER / SMTP_PASSWORD)."
            )

        mime = MimeMessage()
        mime["Subject"] = message.subject
        mime["From"] = self.from_address
        mime["To"] = message.to
        mime.set_content(message.text_body)
        mime.add_alternative(message.html_body, subtype="html")

        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as smtp:
                smtp.starttls()
                smtp.login(self.user, self.password)
                smtp.send_message(mime)
        except (smtplib.SMTPException, OSError) as exc:
            # Log the failure and the recipient, never the body — it holds the
            # raw activation token (LA-01).
            logger.warning("SMTP delivery to %s failed: %s", message.to, exc)
            raise EmailDeliveryFailed(str(exc)) from exc
