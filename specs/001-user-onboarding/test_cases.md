# Test Cases: User Management & Onboarding (UM)

> **Feature:** SRS §6 Feature-01 · SDS §5.2 (UM)
> **Spec:** [spec.md](spec.md) · **Plan:** [plan.md](plan.md)
> **Stories in this file:** UM-US-01 *(TC-01…TC-27, TC-27 an amendment for `plan.md` F1)* · UM-US-02 *(TC-28…TC-56)* · UM-US-03 *(pending, continue from TC-57)*

---

## UM-US-01: Invite a User via Email

### Quality Findings

Problems found while deriving test cases from `spec.md` and `plan.md`. Each one changes how a criterion can be asserted, so it is recorded rather than worked around silently.

#### QF-01

**Description.** AC-09 / FR-17 require an audit entry on every successful invitation, but `plan.md` A9 deliberately implements audit as **structured log lines with no `activity_logs` table**, and no story exposes an audit-read endpoint. There is no API or database surface through which an audit entry can be observed.

**Impact.** AC-09 cannot be asserted through the public API at all.

**Recommendation.** Assert it at the logging boundary instead: `TC-16` uses pytest's `caplog` to capture the emitted record and checks the five LA-02 fields are present and that the token is absent. This is a genuinely weaker assertion than reading a persisted row — it verifies the call happened and its shape, not that an operator could later retrieve it. If an audit-retrieval story is ever specified, AC-09 should be re-tested against the store and this note removed.

#### QF-02

**Description.** EC-05 (two ADMINs invite the same new address simultaneously) needs true write concurrency. The test database is SQLite (constitution ENV-03), which serialises writers, and the suite runs single-threaded with an in-memory database shared through `StaticPool`.

**Impact.** A deterministic "two parallel requests race" test is not constructable in this environment. Writing one that appears to pass would be misleading — it would prove serialisation, not conflict handling.

**Recommendation.** Split the criterion. `TC-14` asserts the **guard that actually resolves the race**: the `users.email` unique index rejects a second insert, and the service maps that `IntegrityError` to `409 USER_EMAIL_ALREADY_ACTIVE` rather than leaking a 500. `TC-15` asserts sequential duplicate submission returns 409 and leaves exactly one row. True parallel-writer verification is deferred to a PostgreSQL run (constitution ENV-03), and is listed as a known coverage limit below.

#### QF-03

**Description.** AC-04 (non-ADMIN → 403) and AC-05 (unauthenticated → 401) both depend on `get_current_user` and `require_admin`, which `plan.md` G1 records as **delivered by SS-US-01 (epic 002)**, not by this story.

**Impact.** `TC-11`, `TC-12` and `TC-13` cannot pass until the login story is implemented. Written now, they would fail for an absent dependency rather than a defect.

**Recommendation.** Write the cases now — they are part of this story's contract — but mark them **blocked on SS-US-01** in the coverage matrix. They must be green before UM-US-01's Verification step closes. Do not weaken them into "endpoint exists" smoke tests.

#### QF-04

**Description.** AC-08 requires the token never reach the inviting ADMIN. A test asserting *absence* is only as good as the string it searches for, and the response is JSON containing an id, an email and two timestamps — none of which resembles a token.

**Impact.** A naive `assert "token" not in body` would pass trivially and prove nothing, since the field is legitimately named `token_expires_at`.

**Recommendation.** `TC-17` asserts absence positively: capture the raw token from the recorded email, then assert that exact 43-character string does not appear anywhere in the serialised response body. `TC-18` separately pins the response key set to exactly the six documented fields, so a future field addition cannot silently leak the token.

#### QF-05

**Description.** AC-06 requires "at least 128 bits of entropy". Entropy is a property of the generator, not of any single value, so no test on one token can demonstrate it.

**Impact.** The criterion is not directly testable as stated.

**Recommendation.** `TC-08` asserts the observable proxies: the emitted token is 43 URL-safe characters (the encoding of 32 random bytes = 256 bits), and 50 successive invitations yield 50 distinct tokens. The generator choice itself — `secrets.token_urlsafe(32)` — is enforced by code review against constitution SEC-02, not by a test. Recorded so the gap is visible rather than assumed covered.

#### QF-06

**Description.** EC-06 (delivery fails *after* the invitation is committed) and EC-07 (delivery not configured) exercise the two `EMAIL_SEND_MODE` branches from `plan.md` A4. In background mode the failure surfaces only in a log; in sync mode it becomes a 502.

**Impact.** Two different assertions are needed for what reads as one concern, and the background case has no HTTP-visible symptom.

**Recommendation.** `TC-19` (background) asserts 201 is still returned, the invitation persists as `PENDING`, and the failure is logged. `TC-20` (sync) asserts 502 `EMAIL_DELIVERY_FAILED`. `TC-21` asserts the recovery path EC-06 promises is real: after a delivery failure, re-inviting the same address succeeds.

#### QF-07

**Description.** SDS §5.2.1 and spec AC-01 require dispatch "via Gmail SMTP", but every automated test uses a recording double (constitution TST-07). No default-suite test proves a real message leaves the process.

**Impact.** The suite can be fully green while SMTP is misconfigured — exactly the failure EC-07 describes.

**Recommendation.** Two layers. `TC-22` is marked `@pytest.mark.smtp`, excluded from the default run, and performs a **real send** against Gmail using `.env` credentials. Additionally the Deploy step (step 5) requires a real delivery to a real inbox as a manual gate — `spec.md` SC-01 is not satisfiable by any automated test in this environment.

#### QF-08

**Description.** `spec.md` EC-04 says an over-long email is rejected, but neither document names the limit. `plan.md` sets `users.email` to `String(320)`.

**Impact.** The boundary value must be assumed before the schema exists.

**Recommendation.** `TC-09` uses 320 as the inclusive maximum (the RFC 5321 practical limit, and the column width in `plan.md`), asserting 321 characters → 422. If the Implement step chooses a different width, update `TC-09` and the schema together in the same change.

### Acceptance Criteria Classification

`[UI]` rows are **deferred, not skipped** — `mobile/` is a skeleton with no screens this round, so no E2E surface exists. They are named here so the mobile round inherits them.

| AC/EC | Title | Label | Rationale |
|---|---|---|---|
| AC-01 | Successfully send an email invitation | **[BOTH]** | API: 201, both rows written, email recorded. UI: invite form success state — deferred |
| AC-02 | Reject an email already belonging to an ACTIVE account | **[BOTH]** | API: 409 `USER_EMAIL_ALREADY_ACTIVE`. UI: inline error — deferred |
| AC-03 | Reject a malformed email address | **[BOTH]** | API: 422 `VALIDATION_ERROR`. UI: field-level validation — deferred |
| AC-04 | Deny access to non-ADMIN callers | **[API]** | 403. No UI surface: a non-ADMIN never sees the invite screen (authorisation, not presentation) |
| AC-05 | Deny access to unauthenticated callers | **[API]** | 401. UI equivalent is a redirect to login, which belongs to SS-US-01 |
| AC-06 | Unguessable token with a 24-hour TTL | **[API]** | Generator and expiry are backend-only; bounded by QF-05 |
| AC-07 | Create the invited account without credentials | **[API]** | Persistence shape only — no UI renders it in this story |
| AC-08 | Never expose the invitation token to the ADMIN | **[API]** | Response-payload contract; bounded by QF-04 |
| AC-09 | Record an invitation audit event | **[API]** | Log-boundary only — no retrieval endpoint exists (QF-01) |
| EC-01 | Case / whitespace-differing duplicate | **[API]** | Normalisation is a backend rule |
| EC-02 | Re-invite a still-`PENDING` address | **[BOTH]** | API: token rotated, one user row. UI: same success state — deferred |
| EC-03 | Re-invite an expired invitation | **[API]** | Indistinguishable from EC-02 at the UI |
| EC-04 | Email exceeding maximum length | **[API]** | 422; bounded by QF-08 |
| EC-05 | Concurrent duplicate submission | **[API]** | Not constructable here — see QF-02 |
| EC-06 | Delivery fails after the invitation is recorded | **[API]** | Log-visible only (QF-06) |
| EC-07 | Delivery not configured | **[API]** | 502 in sync mode (QF-06) |

