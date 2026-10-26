"""FastAPI application factory.

Health check, the exception handlers that guarantee the SDS §6.6 envelope, and
the v1 router. Each story appends its own router to `api.v1.router`.

Constitution: API-01, API-02, API-07, API-08.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import sessionmaker
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core import rate_limit
from app.core.config import Settings, get_settings
from app.core.errors import AppError, ValidationError
from app.db.session import build_engine
from app.services import guest_service

logger = logging.getLogger(__name__)

# Mapping for framework-raised HTTPExceptions so they match API-02/API-04.
_HTTP_ERROR_CODES = {
    401: "NOT_AUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    429: "RATE_LIMIT_EXCEEDED",
}


def _purge_ended_guests(settings: Settings) -> None:
    """SS-US-03 plan.md A9 / spec EC-04: trials that ended while the server was
    down are deleted as it starts, in a session of its own that commits.

    A failure is logged, not raised: access already ends at each trial's end
    regardless of deletion (A5, EC-02), so a failed purge must not keep the
    family's server from starting. The next trial start or `purge-guests`
    retries it.
    """
    engine = build_engine(settings.database_url)
    try:
        with sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)() as db:
            result = guest_service.purge_expired(db)
            db.commit()
        if result.guests:
            logger.info("startup purge removed %d ended guest trial(s)", result.guests)
    except Exception:
        logger.exception("startup purge of ended guest trials failed")
    finally:
        engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app_settings = settings

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        _purge_ended_guests(app_settings)
        yield

    # SS-US-03 plan.md A10: the guest-trial limit is the app's own setting.
    rate_limit.configure(settings)

    app = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
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

    app.state.limiter = rate_limit.limiter
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
    @app.exception_handler(RateLimitExceeded)
    async def _rate_limited(_request: Request, _exc: RateLimitExceeded) -> JSONResponse:
        """SS-US-03 plan.md A10: slowapi's own handler returns its own body;
        this keeps the 429 in the flat envelope (API-02)."""
        return JSONResponse(
            status_code=429,
            content={
                "error_code": _HTTP_ERROR_CODES[429],
                "message": "Too many requests. Please try again later.",
                "details": {},
            },
        )

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
