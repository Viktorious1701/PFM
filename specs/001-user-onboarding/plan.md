# Technical Plan: User Management & Onboarding (UM)

> **Feature:** SRS §6 Feature-01 · SDS §5.2 (UM)
> **Spec:** [spec.md](spec.md)
> **Stories in this file:** UM-US-01 *(designed)* · UM-US-02, UM-US-03 *(pending)*

---

## UM-US-01: Invite a User via Email

### Gaps & Decisions (Resolved)

Code and architecture decisions settled during design. Spec-level findings were folded back into `spec.md` before this step closed.

| ID | Area | Decision | Status |
|----|------|----------|--------|
| A1 | Architecture | Inviting writes **two** rows — a `users` row (`PENDING`) and an `invitations` row — inside one transaction (SDS §4.3.3 ERD, spec BR-08). Neither may exist without the other. | ✅ Resolved |
| A2 | Security | Only `sha256(token)` is persisted, in `invitations.token_hash`. The raw token exists solely in the email body. Deviates from SDS §4.3.3's plain `token UK`; behaviour under every AC is identical. → **ADR-0003** | ✅ Resolved |
| A3 | Code | Re-invite (EC-02/EC-03) marks the outstanding invitation `SUPERSEDED` and inserts a new one, rather than mutating the existing row. Preserves invitation history, which is the reason the entity exists. | ✅ Resolved |
| A4 | Architecture | Mail dispatch runs **off the request path** via `BackgroundTasks` so FR-19 / NFR-01's 300 ms p95 holds; Gmail SMTP costs 1–3 s. An `EMAIL_SEND_MODE=sync` setting forces inline delivery so a misconfiguration surfaces as `502` (spec FR-20, EC-07) — intended for first-time Gmail wiring, not production. | ✅ Resolved |
| A5 | Code | Expiry is computed as `clock.utcnow() + INVITATION_TTL_HOURS`, and `EXPIRED` is **derived** on read by comparing `expires_at`. No status sweeper exists (SDS §2.4.2, spec BR-04). All time reads go through the clock seam → **ADR-0004** | ✅ Resolved |
| A6 | Code | Endpoint is `POST /api/v1/users/invite` per SDS §6.3, **not** `/users/invitations`. The spike used the latter; SDS wins. | ✅ Resolved |
| A7 | Architecture | `users.email` carries the unique index and is stored normalised (trimmed, lower-cased). `invitations.email` is denormalised for audit history and is **not** unique. Uniqueness lives on the account, not the attempt (spec FR-03, BR-01, FR-18). | ✅ Resolved |
| A8 | Code | Role check is a dedicated `require_admin` dependency layered on `get_current_user`, so AC-05 (401) is evaluated strictly before AC-04 (403). Order matters: an unauthenticated caller must never receive a role error that reveals the endpoint exists. | ✅ Resolved |
| A9 | Code | Audit events (FR-17, AC-09) are emitted through a small `audit` helper writing structured log lines. **No** `activity_logs` table this round — SDS §7.1.10 and §10.6 specify structured logs, not a queryable store, and no story requires reading them back. Revisit if an audit-retrieval story appears. | ✅ Resolved |
| A10 | Security | The `create-admin` CLI closes the invite-only bootstrap cycle (spec Assumptions). It writes an `ACTIVE` `ADMIN` directly and is the only path to the first account. → **ADR-0008** | ✅ Resolved |
| G1 | Dependency | AC-04/AC-05 require authentication, which is **SS-US-01 (epic 002)**. The `get_current_user` / `require_admin` dependencies are *designed* here and *delivered* by that story. UM-US-01 cannot reach its Deploy step before login exists. | ✅ Resolved (sequencing) |

---

### Architecture

**Package layout** (additions only; foundation modules already exist and are reused). Rooted at `backend/app/` rather than SDS §4.3.2's original `src/` → **ADR-0007**, and the SDS was corrected to match in v1.1.0.