### Coverage Matrix

Each row lists exactly the TCs whose `**AC:**` field cites that id — matrix and blocks are kept mechanically consistent, so neither can drift from the other.

| AC/EC | Label | Integration TC(s) | E2E TC(s) | Blocked on |
|---|---|---|---|---|
| AC-01 | [BOTH] | TC-01, TC-02, TC-03, TC-22 | *deferred — mobile round* | — |
| AC-02 | [BOTH] | TC-04, TC-05 | *deferred — mobile round* | — |
| AC-03 | [BOTH] | TC-06, TC-07 | *deferred — mobile round* | — |
| AC-04 | [API] | TC-11 | — | ~~SS-US-01~~ **unblocked** (`plan.md` A11) |
| AC-05 | [API] | TC-12, TC-13 | — | ~~SS-US-01~~ **unblocked** (`plan.md` A11) |
| AC-06 | [API] | TC-08, TC-23, TC-24 | — | — |
| AC-07 | [API] | TC-02, TC-10 | — | — |
| AC-08 | [API] | TC-17, TC-18 | — | — |
| AC-09 | [API] | TC-16 | — | — |
| EC-01 | [API] | TC-05, TC-25 | — | — |
| EC-02 | [API] | TC-21, TC-26 | *deferred* | — |
| EC-03 | [API] | TC-26 *(expired variant)* | — | — |
| EC-04 | [API] | TC-09 | — | — |
| EC-05 | [API] | TC-14, TC-15 | — | — |
| EC-06 | [API] | TC-19, TC-21 | — | — |
| EC-07 | [API] | TC-20 | — | — |
| F1 *(`plan.md`)* | [API] | TC-27 | — | — |

`TC-22` is the opt-in live-SMTP case (`@pytest.mark.smtp`). It is the positive counterpart to `EC-07` — it proves the configuration EC-07 fails on is correct — but it does not exercise EC-07's failure path, so it is not listed against it.

