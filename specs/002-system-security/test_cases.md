# Test Cases: System Security (SS)

> **Feature:** SRS §6 Feature-02 · SDS §5.1 (SS)
> **Spec:** [spec.md](spec.md) · **Plan:** [plan.md](plan.md)
> **Stories in this file:** SS-US-01 *(TC-01…TC-11)* · SS-US-02 *(TC-12…TC-15)* · SS-US-03 *(TC-58…TC-96)*

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

---

## SS: UI test cases *(UI fast-track — CLAUDE.md §2)*

> Written after the System Security screens were built, under the UI fast-track ruling (2026-10-19). They pin down what the screens must **do** — each button's request, its answer, and what the person then sees — so a later change cannot silently break it. Visual design is never asserted. Each test arranges its own data through the API under a throwaway account, acts through the real screen, and lives in `mobile/e2e/`, run with `npm run test:e2e` against the real backend. Behaviour the screens cannot reach — expired tokens, other users' records, malformed payloads the client never sends — stays covered by the integration TCs above.

### Coverage Matrix (UI)

| TC | US | AC | E2E test | Status |
| :-- | :-- | :-- | :-- | :-- |
| TC-49 | SS-US-01 | AC-01 | `mobile/e2e/auth.spec.ts` › TC-49 | PASS — 2026-10-19, desktop + phone |
| TC-50 | SS-US-01 | AC-03 | `mobile/e2e/auth.spec.ts` › TC-50 | PASS — 2026-10-19, desktop + phone |
| TC-51 | SS-US-01 | AC-02 | `mobile/e2e/auth.spec.ts` › TC-51 | PASS — 2026-10-19, desktop + phone |
| TC-52 | SS-US-01 | AC-08 | `mobile/e2e/auth.spec.ts` › TC-52 | PASS — 2026-10-19, desktop + phone |
| TC-53 | SS-US-02 | AC-01 | `mobile/e2e/auth.spec.ts` › TC-53 | PASS — 2026-10-19, desktop + phone |
| TC-54 | SS-US-01 | — (server address, `constitution.md` ENV-06) | `mobile/e2e/auth.spec.ts` › TC-54 | PASS — 2026-10-22, desktop + phone |
| TC-55 | SS-US-01 | — (server address, `constitution.md` ENV-06) | — (test replaced by TC-57) | Superseded by TC-57 — 2026-10-22: the hint no longer names a trycloudflare.com address, since the server moved to a fixed Tailscale Funnel address |
| TC-57 | SS-US-01 | — (server address, `constitution.md` ENV-06) | `mobile/e2e/auth.spec.ts` › TC-57 | PASS — 2026-10-23, desktop + phone |
| TC-56 | SS-US-01 | — (server address, `constitution.md` ENV-06) | `mobile/e2e/auth.spec.ts` › TC-56 | PASS — 2026-10-22, desktop + phone |

### TC-49: An ACTIVE account signs in and stays signed in across a reload

- **US:** SS-US-01
- **Given:** An ACTIVE account and the sign-in panel
- **When:** Its email and password are entered and Sign in is pressed; then the page is reloaded
- **Then:** The login request is answered `200`; the Home tab is shown; after the reload the Home tab is shown again without signing in
- **AC:** AC-01
- **Type:** e2e

### TC-50: A wrong password is refused with the generic message

- **US:** SS-US-01
- **Given:** An ACTIVE account
- **When:** Its email and a wrong password are submitted
- **Then:** The login request is answered `401`; "The email or password is incorrect." is shown; the sign-in panel stays
- **AC:** AC-03
- **Type:** e2e

### TC-51: A PENDING account is told to activate first

- **US:** SS-US-01
- **Given:** An invited, not yet activated account
- **When:** Its email and any password are submitted
- **Then:** The login request is refused; the message tells the person their account is not activated yet; the sign-in panel stays
- **AC:** AC-02
- **Type:** e2e

### TC-52: Empty fields are caught before anything is sent

- **US:** SS-US-01
- **Given:** The sign-in panel
- **When:** Sign in is pressed with both fields empty
- **Then:** "Enter your email and password." is shown; no login request is sent
- **AC:** AC-08
- **Type:** e2e

### TC-53: Sign out ends the session on the server and on the device

- **US:** SS-US-02
- **Given:** A signed-in user on any tab
- **When:** Sign out is pressed; then the page is reloaded
- **Then:** The logout request is sent with the session token and answered `200`; the sign-in panel is shown; after the reload it is still the sign-in panel
- **AC:** AC-01
- **Type:** e2e

### TC-54: The sign-in panel names its server, and a changed address is used and remembered

