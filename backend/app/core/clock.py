"""Time access behind one seam.

Every TTL decision in this codebase goes through `utcnow()` so tests can freeze
time by monkeypatching a single function — no `freezegun` dependency needed.
"""

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Timezone-aware current UTC time."""
    return datetime.now(UTC)


def ensure_aware(value: datetime) -> datetime:
    """Attach UTC to a naive datetime.

    SQLite has no native timestamp type: SQLAlchemy stores datetimes as strings
    and drops the tzinfo, so a column written as aware reads back *naive*.
    Comparing that against an aware `utcnow()` raises TypeError. Every read of a
    stored datetime that gets compared or serialised passes through here, which
    keeps the same code correct on both SQLite and Postgres.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
