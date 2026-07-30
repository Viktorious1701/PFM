# Spike post-mortem

**Date:** 2026-07-30 · **Outcome:** discarded and deleted from the working tree. Recoverable with `git show 56768c8` if a detail is ever needed.

> This document is the surviving record. Everything below was extracted before the code was removed, so nothing of value depended on keeping 1,746 lines of rejected implementation in the repository.

## What happened

An implementation-first attempt at Feature-01: **1,746 lines across 26 modules** — models, repositories, schemas, services, routers, an SMTP sender, a CLI, and one test file. Produced with **zero** spec, design, or test-plan artifacts. The single test file was never executed.

It was rejected by the user mid-build: *"we actually been skipped through a lot of phase here… currently we just jump straight into implementation, so i had a hard time understanding anything you write here."*

That is the correct call. The code may have been serviceable, but it was unreadable as a learning artifact because nothing upstream explained *why* it was shaped that way. Documentation written afterwards would have been reverse-engineered justification, not design.

## What it nonetheless proved

Worth keeping, because these are verified environment facts that the Foundation step no longer needs to rediscover:

1. **The stack installs and runs on this machine.** `uv sync` resolved cleanly on pinned CPython 3.13.14; `fastapi` 0.141.1, `sqlalchemy` 2.0.51, `pydantic` 2.13.4, `bcrypt` 5.0.0, `pyjwt` 2.13.0, `alembic` 1.18.5 all have 3.13 wheels — no compilation needed.
2. **Alembic autogenerate works against SQLite** with `render_as_batch=True` in `migrations/env.py`, which is required because SQLite cannot `ALTER` most things in place.
3. **FastAPI ≥0.141 makes `include_router` lazy.** `app.routes` yields `_IncludedRouter` objects with no `.path`, so route inventories must read `app.openapi()["paths"]`. This cost real debugging time; it is now recorded in `CLAUDE.md`.
4. **A clock seam is necessary, not optional.** SQLite stores datetimes without timezone, so a value written as aware reads back naive and comparing it to an aware `utcnow()` raises `TypeError`. `app/core/clock.py` (`utcnow` + `ensure_aware`) survived into the real codebase for this reason.
5. **bcrypt's 72-byte ceiling is a silent truncation**, not an error. It has to be rejected at the schema layer (constitution VL-04).
6. **The bootstrap problem is real.** Registration is invite-only, so with no ACTIVE user nobody can authenticate to send the first invitation. A `create-admin` command is required.

## What it got wrong

Beyond the process failure, the spike also **contradicted `SDS.md`**, which the user supplied after it was written. These are now settled rulings in `CLAUDE.md`:

| Spike | SDS requires |
| :-- | :-- |
| token columns on `users` | separate `invitations` table (§2.1, §4.3.3) |
| `PENDING` / `ACTIVE` | `PENDING_INVITATION` / `ACTIVE` / `DEACTIVATED` (§2.4.1) |
| no roles; any caller could invite | `users.role`; invite + list are ADMIN-only (§5.2) |
| nested `{"error": {"code": …}}` | flat `{"error_code", "message", "details"}` (§6.6) |
| `POST /users/invitations` | `POST /users/invite` (§6.3) |
| activation returned the user object | `{"status": "SUCCESS", "message": …}` (§6.4.2) |
| password min-length only | 8+ chars, 1 upper, 1 digit, 1 special (§7.1.5) |
| no rate limiting, no audit logging | `slowapi` (§7.3), structured audit logs (§7.1.10) |
| treated login as an unspecified gap | login is `US-02-01` / `SS-US-01`, a real MVP story |

## What was kept

Verified infrastructure only, because it was genuinely exercised:

- `pyproject.toml`, `uv.lock`, `.python-version` — dependency resolution proven
- `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako` — migration harness proven. The spike's own migration was **discarded along with the model it encoded**, because a schema must follow the approved domain model rather than precede it. The real migration is written at UM-US-01's Implement step (task `T-03`).
- `app/core/clock.py` — see finding 4
- `app/db/base.py`, `app/db/session.py` — engine and session wiring
- `app/core/config.py`, `app/core/errors.py`, `app/main.py` — trimmed to foundation; each story adds only what its spec justifies

## Lesson recorded

The cycle is not overhead to be optimised away. It is the deliverable. Working code that nobody can follow has negative value on a project whose purpose is learning the method.