```text
backend/app/
├── core/
│   ├── config.py                     # update: add JWT, invitation TTL, SMTP, activation URL settings
│   ├── errors.py                     # update: add UserEmailAlreadyActiveError, EmailDeliveryError,
│   │                                 #         NotAuthenticatedError, ForbiddenError
│   ├── clock.py                      # reuse as-is — utcnow() / ensure_aware()
│   ├── security.py                   # NEW  token generation + sha256 hashing (JWT arrives with SS-US-01)
│   ├── audit.py                      # NEW  structured audit emitter (A9)
│   └── deps.py                       # NEW  get_db, get_settings, get_email_sender,
│                                     #      get_current_user, require_admin  (G1: filled by SS-US-01)
├── models/
│   ├── __init__.py                   # NEW  imports models so Alembic autogenerate sees them
│   ├── user.py                       # NEW  UserModel  + UserStatus, UserRole
│   └── invitation.py                 # NEW  InvitationModel + InvitationStatus
├── schemas/
│   ├── user.py                       # NEW  UserRead
│   └── invitation.py                 # NEW  InviteCreate, InvitationRead
├── repositories/
│   ├── user_repo.py                  # NEW  normalize_email, get_by_email, add_pending_user
│   └── invitation_repo.py            # NEW  add, get_active_for_email, supersede_outstanding
├── services/
│   ├── invitation_service.py         # NEW  create_invitation() + send_invitation_email()
│   └── email/
│       ├── sender.py                 # NEW  EmailSender Protocol + EmailMessage
│       ├── smtp.py                   # NEW  GmailSmtpSender
│       └── templates.py              # NEW  build_invitation_email()
├── api/v1/
│   ├── router.py                     # NEW  aggregates v1 routers
│   └── users.py                      # NEW  POST /users/invite
├── cli.py                            # NEW  create-admin  (A10)
└── main.py                           # update: mount api_router under /api/v1

backend/migrations/versions/
└── <rev>_create_users_and_invitations.py   # NEW  both tables in one revision (DOD-02)

backend/tests/
├── conftest.py                       # NEW  in-memory DB, RecordingEmailSender, frozen clock
└── integration/test_um_us_01_invite.py     # NEW  written at the Implement step from test_cases.md
```

**Domain objects**

| Entity | Table | Key Fields | Notes |
|--------|-------|------------|-------|
| `UserModel` | `users` | `id` PK, `email` **UK**, `password_hash`, `full_name`, `status`, `role`, `created_at` | Created here as `PENDING` with `password_hash`/`full_name` **NULL** (spec FR-05, AC-07). `email` normalised before insert (A7). `id` is `String(36)` UUID text so the same schema runs on SQLite and PostgreSQL (ADR-0001). |
| `UserStatus` | — | `PENDING`, `ACTIVE`, `DEACTIVATED` | SDS §2.4.1 as aligned. Serialised as the literal (NC-05). Only `PENDING` is written by this story. |
| `UserRole` | — | `ADMIN`, `USER` | Invited accounts get `USER` (spec FR-06). `ADMIN` only via the bootstrap CLI. |
| `InvitationModel` | `invitations` | `id` PK, `email` (indexed, **not** unique), `token_hash` **UK**, `expires_at`, `status`, `invited_by_id` FK→`users.id`, `created_at` | One row per invitation *attempt*, so history survives (A3). `token_hash` is `String(64)` sha256 hex (A2). |
| `InvitationStatus` | — | `PENDING`, `ACCEPTED`, `EXPIRED`, `SUPERSEDED` | SDS §2.4.2. This story writes `PENDING` and `SUPERSEDED` only; `ACCEPTED` belongs to UM-US-02. `EXPIRED` is **derived**, never written (A5). |

**Business rules enforced in service layer**

