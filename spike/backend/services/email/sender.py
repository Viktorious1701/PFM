"""The seam that makes US-01-01 AC-5 testable without sending mail."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    text_body: str
    html_body: str


class EmailSender(Protocol):
    """One production implementation (GmailSmtpSender); tests inject a recorder."""

    def send(self, message: EmailMessage) -> None: ...
