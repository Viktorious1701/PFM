# Postman — UM-US-01 Invite a User

Import `pfm-api.postman_collection.json`.

## Setup

```bash
cd backend
uv run alembic upgrade head

# Registration is invitation-only, so the first ADMIN cannot be invited —
# it has to be created directly. This closes that bootstrap cycle.
uv run python -m app.cli create-admin --email boss@example.com --password 'Str0ng-Passw0rd!'

# Prints a bearer token. Paste it into the `admin_token` collection variable.
uv run python -m app.cli mint-token --email boss@example.com

uv run uvicorn app.main:app --reload --port 8000
```

`mint-token` is a **development** helper. Issuing tokens is properly the job of
`POST /api/v1/auth/login`, which belongs to SS-US-01 and is not built yet
(`specs/001-user-onboarding/plan.md` A11). Once it exists, log in instead.

## Where the activation link goes

With no SMTP credentials the server logs a warning and uses a recording sender,
so nothing is actually emailed. The invitation is still created. To see a real
message, set `SMTP_USER` / `SMTP_PASSWORD` in `.env` to a Gmail address plus a
16-character App Password (a normal Google password is rejected by SMTP AUTH).

The raw token is never in an API response — only in the email. That is the point
of AC-08, and the `AC-01` request's description says what to check.

## Order matters for two requests

Run `AC-01` first, then `EC-02` immediately after with the same `new_email`: the
address is now `PENDING`, so the second call re-invites it, rotates the token and
supersedes the first invitation. Run `AC-01` twice by accident and you get the
same thing — change `new_email` between runs if you want a fresh 201.

## Two requests you cannot run yet

| Request | Why | Covered by |
| :-- | :-- | :-- |
| **AC-04** non-ADMIN → 403 | Needs an ACTIVE user whose role is `USER`. `create-admin` only makes ADMINs, and an invited account stays `PENDING` until UM-US-02 (activate) is built — a `PENDING` account cannot hold a token at all. | pytest `TC-11` — `uv run pytest -k non_admin` |
| **EC-07** sync failure → 502 | Needs `EMAIL_SEND_MODE=sync` **and** SMTP credentials that fail to authenticate. Fully unconfigured SMTP falls back to a sender that always succeeds, so you get 201. | pytest `TC-20` — `uv run pytest -k sync_mode` |

Everything else in the collection runs against a stock local setup.

## Swagger

`/docs` (Swagger UI) and `/redoc` are both live.

Click **Authorize** (top right), paste **only the JWT**, and Authorize. Swagger
adds the `Bearer ` prefix itself, and the padlock then applies to every request.

Do **not** look for an `authorization` field among the parameters — there isn't
one. The endpoint declares a bearer security scheme, so the header is managed by
the Authorize dialog. If you send the raw JWT as an `Authorization` header
yourself, remember the prefix: `Authorization: Bearer <token>`. A bare token is a
401, and the message is deliberately the same as for an invalid one, so it will
not tell you the prefix is what's missing.

Tokens last 60 minutes (`JWT_TTL_MINUTES`). An expired one is also a 401 — mint a
fresh one if a request that worked earlier starts failing.

Note that FastAPI ≥0.141 makes `include_router` lazy, so to list routes
programmatically read `app.openapi()["paths"]` — `app.routes` yields
`_IncludedRouter` objects with no `.path`.
