# CLAUDE.md — how work is done in this repo

Personal & Family Finance Management (PFM). This file is the operating contract for AI-assisted work here. Read it before touching anything.

The purpose of this project is to practise the **AIF-SDLC cycle**, where documents drive code. Producing implementation before its spec/design/test artifacts exist defeats the point and has already been rejected once — see `docs/00-foundation/spike-notes.md`.

---

## 1. Reference documents

| File | Owner | Rule |
| :-- | :-- | :-- |
| `SRS.md` v2.0.0 | the user | **Read-only. Never edit.** Requirements baseline: FR, NFR, UXR, BF, Features 01–11 with Gherkin. |
| `SDS.md` v1.0.0 | the user | **Read-only. Never edit.** Technical baseline: domain model, ERD, architecture, API design, security design. |
| `aif-review-checklist.md` | the user | **Read-only. Never edit.** Run before claiming any step gate. |
| `constitution.md` | AI + user | Project rules with stable IDs (AR/API/NC/VL/LA/PF/SEC/DOD), derived from the SDS. |
| `specs/**`, `docs/**` | AI + user | Working artifacts. Design output goes here — **never** into `SDS.md`. |

### They are references, not contracts

`SRS.md` and `SDS.md` were written before the code existed and they leave things open — and in places they contradict each other.

- **Deviate freely** where implementation reality demands it, then record it as an ADR in `docs/02-design/adr/` and list it in the story's `spec.md` *Deviations* section.
- **Stop and ask the user** only when a change would genuinely *break* one of them:
  - contradicts the domain model (`SDS.md` §2) or ERD (§4.3.3),
  - changes a published endpoint contract (`SDS.md` §6),
  - violates an NFR (`SRS.md` §3, `SDS.md` §8),
  - the two documents disagree and the choice is material.
- Everything smaller: decide, document, keep moving.

### Resolved contradictions (do not re-litigate)

| Topic | Ruling | Source |
| :-- | :-- | :-- |
| User status values | `PENDING_INVITATION` / `ACTIVE` / `DEACTIVATED`. **SDS wins** over the SRS's `PENDING`. `EXPIRED` is *derived* from `expires_at`, never stored. | SDS §2.4.1, §7.1.2 |
| Invitation storage | **Separate `invitations` table** per the SDS ERD — not columns on `users`. Inviting creates a `users` row (`PENDING_INVITATION`) *and* an `invitations` row. | SDS §2.1, §4.3.3 |
| Roles | `users.role` = `ADMIN` \| `USER`, enforced now. Invite and list-users are ADMIN-only. | SDS §5.2.1, §5.2.3 |
| Error shape | Flat: `{"error_code", "message", "details"}` — **not** nested under `"error"`. | SDS §6.6 |
| Dev database | SQLite locally (Docker unreachable in this WSL2 setup); PostgreSQL is the target. One `DATABASE_URL` change. ADR required. | SDS §4.1 vs environment |
| Invitation token at rest | Stored **hashed** (SHA-256); the raw token exists only in the email. Deviates from SDS §4.3.3's plain `token UK`. ADR required. | security deviation |

### Story ID map

The two documents number the same stories differently. Always cite both.

| SRS | SDS | Story | Round 1 |
| :-- | :-- | :-- | :-- |
| US-02-01 | SS-US-01 | Login | ✔ step 1 |
| US-01-01 | UM-US-01 | Invite a user via email (ADMIN) | ✔ step 2 |
| US-01-02 | UM-US-02 | Activate user account | ✔ step 3 |
| US-01-03 | UM-US-03 | List users (ADMIN) | ✔ step 4 |
| US-02-02 | SS-US-02 | Logout | deferred |
| — | UM-US-04/05 | View profile / update user | deferred |

### The scope rule ("cut to the current story")

Before starting a story, extract **only** the `SRS.md` / `SDS.md` sections that story implements. Quote them at the top of its `spec.md`, then state what is deliberately excluded. Nothing else enters the working context — this is what stops Features 03–11 leaking into a Feature-01 story.

```markdown
## Source
### SRS §6 Feature-01 · US-01-01 (Gherkin)
> Scenario: Successfully send an email invitation …
### SDS §5.2.1 UM-US-01 (ADMIN)
> 1. Validates email format and checks for existing active accounts. …

## Out of scope for this story
US-01-02, US-01-03, US-02-01 · Features 03–11 · SRS §6 Feature-10/11 placeholders
```

If a story turns out to need something out of scope, that is a finding — write it down, do not silently expand.

---

## 2. The AIF-SDLC cycle

Six steps per story, in **strict order, none skipped or reordered**. Each produces reviewable artifacts and ends at a gate.

| # | Step | Reviewer | Artifacts | Definition of done |
| :-- | :-- | :-- | :-- | :-- |
| 1 | **Spec** | BA | `spec.md` | Story statement (As a / I want / So that), ACs traced to SRS+SDS, every AC a testable observable outcome. No endpoint paths, DB fields, or tech names — those belong to `plan.md`. Exactly one US per file. Stable IDs (`AC-01`, `BR-01`, `EC-01`). |
| 2 | **Design** | SE | `plan.md` + ADRs | Sequence diagram, layer assignment, DTOs, API contract, error codes. Every AC addressed. Constitution rules checked explicitly. No gaps left ambiguous — if there are, go back to Spec rather than patching forward. |
| 3 | **Quality** | QC | `test_cases.md` | ≥1 test case per AC, in Given/When/Then, with US + AC reference + type. Unhappy paths and edge cases covered. TC numbers sequential, appended never rewritten. **Written before test code.** |
| 4 | **Implement** | SE | `tasks.md` + code | Tasks ordered migration → model → repository → service → router. Tests written from `test_cases.md` and seen failing first, then code until green. `pytest` green, `ruff` + `mypy` clean, coverage > 80%. |
| 5 | **Deploy** | SE | evidence | App actually runs; `/health` 200; curl/Postman walkthrough executed with **real pasted output**, including a genuine Gmail delivery. |
| 6 | **Verification** | QC | verification report | Every TC given a result (PASS/FAIL/BLOCKED). Failures reproduced manually, root-caused, logged in `docs/06-defects/`, fixed, re-verified. |

