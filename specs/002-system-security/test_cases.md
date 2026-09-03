# Test Cases: System Security (SS)

> **Feature:** SRS §6 Feature-02 · SDS §5.1 (SS)
> **Spec:** [spec.md](spec.md) · **Plan:** [plan.md](plan.md)
> **Stories in this file:** SS-US-01 *(TC-01…TC-11)* · SS-US-02 *(TC-12…TC-15)*

---

## SS-US-01: Login

### Acceptance Criteria Classification

No login screen change is in scope this round — `mobile/app/(auth)/login.tsx` already exists as a
fixture-driven prototype from UM-US-01's round (its "not yet specified — boilerplate only" banner
is retired once this story wires it to the real endpoint, in Phase 5). All rows below are `[API]`.

| AC/EC | Title | Label | Rationale |
|---|---|---|---|
| AC-01 | Successful login for an ACTIVE account | **[API]** | Token issuance and shape only |
| AC-02 | Reject a PENDING account with the SRS's own message | **[API]** | Response-body contract |
| AC-03 | Reject an incorrect password indistinguishably from an unknown email | **[API]** | Response sameness, bounded by QF-01 |
| AC-04 | Reject a DEACTIVATED account without disclosing it | **[API]** | Response sameness, bounded by QF-01 |
| AC-05 | A DEACTIVATED account's password is still checked before its state is | **[API]** | Precedence — narrower than a first draft's blanket rule; does not extend to `PENDING` (see `spec.md`'s reconciling note) |
| AC-06 | Never expose the credential | **[API]** | Response/log shape, bounded by QF-02 |
| AC-07 | Record an audit event for every attempt | **[API]** | Log-boundary assertion |
| AC-08 | Reject a malformed payload before evaluating credentials | **[API]** | Validation-layer contract |
| AC-09 | No credentials required to call this endpoint | **[API]** | Authorization contract |

### Quality Findings

#### QF-01

**Description.** AC-03/AC-04 require that an unknown email, a wrong password, and a `DEACTIVATED`
account all produce the identical response. A test asserting each case individually correct does
not prove they are indistinguishable *from each other* — the same shape of gap UM-US-01 QF-04 and
UM-US-02 QF-04 both closed for their own oracles.

**Impact.** Three independently-passing assertions could each carry a subtly different message.

**Recommendation.** `TC-04` constructs all three preconditions and asserts the response bodies are
byte-identical, the same technique UM-US-02's TC-47/TC-48 used.

#### QF-02

**Description.** AC-06 requires the password and hash appear in no log entry. There is no
audit-read endpoint (UM-US-01 `plan.md` A9, unchanged), so this can only be proven at the logging
boundary, not by retrieving a persisted record.

**Impact.** A weaker assertion than reading a stored row — it proves the emitted line's shape, not
that an operator could retrieve it later.

**Recommendation.** `TC-07`/`TC-08` use `caplog`, exactly as UM-US-01's TC-16 and UM-US-02's TC-40
did. If an audit-retrieval story is ever specified, this note is retired.

### Coverage Matrix

| AC/EC | Label | Integration TC(s) | E2E TC(s) | Blocked on |
|---|---|---|---|---|
| AC-01 | [API] | TC-01 | *deferred* | — |
| AC-02 | [API] | TC-02 | *deferred* | — |
| AC-03 | [API] | TC-03, TC-04 | — | — |
| AC-04 | [API] | TC-05, TC-04 | — | — |
| AC-05 | [API] | TC-06 | — | — |
| AC-06 | [API] | TC-07 | — | — |
| AC-07 | [API] | TC-07, TC-08 | — | — |
| AC-08 | [API] | TC-09 | — | — |
| AC-09 | [API] | TC-10 | — | — |
| EC-01 | [API] | TC-11 | — | — |

> Every AC and EC has at least one integration TC. `[API]`-only rows are deferred to the mobile
> round for the same reason UM-US-01/UM-US-02 deferred theirs: no screen in this round is wired to
> a real endpoint yet. **Known coverage limit, accepted:** audit durability (QF-02, log-shape only
> — same limit as UM-US-01 QF-01 and UM-US-02 QF-03).

### Test Implementation Map *(filled at step 4)*

`pytest` node ids for each TC. All under `backend/tests/integration/test_ss_us_01_login.py`.

| TC | pytest node id | Result |
|---|---|---|
| TC-01 | `test_successful_login_for_active_account_issues_a_signed_token` | PASS |
| TC-02 | `test_pending_account_refused_regardless_of_password_submitted` | PASS |
| TC-03 | `test_unknown_email_and_wrong_password_against_active_both_return_401` | PASS |
| TC-04 | `test_unknown_wrong_password_and_deactivated_answer_identically` | PASS |
| TC-05 | `test_deactivated_account_with_correct_password_refused_generically` | PASS |
| TC-06 | `test_deactivated_account_with_wrong_password_refused_identically_to_correct` | PASS |
| TC-07 | `test_response_and_audit_log_never_contain_password_or_hash` | PASS |
| TC-08 | `test_refused_login_emits_audit_record_marked_failure` | PASS |
| TC-09 | `test_malformed_or_missing_payload_rejected_with_422_before_any_lookup` (4 params) | PASS |
| TC-10 | `test_login_accepts_a_request_with_no_bearer_token` | PASS |
| TC-11 | `test_email_differing_by_case_and_whitespace_still_matches` | PASS |

Full suite: `134 passed` (120 from UM-US-01/UM-US-02 + 14 here). `ruff check` clean, `mypy app`
clean, coverage **98%**; `auth_service.py`, `api/v1/auth.py`, and `schemas/auth.py` all **100%**.

**One design defect found and fixed before any code was written — the point of the design step.**
A first pass at `plan.md` generalised UM-US-02's "verify the secret before checking state" pattern
into one blanket rule for login too. Tracing through what it would actually do for a `PENDING`
account caught the flaw before implementation: a `PENDING` account's `password_hash` is `NULL`
(UM-US-01 AC-07), so "verify the password first" can only ever fail for it, and AC-02's
SRS-mandated message would never be reachable. Fixed in `spec.md`/`plan.md` (recorded as finding F2)
by narrowing the precedence rule to accounts that actually hold a password — `PENDING` is checked
first and unconditionally instead. `TC-02` is the test that would have caught this the moment code
was written; catching it one step earlier meant the first implementation attempt needed no rework —
all 14 tests passed on the first run.

**One unrelated pre-existing flakiness found while running the full suite alongside this story's
tests.** Three UM-US-02 tests (`TC-29`, `TC-41`, `TC-46`) created an invitation under the **real**
system clock via `get_token_from_invite()`, then jumped to an **absolute** `FROZEN_NOW + delta` via
`advance_clock()` — a race between real wall-clock time and a fixed constant that happened to pass
whenever the suite ran before `FROZEN_NOW`'s time-of-day and fails afterward, which is exactly what
surfaced hours into this session. Fixed by also requesting the `frozen_now` fixture in those three
tests, so the invitation's creation happens under the same frozen clock the later jump is relative
to. Unrelated to this story's own code — recorded here because it was found while verifying it.

---

### TC-01: Successful login for an ACTIVE account issues a signed token

- **US:** SS-US-01
- **Given:** An `ACTIVE` user exists with a known email and password
- **When:** That email and correct password are submitted
- **Then:** The response is `200` with `access_token`, `token_type: "bearer"`, `expires_in`, and `role` matching the account; the token decodes with the configured secret and its subject is the user's id
- **AC:** AC-01, FR-08
- **Type:** integration

### TC-02: A PENDING account is refused with the SRS's message, regardless of the password submitted

- **US:** SS-US-01
- **Given:** A `PENDING` user exists (its `password_hash` is `NULL` — UM-US-01 AC-07)
- **When:** That email is submitted with an arbitrary, obviously-wrong password
- **Then:** The response is `403` `ACCOUNT_NOT_ACTIVATED` with message "Your account is not activated. Please check your email invitation." — no password comparison is possible or attempted, so no password value changes this outcome
- **AC:** AC-02, FR-04, EC-03
- **Type:** integration

### TC-03: An unknown email and a wrong password against an ACTIVE account both return 401 INVALID_CREDENTIALS

- **US:** SS-US-01
- **Given:** One email that matches no account, and one that matches an `ACTIVE` account but with an incorrect password
- **When:** Each is submitted
- **Then:** Both responses are `401` `INVALID_CREDENTIALS` with the same generic message
- **AC:** AC-03, FR-06
- **Type:** integration

### TC-04: Unknown email, wrong password against ACTIVE, and a DEACTIVATED account answer identically

- **US:** SS-US-01
- **Given:** An unknown email, an `ACTIVE` account with a wrong password, and a `DEACTIVATED` account with its correct (pre-deactivation) password
- **When:** Each is submitted
- **Then:** All three response bodies are byte-identical — `401` `INVALID_CREDENTIALS`, same message, same `details` — so none discloses which case occurred. (`PENDING` is deliberately **not** part of this set — AC-02 names it on purpose, per the reconciling note in `spec.md` after EC-03.)
- **AC:** AC-03, AC-04, FR-06, FR-07
- **Type:** integration

### TC-05: A DEACTIVATED account with the correct password is refused generically

- **US:** SS-US-01
- **Given:** A `DEACTIVATED` user exists
- **When:** That email and its correct (pre-deactivation) password are submitted
- **Then:** The response is `401` `INVALID_CREDENTIALS` — not a distinct "deactivated" code, and not `403`
- **AC:** AC-04, FR-07, BR-02
- **Type:** integration

### TC-06: A DEACTIVATED account with the wrong password is refused identically to the right one

- **US:** SS-US-01
- **Given:** A `DEACTIVATED` user exists — one that *does* hold a password hash, from before it was deactivated
- **When:** That email is submitted with an **incorrect** password
- **Then:** The response is `401` `INVALID_CREDENTIALS` — the same outcome as TC-05's correct-password case — proving the password check still runs for an account that has one, and a wrong guess against it reveals nothing extra about its state. (This is deliberately **not** the `PENDING` case — see `spec.md`'s reconciling note: `PENDING` has no password to check in the first place, so this precedence guarantee does not apply to it, by design.)
- **AC:** AC-05, BR-01
- **Type:** integration

