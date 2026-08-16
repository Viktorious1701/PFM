# Feature Specification: System Security (SS)

> **Feature:** SRS §6 Feature-02 · SDS §5.1 (SS)
> **Spec:** [spec.md](spec.md)
> **Stories in this file:** SS-US-01 *(implemented, verified)* · SS-US-02 *(specified)*

---

## Source *(scope extraction — CLAUDE.md §1 scope rule)*

Only the sections below entered the working context for SS-US-01.

**SRS §6 Feature-02 · US-02-01 — Login [MVP]**
> * **As an** Activated User
> * **I want to** log in with my email and password
> * **So that** I can access my private financial dashboard.
>
> ```gherkin
> Scenario: Login successfully with active account
>   Given an ACTIVE user exists with email "jane@gmail.com" and password "SecurePassword123!"
>   When the User enters email "jane@gmail.com"
>   And the User enters password "SecurePassword123!"
>   And the User clicks "Login"
>   Then the System authenticates the user
>   And the System issues a signed JWT token
>   And the User is redirected to the Dashboard
>
> Scenario: Reject login for PENDING (unactivated) user
>   Given a PENDING user exists with email "pending@gmail.com"
>   When the User enters email "pending@gmail.com" and correct password
>   And the User clicks "Login"
>   Then the System denies access
>   And the System displays error "Your account is not activated. Please check your email invitation."
> ```

**SDS §5.1.1 SS-US-01 (Login)**
> * **Goal:** Authenticate active users and return a JWT access token.
> * **Acceptance Criteria:**
>   1. Validates email and password against stored database hashes.
>   2. Rejects authentication if user status is `PENDING`.
>   3. Returns a signed JWT token upon success.

**SDS §7.1.3/§7.1.4/§7.1.6/§7.1.8** — JWT Bearer auth (HS256), email+password input, 60-minute
access token, `POST /api/v1/auth/login` public.

**SRS §2 FR-02** — "The System shall authenticate users via secure credentials (email/password),
enforce JWT-based sessions, and restrict data access so users can only view data they own or are
granted access to." *(The ownership-filtering half is out of scope here — no story in this round
queries user-owned data yet; it applies when one does.)*

**Constitution SEC-06, SEC-07, SEC-10, API-08** — JWT parameters, authz-by-test discipline, no
account enumeration, public endpoint list.

### Out of scope for this story

**SS-US-02 (Logout)** — SRS names it `[MVP]`, but `CLAUDE.md`'s Story ID map defers it explicitly:
a stateless bearer token has nothing server-side to invalidate without a token-revocation store,
which no AC in this round requires; "logging out" is a client-side action (discard the stored
token), already implemented in `mobile/src/store/auth.ts`'s `signOut()`. Revisit if a revocation
requirement is ever specified. Also out of scope: everything Features 03–11 touch, and the
ownership-filtering half of FR-02 (no story yet reads user-owned data).

Deliberately excluded even though adjacent: **what a caller does with the token once issued** —
resolving it into a caller identity (`get_current_user`, `require_admin`) is already built and
verified by UM-US-01 (`plan.md` A11); this story is only the endpoint that *issues* one.

---

## SS-US-01: Login

### User Scenarios & Testing *(mandatory)*

As an **activated User**, I want to sign in with my email and password so that I can reach my
private financial dashboard, and so that nobody can sign in as an account whose access was never
activated or has since been withdrawn.

**Acceptance Criteria**:

**AC-01: Successful login for an ACTIVE account**
**Given** an `ACTIVE` user exists with a known email and password,
**When** that email and its correct password are submitted,
**Then** the system returns a signed JWT access token whose subject identifies the user and whose
role matches the account's role, together with its expiry.

**AC-02: Reject a PENDING account with the SRS's own message**
**Given** a `PENDING` user exists,
**When** any password at all is submitted for that email,
**Then** the system denies access and returns the message "Your account is not activated. Please
check your email invitation." — regardless of what password was submitted, because a `PENDING`
account holds no password to check against in the first place (UM-US-01 AC-07: an invited account
is created with no credentials, set only at activation), so there is no "correct password" this
scenario could require.

**AC-03: Reject an incorrect password indistinguishably from an unknown email**
**Given** an email that either belongs to no account, or belongs to an `ACTIVE` or `DEACTIVATED`
account whose password does not match what was submitted,
**When** that email and password are submitted,
**Then** the system denies access with one generic message, and a caller cannot tell from the
response which of the two happened.