| Rule | Source | Enforcement |
|------|--------|-------------|
| An authenticated ADMIN may submit an email address to invite | AC-01, FR-01 | `POST /api/v1/users/invite` accepting `InviteCreate`, guarded by `require_admin` (A6, A8) |
| Email format validated before anything else | AC-03, FR-02 | `InviteCreate.email: EmailStr` → `422` from the Pydantic layer, before the service runs (VL-01) |
| Invitation persisted as a record distinct from the account | FR-10, BR-08 | `invitations` table with its own lifecycle; `invitation_repo.add()` (A1, ADR-0002) |
| Activation email dispatched to the invited address | AC-01, FR-12 | `send_invitation_email()` → `GmailSmtpSender`; body built by `build_invitation_email()` with the link from `activation_url_template` |
| Success response carries id, email, status, expiry and a confirmation message | AC-01, FR-16 | `InvitationRead` projection, `status_code=201` (API-07, PF-03) |
| Email normalised before comparison or insert | EC-01, FR-03 | `user_repo.normalize_email()` — single definition of "the same address" |
| ACTIVE email rejected | AC-02, FR-04, BR-02 | `create_invitation()` loads by normalised email; `status is ACTIVE` → `UserEmailAlreadyActiveError` (409) |
| PENDING email re-invited, not duplicated | EC-02, EC-03, FR-11, BR-03 | Existing `PENDING` user row is reused; `invitation_repo.supersede_outstanding()` then a fresh insert (A3) |
| Token ≥128-bit, unique | AC-06, FR-08, SEC-02 | `secrets.token_urlsafe(32)` → 256 bits; `token_hash` UK backstops uniqueness |
| TTL exactly 24h | AC-06, FR-09 | `clock.utcnow() + timedelta(hours=settings.invitation_ttl_hours)`, default 24 (A5) |
| Account created without credentials, role USER | AC-07, FR-05, FR-06, BR-05, BR-06 | `add_pending_user()` sets `status=PENDING`, `role=USER`, leaves `password_hash`/`full_name` NULL. A `PENDING` row has no hash, so it cannot authenticate (BR-06); `USER` role cannot invite (BR-05) |
| Inviting ADMIN recorded | FR-07 | `invitations.invited_by_id = current_user.id` |
| Both rows atomic | BR-08, AR-06 | Service flushes only; the **router** commits once. One request, one transaction |
| Token never returned | AC-08, BR-07, FR-13, SEC-03 | `InvitationRead` has no token field; only `token_hash` is persisted; audit omits the token |
| ADMIN-only | AC-04, FR-14 | `require_admin` dependency → `403` |
| Unauthenticated rejected first | AC-05, FR-15, A8 | `get_current_user` runs before `require_admin` → `401` takes precedence over `403` |
| Response inside 300 ms | FR-19, NFR-01 | SMTP dispatched via `BackgroundTasks` after commit (A4) |
| Delivery failure surfaced or logged, never silent | EC-06, EC-07, FR-20, FR-21 | `sync` mode raises `EmailDeliveryError` → `502`; background mode logs the exception and leaves the invitation re-invitable |
| Audit on success | AC-09, FR-17, LA-02, LA-04 | `audit.record()` with actor id, timestamp, invited email, outcome — no token (A9) |
| Concurrent duplicates collapse | EC-05, FR-18, VL-05 | Service-level check plus the `users.email` unique index; the loser's `IntegrityError` maps to `409` |

**Sequence diagram — Invite a User via Email**

```mermaid
sequenceDiagram
    autonumber
    actor Admin as ADMIN
    participant API as FastAPI Router
    participant Dep as Auth Dependencies
    participant Svc as InvitationService
    participant Repo as Repositories
    participant DB as Database
    participant SMTP as Gmail SMTP
    actor Invitee as Invited mailbox

    Note over Admin,Invitee: Main flow — authenticated ADMIN, address not yet in use
    Admin->>API: POST /api/v1/users/invite {email} + Bearer token
    API->>Dep: resolve caller (AC-05 before AC-04, per A8)
    Dep-->>API: ADMIN user
    API->>API: validate email format (AC-03 -> 422 if malformed)
    API->>Svc: create_invitation(email, invited_by)
    Svc->>Svc: normalise email — trim + case-fold (EC-01)
    Svc->>Repo: find user by normalised email
    Repo->>DB: SELECT
    DB-->>Repo: none
    Svc->>Svc: generate token (256-bit) + expiry = now + 24h (AC-06)
    Svc->>Repo: insert user PENDING/USER, no credentials (AC-07)
    Svc->>Repo: insert invitation PENDING with token_hash only (A2)
    Repo->>DB: INSERT x2 (same transaction, BR-08)
    API->>DB: COMMIT
    Note over API,SMTP: Dispatch only after commit — never advertise a token that rolled back
    API-->>Admin: 201 Created + {id, email, status, token_expires_at, message} — no token (AC-08)
    API->>SMTP: send activation email (background, A4)
    SMTP-->>Invitee: activation link containing the raw token (AC-01)
    API->>API: audit record: actor, timestamp, invited email, outcome (AC-09)

    alt Address already PENDING (EC-02 / EC-03)
        Svc->>Repo: mark outstanding invitation SUPERSEDED (A3)
        Svc->>Repo: insert fresh invitation, TTL restarted
        Note over Svc,Invitee: same user row reused; the previous link stops working immediately
    end

    Note over Admin,DB: Error scenarios
    opt Unauthenticated or expired credentials (AC-05)
        Dep-->>Admin: 401 NOT_AUTHENTICATED
    end
    opt Authenticated but not ADMIN (AC-04)
        Dep-->>Admin: 403 FORBIDDEN
    end
    opt Email already belongs to an ACTIVE account (AC-02)
        Svc-->>Admin: 409 USER_EMAIL_ALREADY_ACTIVE
    end
    opt Concurrent duplicate loses the unique index race (EC-05)
        DB-->>Svc: IntegrityError
        Svc-->>Admin: 409 USER_EMAIL_ALREADY_ACTIVE
    end
    opt SMTP unreachable or unconfigured, sync mode (EC-07)
        SMTP-->>API: failure
        API-->>Admin: 502 EMAIL_DELIVERY_FAILED
    end
    opt SMTP fails in background mode (EC-06)
        Note over API: logged; invitation stays PENDING and re-invitable
    end
```