> Every AC and EC has at least one integration TC. `[BOTH]` rows have **no** E2E case because `mobile/` has no screens this round — they are deferred to the mobile round, not silently dropped. TC-11…TC-13 were blocked on SS-US-01 per QF-03; `plan.md` A11 unblocked them by shipping token verification with this story, and all three are green. **Known coverage limits, accepted:** true concurrent-writer behaviour (QF-02, deferred to a PostgreSQL run), generator entropy as a property (QF-05, code review against SEC-02), audit durability (QF-01, log-shape only), and real SMTP delivery (QF-07, opt-in `TC-22` plus a manual Deploy gate). **`TC-27` is new** (`plan.md` F1 amendment, written at UM-US-02's design step) and **is now implemented and PASS** (`plan.md` T-18) — see the Test Implementation Map below for its node id.

---

### Test Implementation Map *(filled at step 4)*

`pytest` node ids for each TC. All under `backend/tests/`, module
`integration/test_um_us_01_invite.py` unless stated. Run one with
`uv run pytest -k <fragment>`.

| TC | pytest node id (`::`-suffix of the module above) | Result |
|---|---|---|
| TC-01 | `test_invite_returns_201_with_the_invitation_record` | PASS |
| TC-02 | `test_invite_writes_both_a_user_row_and_an_invitation_row` | PASS |
| TC-03 | `test_invite_dispatches_an_email_containing_the_activation_link` | PASS |
| TC-04 | `test_inviting_an_active_address_is_rejected_as_conflict` | PASS |
| TC-05 | `test_duplicate_detection_ignores_case_and_surrounding_whitespace` | PASS |
| TC-06 | `test_malformed_email_addresses_are_rejected_as_validation_errors` (5 params) | PASS |
| TC-07 | `test_a_missing_email_field_is_rejected_as_a_validation_error` | PASS |
| TC-08 | `test_every_emitted_token_is_43_urlsafe_chars_and_unique` | PASS |
| TC-09 | `test_an_over_long_email_address_is_rejected_not_truncated` | PASS |
| TC-10 | `test_the_invited_account_has_no_credentials_and_the_default_role` | PASS |
| TC-11 | `test_a_non_admin_caller_is_denied` | PASS |
| TC-12 | `test_an_unauthenticated_caller_is_denied`, `test_an_expired_token_is_denied` | PASS |
| TC-13 | `test_credentials_are_evaluated_before_the_payload` | PASS |
| TC-14 | `test_a_unique_constraint_violation_surfaces_as_conflict_not_server_error` | PASS |
| TC-15 | `test_repeated_submission_yields_exactly_one_account` | PASS |
| TC-16 | `test_a_successful_invitation_emits_an_audit_record_without_the_token` | PASS |
| TC-17 | `test_the_raw_token_appears_nowhere_in_the_response_body` | PASS |
| TC-18 | `test_the_response_exposes_exactly_the_six_documented_fields` | PASS |
| TC-19 | `test_a_background_delivery_failure_does_not_fail_the_request` | PASS |
| TC-20 | `test_a_sync_mode_delivery_failure_returns_bad_gateway` | PASS |
| TC-21 | `test_an_address_whose_email_failed_can_be_reinvited` | PASS |
| TC-22 | `test_a_real_message_is_delivered_through_gmail_smtp` | **PASS** — real Gmail send, confirmed in the inbox. See the Deploy note below. |
| TC-23 | `test_the_invitation_expires_exactly_24_hours_after_creation` | PASS |
| TC-24 | `test_expiry_is_derived_from_the_timestamp_not_stored_as_a_status` | PASS |
| TC-25 | `test_the_stored_email_is_normalised` | PASS |
| TC-26 | `test_reinviting_a_pending_address_rotates_the_token_and_supersedes_the_old_invitation` (`still-valid`, `already-expired`) | PASS |
| TC-27 | `test_reinviting_a_deactivated_address_is_rejected_with_its_own_code` | **PASS** — implemented at UM-US-02's step 4 (`plan.md` T-18). A leftover blanket check in `invitation_service.create_invitation()` was raising `USER_EMAIL_ALREADY_ACTIVE` for `DEACTIVATED` too, ahead of the new branch that never ran; the dead check is removed. |

**Supporting tests, not TCs.** These cover code paths no AC reaches, for DOD-03's
coverage bar. They do not satisfy any test case and are not counted above:
`integration/test_auth_and_envelope.py` (401 variants, API-02 envelope for 404 /
405 / 500), `unit/test_security.py`, `unit/test_email_delivery.py`,
`unit/test_cli.py`, `unit/test_deps_and_audit.py`.

**Deploy evidence (step 5) — TC-22 and SC-01 closed.** `uv run pytest -m smtp`
passed against real Gmail SMTP (App Password, STARTTLS, port 587), and the
message was **confirmed present in the recipient inbox** — a send that does not
raise is not by itself proof of delivery, so the manual check was made. Full run
with the live case included: `86 passed`, nothing skipped.

Two defects were found by the live walkthrough rather than by the suite, which is
the argument for the Deploy gate existing at all:

1. **Bearer scheme.** `Authorization` was a raw `Header()` parameter, so Swagger
   rendered a bare text box; pasting the JWT produced a 401 that looked like a bad
   token rather than a missing `Bearer ` prefix. Now declared as an `HTTPBearer`
   security scheme, so Swagger adds the prefix itself. Regression-guarded by
   `test_auth_is_declared_as_a_bearer_security_scheme_not_a_raw_header`.
2. **TC-22 read `os.environ`** while `.env` is the documented home for credentials
   (SEC-09) and only `pydantic-settings` loads it. Filling in `.env` left TC-22
   silently skipped while appearing configured. Both now route through `Settings()`.

**Defect found and fixed during step 4.** `token_expires_at` and `created_at`
serialised **without a timezone offset** — SQLite drops `tzinfo`, so values read
back naive after `db.refresh()` and a client had no way to know the timezone of
an expiry deadline. Fixed by passing both through `clock.ensure_aware()` at the
serialisation boundary (`api/v1/users.py`). TC-23 originally applied
`ensure_aware` to the *response* before comparing, which hid the bug; it now
asserts `tzinfo is not None` directly.

---

### TC-01: ADMIN invites a new address — 201 with invitation metadata

- **US:** UM-US-01
- **Given:** An authenticated ADMIN, and no existing user with email `family.member@gmail.com`
- **When:** An invitation is submitted for that address
- **Then:** The response is `201`; the body carries `id`, `email` equal to the submitted address, `status` `"PENDING"`, a `token_expires_at` timestamp, `created_at`, and a confirmation `message`
- **AC:** AC-01, FR-01, FR-16
- **Type:** integration

### TC-02: Inviting writes both a user row and an invitation row

- **US:** UM-US-01
- **Given:** An authenticated ADMIN and an unused email address
- **When:** An invitation is submitted successfully
- **Then:** Exactly one `users` row exists for the normalised address with status `PENDING`, and exactly one `invitations` row references it with status `PENDING` and `invited_by_id` equal to the acting ADMIN's id
- **AC:** AC-01, AC-07, FR-07, FR-10, BR-08
- **Type:** integration

### TC-03: An activation email is dispatched containing the activation link

- **US:** UM-US-01
- **Given:** An authenticated ADMIN and a recording email sender
- **When:** An invitation is submitted successfully
- **Then:** Exactly one email is recorded, addressed to the invited address, whose body contains the activation URL built from the configured template with a `token` query parameter; the same URL appears in both the text and HTML alternatives
- **AC:** AC-01, FR-12
- **Type:** integration

### TC-04: Inviting an ACTIVE address is rejected with 409

- **US:** UM-US-01
- **Given:** An `ACTIVE` user already exists with email `family.member@gmail.com`
- **When:** An authenticated ADMIN submits an invitation for that same address
- **Then:** The response is `409` with `error_code` `USER_EMAIL_ALREADY_ACTIVE`; no new `users` row and no new `invitations` row is created, and no email is recorded
- **AC:** AC-02, FR-04, BR-02
- **Type:** integration

### TC-05: Duplicate detection ignores case and surrounding whitespace

- **US:** UM-US-01
- **Given:** An `ACTIVE` user exists with email `family.member@gmail.com`
- **When:** An ADMIN submits `"  Family.Member@Gmail.COM  "`
- **Then:** The response is `409` `USER_EMAIL_ALREADY_ACTIVE` — the address is recognised as the same mailbox after trimming and case-folding, and no second account is created
- **AC:** AC-02, EC-01, FR-03, BR-01
- **Type:** integration

### TC-06: Malformed email addresses are rejected with 422

- **US:** UM-US-01
- **Given:** An authenticated ADMIN
- **When:** An invitation is submitted with each of `not-an-email`, `@nolocal.com`, `spaces in@email.com`, `a@b@c.com`, and an empty string
- **Then:** Each response is `422` with `error_code` `VALIDATION_ERROR` and a non-empty `details.fields` entry locating the `email` field; nothing is persisted and no email is recorded
- **AC:** AC-03, FR-02
- **Type:** integration

### TC-07: A missing email field is rejected with 422

- **US:** UM-US-01
- **Given:** An authenticated ADMIN
- **When:** An invitation is submitted with an empty JSON object
- **Then:** The response is `422` `VALIDATION_ERROR` identifying the absent `email` field
- **AC:** AC-03, FR-02, VL-02
- **Type:** integration

### TC-08: The emitted token is 43 URL-safe characters and never repeats

- **US:** UM-US-01
- **Given:** An authenticated ADMIN and a recording email sender
- **When:** 50 invitations are submitted for 50 distinct addresses
- **Then:** Every emitted token matches `^[A-Za-z0-9_-]{43}$` — the encoding of 32 random bytes, i.e. 256 bits, above NFR-04's 128-bit floor — and all 50 tokens are distinct
- **AC:** AC-06, FR-08 *(bounded by QF-05: entropy of the generator is verified by code review against SEC-02, not by this test)*
- **Type:** integration

### TC-09: An over-long email address is rejected with 422

- **US:** UM-US-01
- **Given:** An authenticated ADMIN
- **When:** An invitation is submitted with a syntactically valid address of 321 characters
- **Then:** The response is `422` `VALIDATION_ERROR`; the address is not truncated and nothing is persisted
- **AC:** EC-04 *(320 assumed as the inclusive maximum per QF-08)*
- **Type:** integration

### TC-10: The invited account carries no credentials and the default role

- **US:** UM-US-01
- **Given:** An authenticated ADMIN
- **When:** An invitation is submitted successfully
- **Then:** The created `users` row has `password_hash` null, `full_name` null, `status` `PENDING`, and `role` `USER` — never `ADMIN`
- **AC:** AC-07, FR-05, FR-06, BR-05, BR-06
- **Type:** integration

### TC-11: A non-ADMIN caller is denied with 403

- **US:** UM-US-01
- **Given:** An authenticated user whose role is `USER`
- **When:** An invitation is submitted
- **Then:** The response is `403` with `error_code` `FORBIDDEN`; nothing is persisted and no email is recorded
- **AC:** AC-04, FR-14, SEC-07 *(blocked on SS-US-01 — QF-03)*
- **Type:** integration

### TC-12: An unauthenticated caller is denied with 401

- **US:** UM-US-01
- **Given:** A caller presenting no `Authorization` header
- **When:** An invitation is submitted with an otherwise valid payload
- **Then:** The response is `401` with `error_code` `NOT_AUTHENTICATED`; nothing is persisted
- **AC:** AC-05, FR-15, SEC-07 *(blocked on SS-US-01 — QF-03)*
- **Type:** integration

### TC-13: Credentials are evaluated before the payload

- **US:** UM-US-01
- **Given:** A caller presenting no credentials
- **When:** An invitation is submitted with a **malformed** email address
- **Then:** The response is `401` `NOT_AUTHENTICATED`, not `422` — an unauthenticated caller learns nothing about payload validity, and the ordering required by `plan.md` A8 holds
- **AC:** AC-05, FR-15
- **Type:** integration

### TC-14: A unique-constraint violation surfaces as 409, not 500

- **US:** UM-US-01
- **Given:** An authenticated ADMIN, and a `users` row already present for the target address such that the service's pre-check is bypassed
- **When:** An insert for the same normalised email is attempted
- **Then:** The resulting integrity error is translated to `409` `USER_EMAIL_ALREADY_ACTIVE`; no `500` escapes and no partial invitation row remains
- **AC:** EC-05, FR-18, VL-05 *(the constructable half of EC-05 — see QF-02)*
- **Type:** integration

### TC-15: Repeated submission of the same new address yields exactly one account

- **US:** UM-US-01
- **Given:** An authenticated ADMIN and an unused email address
- **When:** The identical invitation payload is submitted twice in sequence
- **Then:** Exactly one `users` row exists for that address afterwards; the second response is either `201` (re-invite of the now-`PENDING` address, per EC-02) or `409`, and in neither case is a duplicate account created
- **AC:** EC-05, FR-18, BR-01
- **Type:** integration

### TC-16: A successful invitation emits an audit record without the token

- **US:** UM-US-01
- **Given:** An authenticated ADMIN and log capture enabled
- **When:** An invitation is submitted successfully
- **Then:** One audit record is emitted carrying the acting ADMIN's id, a UTC timestamp, the action, the invited email, and a success result; the raw token appears nowhere in the captured output
- **AC:** AC-09, FR-17, LA-01, LA-02, LA-04 *(log-boundary assertion only — see QF-01)*
- **Type:** integration

### TC-17: The raw token appears nowhere in the response body

- **US:** UM-US-01
- **Given:** An authenticated ADMIN and a recording email sender
- **When:** An invitation is submitted successfully
- **Then:** The exact token string extracted from the recorded email does not occur anywhere in the serialised response body
- **AC:** AC-08, FR-13, BR-07, SEC-03 *(asserted positively per QF-04)*
- **Type:** integration

### TC-18: The response exposes exactly the six documented fields

- **US:** UM-US-01
- **Given:** An authenticated ADMIN
- **When:** An invitation is submitted successfully
- **Then:** The response body's keys are exactly `id`, `email`, `status`, `token_expires_at`, `created_at`, `message` — no more — so no future field can leak the token unnoticed
- **AC:** AC-08, FR-16, PF-03 *(guards QF-04)*
- **Type:** integration

### TC-19: A background delivery failure does not fail the request

- **US:** UM-US-01
- **Given:** An authenticated ADMIN, `EMAIL_SEND_MODE=background`, and an email sender configured to raise
- **When:** An invitation is submitted
- **Then:** The response is `201`; the `users` row remains `PENDING` and its invitation remains `PENDING`; the delivery failure is logged
- **AC:** EC-06, FR-21 *(see QF-06)*
- **Type:** integration

### TC-20: A sync-mode delivery failure returns 502

- **US:** UM-US-01
- **Given:** An authenticated ADMIN, `EMAIL_SEND_MODE=sync`, and an email sender that fails because credentials are absent
- **When:** An invitation is submitted
- **Then:** The response is `502` with `error_code` `EMAIL_DELIVERY_FAILED` — success is never reported for an email that was not sent
- **AC:** EC-07, FR-20 *(see QF-06)*
- **Type:** integration

### TC-21: An address whose email failed can be re-invited successfully

- **US:** UM-US-01
- **Given:** An invitation was created but its delivery failed in background mode (TC-19)
- **When:** The same ADMIN submits an invitation for that address again, with a working sender
- **Then:** The response is `201`, an email is recorded, and exactly one `users` row still exists for the address — the recovery path EC-06 promises is real
- **AC:** EC-06, EC-02, FR-11
- **Type:** integration

### TC-22: A real message is delivered through Gmail SMTP

- **US:** UM-US-01
- **Given:** Valid Gmail credentials in `.env` and `EMAIL_SEND_MODE=sync`
- **When:** The invitation email is dispatched through the real SMTP sender
- **Then:** The send completes without raising, proving host, port, STARTTLS and App Password are correct
- **AC:** AC-01, FR-12 *(opt-in `@pytest.mark.smtp`, excluded from the default run — see QF-07; SC-01 additionally requires a manual inbox check at the Deploy step)*
- **Type:** integration

### TC-23: The invitation expires exactly 24 hours after creation

- **US:** UM-US-01
- **Given:** An authenticated ADMIN and the clock frozen at a known instant `T`
- **When:** An invitation is submitted
- **Then:** The persisted `expires_at` and the returned `token_expires_at` both equal `T + 24h` exactly
- **AC:** AC-06, FR-09, BR-04
- **Type:** integration

### TC-24: Expiry is derived from the timestamp, not stored as a status

- **US:** UM-US-01
- **Given:** An invitation created at frozen time `T`
- **When:** The clock is advanced past `T + 24h`
- **Then:** The stored invitation `status` is still `PENDING` — no sweeper mutated it — while its `expires_at` is now in the past, so any reader derives expiry by comparison
- **AC:** AC-06, BR-04 *(`plan.md` A5; consumption of an expired token belongs to UM-US-02)*
- **Type:** integration

### TC-25: The stored email is normalised

- **US:** UM-US-01
- **Given:** An authenticated ADMIN
- **When:** An invitation is submitted for `"  New.Member@GMAIL.com  "`
- **Then:** The persisted `users.email` is `new.member@gmail.com`, and the email is dispatched to that normalised address
- **AC:** EC-01, FR-03, VL-03
- **Type:** integration

### TC-26: Re-inviting a PENDING address rotates the token and supersedes the old invitation

- **US:** UM-US-01
- **Given:** A `PENDING` user with an outstanding `PENDING` invitation, tested both while that invitation is valid and after the clock is advanced past its expiry
- **When:** An ADMIN submits an invitation for the same address
- **Then:** The response is `201` referencing the **same** user id; exactly one `users` row still exists; the previous invitation is `SUPERSEDED`; a new `PENDING` invitation exists whose token differs from the first and whose expiry restarts from the moment of re-invitation; a new email is dispatched
- **AC:** EC-02, EC-03, FR-11, BR-03
- **Type:** integration

### TC-27: Re-inviting a DEACTIVATED address is rejected with its own code *(amendment — `plan.md` F1)*

- **US:** UM-US-01
- **Given:** A `DEACTIVATED` user exists with email `family.member@gmail.com`
- **When:** An authenticated ADMIN submits an invitation for that same address
- **Then:** The response is `409` with `error_code` `USER_EMAIL_DEACTIVATED` — distinct from `USER_EMAIL_ALREADY_ACTIVE` — and no new `users` row, no new `invitations` row is created, and no email is recorded
- **AC:** *(no spec AC/EC named this case — `plan.md` F1 records the ruling; BR-02 amended reading)*
- **Type:** integration

---

## UM-US-02: Activate a User Account

> **IDs in this section are local to UM-US-02** (`QF-NN`), matching `spec.md`'s per-story convention. Only `TC-NN` runs continuously across the epic — this story continues from `TC-28`.

### Quality Findings

#### QF-01

**Description.** AC-08 requires the two-row transition to be atomic — both take effect or neither does. Every refusal path is fully constructible and shows "neither" (TC-43), and the happy path shows "both" (TC-42), but a genuine **mid-transaction failure** (e.g. the second `UPDATE` failing after the first succeeds) cannot be forced through the public API in this environment — the same class of limit UM-US-01 QF-02 hit for concurrent writes.

**Impact.** Atomicity is proven for every *reachable* outcome, but not by directly interrupting a transaction partway through.

**Recommendation.** Accept the composable proof (TC-42 + TC-43) as the coverage for this environment. `AR-06`'s one-commit-per-request design is itself the structural guard — there is no code path where the router could commit after only one of the two flushed updates — so the residual risk is a design-review item, not a test-automation gap, consistent with how UM-US-01 treated its own untestable concurrency case.

#### QF-02

**Description.** EC-05 (the same valid token submitted twice concurrently) needs true write concurrency, and the test database is SQLite (constitution ENV-03) running single-threaded through `StaticPool` — identical constraint to UM-US-01 QF-02.

**Impact.** A deterministic "two parallel requests race" test is not constructable here.

**Recommendation.** Split the criterion exactly as UM-US-01 QF-02 did. `TC-54` asserts the **guard that resolves the race**: `invitation_repo.mark_accepted()`'s conditional `UPDATE ... WHERE status='PENDING'` affects zero rows on a second call, so a sequential double-submission produces exactly one success and one `INVITATION_TOKEN_INVALID` refusal, never two successes and never a `500`. True parallel-writer verification is deferred to a PostgreSQL run (constitution ENV-03), the same accepted limit as UM-US-01.

#### QF-03

**Description.** AC-07 / FR-17 require the raw password, the stored hash, and the token to appear in no response, log entry, or audit record. Response-body absence (`TC-39`) is fully assertable through the public API. Log and audit absence needs the same log-capture technique UM-US-01 QF-01 used, because — as in that story — there is no `activity_logs` table and no audit-read endpoint (`plan.md` A9, carried over unchanged).

**Impact.** The log/audit half of AC-07 is a weaker assertion than the response-body half: it proves the emitted record's shape, not that an operator could retrieve it later.

**Recommendation.** `TC-40` and `TC-41` use `caplog` exactly as UM-US-01 TC-16 did. If an audit-retrieval story is ever specified, both AC-07 and UM-US-01's AC-09 should be re-tested against the store and this note removed.

#### QF-04

**Description.** The reconciliation recorded in `spec.md` after EC-09 requires that an unrecognised token, an already-used token, a superseded token, and a token whose user is no longer `PENDING` be **indistinguishable** in their reported outcome — on both the activation attempt and the state check. A test that checks each case is *individually* correct (right status, right code) does not prove they are indistinguishable *from each other* — four independently-passing assertions could still each carry a subtly different message or `details` payload, quietly reopening the oracle the spec closed.

**Impact.** The property that matters here is an equality between responses, not a property of any single response — the same shape of problem UM-US-01 QF-04 solved for token absence.

**Recommendation.** `TC-46`/`TC-47` (state check) and `TC-48` (activation attempt) each construct all four preconditions and assert the **complete response bodies are identical** except for fields that must legitimately differ (none, in this case, since neither endpoint echoes anything precondition-specific back). This is a positive assertion of sameness, not an absence check, and it is the test that actually retires the AC-03/AC-11/EC-09 conflict rather than merely avoiding it.

**Extended at the design review.** Sameness across the four preconditions is necessary but was not sufficient: all four could answer identically *and* all four could change together once the clock passed the TTL, which is exactly what `plan.md`'s original check order would have done. `TC-55` therefore asserts sameness along the second axis too — the same four preconditions, re-submitted well past expiry, must answer exactly as they did within the TTL. Without it, the oracle this finding closed would have reopened on a timer.

#### QF-05

**Description.** Neither `SRS.md` nor `SDS.md` names a maximum length for the submitted full name. `plan.md` sets the `users.full_name` column to `String(255)` — inherited from UM-US-01's schema, not chosen for this story — but no AC or EC in `spec.md` requires rejecting or truncating an over-long name.

**Impact.** The boundary is unspecified. Testing a specific over-length rejection would assume a rule nobody has stated, mirroring UM-US-01 QF-08's email-length situation — except UM-US-01 EC-04 *did* name the requirement (reject, don't truncate) and only the number was unstated; here, **no requirement to reject at all** exists.