**AC-04: Reject a DEACTIVATED account without disclosing that it was deactivated**
**Given** a `DEACTIVATED` user exists,
**When** that email and its correct password are submitted,
**Then** the system denies access with the same generic outcome as AC-03 — a withdrawn account
does not confirm to the caller that it once existed and was disabled.

**AC-05: A DEACTIVATED account's password is still checked before its state is**
**Given** a `DEACTIVATED` user exists — one that *does* hold a password hash, set while it was
still `ACTIVE`,
**When** that email is submitted with an **incorrect** password,
**Then** the system denies access with AC-03's generic outcome, never a distinct one — a wrong
password against an account that has one reveals nothing about that account's state. *(This
precedence does not extend to `PENDING`, which has no password to check in the first place — see
AC-02 and the reconciling note after EC-03.)*

**AC-06: Never expose the credential**
**Given** any login attempt, successful or refused,
**When** the result is returned and the attempt is recorded,
**Then** the submitted password and the stored hash appear in no response and no log entry.

**AC-07: Record an audit event for every attempt**
**Given** any login attempt,
**When** it succeeds or is refused,
**Then** the system records an audit entry capturing the timestamp, the attempted email, and the
outcome, and never the password.

**AC-08: Reject a malformed payload before evaluating credentials**
**Given** a request missing the email or the password field, or carrying a malformed email,
**When** it is submitted,
**Then** the system rejects it with a validation error identifying the offending field, before any
database lookup.

**AC-09: No credentials required to call this endpoint**
**Given** a caller presenting no bearer token,
**When** a login is submitted,
**Then** the system processes the request — a person who is not yet signed in has no token to
present.

### Edge Cases

**EC-01**: **Email differing by case or surrounding whitespace** — `"Jane@Gmail.COM"` and
`" jane@gmail.com "` match the same account as `"jane@gmail.com"`, using the same
trim-and-case-fold normalisation UM-US-01 FR-03 already established. One mailbox, one comparison
rule, used everywhere an email is looked up.

**EC-02**: **An ACTIVE account with the correct password succeeds regardless of when it was
activated** — there is no additional cooldown or first-login ceremony beyond activation itself.

**EC-03**: **A `PENDING` account has no password to check in the first place** — its
`password_hash` is `NULL` (UM-US-01 AC-07: an invited account holds no credentials until
activation). AC-02 therefore reports its message for **every** password submitted against a
`PENDING` email, correct or not, because "correct" has no meaning where nothing was ever stored to
compare against. See the reconciling note below — an earlier draft of this spec required password
verification to precede every state check without exception, which would have made AC-02's SRS-
mandated message permanently unreachable.

> **Reconciling AC-02 and AC-05.** A first pass at this story wrote one blanket rule — "password
> verification always precedes any account-state check" — reasoning by analogy from UM-US-02's own
> BR-02 (which checks token/invitation state before expiry). Applied here without qualification, it
> is wrong: `PENDING` accounts hold **no** password (UM-US-01 BR-06), so "verify the password
> first" for a `PENDING` account can only ever fail, landing on AC-03's generic refusal and never
> reaching AC-02's message at all — silently defeating the SRS's own explicit Gherkin scenario for
> this story. **Resolved by narrowing where the precedence rule applies**: it governs accounts that
> *have* a password to check — `ACTIVE` and `DEACTIVATED` — where a wrong guess must never leak
> state (AC-05). For `PENDING`, there is nothing to verify, so the state check runs unconditionally
> and immediately. This is not a weaker guarantee arrived at by accident: `PENDING` is exactly the
> one state SRS's own Gherkin insists be disclosed by name, precisely because its absent password
> already makes "wrong password" an incoherent question to ask of it. It is a materially different
> case from UM-US-02's, where every state (including the equivalent of `PENDING` — an outstanding,
> unconsumed invitation) has a real secret token behind it worth protecting symmetrically.

### Requirements *(mandatory)*

#### Functional Requirements

- **FR-01**: The system must **accept** an email and a password from a caller presenting no
  credentials (SRS FR-02; SDS §7.1.4; constitution API-08).
- **FR-02**: The system must **validate** the payload — a present, correctly formatted email and a
  non-empty password — before any database lookup (AC-08).
- **FR-03**: The system must **normalise** the submitted email exactly as UM-US-01 FR-03 does —
  trimmed and case-folded — before comparison (EC-01).
