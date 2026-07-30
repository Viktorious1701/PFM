# ADR-0005: One flat error envelope for every failure

**Status:** Accepted · **Date:** 2026-07-30
**Relates to:** SDS §6.6 · constitution API-02, API-04, VL-02 · plan Error flows

## Context

FastAPI produces at least three different error shapes out of the box: `{"detail": "..."}` for `HTTPException`, `{"detail": [{"loc": …, "msg": …}]}` for request-validation failures, and an HTML traceback or bare 500 for unhandled exceptions. `SDS.md` §6.6 specifies one shape:

```json
{"error_code": "INVITATION_TOKEN_EXPIRED", "message": "…", "details": {}}
```

A client that must branch on three shapes will get it wrong — and the mobile app (SDS §4.3.1) needs one predictable path to turn a failure into a message.

## Decision

Four exception handlers in `app/main.py`, so **no** response can escape in another shape:

| Handler | Covers | Produces |
| :-- | :-- | :-- |
| `AppError` | domain errors raised by services | the subclass's `error_code` + status |
| `RequestValidationError` | Pydantic payload failures | `422 VALIDATION_ERROR`, all field errors together in `details.fields` (VL-02) |
| `StarletteHTTPException` | framework-raised 401/403/404/405/429 | mapped `error_code` |
| `Exception` | anything unhandled | `500 INTERNAL_ERROR`, trace logged, internals never leaked (LA-01) |

`AppError` subclasses carry their own `status_code` and `error_code`, so raising `UserEmailAlreadyActiveError()` in a service is all that is needed — the router does not translate.

Note the envelope is **flat**: `error_code` at the top level, not nested under an `"error"` key. The spike used the nested form; the SDS is authoritative.

## Consequences

**Positive**
- One documented shape; verified in place — `GET /nope` already returns `{"error_code": "NOT_FOUND", …}`.
- Services throw domain errors and stay free of HTTP concepts (AR-05).
- Error codes are a stable contract, catalogued per story in `plan.md`, so clients branch on `error_code` rather than parsing prose.

**Negative**
- Diverges from FastAPI's documented default, so contributors expecting `detail` will be surprised. Mitigated by the handlers being in one file and this ADR.
- Every new domain error must define its `error_code` and status; forgetting means inheriting `INTERNAL_ERROR`/500. Caught by requiring each story's `plan.md` to list its error flows.
- The generic `Exception` handler can mask bugs during development if the log is not watched.

## Alternatives rejected

- **The nested `{"error": {"code": …}}` form** — arguably tidier for future top-level siblings, but contradicts SDS §6.6.
- **FastAPI defaults** — free, but pushes three-shape branching onto every client.
- **RFC 7807 `application/problem+json`** — a real standard with tooling, but heavier, and it would contradict the SDS for no benefit at this scale.