**Error flows**

| Scenario | HTTP | Error Code |
|----------|------|------------|
| Malformed or missing email | 422 | `VALIDATION_ERROR` |
| Email exceeds maximum supported length (EC-04) | 422 | `VALIDATION_ERROR` |
| Email belongs to an ACTIVE account (AC-02, EC-01, EC-05) | 409 | `USER_EMAIL_ALREADY_ACTIVE` |
| No or invalid bearer credentials (AC-05) | 401 | `NOT_AUTHENTICATED` |
| Authenticated, role is not ADMIN (AC-04) | 403 | `FORBIDDEN` |
| Mail delivery fails in `sync` mode (EC-07) | 502 | `EMAIL_DELIVERY_FAILED` |
| Unexpected server error | 500 | `INTERNAL_ERROR` |

All in the flat envelope `{"error_code", "message", "details"}` (SDS §6.6, API-02). No CSRF concern — stateless bearer auth (SDS §7.1.9).

**Constitution notes**

| Rule | Status | Note |
|------|--------|------|
| AR-01 Service owns business rules | Required | Normalisation, ACTIVE check, token generation, supersede, and both inserts live in `invitation_service.create_invitation()` |
| AR-02 Thin router | Required | Router binds the payload, resolves dependencies, calls the service, commits, schedules the background send, formats the response |
| AR-03 Repository isolation | Required | `user_repo` / `invitation_repo` hold queries only; no business rules |
| AR-05 No framework objects in services | Required | `BackgroundTasks` stays in the router; the service receives an `EmailSender` and plain values |
| AR-06 One transaction per request | Required | Service flushes; the router commits once, covering both inserts (BR-08) |
| API-01 Versioned plural path | Required | `POST /api/v1/users/invite` (A6) |
| API-02 Flat error envelope | Required | Already implemented in `main.py`, including the validation handler → **ADR-0005** |
| API-03 Status codes | Required | 201 create · 401 · 403 · 409 conflict · 422 validation · 502 upstream |
| API-04 Prefixed error codes | Required | `USER_EMAIL_ALREADY_ACTIVE`, `EMAIL_DELIVERY_FAILED` |
| API-05 No generic status endpoint | Required | `/users/invite` is an explicit business action |
| API-06 Pagination | **N/A** | Single-resource creation; no list in this story |
| API-07 Explicit response_model | Required | `response_model=InvitationRead`, `status_code=201` |
| API-08 Public endpoint list | Required | This route is **protected**; the public list is unchanged |
| NC-02 Naming | Required | `UserModel` / `InvitationModel`; `InviteCreate` / `InvitationRead` / `UserRead`; tables `users` / `invitations` |
| NC-04 Column naming | Required | snake_case; `invited_by_id` FK; `expires_at` / `created_at` |
| NC-05 Enum serialisation | Required | `"PENDING"`, `"USER"` as literals |
| NC-06 Concise service methods | Required | `InvitationService.create_invitation`, not `create_user_invitation` |
| VL-01 Pydantic is the source of truth | Required | `EmailStr` + max length on `InviteCreate` |
| VL-02 Errors grouped | Required | Handled by the existing `RequestValidationError` handler |
| VL-03 Email normalised | Required | `normalize_email()` before every comparison |
| VL-05 Two-level uniqueness | Required | Service check + `users.email` unique index (EC-05) |
| VL-04 Password policy | **N/A** | No password is set by this story (UM-US-02 owns it). The `create-admin` CLI does hash one, using bcrypt directly → **ADR-0006** |
| VL-07 Decimal money | **N/A** | No monetary value in this story |
| SEC-02 Token entropy | Required | `secrets.token_urlsafe(32)` = 256 bits, over NFR-04's 128-bit floor |
| SEC-03 Hash at rest | Required | `token_hash` only (A2, ADR-0003) |
| SEC-04 Single use | **N/A** | Consumption is UM-US-02; this story only issues |
| SEC-05 TTL enforced on read | **N/A** | No token is read here; enforced by UM-US-02 |
| SEC-06 JWT parameters | Required (exempt) | Consumed here, defined by SS-US-01 (G1) |
| SEC-07 Authz proven by test | Required | 401 and 403 each get a dedicated test case |
| SEC-08 Ownership filter | **N/A** | No user-owned data is queried |
| SEC-09 Secrets from .env | Required | SMTP credentials via `pydantic-settings`; `.env` gitignored |
| SEC-10 No enumeration | Required (exempt) | AC-02 **deliberately** discloses that an address is already active — an ADMIN needs to know. Documented exemption in `spec.md` |
| SEC-11 Rate limiting | Required (spec-stricter) | SDS §7.3 names `slowapi` on invite. Deferred to a follow-up task **T-13** with an explicit note, because no AC or EC requires it and adding middleware now would be unspecified scope |
| LA-01 No secrets in logs | Required | Audit records the invited email and actor id, never the token |
| LA-02 Audit five fields | Required | actor, timestamp, action, target email, result (A9) |
| LA-04 Invitation is auditable | Required | AC-09 / FR-17 |
| PF-01 300 ms p95 | Required | SMTP off the request path (A4) |
| PF-02 Indexed lookups | Required | `users.email` UK, `invitations.token_hash` UK, `invitations.email` indexed |
| PF-03 DTO projection | Required | `InvitationRead` — five fields, no ORM graph |
| TST-01/02 AC→TC coverage | Required | Every AC and EC mapped in `test_cases.md` before any test code |
| TST-07 SMTP mocked | Required | `RecordingEmailSender` by default; one opt-in `@pytest.mark.smtp` live test |
| DOD-02 Migration | Required | One Alembic revision creating both tables |
| DOD-03 Coverage > 80% | Required | Measured at the Implement step |