**If implementation diverges from `plan.md`, redefine the plan first** — never deviate silently and patch the document afterwards.

Diagrams, ERDs and sequence diagrams belong to the **Design** step. They are not introduced or altered during Implementation.

### Artifact layout

One folder per story, so "exactly one US per `spec.md`" holds:

```
specs/
├── 001-user-onboarding/              Feature-01 / UM
│   ├── us-01-01-invite-user/         spec.md  plan.md  test_cases.md  tasks.md
│   ├── us-01-02-activate-account/
│   └── us-01-03-list-users/
└── 002-system-security/              Feature-02 / SS
    └── us-02-01-login/
```

Supporting documents live in `docs/`: `traceability.md` (master matrix), `00-foundation/`, `02-design/adr/`, `05-verification/`, `06-defects/`, `mobile-readiness.md`.

### Gate cadence

- **US-02-01 (login)** — the first story through the cycle: stop at **every** step gate.
- Later stories: stop after Spec+Design, after Quality, and after Verification.
- More gates on request; never fewer without being asked.

### Traceability

`docs/traceability.md` is the master matrix: **SRS/SDS story → AC → TC → pytest node id → status**. Updated at step 3 (TC ids) and step 4 (pytest node ids). A story is done when every AC resolves through it to a passing test. Nothing else counts as done.

### Review checklist

Before claiming **any** gate, run the artifact through `aif-review-checklist.md` and record the result using its gate-record template. A gate claimed without the checklist is not a gate.

Items in that checklist covering Jira tickets, branch naming (`feature/bee-NNN-…`), Java/Spring/Flyway, Playwright, shadcn/ui and Testcontainers are **N/A for this project** — mark them so explicitly rather than silently skipping. Their intent maps here as: task tracking → the session task list; Flyway → Alembic; Playwright/Testcontainers → `pytest` + `httpx`.

---

## 3. Commands

`uv` is the only entry point — this machine's system Python has no pip.

```bash
cd backend

uv sync                                   # install/refresh dependencies
uv run pytest -v                          # full suite, SMTP mocked
uv run pytest --cov=app --cov-report=term-missing   # coverage (DOD: >80%)
uv run pytest -m smtp                     # opt-in: real Gmail send (needs .env)
uv run ruff check . && uv run ruff format .
uv run mypy app
uv run alembic revision --autogenerate -m "…"
uv run alembic upgrade head
uv run python -m app.cli create-admin --email you@example.com --password '…'
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger at `/docs`, ReDoc at `/redoc`. FastAPI ≥0.141 makes `include_router` lazy — to list routes read `app.openapi()["paths"]`, not `app.routes`.

---

## 4. Conventions

Full rules with stable IDs live in [`constitution.md`](constitution.md). The essentials:

- **Layering** `router → service → repository → model` (AR-01…03). No queries in routers, no `Request`/`Response` objects in services.
- **Transactions** services never commit; the router owns the commit, so one request is one transaction (NFR-05).
- **Time** all reads go through `app.core.clock.utcnow()`. Never `datetime.now()`. SQLite returns naive datetimes — pass them through `clock.ensure_aware()` before comparing or serialising.
- **Money** `DECIMAL(15,2)` / Python `Decimal`. Never float.
- **Errors** one flat envelope, validation included: `{"error_code": "INVITATION_TOKEN_EXPIRED", "message": "…", "details": {}}`. Codes are `UPPER_SNAKE_CASE` with a resource prefix, catalogued in the story's `plan.md`.
- **Config** `pydantic-settings` in `app/core/config.py`, grown per story — a story adds only the settings its spec justifies. Secrets from `.env` (gitignored); `.env.example` documents every key.
- **Secrets** never log or return a raw token, password, or hash. Invitation tokens are stored hashed.
- **Tests** named for what they prove, each carrying its `TC-xx` id in a docstring. A test that cannot fail is not a test.
- **Commits** one per step gate, so `git log` reads as the cycle:
  ```
  docs(spec):   US-02-01 login — AC-01..05
  docs(design): US-02-01 plan + ADR-0002 JWT session
  docs(test):   US-02-01 test_cases TC-0201-01..12
  test:         US-02-01 failing tests from TC plan
  feat:         US-02-01 login endpoint — TC-0201-* green
  docs(verify): US-02-01 verification report
  ```

---

## 5. Current state and boundaries

- **Round 1 scope:** US-02-01 login, then US-01-01 invite, US-01-02 activate, US-01-03 list users. **Out of scope:** everything else, including Features 03–11 and SRS §6 Feature-10/11 placeholders.
- **Backend only.** No `mobile/` code until Feature-01 is verified. React Native/Expo analysis lives in `docs/mobile-readiness.md`; SDS §4.3.1 is the target design.
- **`spike/`** holds the discarded implementation-first attempt. Reference only — never edit it, never import from it.
- Dev DB is SQLite; PostgreSQL is the deployment target (SDS §4.5).

## 6. Honesty rules

- Never report a step complete without its artifact on disk.
- Never write "tests pass" without having run them and pasted the output.
- State skipped, blocked, or deviating work in the same message, not later.
- Do not write documentation that retroactively justifies code already written.