- **US:** SS-US-01
- **Given:** The sign-in panel, on the build's default server address
- **When:** Change is pressed, a different address for the same backend is entered (`http://127.0.0.1:8000`), Use this server is pressed, and an ACTIVE account signs in; then the page is reloaded after signing out
- **Then:** The panel shows the new server's host; the login request goes to that address and is answered `200`; after the reload the panel still shows the new host
- **AC:** — (not an SRS/SDS acceptance criterion: the family's server address changes with every tunnel start, `constitution.md` ENV-06)
- **Type:** e2e

### TC-55: Something that isn't a server address is refused before anything is sent

- **US:** SS-US-01
- **Given:** The sign-in panel with the server address open for editing
- **When:** `not a server` is entered and Use this server is pressed
- **Then:** "That isn’t a server address. It looks like abc-def.trycloudflare.com" is shown; the address is not changed; no request is sent
- **AC:** — (`constitution.md` ENV-06)
- **Type:** e2e

### TC-56: An unreachable server is named as the problem

- **US:** SS-US-01
- **Given:** The server address set to one where nothing is listening
- **When:** An email and password are submitted
- **Then:** "Could not reach the server. Check your connection and the server address." is shown; the sign-in panel stays
- **AC:** — (`constitution.md` ENV-06)
- **Type:** e2e

### TC-57: Something that isn't a server address is refused before anything is sent (supersedes TC-55)

- **US:** SS-US-01
- **Given:** The sign-in panel with the server address open for editing
- **When:** `not a server` is entered and Use this server is pressed
- **Then:** "That isn’t a server address. It looks like laptop-name.tailnet.ts.net" is shown; the address is not changed; no request is sent
- **AC:** — (`constitution.md` ENV-06)
- **Type:** e2e

---

## SS-US-03: Guest trial

> **IDs in this section are local to SS-US-03.** `AC-NN`/`EC-NN`/`FR-NN` below refer to `spec.md`'s
> SS-US-03 section. `TC-NN` continues the epic from `TC-57`; `QF-NN` continues from SS-US-01's
> `QF-02`. Written at step 3, **before any test code** (TST-02). Integration TCs run under
> `uv run pytest` against `backend/tests/integration/test_ss_us_03_guest_trial.py`; e2e TCs are
> appended to `mobile/e2e/auth.spec.ts` (the epic's e2e file) and run with `npm run test:e2e` against
> the real backend — behaviour only, never visual design (`CLAUDE.md` §1.1 rule 0).

### Acceptance Criteria Classification

| AC/EC | Title | Label | Rationale |
|---|---|---|---|
| AC-01 | Start a guest trial without an invitation or credentials | **[BOTH]** | API: `201` and the session's shape; UI: the button signs the visitor in |
| AC-02 | The first view holds exactly one example | **[BOTH]** | API: exact rows and balance; UI: the example wallet is on screen |
| AC-03 | A guest uses the app as a member does | **[BOTH]** | API: every member route works and is owner-scoped; UI: adding a wallet works |
| AC-04 | The guest stays signed in for the whole trial | **[BOTH]** | API: token lifetime; UI: still a guest after a reload |
| AC-05 | Access ends when the trial ends | **[BOTH]** | API: `401`; UI: back to sign-in — a refused session simulated in the browser (QF-05) |
| AC-06 | An ended trial is deleted with everything in it | **[API]** | Server-side deletion; nothing on screen |
| AC-07 | A guest can never be signed into with credentials, emailed, or upgraded | **[API]** | Validation, service and CLI refusals |
| AC-08 | Guests are not family members | **[API]** | List contents and total |
| AC-09 | A guest cannot act as an administrator | **[BOTH]** | API: `403`; UI: no Family tab |
| AC-10 | Trial starts from one client are limited | **[API]** | `429` — not constructible against a shared e2e backend (QF-06) |
| AC-11 | The number of live trials is capped | **[API]** | `503` — same reason |
| AC-12 | Starting a trial is all-or-nothing | **[API]** | Rollback, forced by a failing seed step |
| AC-13 | Trial creation and deletion are recorded | **[API]** | Log-boundary assertion (QF-07) |
| AC-14 | The guest is always told they are on a trial | **[UI]** | Banner text and date |
| AC-15 | Signing out keeps the trial | **[BOTH]** | API: logout deletes nothing and the token still works; UI: no dialog, Continue offered |
| AC-16 | A saved trial can be continued on the same device | **[BOTH]** | API: the token still works after logout; UI: Continue lands on Home with the data |
| AC-17 | A saved trial that has ended by the device's clock is not offered | **[UI]** | Device-only decision, no request |
| AC-18 | A saved trial the server no longer accepts is discarded with a message | **[BOTH]** | API: ended or deleted guest `401`; UI: message, button gone |
| AC-19 | "Try as a guest" always starts a new trial | **[BOTH]** | API: a second trial is a separate account; UI: replaces the saved one |
| AC-20 | Signing in as a member keeps the saved trial | **[UI]** | Device storage across a member session |
| EC-01 | The exact moment the trial ends | **[API]** | Clock-seam boundary |
| EC-02 | Ended but not yet deleted | **[API]** | Stored end time in the past, row still present |
| EC-03 | Cap reached, but some counted trials have ended | **[API]** | Lazy purge before counting |
| EC-04 | The server restarts | **[API]** | Startup purge |
| EC-05 | Two guests at once | **[API]** | Isolation |
| EC-06 | A guest removes the example | **[API]** | Member rules on the example |
| EC-07 | How many days are left | **[UI]** | N from the saved trial end (QF-08) |
| EC-08 | A former guest is later invited | **[API]** | Invitation unaffected by the trial |
| EC-09 | Sign-in naming a guest's placeholder address | **[API]** | `422` at the boundary, `INVALID_CREDENTIALS` at the service (`plan.md` F1) |
| EC-10 | The device's clock disagrees with the server's | **[UI]** | Both directions, simulated in device storage |
| EC-11 | A guest signs out while the server cannot be reached | **[UI]** | Network failure simulated in the browser |
| EC-12 | A guest is refused while using the app | **[BOTH]** | API: `401`; UI: ended message, saved trial dropped |

### Quality Findings

#### QF-03

**Description.** PyJWT validates a token's `exp` against the real wall clock, not the
`app.core.clock` seam that `TST-06` tests freeze. A test that advances the seam past the trial end
does not make the token itself expire, and a token minted under a frozen clock far from real time
could already be expired in real terms.

**Impact.** A boundary test written against the token's own `exp` would be measuring PyJWT and real
time, not this story's rule.

**Recommendation.** The trial-end boundary (EC-01) is asserted against the **stored end time**, which
is the authoritative check (`plan.md` A4/A5): `TC-65`/`TC-66` move the seam, never the token. The
token's lifetime is asserted separately by decoding it (`TC-62`: `exp − iat` equals the trial
length). Tests freeze the clock near real time, as the existing suites already do.

#### QF-04

**Description.** AC-10's limit is **per client address**, but every request from the `httpx` test
client arrives from the same address.

**Impact.** The integration suite can prove that the sixth start from one address is refused; it
cannot prove that a different visitor is unaffected, nor that the address counted behind Tailscale
Funnel is the visitor's (`plan.md` A11).

**Recommendation.** `TC-75` proves the count and the refusal. The per-visitor half is `plan.md` T-15 —
two real requests through the live Funnel address from different networks, pasted at the Deploy gate.
If the implementation keys on a forwarded header explicitly (A11's fallback), `TC-75` gains a second
client value and asserts it is unaffected.

#### QF-05

**Description.** A genuinely ended trial cannot be produced end-to-end: the e2e suite drives the real
backend, which has no clock seam, and a trial lasts 7 days.

**Impact.** The client paths that react to an ended trial — AC-05, AC-17, AC-18, EC-10, EC-12 — cannot
be driven by a real expiry in the browser.

**Recommendation.** The e2e TCs produce the two observable conditions instead, through device storage:
a token the server refuses (`401`, exactly what an ended or purged trial returns — `TC-92`, `TC-96`),
and a saved trial end already in the past (`TC-93`). The server side of a real expiry is proven by
`TC-65`/`TC-66`/`TC-67` under the clock seam.

#### QF-06

**Description.** The e2e backend sees every request from `127.0.0.1`, so the suite's own guest tests
spend the per-client allowance (5 per hour) and accumulate live trials toward the cap (200) — trials
stay in the dev database until 7 days after they started.

**Impact.** Run as configured for production, the guest e2e tests would start failing with `429` after
the fifth trial in an hour, and `429`/`503` themselves cannot be produced on demand without starving
every other test.

**Recommendation.** The e2e backend's `.env` raises `GUEST_RATE_LIMIT` (and `GUEST_MAX_ACTIVE` if
needed) — the reason those are settings at all (`plan.md` A10, T-14). `429` and `503` are proven by
integration TCs only (`TC-75`, `TC-74`); the client's display of their message is not e2e-tested.

#### QF-07

**Description.** AC-13's audit entries are structured log lines; there is no audit-read endpoint
(UM-US-01 `plan.md` A9, unchanged).

**Impact.** Same limit as QF-02: the tests prove the emitted line's shape, not that it can be retrieved
later.

**Recommendation.** `TC-69`/`TC-70` use `caplog`, as `TC-07`/`TC-08` do.

#### QF-08

**Description.** "N days left" depends on the moment it is rendered (`plan.md` A19: whole days,
rounded down, at least 1).

**Impact.** A literal such as "6 days left" in a test is right only if the test runs within the same
day-boundary as the trial's start — usually, but not by construction.

**Recommendation.** `TC-90` computes the expected N from the trial end the server returned, with the
same rule, at assertion time; the rule's two edges (6 days 23 hours → 6, under one day → 1) are
asserted by `TC-93` through device storage, not by waiting.

### Coverage Matrix

| AC/EC | Label | Integration TC(s) | E2E TC(s) | Blocked on |
|---|---|---|---|---|
| AC-01 | [BOTH] | TC-58, TC-59 | TC-86 | — |
| AC-02 | [BOTH] | TC-60 | TC-86 | — |
| AC-03 | [BOTH] | TC-61, TC-63 | TC-88 | — |
| AC-04 | [BOTH] | TC-62 | TC-87 | — |
| AC-05 | [BOTH] | TC-65, TC-67 | TC-96 | — |
| AC-06 | [API] | TC-68 | — | — |
| AC-07 | [API] | TC-59, TC-77, TC-78, TC-79, TC-80, TC-81 | — | — |
| AC-08 | [API] | TC-82 | — | — |
| AC-09 | [BOTH] | TC-83 | TC-89 | — |
| AC-10 | [API] | TC-75 | — *(QF-06)* | per-visitor half: `plan.md` T-15 (QF-04) — closed 2026-10-26, Test Implementation Map note 3 |
| AC-11 | [API] | TC-74 | — *(QF-06)* | — |
| AC-12 | [API] | TC-76 | — | — |
| AC-13 | [API] | TC-69, TC-70 | — | — |
| AC-14 | [UI] | — | TC-86, TC-87 | — |
| AC-15 | [BOTH] | TC-85 | TC-90 | — |
| AC-16 | [BOTH] | TC-85 | TC-90 | — |
| AC-17 | [UI] | — | TC-93 | — |
| AC-18 | [BOTH] | TC-65, TC-67 | TC-92 | — |
| AC-19 | [BOTH] | TC-64 | TC-94 | — |
| AC-20 | [UI] | — | TC-95 | — |
| EC-01 | [API] | TC-66 | — | — |
| EC-02 | [API] | TC-65 | — | — |
| EC-03 | [API] | TC-73 | — | — |
| EC-04 | [API] | TC-71 | — | — |
| EC-05 | [API] | TC-64 | — | — |
| EC-06 | [API] | TC-61 | — | — |
| EC-07 | [UI] | — | TC-90, TC-93 | — |
| EC-08 | [API] | TC-84 | — | — |
| EC-09 | [API] | TC-77, TC-78 | — | — |
| EC-10 | [UI] | — | TC-92, TC-93 | — |
| EC-11 | [UI] | — | TC-91 | — |
| EC-12 | [BOTH] | TC-65 | TC-96 | — |

> Every AC and EC has at least one TC; every `[BOTH]`/`[UI]` row has an e2e TC. FR-07's operator
> command is `TC-72`. **Known coverage limits, accepted:** the per-visitor half of AC-10 (QF-04, closed
> by T-15 at Deploy), real expiry in the browser (QF-05 — simulated through device storage), the
> client's `429`/`503` message (QF-06), audit durability (QF-07).

### Test Implementation Map *(filled at step 4)*

Integration TCs: `backend/tests/integration/test_ss_us_03_guest_trial.py`. E2E TCs: `mobile/e2e/auth.spec.ts`, run on both Playwright projects (`desktop`, `phone`) against the real dev backend.

| TC | pytest node id / e2e test | Result |
|---|---|---|
| TC-58 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_starting_a_trial_needs_no_credentials_and_returns_a_guest_session` | PASS — 2026-10-26 |
| TC-59 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_guest_account_has_placeholder_address_no_password_and_seven_day_end` | PASS — 2026-10-26 |
| TC-60 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_new_trial_holds_exactly_one_example_wallet_with_one_example_expense` | PASS — 2026-10-26 |
| TC-61 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_guest_can_do_everything_a_member_can_including_removing_the_example` | PASS — 2026-10-26 — see note 1 |
| TC-62 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_guest_token_lasts_the_whole_trial_not_sixty_minutes` | PASS — 2026-10-26 |
| TC-63 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_guest_and_member_cannot_see_each_others_data` | PASS — 2026-10-26 |
| TC-64 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_two_trials_are_two_separate_guests_each_with_a_fresh_example` | PASS — 2026-10-26 |
| TC-65 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_guest_whose_trial_has_ended_is_refused_even_before_deletion` | PASS — 2026-10-26 |
| TC-66 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_trial_ends_exactly_at_its_end_time` | PASS — 2026-10-26 |
| TC-67 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_deleted_guests_token_is_refused` | PASS — 2026-10-26 |
| TC-68 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_purge_removes_an_ended_trial_with_all_its_data_and_nothing_else` | PASS — 2026-10-26 |
| TC-69 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_starting_a_trial_is_audited_without_the_token` | PASS — 2026-10-26 |
| TC-70 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_deleting_an_ended_trial_is_audited_with_counts` | PASS — 2026-10-26 |
| TC-71 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_ended_trials_are_deleted_when_the_server_starts` | PASS — 2026-10-26 |
| TC-72 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_purge_guests_command_deletes_ended_trials_and_reports_what_it_removed` | PASS — 2026-10-26 |
| TC-73 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_an_ended_trial_never_holds_a_place_under_the_cap` | PASS — 2026-10-26 |
| TC-74 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_at_the_cap_a_new_trial_is_refused_and_nothing_is_created` | PASS — 2026-10-26 |
| TC-75 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_sixth_trial_start_from_one_client_within_an_hour_is_refused` | PASS — 2026-10-26 — see note 3 (per-visitor half) |
| TC-76 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_failure_while_creating_the_example_leaves_nothing_behind` | PASS — 2026-10-26 |
| TC-77 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_login_service_never_authenticates_a_guest_whatever_the_password` | PASS — 2026-10-26 — see note 2 |
| TC-78 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_login_naming_a_guests_placeholder_address_is_rejected_before_any_lookup` | PASS — 2026-10-26 |
| TC-79 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_admin_cannot_invite_a_guests_address_or_any_guest_style_address` | PASS — 2026-10-26 |
| TC-80 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_invitation_service_refuses_a_guest_address_past_the_validation_layer` | PASS — 2026-10-26 |
| TC-81 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_promote_admin_refuses_a_guest_account` | PASS — 2026-10-26 |
| TC-82 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_guests_are_absent_from_the_admins_user_list_and_its_total` | PASS — 2026-10-26 |
| TC-83 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_guest_cannot_invite_or_list_users` | PASS — 2026-10-26 |
| TC-84 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_former_guests_invitation_starts_an_ordinary_account_with_nothing_from_the_trial` | PASS — 2026-10-26 |
| TC-85 | `backend/tests/integration/test_ss_us_03_guest_trial.py::test_guests_sign_out_deletes_nothing_and_its_token_keeps_working` | PASS — 2026-10-26 |
| TC-86 | `mobile/e2e/auth.spec.ts` › TC-86 "Try as a guest" lands on Home with the example and the trial notice | PASS — 2026-10-26, desktop + phone |
| TC-87 | `mobile/e2e/auth.spec.ts` › TC-87 A guest is still a guest after a reload | PASS — 2026-10-26, desktop + phone |
| TC-88 | `mobile/e2e/auth.spec.ts` › TC-88 A guest can add a wallet | PASS — 2026-10-26, desktop + phone |
| TC-89 | `mobile/e2e/auth.spec.ts` › TC-89 A guest sees no Family tab | PASS — 2026-10-26, desktop + phone |
| TC-90 | `mobile/e2e/auth.spec.ts` › TC-90 A guest signs out, and continues the same trial from the sign-in screen | PASS — 2026-10-26, desktop + phone |
| TC-91 | `mobile/e2e/auth.spec.ts` › TC-91 A guest's sign-out while the server cannot be reached still keeps the trial | PASS — 2026-10-26, desktop + phone |
| TC-92 | `mobile/e2e/auth.spec.ts` › TC-92 A saved trial the server refuses is dropped with a message | PASS — 2026-10-26, desktop + phone |
| TC-93 | `mobile/e2e/auth.spec.ts` › TC-93 A saved trial whose end has passed by the device's clock is not offered, and N is never 0 | PASS — 2026-10-26, desktop + phone |
| TC-94 | `mobile/e2e/auth.spec.ts` › TC-94 "Try as a guest" with a saved trial starts a new one and replaces it | PASS — 2026-10-26, desktop + phone |
| TC-95 | `mobile/e2e/auth.spec.ts` › TC-95 A member's sign-in leaves the saved trial for later | PASS — 2026-10-26, desktop + phone |
| TC-96 | `mobile/e2e/auth.spec.ts` › TC-96 A guest refused while using the app returns to sign-in, told the trial has ended | PASS — 2026-10-26, desktop + phone |

Full backend suite: `660 passed` (632 pre-existing, unmodified, + 28 here — `plan.md` A5's condition for changing `get_current_user`). `ruff check` and `ruff format --check` clean, `mypy app` clean, coverage **99%**; `guest_service.py`, `rate_limit.py`, `auth_service.py`, `user_repo.py` and the four changed repositories **100%**. Full e2e suite: `110 passed` (88 pre-existing + 22 here: TC-86…TC-96 × desktop + phone). `npm run typecheck` clean.

**Seen failing first.** Before any implementation code existed, all 28 integration tests ran red for the right reason — the route absent (`404 NOT_FOUND` on `POST /auth/guest`) and, for TC-80, `DID NOT RAISE ValidationError`. The 11 e2e tests were run against the pre-story client (the six client files restored from `HEAD` for the run) and all 11 failed on the missing buttons, then passed on the story's client after a clean Metro restart. Each key guard was also mutated out once to prove its TC can fail: removing the `role != GUEST` filter fails TC-82; removing the ended-guest check in `get_current_user` fails TC-66; removing the `promote-admin` refusal fails TC-81; removing the lazy purge from `start()` fails TC-73.

**Note 1 — TC-61's wording.** TC-61 names `200` for the deletion of the example transaction; the member's own route answers `204 No Content` (TM-US-05). The TC's stated intent is "each answers exactly as for a member", so the test asserts `204` — the member's status — and the TC text is the imprecision, not the code. TC-61 itself is left unrewritten (`CLAUDE.md` §1.1 rule 4).

**Note 2 — `plan.md` F1 confirmed in code.** With both F1 guards removed from `auth_service.authenticate()` (the real-hash requirement and the `GUEST` refusal), TC-77 fails with `DID NOT RAISE InvalidCredentialsError`: the timing-parity dummy password did sign a guest in. With either guard alone it passes — the two are independent layers, behind `EmailStr`'s `422` at the API boundary (TC-78).

**Note 3 — the per-visitor half of AC-10 (QF-04), closed by `plan.md` T-15 on 2026-10-26.** The live log records public visitor addresses with port `0` (uvicorn's proxy-header rewrite). One request through `https://an-dang.tail8ac910.ts.net/health` carrying a forged `X-Forwarded-For: 203.0.113.7` was logged as `100.116.139.73:0` — this laptop's own tailnet address — not the forged one. So the limiter's key (`request.client.host`) is the real visitor behind Funnel, and a visitor cannot choose it by sending the header. Residual, accepted by the cap: an IPv6 visitor is keyed per full address (the live log already shows one, `2a03:cfc0:…`), so a host with a /64 could rotate addresses; AC-11's 200-trial cap still bounds the total.

**Deployment-time setting (QF-06).** The e2e backend is started with `GUEST_RATE_LIMIT=1000/hour GUEST_MAX_ACTIVE=100000` **as environment variables**, not in `backend/.env` as `plan.md` T-14 says, because `scripts/serve.sh` runs the live server from the same `backend/` directory and pydantic-settings would read `.env` there too — raising the limit in `.env` would raise it on the family's public server. `.env.example` documents this.

Gmail delivery: **N/A** for this story — a guest never receives email (SEC-12), and the story sends none.

### TC-58: Starting a trial needs no credentials and returns a guest session

- **US:** SS-US-03
- **Given:** A caller presenting no `Authorization` header, and the clock frozen
- **When:** `POST /api/v1/auth/guest` is sent with no body
- **Then:** The response is `201` with exactly `access_token`, `token_type: "bearer"`, `expires_in: 604800`, `role: "GUEST"`, and `expires_at` equal to the frozen time plus 7 days, carrying a UTC offset; the body contains no email, password or hash field
- **AC:** AC-01, FR-01, FR-02, FR-04
- **Type:** integration

### TC-59: The guest account has a placeholder address, no password, and a 7-day end

- **US:** SS-US-03
- **Given:** The clock frozen
- **When:** A trial is started and the new account is read back from the database
- **Then:** Its status is `ACTIVE` and role `GUEST`; its email matches `guest-<uuid4>@guest.invalid`; its password hash and full name are empty; its trial end is exactly the frozen time plus 7 days
- **AC:** AC-01, AC-07, FR-02, BR-01, BR-03
- **Type:** integration

### TC-60: A new trial holds exactly one example wallet with one example expense

- **US:** SS-US-03
- **Given:** A trial that has just started
- **When:** The guest lists its wallets, categories, transactions and budgets with its token
- **Then:** Exactly one wallet — "Example wallet", `VND`, balance `450000.00`; exactly one category — "Food", `EXPENSE`; exactly one transaction — `50000.00`, `EXPENSE`, note "Example: lunch", against that wallet and category; no budgets
- **AC:** AC-02, FR-03
- **Type:** integration

### TC-61: A guest can do everything a member can, including removing the example

- **US:** SS-US-03
- **Given:** A guest holding its token
- **When:** It creates a wallet, a category, a transaction and a budget; edits and deletes the example transaction; archives the example wallet; and requests its summary report
- **Then:** Each answers exactly as for a member — `201` for each creation, `200` for the edit, the deletion, the archive and the report — and the report reflects only the guest's own data
- **AC:** AC-03, EC-06, BR-04
- **Type:** integration

### TC-62: A guest's token lasts the whole trial, not 60 minutes

- **US:** SS-US-03
- **Given:** A trial started under a frozen clock
- **When:** Its token is decoded with the configured secret; then the clock seam is advanced 61 minutes and the guest lists its wallets
- **Then:** The token's `exp − iat` is 7 days (604800 seconds) and its `role` claim is `GUEST`; the request 61 minutes later is answered `200`
- **AC:** AC-04, FR-04
- **Type:** integration

### TC-63: A guest and a member cannot see each other's data

- **US:** SS-US-03
- **Given:** An `ACTIVE` member with a wallet, and a guest
- **When:** The guest lists wallets and requests the member's wallet by id; the member lists wallets
- **Then:** The guest's list holds only its example; its request for the member's wallet is `404 WALLET_NOT_FOUND`; the member's list holds none of the guest's wallets
- **AC:** AC-03, BR-04
- **Type:** integration

### TC-64: Two trials are two separate guests, each with a fresh example

- **US:** SS-US-03
- **Given:** No trials
- **When:** Two trials are started, one after the other
- **Then:** The two tokens name different accounts; each guest sees exactly one example wallet, and the two example wallets have different ids; neither guest can read the other's wallet by id (`404`)
- **AC:** EC-05, AC-19, AC-03
- **Type:** integration

### TC-65: A guest whose trial has ended is refused even before deletion

- **US:** SS-US-03
- **Given:** A guest whose stored trial end has been moved one minute into the past, its row and data still present, its token still cryptographically valid
- **When:** It lists its wallets
- **Then:** The response is `401 NOT_AUTHENTICATED`, byte-identical to the response for a request with no token at all
- **AC:** AC-05, EC-02, FR-05
- **Type:** integration

### TC-66: The trial ends exactly at its end time

- **US:** SS-US-03
- **Given:** A guest, and the clock seam set first to one second before its trial end, then to exactly its trial end
- **When:** It lists its wallets at each moment
- **Then:** One second before, the response is `200`; exactly at the end, it is `401 NOT_AUTHENTICATED`
- **AC:** EC-01, BR-01, FR-05
- **Type:** integration

### TC-67: A deleted guest's token is refused

- **US:** SS-US-03
- **Given:** A guest whose trial has ended and has been purged
- **When:** Its token is presented to any protected route
- **Then:** The response is `401 NOT_AUTHENTICATED`
- **AC:** AC-05, FR-05
- **Type:** integration

### TC-68: Purge removes an ended trial with all its data, and nothing else

- **US:** SS-US-03
- **Given:** An ended guest owning its example plus an extra wallet, category, budget and transaction; a live guest with its example; an `ACTIVE` member with a wallet, category, budget and transaction
- **When:** The purge runs
- **Then:** The ended guest's account, wallets, categories, budgets and transactions are all gone; the live guest's and the member's rows are all present with unchanged balances; the purge reports the counts it removed per kind
- **AC:** AC-06, FR-06
- **Type:** integration

### TC-69: Starting a trial is audited without the token

- **US:** SS-US-03
- **Given:** Log capture enabled
- **When:** A trial is started
- **Then:** One `GUEST_CREATED` record is emitted with result `SUCCESS`, the guest's id as actor and target, and the trial end; neither the access token nor the placeholder address appears in it
- **AC:** AC-13, FR-13
- **Type:** integration

### TC-70: Deleting an ended trial is audited with counts

- **US:** SS-US-03
- **Given:** An ended guest owning one wallet, one category, one transaction and one budget, and log capture enabled
- **When:** The purge runs
- **Then:** One `GUEST_PURGED` record is emitted with result `SUCCESS`, the guest's id as target, and counts `wallets: 1`, `categories: 1`, `transactions: 1`, `budgets: 1`; no token, password or hash appears in it
- **AC:** AC-13, FR-13
- **Type:** integration

### TC-71: Ended trials are deleted when the server starts

- **US:** SS-US-03
- **Given:** An ended guest with its example in the database, and a live guest
- **When:** The application starts (its startup hook runs)
- **Then:** The ended guest and its data are gone; the live guest is untouched
- **AC:** EC-04, AC-06, FR-07
- **Type:** integration

### TC-72: The purge-guests command deletes ended trials and reports what it removed

- **US:** SS-US-03
- **Given:** An ended guest with its example, and a live guest
- **When:** `python -m app.cli purge-guests` is run against the same database
- **Then:** It exits `0` and prints the number of trials and rows removed; the ended guest and its data are gone; the live guest is untouched
- **AC:** AC-06, FR-07
- **Type:** integration

### TC-73: An ended trial never holds a place under the cap

- **US:** SS-US-03
- **Given:** The cap set to 2, one live guest and one ended guest
- **When:** A trial is started
- **Then:** The response is `201`; the ended guest has been deleted; two guests remain, both live
- **AC:** EC-03, AC-11, FR-07
- **Type:** integration

### TC-74: At the cap, a new trial is refused and nothing is created

- **US:** SS-US-03
- **Given:** The cap set to 2, and two live guests
- **When:** A third trial is started
- **Then:** The response is `503 GUEST_LIMIT_REACHED` in the flat envelope; the number of accounts, wallets, categories and transactions is unchanged
- **AC:** AC-11, FR-11, BR-06
- **Type:** integration

### TC-75: The sixth trial start from one client within an hour is refused

- **US:** SS-US-03
- **Given:** The production limit (`5/hour`) and a reset limiter
- **When:** Six trials are started in succession from the same client
- **Then:** The first five are `201`; the sixth is `429 RATE_LIMIT_EXCEEDED` in the flat envelope (`error_code`, `message`, `details`); exactly five guest accounts exist
- **AC:** AC-10, FR-10, BR-06
- **Type:** integration

### TC-76: A failure while creating the example leaves nothing behind

- **US:** SS-US-03
- **Given:** Creating the example transaction forced to fail with an unexpected error
- **When:** A trial is started
- **Then:** The response is `500 INTERNAL_ERROR`; no guest account, wallet, category or transaction from that attempt exists
- **AC:** AC-12, FR-12
- **Type:** integration

### TC-77: The login service never authenticates a guest, whatever password is submitted

- **US:** SS-US-03
- **Given:** A guest account, and the login service called directly with that guest's placeholder address (the API boundary would reject the address first — TC-78)
- **When:** It is called with the timing-parity dummy password, then with an arbitrary password
- **Then:** Both raise the generic invalid-credentials refusal; no token is issued (`plan.md` F1)
- **AC:** AC-07, EC-09, FR-08
- **Type:** integration

### TC-78: A login naming a guest's placeholder address is rejected before any lookup

- **US:** SS-US-03
- **Given:** A guest account
- **When:** `POST /api/v1/auth/login` is sent with its placeholder address and any password
- **Then:** The response is `422 VALIDATION_ERROR` naming the email field; no token is issued and no login audit record is emitted
- **AC:** AC-07, EC-09, FR-08
- **Type:** integration

### TC-79: An ADMIN cannot invite a guest's address, or any guest-style address

- **US:** SS-US-03
- **Given:** An ADMIN, a live guest, and email capture
- **When:** The ADMIN invites the guest's exact placeholder address, then a fresh `someone@guest.invalid`
- **Then:** Both responses are `422 VALIDATION_ERROR`; no invitation row is created and no email is sent; the guest's account is unchanged
- **AC:** AC-07, FR-08
- **Type:** integration

### TC-80: The invitation service refuses a guest address even past the validation layer

- **US:** SS-US-03
- **Given:** An ADMIN, and the invitation service called directly with `guest-x@guest.invalid`
- **When:** It runs
- **Then:** It raises the validation refusal (`422`) and creates neither a user nor an invitation (`plan.md` A13's defensive layer)
- **AC:** AC-07, FR-08
- **Type:** integration

### TC-81: promote-admin refuses a guest account

- **US:** SS-US-03
- **Given:** A guest account
- **When:** `python -m app.cli promote-admin --email <its placeholder address> --password '…'` is run
- **Then:** It exits `1` with a message on stderr; the account is still `GUEST`, still `ACTIVE`, still without a password
- **AC:** AC-07, FR-08, BR-02
- **Type:** integration

### TC-82: Guests are absent from the ADMIN's user list and its total

- **US:** SS-US-03
- **Given:** An ADMIN, one `ACTIVE` member, one `PENDING` invitee, and two live guests
- **When:** The ADMIN lists users
- **Then:** The items contain the ADMIN, the member and the invitee and no guest; the total counts exactly those three
- **AC:** AC-08, FR-09, BR-05
- **Type:** integration

### TC-83: A guest cannot invite or list users

- **US:** SS-US-03
- **Given:** A guest holding its token
- **When:** It sends `POST /api/v1/users/invite` with a valid address, then `GET /api/v1/users`
- **Then:** Both are `403 FORBIDDEN`; no invitation is created
- **AC:** AC-09, BR-05
- **Type:** integration

### TC-84: A former guest's invitation starts an ordinary account with nothing from the trial

- **US:** SS-US-03
- **Given:** A live guest, and an ADMIN
- **When:** The ADMIN invites a real address for the same person
- **Then:** The response is `201`; the new account is `PENDING`, role `USER`, with no wallets or categories; the guest account and its example are unchanged
- **AC:** EC-08, AC-07, BR-02
- **Type:** integration

### TC-85: A guest's sign-out deletes nothing, and its token keeps working

- **US:** SS-US-03
- **Given:** A live guest with its example and one extra wallet, holding its token
- **When:** It calls `POST /api/v1/auth/logout`, then lists its wallets with the same token
- **Then:** The logout is `200` with the same `LogoutResult` shape SS-US-02 returns to anyone; the guest account, its wallets, category and transaction are all still present; the later wallet list is `200` with both wallets — the trial can be continued
- **AC:** AC-15, AC-16, FR-15, BR-07
- **Type:** integration

### TC-86: "Try as a guest" lands on Home with the example and the trial notice

- **US:** SS-US-03
- **Given:** The sign-in panel, with no saved guest trial on the device
- **When:** "Try as a guest" is pressed; then the Wallets tab is opened
- **Then:** The trial request is answered `201`; the Home tab is shown; the banner reads "Guest trial — deleted on <date>. Ask your family's admin for an invitation to keep using PFM." with the date of the response's trial end; the Wallets tab lists "Example wallet"
- **AC:** AC-01, AC-02, AC-14
- **Type:** e2e

### TC-87: A guest is still a guest after a reload

- **US:** SS-US-03
- **Given:** A guest who has just started a trial from the sign-in panel
- **When:** The page is reloaded
- **Then:** The Home tab is shown without signing in, and the trial banner is still shown with the same date
- **AC:** AC-04, AC-14
- **Type:** e2e

### TC-88: A guest can add a wallet

- **US:** SS-US-03
- **Given:** A guest on the Wallets tab
- **When:** The add-wallet form is filled with a new name and balance and submitted
- **Then:** The create request is answered `201`; the new wallet is listed beside "Example wallet"
- **AC:** AC-03
- **Type:** e2e

### TC-89: A guest sees no Family tab

- **US:** SS-US-03
- **Given:** A guest
- **When:** The tab bar is shown
- **Then:** There is no Family tab
- **AC:** AC-09
- **Type:** e2e

### TC-90: A guest signs out, and continues the same trial from the sign-in screen

- **US:** SS-US-03
- **Given:** A guest who started a trial and added a wallet
- **When:** Sign out is pressed; then the page is reloaded; then "Continue guest trial" is pressed and the Wallets tab opened
- **Then:** No confirmation is asked; the logout request is answered `200` and the sign-in panel is shown with "Continue guest trial — N days left", N computed from the trial end the server returned (whole days, rounded down, at least 1 — QF-08), beside "Try as a guest"; after the reload it is still offered; pressing it sends one wallet-list request answered `200`, the Home tab and the trial banner are shown, and the Wallets tab lists "Example wallet" and the added wallet
- **AC:** AC-15, AC-16, EC-07
- **Type:** e2e

### TC-91: A guest's sign-out while the server cannot be reached still keeps the trial

- **US:** SS-US-03
- **Given:** A guest, and the browser set to fail the logout request with a network error
- **When:** Sign out is pressed; then the network is restored and "Continue guest trial" is pressed
- **Then:** The sign-in panel is shown with "Continue guest trial" offered; continuing answers `200` and lands on Home with the guest's data
- **AC:** EC-11, AC-15
- **Type:** e2e

### TC-92: A saved trial the server refuses is dropped with a message

- **US:** SS-US-03
- **Given:** A guest who has signed out, and the saved trial's token in device storage replaced by one the server refuses — the same `401` an ended or deleted trial gets (QF-05)
- **When:** "Continue guest trial" is pressed; then the page is reloaded
- **Then:** The wallet-list request is answered `401`; "Your guest trial has ended." is shown; the sign-in panel stays and "Continue guest trial" is gone; after the reload it is still gone, and "Try as a guest" is still offered
- **AC:** AC-18, EC-10
- **Type:** e2e

### TC-93: A saved trial whose end has passed by the device's clock is not offered, and N is never 0

- **US:** SS-US-03
- **Given:** A saved guest trial in device storage, its trial end set in turn to one minute in the past, to five hours ahead, and to 6 days 23 hours ahead
- **When:** The sign-in panel is shown for each
- **Then:** One minute past: no "Continue guest trial", no message, and no request is sent; five hours ahead: "Continue guest trial — 1 day left"; 6 days 23 hours ahead: "Continue guest trial — 6 days left"
- **AC:** AC-17, EC-07, EC-10
- **Type:** e2e

### TC-94: "Try as a guest" with a saved trial starts a new one and replaces it

- **US:** SS-US-03
- **Given:** A guest who added a wallet named for this test, then signed out — so the device holds that trial
- **When:** "Try as a guest" is pressed; the Wallets tab is opened; then Sign out is pressed and "Continue guest trial" pressed
- **Then:** The trial request is answered `201`; the Wallets tab lists only "Example wallet", not the earlier trial's wallet; after signing out, exactly one "Continue guest trial" is offered, and continuing shows the new trial — still only "Example wallet"
- **AC:** AC-19, BR-08, FR-16
- **Type:** e2e

### TC-95: A member's sign-in leaves the saved trial for later

- **US:** SS-US-03
- **Given:** A guest who added a wallet and signed out, and an `ACTIVE` member
- **When:** The member signs in, opens the Wallets tab, and signs out; then "Continue guest trial" is pressed and the Wallets tab opened
- **Then:** The member's Wallets tab shows none of the guest's wallets; after the member signs out, "Continue guest trial" is still offered; continuing lists the guest's "Example wallet" and its added wallet
- **AC:** AC-20, FR-16
- **Type:** e2e

### TC-96: A guest refused while using the app returns to sign-in, told the trial has ended

- **US:** SS-US-03
- **Given:** A signed-in guest whose session token, and its saved copy, are replaced in device storage by one the server refuses (QF-05)
- **When:** The page is reloaded
- **Then:** The first data request is answered `401`; the sign-in panel is shown with "Your guest trial has ended."; "Continue guest trial" is not offered
- **AC:** EC-12, AC-05, FR-16
- **Type:** e2e
