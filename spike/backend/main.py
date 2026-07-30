"""App factory, exception handlers, and the two non-API routes."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import AppError, ValidationError

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "Family Budget & Expense Tracker — Feature-01 (User Onboarding & Access "
            "Control). Invite-only registration: US-01-01 invite, US-01-02 activate, "
            "US-01-03 list."
        ),
    )

    _register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/health", tags=["ops"], summary="Liveness probe")
    def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    @app.get(
        "/.well-known/assetlinks.json",
        tags=["ops"],
        summary="Android App Links verification (reserved)",
    )
    def assetlinks() -> JSONResponse:
        """Empty until the first signed Android build exists.

        Android only opens https://<domain>/activate in the app if this file
        lists the app's package name and signing-cert SHA-256. Serving the route
        now means no deployment shape change later.
        """
        if not (settings.android_package_name and settings.android_cert_sha256):
            return JSONResponse([])
        return JSONResponse(
            [
                {
                    "relation": ["delegate_permission/common.handle_all_urls"],
                    "target": {
                        "namespace": "android_app",
                        "package_name": settings.android_package_name,
                        "sha256_cert_fingerprints": [settings.android_cert_sha256],
                    },
                }
            ]
        )

    @app.get("/activate", response_class=HTMLResponse, include_in_schema=False)
    def activate_landing(token: str = "") -> HTMLResponse:
        """Minimal fallback so the emailed link does something in a browser.

        Deliberately unstyled and dependency-free — the real client is the mobile
        app (a later round). Delete this route and point ACTIVATION_URL_TEMPLATE
        at the app's deep link if you would rather keep the backend pure API.
        """
        return HTMLResponse(_ACTIVATE_HTML.replace("__TOKEN__", token))

    return app


_ACTIVATE_HTML = """<!doctype html>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Activate your PFM account</title>
<body style="font-family:sans-serif;max-width:26rem;margin:3rem auto;padding:0 1rem">
<h2>Activate your account</h2>
<form id="f">
  <input type="hidden" id="token" value="__TOKEN__">
  <p><label>Full name<br><input id="full_name" required style="width:100%;padding:.5rem"></label>
  <p><label>Password (min 8 chars)<br>
     <input id="password" type="password" minlength="8" required style="width:100%;padding:.5rem"></label>
  <p><button style="padding:.6rem 1.2rem">Activate</button>
</form>
<pre id="out" style="white-space:pre-wrap"></pre>
<script>
document.getElementById('f').onsubmit = async (e) => {
  e.preventDefault();
  const r = await fetch('/api/v1/users/activate', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      token: document.getElementById('token').value,
      full_name: document.getElementById('full_name').value,
      password: document.getElementById('password').value,
    }),
  });
  const body = await r.json();
  document.getElementById('out').textContent =
    (r.ok ? 'Activated. You can log in now.\\n\\n' : 'Failed (' + r.status + ')\\n\\n')
    + JSON.stringify(body, null, 2);
};
</script>
</body>
"""


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_envelope())

    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Reshape Pydantic's 422 into the same envelope as domain errors.

        US-01-01 AC-1 (malformed email) lands here.
        """
        details = {
            "fields": [
                {
                    "location": list(err.get("loc", [])),
                    "message": err.get("msg", ""),
                    "type": err.get("type", ""),
                }
                for err in exc.errors()
            ]
        }
        wrapped = ValidationError(details=details)
        return JSONResponse(status_code=wrapped.status_code, content=wrapped.to_envelope())

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        codes = {401: "NOT_AUTHENTICATED", 403: "FORBIDDEN", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": codes.get(exc.status_code, "HTTP_ERROR"),
                    "message": str(exc.detail),
                    "details": {},
                }
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error")
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Unexpected server error.",
                    "details": {},
                }
            },
        )


app = create_app()
