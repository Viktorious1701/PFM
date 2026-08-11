"""FastAPI application factory.

Health check, the exception handlers that guarantee the SDS §6.6 envelope, and
the v1 router. Each story appends its own router to `api.v1.router`.

Constitution: API-01, API-02, API-07, API-08.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import AppError, ValidationError

logger = logging.getLogger(__name__)

# Mapping for framework-raised HTTPExceptions so they match API-02/API-04.
_HTTP_ERROR_CODES = {
    401: "NOT_AUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    429: "RATE_LIMIT_EXCEEDED",
}


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "Personal & Family Finance Management API. "
            "Round 1 scope: US-02-01 login, US-01-01 invite, US-01-02 activate, "
            "US-01-03 list users."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _register_exception_handlers(app)

    @app.get("/health", tags=["ops"], summary="Liveness probe")
    def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    # API-01: everything business-facing lives under /api/v1.
    #
    # FastAPI >=0.141 makes include_router lazy, so `app.routes` yields
    # _IncludedRouter objects with no `.path`. To inventory routes, read
    # `app.openapi()["paths"]` instead (CLAUDE.md §3, spike finding 3).
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_envelope())

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        """VL-02: all field errors returned together, in the API-02 envelope."""
        wrapped = ValidationError(
            details={
                "fields": [
                    {
                        "location": [str(part) for part in err.get("loc", [])],
                        "message": err.get("msg", ""),
                        "type": err.get("type", ""),
                    }
                    for err in exc.errors()
                ]
            }
        )
        return JSONResponse(status_code=wrapped.status_code, content=wrapped.to_envelope())

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": _HTTP_ERROR_CODES.get(exc.status_code, "HTTP_ERROR"),
                "message": str(exc.detail),
                "details": {},
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled(_request: Request, _exc: Exception) -> JSONResponse:
        # LA-01: log the trace, but never leak internals to the client.
        logger.exception("unhandled error")
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_ERROR",
                "message": "Unexpected server error.",
                "details": {},
            },
        )


app = create_app()
