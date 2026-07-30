# ADR-0001: Toolchain, and SQLite for local development

**Status:** Accepted · **Date:** 2026-07-30 · **Deciders:** user + AI
**Relates to:** SDS §4.1, §4.5, §9.1.2 · constitution ENV-01…ENV-04

## Context

`SDS.md` §4.1/§4.5 specify PostgreSQL with Alembic migrations, deployed as a container on a PaaS. The development machine cannot provide that:

- **No Python package installer.** System Python is 3.14.4 with neither `pip` nor `ensurepip`. Installing `python3-pip` needs a sudo password the automation does not have.
- **Docker daemon unreachable.** The Docker CLI exists at `/mnt/c/Program Files/Docker/…` but WSL2 integration is disabled, so no PostgreSQL container can start.

## Decision

1. **`uv` is the only Python entry point.** Installed to `~/.local/bin` without sudo; it manages both dependencies and its own interpreter.
2. **CPython is pinned to 3.13** in `backend/.python-version`, not the system 3.14, so dependencies resolve to well-supported wheels rather than compiling from source.
3. **SQLite is the local and test database**; PostgreSQL remains the deployment target. The switch is one `DATABASE_URL` value.

## Consequences

**Positive** — zero-privilege setup; verified working (`uv sync` resolved, `alembic upgrade head` succeeded, `ruff`/`mypy` clean). Tests need no external service, so the suite runs anywhere.

**Negative — and these are real constraints on design, not just notes:**

| SQLite behaviour | Guard |
| :-- | :-- |
| Drops `tzinfo`; an aware datetime reads back naive, and comparing it to an aware `utcnow()` raises `TypeError` | `clock.ensure_aware()` on every stored-datetime read — ADR-0004 |
| Cannot `ALTER` most columns in place | `render_as_batch=True` in `migrations/env.py` |
| No native `UUID` type | `id` columns are `String(36)` UUID text, portable to both engines |
| Weaker concurrency than PostgreSQL | Concurrency edge cases (spec EC-05) are asserted through the unique index, not through simulated parallel writes |

**Nothing may depend on SQLite-specific behaviour** (constitution ENV-03). Before the first deployment, the suite must be run once against PostgreSQL to confirm the abstraction held.

## Alternatives rejected

- **`sudo apt install python3-pip python3-venv`** — needs an interactive password; also keeps Python 3.14, where some wheels were still absent.
- **Enable Docker WSL2 integration and run PostgreSQL** — a valid future step, but it requires a change on the Windows host outside this environment's control. Revisit before deployment.