- **FR-04**: The system must **refuse** login for a `PENDING` account immediately, before
  attempting any password comparison, naming the reason with the SRS's exact message — a `PENDING`
  account holds no password to verify against (AC-02, EC-03).
- **FR-05**: For every account that **does** hold a password — `ACTIVE` or `DEACTIVATED` — and for
  an email matching no account at all, the system must **verify** the submitted password (against
  the real hash, or a fixed dummy hash when no account matches) before reaching any further check
  (constitution SEC-01; AC-05, BR-01).
- **FR-06**: The system must **refuse** login when no account matches the normalised email, or a
  matched `ACTIVE`/`DEACTIVATED` account's password does not match, reporting one generic outcome
  for all three (AC-03).
- **FR-07**: The system must **refuse** login for a `DEACTIVATED` account whose password matched,
  reporting the same generic outcome as FR-06 — never distinguishing "deactivated" from "unknown
  or wrong password" (AC-04).
- **FR-08**: The system must **issue** a signed JWT on success, carrying the user's id as subject
  and the user's role, with a 60-minute expiry (AC-01; constitution SEC-06).
- **FR-09**: The system must **exclude** the submitted password and the stored hash from every
  response and log entry (AC-06).
- **FR-10**: The system must **record** an audit entry for every login attempt, success or
  refusal, capturing the attempted email and the outcome, and never the password (AC-07).

#### Business Rules

- **BR-01**: For an account that holds a password (`ACTIVE` or `DEACTIVATED`), password
  verification happens **before** any further state check — a wrong password is refused
  identically regardless of that account's status (AC-05). `PENDING` is the one exception: it
  holds no password, so its state is reported unconditionally, on any password at all (FR-04,
  EC-03) — this is not a violation of the rule, it is the reason the rule is scoped to accounts
  that have something to verify.
- **BR-02**: An account not in `ACTIVE` status never receives a session, regardless of password
  correctness — `PENDING` is named, `DEACTIVATED` is not (FR-04, FR-07).
- **BR-03**: The raw password is never stored, logged, or returned — only ever compared (AC-06).
- **BR-04**: Email comparison is case- and whitespace-insensitive, identically to UM-US-01 BR-01
  (EC-01).

#### Key Entities

- **User**: The account being authenticated. Only an `ACTIVE` user's password check can succeed;
  this story reads the entity UM-US-01 creates and UM-US-02 activates, and writes nothing to it.
- **Session** *(not a stored entity)*: The JWT itself is the session — stateless, carrying subject
  and role, expiring on its own after 60 minutes. Nothing server-side tracks it (SS-US-02 deferred).

### Success Criteria *(mandatory)*

- **SC-01**: An activated person can sign in with their email and password and reach the app.
- **SC-02**: A `PENDING` person is told clearly why they cannot yet sign in, and how to fix it.
- **SC-03**: Nobody can learn from a login attempt whether an `ACTIVE` account exists at that
  email, whether it was deactivated, or only that a password was wrong — those three cases answer
  identically. The one deliberate exception is `PENDING` (AC-02): the SRS requires that state to be
  named, and its absent password already makes the exception a narrow one — see the note after
  EC-03 for why that account status is different from the others.
- **SC-04**: No submitted or stored password is ever recoverable from a response or a log.
- **SC-05**: Every login attempt — successful or not — leaves an audit trail.

### Assumptions & Dependencies

- **UM-US-01 and UM-US-02 must exist first**, since this story authenticates accounts they create
  and activate. Both are implemented and verified.
- **Token verification already exists.** UM-US-01's `plan.md` A11 shipped `get_current_user` /
  `require_admin` ahead of this story, precisely so UM-US-01 was not blocked on an unwritten epic.
  This story delivers the other half — the endpoint that *issues* what those dependencies verify.
  No change to `get_current_user`/`require_admin` is anticipated; if this story's design surfaces
  one, it is a finding, not a silent edit to already-verified code.
- **The password policy comes from UM-US-02 activation**, not from this story — login only
  compares against whatever hash activation already produced. This story adds no new policy.