### TC-07: The response and audit log never contain the password or its hash

- **US:** SS-US-01
- **Given:** An `ACTIVE` user, and log capture enabled
- **When:** A login is submitted with the correct password
- **Then:** The response body contains neither the submitted password nor the stored hash; the captured audit log line contains neither either
- **AC:** AC-06, AC-07, FR-09
- **Type:** integration

### TC-08: A refused login also emits an audit record, marked FAILURE

- **US:** SS-US-01
- **Given:** An unknown email, and log capture enabled
- **When:** A login is submitted and refused
- **Then:** One audit record is emitted with result `FAILURE`, the attempted email as target, and no credential in it
- **AC:** AC-07, FR-10
- **Type:** integration

### TC-09: A malformed or missing payload is rejected with 422 before any lookup

- **US:** SS-US-01
- **Given:** A request missing the password field, missing the email field, and one with a malformed email, in turn
- **When:** Each is submitted
- **Then:** Each response is `422` `VALIDATION_ERROR`; no audit record is emitted for any of them, since the service never runs
- **AC:** AC-08, FR-02
- **Type:** integration

### TC-10: The endpoint accepts a request with no bearer token

- **US:** SS-US-01
- **Given:** A caller presenting no `Authorization` header at all
- **When:** A valid login is submitted
- **Then:** The request is processed normally and succeeds — never a `401` for the absent header itself
- **AC:** AC-09
- **Type:** integration

