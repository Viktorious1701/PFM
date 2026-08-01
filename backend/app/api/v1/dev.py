"""Dev-only tooling (UM-US-01 A14).

`GET /api/v1/dev/outbox` lets an ADMIN read activation links written by
`FileOutboxSender` (A13) without a real mailbox — for this environment, where
the only real inbox belongs to whichever address happens to be configured for
Gmail SMTP.

This does **not** widen constitution API-08's public-endpoint list: the route
requires `AdminDep`, same as `/users` list. It does **not** touch
`InvitationRead` either, so UM-US-01 AC-08/FR-13 (the invite response itself
never carries a token) stays exactly as true as before this route existed —
this is a separate, authenticated read of already-sent mail, not a new field
on an existing response.

**Refuses to exist in production** (`settings.environment == "production"`),
returning 404 rather than merely relying on it never being called — an
endpoint that can be reached is a bigger attack surface than one that cannot.
"""

import re
from pathlib import Path

from fastapi import APIRouter
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.deps import AdminDep, SettingsDep
from app.schemas.dev import OutboxList, OutboxMessage

router = APIRouter(prefix="/dev", tags=["dev"])

_URL_RE = re.compile(r"https?://\S+")
_MAX_MESSAGES = 20


@router.get(
    "/outbox",
    response_model=OutboxList,
    summary="Read recent outbox messages (ADMIN, non-production only)",
    description=(
        "Lists the most recent messages written by the file outbox transport "
        "(EMAIL_TRANSPORT=outbox), each with its activation link if present. "
        "404s outside development — never present in a production deployment."
    ),
    responses={
        401: {"description": "NOT_AUTHENTICATED"},
        403: {"description": "FORBIDDEN — authenticated, but not an ADMIN"},
        404: {"description": "Not found — this route does not exist outside development"},
    },
)
def read_outbox(
    admin: AdminDep,
    settings: SettingsDep,
) -> OutboxList:
    if settings.environment == "production":
        raise StarletteHTTPException(status_code=404, detail="Not Found")

    directory = Path(settings.outbox_dir)
    if not directory.is_dir():
        return OutboxList(messages=[])

    files = sorted(directory.glob("*.eml"), reverse=True)[:_MAX_MESSAGES]
    messages = [_parse_message(f) for f in files]
    return OutboxList(messages=messages)


def _parse_message(path: Path) -> OutboxMessage:
    content = path.read_text(encoding="utf-8")
    to = ""
    sent_at = ""
    for line in content.splitlines():
        if line.startswith("To: "):
            to = line.removeprefix("To: ").strip()
        elif line.startswith("Date: "):
            sent_at = line.removeprefix("Date: ").strip()
        elif line == "":
            break

    url_match = _URL_RE.search(content)
    return OutboxMessage(
        to=to, sent_at=sent_at, activation_url=url_match.group(0) if url_match else None
    )
