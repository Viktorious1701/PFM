# constitution.md — PFM project rules

Stable, citable rules for the PFM codebase. `aif-review-checklist.md` references rule IDs; this file defines them for **this** stack (Python 3.13 / FastAPI / SQLAlchemy 2.0 / React Native Expo), derived from `SDS.md`.

Every rule has a permanent ID. Cite them in `plan.md`, in review findings, and in ADRs. Never renumber — supersede instead.

**Source of authority:** `SRS.md` v2.0.0 is the requirements baseline. `SDS.md` v1.1.0 supplies the technical rules cited here — §4.7 (architecture principles), §6.1 (API standards), §7 (security), §8 (NFR), §12 (naming, DoD).

Precedence: **SRS → SDS → this file.** Where this file and the SDS disagree, the SDS wins and this file gets corrected; where the SDS and the SRS disagree, the SRS wins and the SDS gets corrected (see `docs/00-foundation/srs-sds-alignment.md`).

**NFR ids** are the SRS §3 scheme, which SDS §8.1 was renumbered to match. `NFR-04` means Security & Token Enforcement in both documents.

---

## AR — Architecture & Layering

*Source: SDS §4.3.2, §4.7, SRS NFR-03*

- **AR-01** Business logic lives in the **service layer** only. Never in routers, never in repositories.
- **AR-02** Routers are thin: HTTP binding, dependency injection, delegate to a service, format the response. No branching on business state.
- **AR-03** Repositories are data access only — queries and persistence. No business rules, no HTTP concepts.
- **AR-04** DTO ↔ model mapping happens in schemas or services, never in routers or repositories.
- **AR-05** A service function never touches `Request`, `Response`, `BackgroundTasks`, or any Starlette/FastAPI object. Pass plain values.
- **AR-06** Multi-entity writes execute in **one** transaction. Services never call `commit()`; the router owns the commit boundary.
- **AR-07** Sequence diagrams and call chains follow `router → service → repository`. A router calling a repository directly is a violation.
- **AR-08** Module layout follows SDS §4.3.2: `api/`, `services/`, `repositories/`, `models/`, `schemas/`, `core/`. (Deviation: rooted at `app/` not `src/` — see ADR-0001.)

## API — API Design

*Source: SDS §6.1, §6.3, §6.6, §12.1*

- **API-01** All endpoints under `/api/v1`, lowercase, plural resource nouns (`/users`, `/wallets`, `/transactions`).
- **API-02** Error responses use the flat envelope, **including validation failures**:
  ```json
  {"error_code": "INVITATION_TOKEN_EXPIRED", "message": "…", "details": {}}
  ```
- **API-03** HTTP status codes: `200` read/update · `201` creation · `400` malformed or expired-token per SRS · `401` unauthenticated · `403` authenticated but forbidden · `404` not found · `409` business conflict · `422` payload validation.
- **API-04** Error codes are `UPPER_SNAKE_CASE` with a resource prefix (`INVITATION_TOKEN_EXPIRED`, `USER_EMAIL_ALREADY_ACTIVE`), and every code a story can emit is catalogued in that story's `plan.md`.
- **API-05** No generic `updateStatus` endpoint. Each business state transition gets its own explicit endpoint (`/users/activate`, not `PATCH /users/{id}` with a status field).
- **API-06** List endpoints accept `page` and `page_size`; default 25, maximum 100. Responses carry a total count.
- **API-07** Every endpoint declares an explicit `response_model` and status code so the generated OpenAPI schema is accurate (SDS §4.7 API-First).
- **API-08** Public endpoints are exactly: `POST /api/v1/auth/login`, `POST /api/v1/users/activate`, `GET /api/v1/users/activate`, `GET /health`. Everything else requires a bearer token (SDS §7.1.8). Adding a public route requires an ADR.

## NC — Naming Conventions

*Source: SDS §2.1, §12.1*

- **NC-01** Modules and packages: lowercase snake_case, singular for a module of one concept (`user_repo.py`, `invitation_service.py`).
- **NC-02** SQLAlchemy models `UserModel`-style per SDS §2.1; Pydantic DTOs `UserRead` / `UserCreate` / `InviteCreate` / `UserActivate`; tables lowercase plural snake_case (`users`, `invitations`).
- **NC-03** API paths lowercase hyphenated nouns. No verbs except for explicit state transitions permitted by API-05.
- **NC-04** Columns snake_case; foreign keys `<entity>_id`; timestamps `created_at` / `updated_at` / `expires_at`.
- **NC-05** Enum values are `UPPER_SNAKE_CASE` strings in the database and serialise as the same literal in JSON (`"PENDING"`, `"ACTIVE"`, `"SUPERSEDED"`). Human-friendly labels are a client concern.
- **NC-06** Service methods are concise within their context: `InvitationService.create`, not `create_invitation`.
- **NC-07** Parameters holding collections are plural (`user_ids`, `roles`).

## VL — Validation

*Source: SDS §6.2, §7.1.5, SRS NFR-04*

- **VL-01** Pydantic schemas are the source of truth for request validation. Client-side validation is UX only.
- **VL-02** Validation errors are returned **together** in one `422`, not one error per field.
- **VL-03** Email is validated with `EmailStr` and normalised to lowercase before any uniqueness check.
- **VL-04** Password policy (SDS §7.1.5): minimum 8 characters, at least one uppercase letter, one digit, one special character. Additionally capped at 72 **bytes** UTF-8, because bcrypt silently truncates beyond that — reject rather than truncate.
- **VL-05** Uniqueness is enforced at two levels: a service-layer check returning `409` with a specific code, and a database unique index as the backstop.
- **VL-06** Referenced entities are verified to exist and be active before use — `404` if absent, `409` if present but in the wrong state.
- **VL-07** Monetary values use `Decimal` with `DECIMAL(15,2)` precision (SRS NFR-05). Never float.