### TC-11: Email differing by case or surrounding whitespace still matches the account

- **US:** SS-US-01
- **Given:** An `ACTIVE` user exists with email `jane@gmail.com`
- **When:** `"  Jane@Gmail.COM  "` is submitted with the correct password
- **Then:** The response is `200` with a token for that same account
- **AC:** EC-01, FR-03, BR-04
- **Type:** integration

---

## SS-US-02: Logout

> **IDs in this section are local to SS-US-02.** `AC-01`/`AC-02` below refer to `spec.md`'s
> SS-US-02 section, not SS-US-01's. `TC-NN` continues from `TC-11`.

### Acceptance Criteria Classification

No logout screen exists in `mobile/` this round — `mobile/src/store/auth.ts`'s `signOut()` is a
fixture-driven client action built during UM-US-01's round, not wired to any real endpoint yet
(spec *Out of scope*). All rows below are `[API]`, deferred rather than skipped, on the same basis
as SS-US-01's own login-screen rows.

| AC/EC | Title | Label | Rationale |
|---|---|---|---|
| AC-01 | Successful logout for an authenticated caller | **[API]** | Response shape and confirmation only — no screen wired this round |
| AC-02 | Reject a caller with no valid credentials | **[API]** | Authorization contract, identical shape to every other protected route's 401 |

### Coverage Matrix

