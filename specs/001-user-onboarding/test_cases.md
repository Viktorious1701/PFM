# Test Cases: User Management & Onboarding (UM)

> **Feature:** SRS §6 Feature-01 · SDS §5.2 (UM)
> **Spec:** [spec.md](spec.md) · **Plan:** [plan.md](plan.md)
> **Stories in this file:** UM-US-01 *(TC-01…TC-26)* · UM-US-02, UM-US-03 *(pending, continue from TC-27)*

---

## UM-US-01: Invite a User via Email

### Quality Findings

Problems found while deriving test cases from `spec.md` and `plan.md`. Each one changes how a criterion can be asserted, so it is recorded rather than worked around silently.

#### QF-01

**Description.** AC-09 / FR-17 require an audit entry on every successful invitation, but `plan.md` A9 deliberately implements audit as **structured log lines with no `activity_logs` table**, and no story exposes an audit-read endpoint. There is no API or database surface through which an audit entry can be observed.

**Impact.** AC-09 cannot be asserted through the public API at all.

**Recommendation.** Assert it at the logging boundary instead: `TC-16` uses pytest's `caplog` to capture the emitted record and checks the five LA-02 fields are present and that the token is absent. This is a genuinely weaker assertion than reading a persisted row — it verifies the call happened and its shape, not that an operator could later retrieve it. If an audit-retrieval story is ever specified, AC-09 should be re-tested against the store and this note removed.

#### QF-02

**Description.** EC-05 (two ADMINs invite the same new address simultaneously) needs true write concurrency. The test database is SQLite (ADR-0001), which serialises writers, and the suite runs single-threaded with an in-memory database shared through `StaticPool`.

**Impact.** A deterministic "two parallel requests race" test is not constructable in this environment. Writing one that appears to pass would be misleading — it would prove serialisation, not conflict handling.

**Recommendation.** Split the criterion. `TC-14` asserts the **guard that actually resolves the race**: the `users.email` unique index rejects a second insert, and the service maps that `IntegrityError` to `409 USER_EMAIL_ALREADY_ACTIVE` rather than leaking a 500. `TC-15` asserts sequential duplicate submission returns 409 and leaves exactly one row. True parallel-writer verification is deferred to the PostgreSQL run named in ADR-0001, and is listed as a known coverage limit below.

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

`TC-22` is the opt-in live-SMTP case (`@pytest.mark.smtp`). It is the positive counterpart to `EC-07` — it proves the configuration EC-07 fails on is correct — but it does not exercise EC-07's failure path, so it is not listed against it.

> Every AC and EC has at least one integration TC. `[BOTH]` rows have **no** E2E case because `mobile/` has no screens this round — they are deferred to the mobile round, not silently dropped. TC-11…TC-13 were blocked on SS-US-01 per QF-03; `plan.md` A11 unblocked them by shipping token verification with this story, and all three are green. **Known coverage limits, accepted:** true concurrent-writer behaviour (QF-02, deferred to a PostgreSQL run), generator entropy as a property (QF-05, code review against SEC-02), audit durability (QF-01, log-shape only), and real SMTP delivery (QF-07, opt-in `TC-22` plus a manual Deploy gate).

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