## SEC — Security

*Source: SDS §7, SRS NFR-04, NFR-06*

- **SEC-01** Passwords hashed one-way with bcrypt or argon2. No plaintext password is ever stored, logged, or returned.
- **SEC-02** Invitation tokens come from `secrets.token_urlsafe(32)` — 256 bits, exceeding NFR-04's 128-bit floor.
- **SEC-03** Only the SHA-256 **hash** of an invitation token is persisted. The raw token exists solely in the email body. (Deviation from SDS §4.3.3 — ADR-0003.)
- **SEC-04** Invitation tokens are single-use: activation invalidates the token in the same transaction as the status change.
- **SEC-05** TTL is enforced on every token read, comparing against `clock.utcnow()`. An expired token never grants access.
- **SEC-06** JWT: HS256, 60-minute expiry, `sub` = user id (SDS §7.1.3, §7.1.6).
- **SEC-07** Every protected route resolves the caller through the auth dependency, and every ADMIN-only route additionally asserts role — each proven by a test that expects `401` and `403` respectively.
- **SEC-08** Queries for user-owned data filter on the authenticated `user_id` at the repository layer (SDS §7.2, SRS NFR-06).
- **SEC-09** No secret is hardcoded. All come from `.env` via `pydantic-settings`; `.env` is gitignored and `.env.example` lists every key with no real values.
- **SEC-10** Error messages must not reveal whether an account exists, except where a story deliberately does so (an ADMIN inviting an existing active address — documented in that story's spec).
- **SEC-11** Rate limiting on invitation endpoints to blunt invite spam (SDS §7.3 DoS row).

## LA — Logging & Audit

*Source: SDS §7.1.10, §10.6*

- **LA-01** No PII, passwords, tokens, or credentials in log statements. Log the user id, not the email, where either would do.
- **LA-02** Audit-worthy events log at INFO with five fields: UTC timestamp, actor user id, action, target entity id, result. Structured (JSON) output.
- **LA-03** `401` and `403` responses log at WARN with method, path, caller id if known, and the requirement that failed.
- **LA-04** Invitations sent, activations completed, and logins (success and failure) are audit events under LA-02.

## PF — Performance

*Source: SRS NFR-01, SDS §8.1*

- **PF-01** Primary read/write endpoints respond in under **300 ms** p95. Slow I/O such as SMTP moves off the request path.
- **PF-02** Columns used in `WHERE`, `JOIN`, or `ORDER BY` carry an index. No N+1 query patterns.
- **PF-03** Responses are built from DTO projections — never a full ORM entity graph.
- **PF-04** List endpoints are always bounded (see API-06). No unbounded result set reaches a client.

## TST — Testing

*Source: SDS §12.3, aif-review-checklist Step 3*

- **TST-01** Every AC in `spec.md` has at least one test case in `test_cases.md`, and every test case names the AC it covers.
- **TST-02** Test cases are written in Given/When/Then **before** any test code exists.
- **TST-03** Tests assert observable behaviour. Asserting only that a mock was called is not a test.
- **TST-04** Unhappy paths covered: invalid payload, missing auth, insufficient role, wrong state, conflict.
- **TST-05** Boundaries covered: TTL at exactly the limit and one second past, empty lists, min/max lengths, case differences in email.
- **TST-06** Tests are deterministic. Time comes from the patched clock seam; no reliance on ordering, sleeps, or network.
- **TST-07** SMTP is mocked by default. A live-delivery test exists but is marked `@pytest.mark.smtp` and excluded from the default run.
- **TST-08** Each test creates the data it needs. No dependence on seeded rows or on another test having run.
- **TST-09** Artifacts conform to `artifact-templates/`: section order, heading style, ID schemes (`AC`/`EC`/`FR`/`BR`/`SC`/`QF`/`TC`/`T`), and status vocabularies. One file per epic; stories appended, never split into separate files.

## DOD — Definition of Done

*Source: SDS §12.3*

- **DOD-01** Code follows the layering in AR-01…03.
- **DOD-02** Every model change ships an Alembic migration, and `alembic upgrade head` succeeds on an empty database.
- **DOD-03** `pytest` green with coverage **> 80%**.
- **DOD-04** `ruff check` and `mypy app` clean.
- **DOD-05** Routes match the generated OpenAPI schema; `/docs` renders without error.
- **DOD-06** At least one integration test per endpoint covering the happy path, plus its documented error cases.
- **DOD-07** `docs/traceability.md` updated with real pytest node ids.
- **DOD-08** Deviations from `SRS.md` / `SDS.md` each carry an ADR.

## ENV — Environment

*Source: verified 2026-07-30, see docs/00-foundation/environment.md*

- **ENV-01** `uv` is the only Python entry point; system Python has no pip. Every command is `uv run …`.
- **ENV-02** Python is pinned to 3.13 (`.python-version`), not the system 3.14, to stay on well-supported wheels.
- **ENV-03** Local database is SQLite; PostgreSQL is the deployment target (SDS §4.5). Nothing may depend on SQLite-only behaviour. ADR-0001.
- **ENV-04** No Docker, Android SDK, or emulator is available in this environment. Work requiring them is deferred and documented, never faked.

---

## Amendment procedure

1. Propose the change in the ADR that motivates it.
2. Update this file in the same commit as the ADR.
3. Never renumber an existing rule — mark it `superseded by <new id>` and add the replacement.
