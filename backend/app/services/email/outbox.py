"""File-based outbox sender.

UM-US-01 A13: an alternate `EmailSender` for environments where no real
mailbox is available to read an activation link from. Writes each message as
an `.eml` file instead of sending it — a real client can open the file
directly, and the dev outbox route (A14) can list and parse them.

This is the only `EmailSender` implementation that *persists* — the existing
`RecordingEmailSender` is rebuilt fresh per request by `get_email_sender`
(`core/deps.py`), so it cannot double as an outbox across requests.
"""

import re
from datetime import datetime
from pathlib import Path

from app.core import clock
from app.services.email.sender import EmailDeliveryFailed, EmailMessage

_SAFE_CHARS = re.compile(r"[^A-Za-z0-9@._-]+")


def _safe_filename(to: str, timestamp: datetime) -> str:
    """A filesystem-safe, sortable name — timestamp first so `ls` sorts by send order."""
    stamp = timestamp.strftime("%Y%m%dT%H%M%S%f")
    safe_to = _SAFE_CHARS.sub("_", to)
    return f"{stamp}_{safe_to}.eml"


class FileOutboxSender:
    """Writes each message to `directory` as an RFC 5322-shaped `.eml` file."""

    def __init__(self, *, directory: Path) -> None:
        self.directory = directory

    def send(self, message: EmailMessage) -> None:
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            timestamp = clock.utcnow()
            path = self.directory / _safe_filename(message.to, timestamp)
            content = (
                f"To: {message.to}\n"
                f"Subject: {message.subject}\n"
                f"Date: {timestamp.isoformat()}\n"
                "\n"
                f"{message.text_body}\n"
            )
            path.write_text(content, encoding="utf-8")
        except OSError as exc:
            # Constitution AR-05-adjacent: any sender may fail; the service
            # layer already knows how to translate this into EC-06/EC-07's
            # documented outcomes (spec EmailDeliveryError -> 502 or logged).
            raise EmailDeliveryFailed(str(exc)) from exc