- **DEACTIVATED's login treatment is a finding, not an anchored requirement.** Neither SRS §6 nor
  SDS §5.1.1 names `DEACTIVATED` for login — only `PENDING` is named. AC-04/FR-07's ruling (fold
  it into the generic refusal, don't disclose it) is derived from constitution SEC-10 and from how
  UM-US-02 already treated the analogous case (EC-07: a `DEACTIVATED` user's invitation token is
  refused generically, not named). Recorded here rather than assumed silently; extending `SRS.md`
  to name it explicitly would be a requirements change, which is the product owner's call, not an
  alignment the AI can make on its own (`CLAUDE.md` §1).

---

## SS-US-02: Logout

> **IDs in this section are local to SS-US-02.** `AC-01` below is not SS-US-01's `AC-01`; each
> story section numbers its own criteria, per `artifact-templates/spec-templates.md`. Only `TC-NN`
> in `test_cases.md` runs continuously across the epic (`CLAUDE.md` §1.1 rule 4).

### Source *(scope extraction — CLAUDE.md §1 scope rule)*

**SRS §6 Feature-02 · US-02-02 — Logout [MVP]**
> * **As an** Authenticated User
> * **I want to** log out of the system
> * **So that** my session is terminated securely.

No Gherkin accompanies this story. Unlike US-02-01's two-scenario block, `SRS.md` gives US-02-02
exactly the one unscenario'd statement quoted above — no scenario for a successful logout, none for
an unauthenticated caller. Stated plainly here rather than inventing scenarios the baseline does not
contain.

**SDS §5.1.2 SS-US-02 (All)**
> * **Goal:** Invalidate local tokens and terminate user session context.

No enumerated acceptance criteria accompany this goal either — unlike §5.1.1's three numbered
criteria for login, §5.1.2 is one sentence. `SDS §6.5` (API → User Story Traceability) does not list
a logout row at all — no `SS-API-02`, no endpoint entry — so this story's endpoint has no prior
published contract to align to; the contract is created here, for the first time.

**SDS §7.1.6 Session Management**
> Short-lived access tokens (60 minutes).

**SDS §7.1.7 Authentication Controls**
> Endpoints check user context and reject tokens belonging to non-active user accounts.

Together, these two lines are why this story is scoped the way it is: `SDS.md` describes a
stateless-JWT architecture — no refresh token, no session table, no revocation list anywhere in the
document — where every request re-derives its own validity from the token's signature, expiry, and
the current row in `users` (§7.1.7). There is nothing server-side for a "logout" call to mark.

**Constitution SEC-06, SEC-07** — JWT parameters (HS256, 60-minute expiry); every protected route
resolves the caller through the auth dependency, proven by a test expecting `401`.

### Out of scope for this story

Features 03–11 · SRS §6 Feature-10/11 placeholders · SDS-only stories UM-US-04/05, DC-US-01/02.

Deliberately excluded even though adjacent:

- **A token-revocation store.** Making a still-valid JWT actually unusable before its natural
  expiry needs somewhere to record that it was revoked — a table, or a cache keyed by token or by
  user, consulted on every subsequent request. No AC in this story, no line in `SRS.md` or
  `SDS.md` §5.1.2, and no constitution rule requires one. Building it now would be implementing
  ahead of a requirement rather than behind one — see the ruling in *Assumptions & Dependencies*
  below.
- **Refresh tokens.** `SDS.md` §7.1.6 names none; there is nothing to revoke that a refresh flow
  would otherwise silently re-issue.
- **Wiring the mobile prototype's `signOut()` to a real endpoint.** `mobile/src/store/auth.ts`
  already discards the stored token client-side, built during UM-US-01's round as a fixture-driven
  prototype action. This story adds the backend endpoint; pointing the mobile action at it is a
  later phase's job, mirroring how SS-US-01's own login screen wiring was deferred (`test_cases.md`
  header note).

### User Scenarios & Testing *(mandatory)*

As an **authenticated User**, I want to end my current session with one explicit action, so that
continuing to use this device afterward requires signing in again rather than relying on a token
this device already holds.

**Acceptance Criteria**:

**AC-01: Successful logout for an authenticated caller**
**Given** a caller presenting a currently valid bearer token,
**When** that caller calls the logout endpoint,
**Then** the system returns a success response confirming the session has ended, and the response
carries no credential of any kind.

**AC-02: Reject a caller with no valid credentials**
**Given** a caller presenting no bearer token, a malformed one, or one whose signature does not
verify,
**When** that caller calls the logout endpoint,
**Then** the system denies the request with the same generic unauthenticated outcome every other
protected route in this system already returns — there is no special no-credentials-required
carve-out for logout; a caller must already be signed in to sign out.

