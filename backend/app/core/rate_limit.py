"""The guest-trial rate limiter (SS-US-03 plan.md A10, SDS §7.3, SEC-11).

One `slowapi` limiter, used on exactly one route: `POST /api/v1/auth/guest`,
the one public route that creates server-side rows for anyone on the internet.
The invite and activate limits SEC-11 names stay deferred (UM-US-01 T-13,
UM-US-02 T-08).

Keyed on the client address uvicorn reports (`request.client.host`). Behind
Tailscale Funnel that is the visitor's address only because uvicorn's proxy
headers handling replaces the tunnel's 127.0.0.1 with the forwarded client —
plan.md A11, confirmed at the Deploy step (T-15).

In-memory storage: per process, reset on restart — enough for one uvicorn
process on one laptop (ENV-06). Tests reset it between tests (TST-08).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import Settings, get_settings

limiter = Limiter(key_func=get_remote_address)

# The limit string comes from the app's own settings (A16). slowapi evaluates a
# callable limit per request but passes it no request, so the value the
# running app was built with is held here; `create_app` sets it.
_guest_rate_limit: str = get_settings().guest_rate_limit


def configure(settings: Settings) -> None:
    """Bind the guest-trial limit to the settings the app was created with."""
    global _guest_rate_limit
    _guest_rate_limit = settings.guest_rate_limit


def guest_rate_limit() -> str:
    """The current per-client limit for starting a guest trial, e.g. "5/hour"."""
    return _guest_rate_limit
