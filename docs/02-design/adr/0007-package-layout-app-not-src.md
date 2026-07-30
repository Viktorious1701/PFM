# ADR-0007: Backend package is `backend/app/`, not `src/`

**Status:** Accepted · **Date:** 2026-07-30
**Relates to:** SDS §4.3.2 *(corrected in v1.1.0)* · constitution AR-08

## Context

`SDS.md` §4.3.2 originally showed the backend tree rooted at a bare `src/`. The repository is a monorepo that will hold a React Native client alongside the API (SDS §4.3.1), so a top-level `src/` would be ambiguous about which application it belongs to. A bare `src/` is also not importable as a package without path manipulation.

## Decision

```
backend/            # the API project root: pyproject.toml, alembic.ini, .env
├── app/            # the importable package
│   ├── api/v1/  services/  repositories/  models/  schemas/  core/
│   └── main.py
├── migrations/
└── tests/
mobile/             # React Native client (later round)
```

Imports read `from app.core.config import get_settings`. `SDS.md` §4.3.2 was corrected to match in v1.1.0, with the **layer names kept normative** — the constitution's AR-01…AR-03 bind to `api`/`services`/`repositories`, not to any particular parent directory.

## Consequences

**Positive** — unambiguous ownership in a monorepo; `app` is a real importable package with no `sys.path` tricks; each project keeps its own dependency manifest, so `uv` and npm never contend.

**Negative** — every command runs from `backend/`, which is a small friction the `CLAUDE.md` command list absorbs by prefixing `cd backend`. Diverges from the `src/` layout convention some Python tooling assumes; `[tool.pytest.ini_options] pythonpath = ["."]` covers it.

## Alternatives rejected

- **`src/` as originally written** — ambiguous in a monorepo and not directly importable.
- **`backend/src/app/`** — the full src-layout, which is genuinely better for *distributable libraries* because it prevents accidentally importing from the working directory. This is a deployed application, never installed from a wheel, so the benefit does not apply and the extra nesting is noise.
