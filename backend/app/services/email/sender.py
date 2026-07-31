"""Email sending seam.

A Protocol rather than a base class so the test double is a plain object with no
inheritance, and so the service depends on the capability rather than on SMTP.

Constitution AR-05: services receive an `EmailSender`, never a framework object.
TST-07: SMTP is mocked by default; real delivery is opt-in.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EmailMessage:
    """One outbound message.

    Both alternatives carry the activation URL, because a recipient whose client
    strips HTML must still be able to activate (test_cases TC-03 asserts the URL
    is present in both).
    """

    to: str
    subject: str
    text_body: str
    html_body: str


class EmailDeliveryFailed(Exception):
    """Raised by a sender when delivery could not be completed.

    Translated to a 502 `EMAIL_DELIVERY_FAILED` in sync mode (spec EC-07,
    FR-20), or logged and swallowed in background mode (EC-06, FR-21). Either
    way the invitation stays recorded and re-invitable — never a silent success
    (SC-09).
    """


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> None:
        """Deliver the message, or raise `EmailDeliveryFailed`."""
        ...


class RecordingEmailSender:
    """Test double: records instead of sending (TST-07).

    Lives in application code rather than in the test tree because the dev
    server also uses it when no SMTP credentials are configured — that way a
    developer without a Gmail App Password still gets a working invite flow, and
    the recorded message is inspectable.
    """

    def __init__(self, *, fail: bool = False) -> None:
        self.sent: list[EmailMessage] = []
        self.fail = fail

    def send(self, message: EmailMessage) -> None:
        if self.fail:
            raise EmailDeliveryFailed("RecordingEmailSender configured to fail")
        self.sent.append(message)

    @property
    def last(self) -> EmailMessage | None:
        return self.sent[-1] if self.sent else None