| AC/EC | Label | Integration TC(s) | E2E TC(s) | Blocked on |
|---|---|---|---|---|
| AC-01 | [API] | TC-12 | *deferred* | — |
| AC-02 | [API] | TC-13, TC-14 | — | — |
| EC-01 | [API] | TC-14 | — | — |
| EC-02 | [API] | TC-15 | — | — |

> Every AC and EC has at least one integration TC. The `[API]`-only rows are deferred to the mobile
> round for the same reason SS-US-01/UM-US-01/UM-US-02 deferred theirs: no screen in this round is
> wired to a real endpoint yet. **No audit coverage row exists here, by design** — `plan.md` A2
> records that constitution LA-04 does not name logout as an audit-worthy event for this epic, so
> unlike SS-US-01's login (which has TC-07/TC-08 asserting an audit record), this story emits none
> to test for. `TC-15` is the positive proof for EC-02's documented scope statement (`plan.md` A3):
> it does not merely assert the absence of a defect, it re-uses the same token after logout and
> shows it still authenticates.

### Test Implementation Map *(filled at step 4)*

`pytest` node ids for each TC. All under `backend/tests/integration/test_ss_us_02_logout.py`.

| TC | pytest node id | Result |
|---|---|---|
| TC-12 | `test_successful_logout_returns_confirmation_with_no_credential` | PASS |
| TC-13 | `test_no_bearer_token_is_refused_with_401_not_authenticated` | PASS |
| TC-14 | `test_malformed_invalid_or_expired_token_refused_identically` (3 params: malformed, invalid-signature, expired) | PASS |
| TC-15 | `test_token_still_authenticates_after_logout_until_its_own_expiry` | PASS |

Full suite: `172 passed` (166 pre-existing + 6 here). `ruff check` and `ruff format --check` clean,
`mypy app` clean, coverage **98%**; `auth_service.py` and `api/v1/auth.py` both **100%**,
`schemas/auth.py` **100%**.

Before any implementation code existed, the route was confirmed absent (`POST /auth/logout` under a
renamed path returned `404`) so all six cases failed for the right reason — a missing route, not an
import error or a false-positive assertion — matching this repo's TDD requirement. Adding
`LogoutResult`, `auth_service.logout()`, and the router turned all six green on the first run; no
rework was needed and no defect was found along the way.

### TC-12: Successful logout for an authenticated caller returns a confirmation with no credential

- **US:** SS-US-02
- **Given:** An `ACTIVE` user holding a currently valid bearer token, obtained via login
- **When:** That caller calls `POST /auth/logout` with the token
- **Then:** The response is `200` with `{"status": "SUCCESS", "message": ...}`; the response body
  contains no token, no `access_token` field, and no other credential of any kind
- **AC:** AC-01, FR-02, FR-04
- **Type:** integration

### TC-13: A caller presenting no bearer token is refused with 401 NOT_AUTHENTICATED

- **US:** SS-US-02
- **Given:** A caller presenting no `Authorization` header at all
- **When:** `POST /auth/logout` is called
- **Then:** The response is `401` `NOT_AUTHENTICATED` — the same generic outcome every other
  protected route in this system already returns; there is no unauthenticated path through logout
- **AC:** AC-02, FR-01, FR-03, BR-01
- **Type:** integration

### TC-14: A malformed token, an invalid signature, or an expired token is refused identically

- **US:** SS-US-02
- **Given:** In turn — a syntactically malformed bearer token, a token whose signature does not
  verify, and a token that is well-formed but past its 60-minute expiry
- **When:** `POST /auth/logout` is called with each in turn
- **Then:** Each response is `401` `NOT_AUTHENTICATED` — indistinguishable from one another and
  from TC-13's no-token case; logout is not exempt from ordinary token verification
- **AC:** AC-02, EC-01, FR-03
- **Type:** integration

### TC-15: A token presented at logout still authenticates afterward, until its own natural expiry

- **US:** SS-US-02
- **Given:** An `ACTIVE` user holding a currently valid bearer token
- **When:** The caller calls `POST /auth/logout` successfully, then calls `POST /auth/logout`
  **again** with the exact same token (chosen over a different protected route so the test needs
  no assumption about the caller's role — `CurrentUserDep` is the only requirement either call has)
- **Then:** The second call also succeeds with `200` — logout performed no server-side revocation,
  exactly as `spec.md`'s Assumptions & Dependencies documents; the token continues to authenticate
  until it expires on its own
- **AC:** EC-02, FR-05, BR-02
- **Type:** integration