### Edge Cases

**EC-01**: **An already-expired bearer token presented at the logout endpoint** — refused with the
same generic outcome as AC-02, identically to how any other protected route treats an expired token
(`get_current_user`, per constitution SEC-10's non-enumeration principle already applied everywhere
else in this codebase). Logout is not exempt from ordinary token verification merely because its
purpose is to end a session.

**EC-02**: **The presented token remains valid after a successful logout, until its own natural
60-minute expiry** — this is not a defect. Logout in this story is a client-side action (AC-01's
response is a confirmation, not a revocation), so a token that is copied elsewhere before logout, or
resubmitted afterward by a caller who never discards it, continues to authenticate normally until it
expires on its own. See *Assumptions & Dependencies* below for why this is the story's real,
deliberately scoped contract rather than an oversight.

### Requirements *(mandatory)*

#### Functional Requirements

- **FR-01**: The system must **accept** a logout request only from a caller presenting a currently
  valid bearer token (AC-01, AC-02).
- **FR-02**: The system must **return** a success response confirming the session has ended, on
  every request that reaches the service (AC-01).
- **FR-03**: The system must **refuse** a caller with no bearer token, a malformed one, an invalid
  signature, or an expired one, with the same generic unauthenticated outcome used by every other
  protected route (AC-02, EC-01).
- **FR-04**: The system must **exclude** the caller's token and any other credential material from
  the response (AC-01; constitution LA-01).
- **FR-05**: The system must **not** write, mark, or otherwise persist any server-side revocation
  record as part of this operation — there is no revocation store to write to, by design (EC-02; see
  the scope ruling in *Assumptions & Dependencies*).

#### Business Rules

- **BR-01**: Logout requires being authenticated. There is no unauthenticated path through this
  endpoint — a caller with nothing to end cannot be told an ordinary session ended (BR-01, AC-02).
- **BR-02**: A bearer token's validity is governed entirely by its own signature and expiry,
  unaffected by any prior logout call against it (EC-02). Nothing this story does changes what
  `get_current_user` accepts for a token minted before or after a logout call.

#### Key Entities

- **Session** *(not a stored entity)*: The JWT itself is the session, exactly as SS-US-01 describes
  it — stateless, expiring on its own after 60 minutes. This story adds the explicit client-facing
  action of ending one; it adds no new entity and no new column, because there is nothing
  server-side to represent a session's end.

### Success Criteria *(mandatory)*

- **SC-01**: An authenticated person can end their session with one explicit call and receive a
  clear confirmation.
- **SC-02**: Nobody can call this endpoint without already holding valid credentials — the same
  authentication guarantee every other protected route in this system provides.
- **SC-03**: The system never implies a server-side revocation it cannot perform. What "logout"
  means here — the client discards its token, and the token otherwise expires on its own — is
  documented plainly rather than left to be discovered by testing.

### Assumptions & Dependencies

- **SS-US-01 must exist first.** This story's caller presents a token that only the login endpoint
  issues; SS-US-01 is implemented and verified, so this dependency is satisfied.
- **This story's real contract is client-side-only token invalidation — decided, not a gap.** The
  system's whole auth design is stateless JWTs (SDS §7.1.6: 60-minute TTL, HS256, no refresh token,
  no session store, no revocation list — confirmed by `get_current_user` in `core/deps.py`, which
  checks only signature, expiry, and the current row's status). A literal server-side "invalidate
  this token" is not implementable without a new revocation store that does not exist and that no AC
  in this round requires. `POST /api/v1/auth/logout` therefore returns a success response, and the
  actual security action — discarding the stored token — happens on the client afterward, exactly
  as `mobile/src/store/auth.ts`'s existing `signOut()` already does against fixtures. If a
  revocation requirement is ever specified, this is a new design, not an extension of this one.
- **Any authenticated User, not only ADMIN, may log out.** SRS names the caller "an Authenticated
  User," not an ADMIN-only action — unlike UM-US-01/UM-US-03. The endpoint depends on whichever
  dependency resolves *any* currently-authenticated caller, not the ADMIN-only one.
- **Resolving a caller from a bearer token is already built and verified.** `get_current_user` is
  UM-US-01's `plan.md` A11, exercised by every existing protected route. This story adds no change
  to it — it only adds the one route whose entire job is to be called *last*, after which the caller
  is expected to stop presenting that token.