**Recommendation.** **Amended at the design review.** The *policy* stays unspecified, but the finding as first written conflated two things: what the limit ought to be (genuinely unstated) and what the stored record can hold (already decided, `String(255)`, by UM-US-01's migration). The second is not an open question, and leaving it unbounded is not neutral — SQLite ignores column width, so a 300-character name is accepted locally and raises `DataError` → **500** on PostgreSQL, exactly the environment-dependent divergence ENV-03 exists to prevent. `plan.md` P6 therefore bounds `ActivateRequest.full_name` at the column width, spec **FR-23** and AC-10 record it, and `TC-56` asserts the deterministic `422`. What remains an accepted gap is only whether 255 is the *right* number for a person's name — a product question needing its own EC before any test can assert a different one. `TC-38` (non-ASCII name) still uses a name well under the bound and proves only exact, untransliterated storage.

### Acceptance Criteria Classification

No activation screen exists in `mobile/` this round — only UM-US-01's invite screen was built as a fixture-driven prototype (`CLAUDE.md` §5). `[BOTH]` rows below are still deferred, not skipped, on the same basis as UM-US-01's: SRS UXR-04 describes a real one-page form, so the UI surface is in scope conceptually, just not built yet.

| AC/EC | Title | Label | Rationale |
|---|---|---|---|
| AC-01 | Successfully activate an account within its TTL | **[BOTH]** | API: 200, both rows transition. UI: the 1-page form's success state — deferred |
| AC-02 | Reject an expired token | **[BOTH]** | API: 400 `INVITATION_TOKEN_EXPIRED`. UI: the "ask for a new invitation" message (UXR-04) — deferred |
| AC-03 | Reject a token that matches no invitation | **[BOTH]** | API: 400 `INVITATION_TOKEN_INVALID`. UI: generic "link no longer valid" message — deferred |
| AC-04 | Reject a token that has already been used | **[BOTH]** | Same generic outcome and UI surface as AC-03 (spec reconciliation) — deferred |
| AC-05 | Reject a superseded token | **[BOTH]** | Same generic outcome and UI surface as AC-03 — deferred |
| AC-06 | Enforce the password policy | **[BOTH]** | API: 422 `VALIDATION_ERROR`. UI: field-level password rules — deferred |
| AC-07 | Never expose the credential | **[API]** | Response/log/audit shape only — no UI surface renders this; bounded by QF-03 |
| AC-08 | Activate and invalidate as one atomic outcome | **[API]** | Persistence shape only; bounded by QF-01 |
| AC-09 | Do not establish a session | **[API]** | Response-payload contract; the UI redirect to login is UM-US-01/SS-US-01 territory, not a distinct rendering path here |
| AC-10 | Require a full name | **[BOTH]** | API: 422 `VALIDATION_ERROR`. UI: field-level name validation — deferred |
| AC-11 | Report a token's usability without consuming it | **[BOTH]** | API: `usable`/`expired`/`not_usable`. UI: the pre-check UXR-04 exists for — deferred; bounded by QF-04 |
| AC-12 | Accept the request without credentials | **[API]** | Authorization contract, not a rendering path — matches how UM-US-01 classified its analogous AC-04/AC-05 |
| EC-01 | Full name with surrounding whitespace | **[API]** | Persistence-shape only (trimming) |
| EC-02 | Password exactly at the policy boundary | **[API]** | Backend boundary; UI surface is AC-06's, not a distinct case |
| EC-03 | Password exceeding the maximum supported length | **[BOTH]** | Same validation message surface as AC-06 — deferred |
| EC-04 | Non-ASCII full name | **[API]** | Exact-storage guarantee, not a distinct UI case |
| EC-05 | The same valid token submitted twice concurrently | **[API]** | Not constructable at the UI; backend race guard — bounded by QF-02 |
| EC-06 | Token belonging to a user who is already ACTIVE | **[API]** | Same generic UI surface as AC-03 group — not a distinct rendering path |
| EC-07 | Token belonging to a DEACTIVATED user | **[API]** | Same generic UI surface as AC-03 group |
| EC-08 | Token submitted with altered surrounding characters | **[API]** | Backend exact-match comparison; UI shows the same generic message as AC-03 |
| EC-09 | State requested for a token that is not currently usable | **[API]** | Same generic UI surface as AC-11's `not_usable` case; bounded by QF-04 |
| EC-10 | Token at the exact instant of expiry | **[API]** | Backend boundary, no distinct UI surface |
| EC-11 | Token expired *and* unusable for another reason | **[API]** | Precedence of one refusal code over another; no distinct UI surface — the UI shows AC-03's generic message either way |

### Coverage Matrix

| AC/EC | Label | Integration TC(s) | E2E TC(s) | Blocked on |
|---|---|---|---|---|
| AC-01 | [BOTH] | TC-28 | *deferred — mobile round* | — |
| AC-02 | [BOTH] | TC-29, TC-53 | *deferred* | — |
| AC-03 | [BOTH] | TC-30, TC-47, TC-48 | *deferred* | — |
| AC-04 | [BOTH] | TC-31, TC-47, TC-48 | *deferred* | — |
| AC-05 | [BOTH] | TC-32, TC-47, TC-48 | *deferred* | — |
| AC-06 | [BOTH] | TC-33 | *deferred* | — |
| AC-07 | [API] | TC-39, TC-40 | — | — |
| AC-08 | [API] | TC-42, TC-43 | — | — |
| AC-09 | [API] | TC-44 | — | — |
| AC-10 | [BOTH] | TC-36, TC-56 | *deferred* | — |
| AC-11 | [BOTH] | TC-45, TC-46, TC-47 | *deferred* | — |
| AC-12 | [API] | TC-49 | — | — |
| EC-01 | [API] | TC-37 | — | — |
| EC-02 | [API] | TC-35 | — | — |
| EC-03 | [BOTH] | TC-34 | *deferred* | — |
| EC-04 | [API] | TC-38 | — | — |
| EC-05 | [API] | TC-54 | — | — |
| EC-06 | [API] | TC-50, TC-47, TC-48 | — | — |
| EC-07 | [API] | TC-51, TC-47, TC-48 | — | — |
| EC-08 | [API] | TC-52 | — | — |
| EC-09 | [API] | TC-46, TC-47 | — | — |
| EC-10 | [API] | TC-53 | — | — |
| EC-11 | [API] | TC-55 | — | — |
| FR-23 | [API] | TC-56 | — | — |

> Every AC and EC has at least one integration TC. `[BOTH]` rows have **no** E2E case for the same reason as UM-US-01's: `mobile/` has no screen for this story yet. **Known coverage limits, accepted:** full mid-transaction atomicity (QF-01, structural guard only), true concurrent-writer behaviour (QF-02, deferred to a PostgreSQL run — same limit as UM-US-01 QF-02), and audit durability (QF-03, log-shape only — same limit as UM-US-01 QF-01).
>
> **Two rows were added at the design review, and one limit was retired.** `EC-11` and `FR-23` did
> not exist when this matrix was first written; both came out of reviewing `plan.md` against the
> ACs it claimed to satisfy. `EC-11` closes a precedence hole that would have let expiry override
> AC-04/AC-05 after twenty-four hours (`TC-55`), and `FR-23` bounds the full name at the width the
> record already has (`TC-56`), which downgrades QF-05 from an untestable gap to an open *product*
> question. `FR-18` and `FR-17` were narrowed in `spec.md` rather than left unmet — `TC-40`/`TC-41`
> assert the audit events that do exist, and no test asserts an audit record for a `422`, because
> by design none is emitted (`plan.md` F2, A10).

### Test Implementation Map *(filled at step 4)*

`pytest` node ids for each TC. All under `backend/tests/integration/test_um_us_02_activate.py`
unless stated. Run one with `uv run pytest -k <fragment>`.

| TC | pytest node id | Result |
|---|---|---|
| TC-28 | `test_activate_happy_path_activates_user_and_marks_invitation_accepted` | PASS |
| TC-29 | `test_activate_expired_token_returns_400_token_expired` | PASS |
| TC-30 | `test_activate_unknown_token_returns_400_token_invalid` | PASS |
| TC-31 | `test_activate_already_used_token_returns_400_token_invalid` | PASS |
| TC-32 | `test_activate_superseded_token_returns_400_token_invalid` | PASS |
| TC-33 | `test_activate_weak_password_returns_422_validation_error` (4 params) | PASS |
| TC-34 | `test_activate_over_long_password_rejected_not_truncated` | PASS |
| TC-35 | `test_activate_password_at_exact_policy_boundary_is_accepted` | PASS |
| TC-36 | `test_activate_empty_or_whitespace_full_name_returns_422` (2 params), `test_activate_missing_full_name_field_returns_422` | PASS |
| TC-37 | `test_activate_full_name_with_surrounding_whitespace_is_trimmed` | PASS |
| TC-38 | `test_activate_non_ascii_full_name_stored_exactly` | PASS |
| TC-39 | `test_activate_response_body_never_contains_password_hash_or_token` | PASS |
| TC-40 | `test_activate_success_emits_audit_record_without_credential` | PASS |
| TC-41 | `test_activate_refusal_emits_audit_record_marked_failure` | PASS |
| TC-42 | `test_activate_happy_path_activates_user_and_marks_invitation_accepted` (same node as TC-28 — its assertions already cover both rows transitioning together) | PASS |
| TC-43 | `test_activate_every_refusal_leaves_rows_byte_for_byte_unchanged` (5 preconditions) | PASS |
| TC-44 | `test_activate_success_response_exposes_exactly_two_fields_no_session` | PASS |
| TC-45 | `test_check_token_state_reports_usable_without_mutating` | PASS |
| TC-46 | `test_check_token_state_reports_expired_without_mutating` | PASS |
| TC-47 | `test_state_check_answers_identically_across_the_four_not_usable_cases` | PASS |
| TC-48 | `test_activation_attempt_answers_identically_across_the_four_not_usable_cases` | PASS |
| TC-49 | `test_activate_endpoints_require_no_authentication` | PASS |
| TC-50 | `test_activate_token_whose_user_is_active_is_refused` | PASS |
| TC-51 | `test_activate_token_whose_user_is_deactivated_is_refused` | PASS |
| TC-52 | `test_activate_token_with_altered_whitespace_does_not_match` | PASS |
| TC-53 | `test_activate_token_at_exact_instant_of_expiry_is_treated_as_expired` | PASS |
| TC-54 | `test_sequential_double_submission_of_one_token_succeeds_exactly_once` | PASS |
| TC-55 | `test_expiry_never_overrides_another_refusal_reason` (4 preconditions) | PASS |
| TC-56 | `test_activate_full_name_over_255_characters_rejected_not_truncated` | PASS |

Full suite: `120 passed` (86 from UM-US-01 + TC-27's new test, 34 from UM-US-02). `ruff check` clean,
`mypy app` clean, coverage **98%** (constitution DOD-03's floor is 80%).

**One defect found while writing these tests, fixed, re-verified (constitution §6 honesty rule).**
`activation_service.activate_account()`'s audit call for an unrecognised token logged
`raw_token[:6] + "..."` as the `target` field — a fragment of the raw invitation token reaching the
audit log, which spec FR-17/BR-07 and constitution LA-01 both forbid. `audit.record()`'s
forbidden-key guard only scans `**extra` kwarg *names* for words like "token", not the value of a
required parameter like `target`, so this slipped past it silently. No TC in this file's original
draft would have caught it either — none asserted the *content* of the failure-path audit log, only
that a record was emitted. Fixed by using a fixed sentinel (`"unknown"`) instead of any token
material, and `test_activate_refusal_emits_audit_record_marked_failure` (TC-41) now asserts the raw
token is absent from the captured log line, the same technique UM-US-01's TC-16/TC-17 already used
for the response body.

---

### TC-28: An invited person activates within TTL — 200, account usable

- **US:** UM-US-02
- **Given:** A `PENDING` user whose outstanding invitation has not yet expired
- **When:** The invitation's token is submitted together with full name `"Jane Doe"` and a password meeting the policy
- **Then:** The response is `200` with `{"status": "SUCCESS", "message": ...}`; the `users` row now has `status` `ACTIVE`, `full_name` `"Jane Doe"`, and a `password_hash` that verifies against the submitted password; the `invitations` row is `ACCEPTED`
- **AC:** AC-01, FR-10, FR-11, FR-12, FR-13, FR-15, BR-01
- **Type:** integration

### TC-29: Reject an expired token — 400 INVITATION_TOKEN_EXPIRED

- **US:** UM-US-02
- **Given:** A `PENDING` user with an invitation whose expiry instant is in the past (clock advanced past `T + 24h`)
- **When:** That invitation's token is submitted for activation
- **Then:** The response is `400` `INVITATION_TOKEN_EXPIRED`; the user remains `PENDING`, the invitation's status is untouched
- **AC:** AC-02, FR-04, BR-05
- **Type:** integration

### TC-30: Reject a token matching no invitation — 400 INVITATION_TOKEN_INVALID

- **US:** UM-US-02
- **Given:** A syntactically plausible token that hashes to no row in `invitations`
- **When:** It is submitted for activation
- **Then:** The response is `400` `INVITATION_TOKEN_INVALID`; nothing is created or changed
- **AC:** AC-03, FR-03
- **Type:** integration

### TC-31: Reject a token that has already been used — 400 INVITATION_TOKEN_INVALID

- **US:** UM-US-02
- **Given:** An invitation already `ACCEPTED` (activated once via TC-28's flow)
- **When:** The same token is submitted a second time
- **Then:** The response is `400` `INVITATION_TOKEN_INVALID`; the user's `full_name`/`password_hash` from the first activation are unchanged
- **AC:** AC-04, FR-05, BR-01
- **Type:** integration

### TC-32: Reject a superseded token — 400 INVITATION_TOKEN_INVALID

- **US:** UM-US-02
- **Given:** An address re-invited per UM-US-01 EC-02, so the earlier invitation is `SUPERSEDED`
- **When:** The earlier (superseded) token is submitted
- **Then:** The response is `400` `INVITATION_TOKEN_INVALID`; the user remains `PENDING`; the current (non-superseded) invitation is unaffected
- **AC:** AC-05, FR-05, BR-04
- **Type:** integration

### TC-33: Password policy violations are rejected with 422

- **US:** UM-US-02
- **Given:** A `PENDING` user with a usable invitation
- **When:** Activation is submitted with each of: `"short1!"` (too short), `"nouppercase1!"` (no uppercase), `"NoDigitsHere!"` (no digit), `"NoSpecialChar1"` (no special character)
- **Then:** Each response is `422` `VALIDATION_ERROR` identifying the `password` field; the user remains `PENDING` and the invitation remains usable in every case
- **AC:** AC-06, FR-07
- **Type:** integration

### TC-34: An over-long password is rejected, not truncated

- **US:** UM-US-02
- **Given:** A `PENDING` user with a usable invitation
- **When:** Activation is submitted with a password of 73 bytes UTF-8 that otherwise satisfies the policy
- **Then:** The response is `422` `VALIDATION_ERROR`; the password is not silently shortened and nothing is persisted
- **AC:** EC-03, FR-08
- **Type:** integration

### TC-35: A password exactly at the policy boundary is accepted

- **US:** UM-US-02
- **Given:** A `PENDING` user with a usable invitation
- **When:** Activation is submitted with a password of exactly 8 characters carrying exactly one uppercase letter, one digit, and one special character
- **Then:** The response is `200`; the account activates successfully — the policy is a floor, not a target
- **AC:** EC-02, BR-09
- **Type:** integration

### TC-36: A missing, empty, or whitespace-only full name is rejected with 422

- **US:** UM-US-02
- **Given:** A `PENDING` user with a usable invitation
- **When:** Activation is submitted with `full_name` absent, `""`, and `"   "` in turn
- **Then:** Each response is `422` `VALIDATION_ERROR` identifying the `full_name` field; the user remains `PENDING`
- **AC:** AC-10, FR-09
- **Type:** integration

### TC-37: A full name with surrounding whitespace is stored trimmed

- **US:** UM-US-02
- **Given:** A `PENDING` user with a usable invitation
- **When:** Activation is submitted with `full_name` `"  Jane Doe  "`
- **Then:** The response is `200`; the persisted `full_name` is `"Jane Doe"` — interior spacing preserved, surrounding whitespace removed
- **AC:** EC-01, FR-09
- **Type:** integration

### TC-38: A non-ASCII full name is stored and returned exactly as submitted

- **US:** UM-US-02
- **Given:** A `PENDING` user with a usable invitation
- **When:** Activation is submitted with `full_name` `"Đặng Ngọc Thịnh"`
- **Then:** The response is `200`; the persisted `full_name` is byte-for-byte `"Đặng Ngọc Thịnh"` — no transliteration, accent-stripping, or case-folding
- **AC:** EC-04, FR-09
- **Type:** integration

### TC-39: The raw password, its hash, and the token appear nowhere in the response body

- **US:** UM-US-02
- **Given:** A `PENDING` user with a usable invitation
- **When:** Activation is submitted successfully
- **Then:** The response body contains neither the submitted password, nor the computed `password_hash`, nor the submitted token, in any form — asserted positively by checking the exact strings are absent from the serialised body (mirrors UM-US-01 QF-04's method)
- **AC:** AC-07, FR-17
- **Type:** integration

### TC-40: A successful activation emits an audit record with the five LA-02 fields and no credential

- **US:** UM-US-02
- **Given:** A `PENDING` user with a usable invitation, and log capture enabled
- **When:** Activation is submitted successfully
- **Then:** One audit record is emitted carrying the activated user's id, a UTC timestamp, the action, the target, and result `SUCCESS`; the raw password, the hash, and the token appear nowhere in the captured output
- **AC:** AC-07, FR-18, LA-01, LA-02, LA-04 *(log-boundary assertion only — see QF-03)*
- **Type:** integration

### TC-41: A refused activation also emits an audit record, marked FAILURE

- **US:** UM-US-02
- **Given:** An expired invitation, and log capture enabled
- **When:** Its token is submitted for activation and refused
- **Then:** One audit record is emitted with result `FAILURE`, identifying the target, and containing no credential
- **AC:** FR-18, LA-02, LA-04 *(log-boundary assertion only — see QF-03)*
- **Type:** integration

### TC-42: A successful activation transitions both rows together

- **US:** UM-US-02
- **Given:** A `PENDING` user with a usable invitation
- **When:** Activation is submitted successfully
- **Then:** The `users` row is `ACTIVE` **and** the `invitations` row is `ACCEPTED` — both observed true in the same read after the request completes
- **AC:** AC-08, FR-14
- **Type:** integration

### TC-43: Every refusal leaves both rows exactly as they were

- **US:** UM-US-02
- **Given:** In turn: an expired invitation, an already-`ACCEPTED` invitation, a `SUPERSEDED` invitation, an invitation whose user is `ACTIVE`, and an invitation whose user is `DEACTIVATED`
- **When:** Each token is submitted for activation and refused
- **Then:** In every case, the `users` row and the `invitations` row are byte-for-byte unchanged from their state immediately before the request
- **AC:** AC-08, BR-05
- **Type:** integration

### TC-44: The success response exposes exactly the two documented fields, no session

- **US:** UM-US-02
- **Given:** A `PENDING` user with a usable invitation
- **When:** Activation is submitted successfully
- **Then:** The response body's keys are exactly `status` and `message` — no `token`, no `access_token`, no session identifier of any kind
- **AC:** AC-09, FR-16
- **Type:** integration

### TC-45: The state check reports `usable` for a fresh token, without mutating it

- **US:** UM-US-02
- **Given:** A `PENDING` user with an outstanding, unexpired invitation
- **When:** The token's state is requested (no activation attempted)
- **Then:** The response reports `usable`; a subsequent activation with the same token still succeeds — the check changed nothing
- **AC:** AC-11
- **Type:** integration

### TC-46: The state check reports `expired` for an expired token, without mutating it

- **US:** UM-US-02
- **Given:** A `PENDING` user with an invitation past its expiry
- **When:** The token's state is requested
- **Then:** The response reports `expired`; the invitation's stored status is unchanged by the request (it is not advanced, only reported)
- **AC:** AC-11, EC-09
- **Type:** integration

### TC-47: The state check reports the same `not_usable` outcome for four different reasons

- **US:** UM-US-02
- **Given:** Four tokens in turn: one matching no invitation, one already `ACCEPTED`, one `SUPERSEDED`, and one whose user is `DEACTIVATED`
- **When:** Each token's state is requested
- **Then:** All four responses report `not_usable`, and the four response bodies are otherwise identical — no field anywhere distinguishes an unrecognised token from an already-used, superseded, or wrong-user-state one (proves the spec's AC-03/AC-11/EC-09 reconciliation — QF-04)
- **AC:** AC-11, EC-09, AC-03, AC-04, AC-05, EC-06, EC-07
- **Type:** integration

### TC-48: Activation refusals for the same four reasons are indistinguishable from each other

- **US:** UM-US-02
- **Given:** The same four tokens as TC-47 (unrecognised, already-used, superseded, `DEACTIVATED`-user)
- **When:** Each is submitted for activation
- **Then:** All four responses are `400` `INVITATION_TOKEN_INVALID`, and the four response bodies are byte-for-byte identical except for nothing (no precondition-specific detail leaks through `message` or `details`) — the POST-side counterpart to TC-47's proof (QF-04)
- **AC:** AC-03, AC-04, AC-05, EC-06, EC-07
- **Type:** integration

### TC-49: Neither route requires an `Authorization` header

- **US:** UM-US-02
- **Given:** A caller presenting no credentials at all
- **When:** An activation is submitted with a usable token, and separately a state check is requested
- **Then:** Both requests are processed normally — no `401` — because an invited person has no account yet to authenticate with
- **AC:** AC-12, BR-08
- **Type:** integration

### TC-50: A token whose user is already ACTIVE is refused

- **US:** UM-US-02
- **Given:** An invitation whose `PENDING` user has since been activated by another path, so the user is now `ACTIVE` while the invitation row itself is still `PENDING`
- **When:** That token is submitted for activation
- **Then:** The response is `400` `INVITATION_TOKEN_INVALID` — re-running activation must not overwrite a live password
- **AC:** EC-06, FR-06
- **Type:** integration

### TC-51: A token whose user is DEACTIVATED is refused

- **US:** UM-US-02
- **Given:** An invitation whose user has since been set `DEACTIVATED`
- **When:** That token is submitted for activation
- **Then:** The response is `400` `INVITATION_TOKEN_INVALID` — a withdrawn account is not restored by an old invitation link
- **AC:** EC-07, FR-06
- **Type:** integration

### TC-52: A token altered by surrounding whitespace does not match

- **US:** UM-US-02
- **Given:** A `PENDING` user with a usable invitation whose raw token is known
- **When:** Activation is submitted with that token plus a leading or trailing space
- **Then:** The response is `400` `INVITATION_TOKEN_INVALID` — treated as unrecognised, not as the original token with noise around it; no normalisation is applied
- **AC:** EC-08, FR-02
- **Type:** integration

### TC-53: A token at the exact instant of expiry is treated as expired

- **US:** UM-US-02
- **Given:** An invitation created at frozen time `T` with a 24-hour TTL
- **When:** The clock is set to exactly `T + 24h` and the token is submitted
- **Then:** The response is `400` `INVITATION_TOKEN_EXPIRED` — the TTL is valid strictly *until* its expiry instant, not through it
- **AC:** EC-10, AC-02, BR-03
- **Type:** integration

### TC-54: Sequential double-submission of one valid token succeeds exactly once

- **US:** UM-US-02
- **Given:** A `PENDING` user with a single usable invitation
- **When:** The identical activation payload is submitted twice in immediate sequence
- **Then:** Exactly one submission returns `200` and activates the account; the other returns `400` `INVITATION_TOKEN_INVALID`; the user ends `ACTIVE` exactly once, never twice, never partially — the constructable half of EC-05 (true parallel writers deferred, see QF-02)
- **AC:** EC-05, FR-20
- **Type:** integration

### TC-55: Expiry never overrides another refusal reason, however much time has passed

- **US:** UM-US-02
- **Given:** Four invitations, each unusable for a non-expiry reason **and** advanced well past its 24-hour TTL: one already `ACCEPTED`, one `SUPERSEDED`, one whose user is `ACTIVE`, and one whose user is `DEACTIVATED`
- **When:** Each token is submitted for activation, and each token's state is requested
- **Then:** Every one of the eight responses is the `not_usable` outcome — `400` `INVITATION_TOKEN_INVALID` for the activations and `state: "not_usable"` for the state checks — and **none** is `INVITATION_TOKEN_EXPIRED` or `expired`. Asserted as an equality against the corresponding within-TTL responses from TC-47/TC-48: the same four preconditions must answer identically before and after the TTL passes, so no client can distinguish a used token from an unissued one by waiting a day
- **AC:** EC-11, BR-02, FR-22, AC-04, AC-05, EC-06, EC-07
- **Type:** integration

### TC-56: A full name longer than the account record can hold is rejected, not truncated

- **US:** UM-US-02
- **Given:** A `PENDING` user with a usable invitation
- **When:** Activation is submitted with a `full_name` of 256 characters, one past the stored width
- **Then:** The response is `422` `VALIDATION_ERROR` identifying the `full_name` field; the user remains `PENDING` and nothing is persisted — deterministically, on SQLite and PostgreSQL alike, rather than passing locally and failing as a `500` on the deployment target (QF-05 as amended, ENV-03)
- **AC:** AC-10, FR-23
- **Type:** integration
