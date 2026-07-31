"""Structured audit emitter.

spec AC-09 / FR-17, constitution LA-01, LA-02, LA-04.

plan.md A9: audit events are structured log lines, not an `activity_logs` table.
SDS §7.1.10 and §10.6 specify structured logs, and no story in scope reads
events back, so a queryable store would be unrequested scope. Revisit if an
audit-retrieval story appears.

LA-02 requires five fields: actor, timestamp, action, target, result.
LA-01 forbids secrets — **no caller may pass a token, password or hash.**
"""

import logging
from typing import Any, Literal

from app.core import clock

logger = logging.getLogger("app.audit")

AuditResult = Literal["SUCCESS", "FAILURE"]

# Substrings that must never appear in an audit key. Cheap guard against a
# future caller casually widening `extra` to include a secret.
_FORBIDDEN_KEYS = ("token", "password", "hash", "secret")


def record(
    *,
    action: str,
    actor_id: str | None,
    target: str,
    result: AuditResult,
    **extra: Any,
) -> None:
    """Emit one audit event.

    `target` is the thing acted upon — for UM-US-01, the invited email address.
    `actor_id` is None only for an unauthenticated attempt.
    """
    for key in extra:
        if any(word in key.lower() for word in _FORBIDDEN_KEYS):
            raise ValueError(f"Audit field {key!r} looks like a secret; LA-01 forbids logging it.")

    event: dict[str, Any] = {
        "audit": True,
        "action": action,
        "actor_id": actor_id,
        "target": target,
        "result": result,
        "timestamp": clock.utcnow().isoformat(),
        **extra,
    }
    logger.info("audit %s %s %s", action, result, event)