**Element IDs**

| Element | ID | Status | File |
|---------|----|--------|------|
| — | — | **N/A (mobile deferred)** | No UI exists this round. `mobile/` is a skeleton with no screens; element IDs are defined when UM-US-01's invite screen is built in a later round. |

**Open tasks**

| ID | Task | File |
|----|------|------|
| T-01 | `UserModel` + `UserStatus` + `UserRole` | `backend/app/models/user.py` |
| T-02 | `InvitationModel` + `InvitationStatus` | `backend/app/models/invitation.py` |
| T-03 | Alembic revision creating `users` and `invitations` with their indexes | `backend/migrations/versions/` |
| T-04 | `security.py`: `generate_invitation_token()`, `hash_token()` | `backend/app/core/security.py` |
| T-05 | `config.py`: `invitation_ttl_hours`, `activation_url_template`, SMTP block, `email_send_mode` | `backend/app/core/config.py` |
| T-06 | `errors.py`: `UserEmailAlreadyActiveError` 409, `EmailDeliveryError` 502, `NotAuthenticatedError` 401, `ForbiddenError` 403 | `backend/app/core/errors.py` |
| T-07 | `audit.py`: structured `record()` emitter (LA-02) | `backend/app/core/audit.py` |
| T-08 | Repositories: `normalize_email`, `get_by_email`, `add_pending_user`, `add`, `get_active_for_email`, `supersede_outstanding` | `backend/app/repositories/{user_repo,invitation_repo}.py` |
| T-09 | `EmailSender` Protocol, `GmailSmtpSender`, `build_invitation_email()` | `backend/app/services/email/` |
| T-10 | `invitation_service.create_invitation()` + `send_invitation_email()` | `backend/app/services/invitation_service.py` |
| T-11 | Schemas `InviteCreate`, `InvitationRead`, `UserRead` | `backend/app/schemas/` |
| T-12 | `POST /api/v1/users/invite` router + mount `api_router` in `main.py` | `backend/app/api/v1/users.py`, `main.py` |
| T-13 | **Deferred:** `slowapi` rate limiting on the invite route (SDS §7.3). No AC requires it; raise as its own story rather than smuggling it in | `backend/app/main.py` |
| T-14 | `create-admin` CLI — bootstrap ADMIN (A10, ADR-0008) | `backend/app/cli.py` |
| T-15 | `deps.py`: `get_current_user`, `require_admin` — **blocked on SS-US-01** (G1) | `backend/app/core/deps.py` |
| T-16 | Test fixtures: in-memory DB, `RecordingEmailSender`, frozen clock | `backend/tests/conftest.py` |
| T-17 | Integration tests written from `test_cases.md` | `backend/tests/integration/test_um_us_01_invite.py` |
