# Feature Specification: System Security (SS)

> **Feature:** SRS §6 Feature-02 · SDS §5.1 (SS)
> **Spec:** [spec.md](spec.md)
> **Stories in this file:** SS-US-01 *(implemented, verified)* · SS-US-02 *(specified)* · SS-US-03 *(specified)*

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

---

## SS-US-03: Guest trial

> **IDs in this section are local to SS-US-03**, matching SS-US-02's convention: `AC-01` below is not
> SS-US-01's or SS-US-02's `AC-01`. Only `TC-NN` in `test_cases.md` runs continuously across the epic
> (`CLAUDE.md` §1.1 rule 4).

### Source *(scope extraction — CLAUDE.md §1 scope rule)*

Only the sections below entered the working context for SS-US-03. The SRS and SDS text quoted here
was added for this story on the product owner's decisions of 2026-10-23 and 2026-10-26 (SRS v2.4.0,
SDS v1.6.0).

**SRS §1.3 Constraints — *Verified Accounts Only* (v2.4.0)**
> Open self-registration without email verification is disabled to prevent non-existent emails in
> the database. **One exception (v2.4.0): the guest trial** (US-02-03). A visitor may start a
> time-limited guest trial without an invitation. A guest trial carries no real email address and
> receives no email, cannot be upgraded into a member account, and is deleted together with all of its
> data 7 days after it starts. Signing out does not delete it: the trial can be continued on the same
> device until those 7 days end — so no unverified address ever enters the database, and nothing from a
> trial outlives it.

**SRS §6 Feature-02 · US-02-03 — Guest Trial [MVP]**
> * **As a** Visitor without an invitation
> * **I want to** try the app as a guest
> * **So that** I can see what it does before asking my family's admin for an invitation.
>
> ```gherkin
> Scenario: Start a guest trial without an invitation
>   Given a Visitor is on the sign-in screen and is not signed in
>   When the Visitor clicks "Try as a guest"
>   Then the System creates a temporary guest account that expires 7 days from now
>   And the System signs the Visitor in as a guest
>   And the Visitor sees one example wallet holding one example transaction
>   And the System displays "Guest trial — deleted on <date>. Ask your family's admin for an invitation to keep using PFM."
>
> Scenario: A guest uses the app like a member
>   Given a Visitor is signed in as a guest
>   When the guest adds a wallet, a category, a budget or a transaction
>   Then the System saves it to the guest's own trial
>   And no other User can see it
>
> Scenario: The trial ends after 7 days
>   Given a guest trial started 7 days ago
>   When the guest opens the app
>   Then the System denies access
>   And the guest is returned to the sign-in screen
>   And the System deletes the guest account and all of its data
>
> Scenario: A guest trial cannot be upgraded
>   Given a Visitor is signed in as a guest
>   When the Visitor wants to keep using PFM
>   Then the Visitor must be invited by an ADMIN like any other User
>   And nothing from the guest trial is carried into the new account
>
> Scenario: A guest signs out and continues the trial later on the same device
>   Given a Visitor is signed in as a guest
>   When the guest clicks "Sign out"
>   Then the guest is returned to the sign-in screen
>   And the System keeps the guest trial and all of its data
>   And the sign-in screen offers "Continue guest trial — N days left", where N is the whole days until the trial ends
>   When the guest clicks "Continue guest trial — N days left"
>   Then the guest is signed in to the same trial with all of its data
>
> Scenario: A guest trial that has ended cannot be continued
>   Given a device holds a guest trial that has ended
>   When the Visitor clicks "Continue guest trial"
>   Then the System denies access
>   And the sign-in screen no longer offers to continue the trial
>   And the System displays "Your guest trial has ended."
>
> Scenario: Guests are not family members
>   Given a guest trial exists
>   When an ADMIN views the list of users
>   Then the guest does not appear in the list
> ```

**SDS §5.1.3 SS-US-03: Guest Trial (unauthenticated)**
> * **Goal:** Let a visitor without an invitation try the real app for 7 days as a temporary guest
>   account on the server — seeded with one example wallet holding one example transaction — that is
>   never upgraded and is deleted with all of its data when the trial ends. Signing out keeps the
>   trial, which the same device can continue until then.

**SDS §7.3 Denial of Service row (v1.6.0)** — starting a guest trial is limited to 5 per hour per
client address, and to 200 live guest trials in total, because it is the one public route that
creates server-side rows for anyone on the internet (the live server is public through Tailscale
Funnel, `constitution.md` ENV-06).

**Product-owner rulings** — 2026-10-23: server-side guest account on the members' APIs, 7 days then
deleted with all its data, never upgraded, one example wallet with one example transaction.
2026-10-26: Sign out does **not** delete the trial; the device keeps it and the sign-in screen offers
"Continue guest trial — N days left" (N = whole days until the trial ends, at least 1 while it has not
ended) beside "Try as a guest", which always starts a new trial and replaces the saved one on that
device. One saved trial per device; signing in as a member does not discard it. A visitor can always
start a new trial; only invited members get permanent accounts.

**Constitution SEC-12** (guest accounts never receive email, cannot be upgraded, are deleted with all
their data when the trial ends and never on sign-out), **SEC-06** (whose 60-minute token SEC-12 makes
the one exception to), **SEC-10**, **SEC-11**, **API-08**.

### Out of scope for this story

Features 03–11 as *requirements* — a guest uses the existing wallet, category, budget, transaction and
report behaviour exactly as built; this story changes none of it · SDS-only stories UM-US-04/05,
DC-US-01/02 · SRS §6 Feature-10/11 placeholders.

Deliberately excluded even though adjacent:

- **Upgrading a trial into a member account.** Ruled out by the product owner. A guest who wants in is
  invited normally (UM-US-01) and starts fresh.
- **Ending a trial early.** Nothing — not sign-out, not an ADMIN — deletes a trial before its 7 days
  end.
- **Continuing a trial on another device, or holding several trials on one.** A trial can be continued
  only on the device that holds it, and a device holds one.
- **Rate limiting the invite and activate routes.** SDS §7.3 and SEC-11 still defer those (UM-US-01
  T-13, UM-US-02 T-08); this story limits only the route it adds.
- **Showing guests anywhere in an ADMIN's view.** No ADMIN screen lists, counts, or manages guest
  trials in this story.

### User Scenarios & Testing *(mandatory)*

As a **Visitor without an invitation**, I want to try the real app as a guest — with one example to
show me what a wallet and a transaction look like, and the freedom to step away and come back on the
same phone — so that I can see what it does before I ask my family's admin for an invitation, knowing
that nothing I enter outlives the 7-day trial.

**Acceptance Criteria**:

**AC-01: Start a guest trial without an invitation or credentials**
**Given** a visitor who is not signed in and holds no invitation,
**When** they choose "Try as a guest",
**Then** the system creates a temporary guest account, signs the visitor in as a guest immediately,
and tells the visitor's app the exact moment the trial ends — 7 days after it started.

**AC-02: The first view holds exactly one example**
**Given** a guest trial that has just started,
**When** the guest looks at their data for the first time,
**Then** they find exactly one wallet, named "Example wallet", in Vietnamese đồng, holding exactly one
expense of 50,000.00 noted "Example: lunch" in a category named "Food", with the wallet's balance
showing 450,000.00 — its opening 500,000.00 less that expense — and nothing else.

**AC-03: A guest uses the app as a member does**
**Given** a signed-in guest,
**When** they add, change or remove wallets, categories, budgets and transactions — including the
example — and view their reports,
**Then** every action behaves exactly as it does for a member, and the data is the guest's own: no
other user, member or guest, can see it, and the guest can see no one else's.

**AC-04: The guest stays signed in for the whole trial**
**Given** a guest whose trial has not ended,
**When** they keep using the app — including more than an hour after the trial started,
**Then** they are not signed out before the trial ends; a guest holds no password, so a session shorter
than the trial would lock it out of its own data.

**AC-05: Access ends when the trial ends**
**Given** a guest whose trial has ended,
**When** that guest makes any request,
**Then** the system refuses it with the same generic unauthenticated outcome every protected action
returns, and the app returns the guest to the sign-in screen.

**AC-06: An ended trial is deleted with everything in it**
**Given** a trial that has ended, owning wallets, categories, budgets and transactions,
**When** the system deletes ended trials,
**Then** the guest account and every wallet, category, budget and transaction it owned are removed,
and no member's data, nor any live guest's, is changed.

**AC-07: A guest can never be signed into with credentials, emailed, or upgraded**
**Given** a guest account,
**When** anyone tries to sign in to it with an email and password, invite its address, or turn it into
a member or an administrator,
**Then** the system refuses every one of those: a guest has no real email address and no password,
receives no email, and is never converted into another kind of account.

**AC-08: Guests are not family members**
**Given** a live guest trial,
**When** an ADMIN views the list of users,
**Then** the guest does not appear in it, and the list's total does not count it.

**AC-09: A guest cannot act as an administrator**
**Given** a signed-in guest,
**When** they try to invite someone or list the family's users,
**Then** the system refuses with the same "only an administrator" outcome a member receives, and the
app shows a guest no Family section at all.

**AC-10: Trial starts from one client are limited**
**Given** a client that has started 5 guest trials within the last hour,
**When** it tries to start a sixth,
**Then** the system refuses with a "too many requests" outcome and creates no account.

**AC-11: The number of live trials is capped**
**Given** 200 guest trials that have not ended,
**When** any visitor tries to start another,
**Then** the system refuses with a "not available right now" outcome and creates no account.

**AC-12: Starting a trial is all-or-nothing**
**Given** a visitor starting a trial,
**When** any part of creating the guest account or its example fails,
**Then** nothing is left behind — no guest account without its example, and no example without its
account.

**AC-13: Trial creation and deletion are recorded**
**Given** a trial that starts, or an ended trial that is deleted,
**When** that happens,
**Then** the system records an audit entry — for a deletion, how many wallets, categories, budgets and
transactions went with it — and never a credential.

**AC-14: The guest is always told they are on a trial**
**Given** a signed-in guest, on any screen,
**When** the app is open — including after it is reloaded,
**Then** it shows "Guest trial — deleted on <date>. Ask your family's admin for an invitation to keep
using PFM.", where `<date>` is the day the trial ends.

**AC-15: Signing out keeps the trial**
**Given** a signed-in guest,
**When** they choose "Sign out",
**Then** they are signed out at once, with no confirmation step — nothing is lost; the system deletes
nothing, the trial and all its data stay as they were, and the sign-in screen offers "Continue guest
trial — N days left".

**AC-16: A saved trial can be continued on the same device**
**Given** a device holding a guest trial that has not ended, and nobody signed in,
**When** "Continue guest trial — N days left" is chosen,
**Then** the guest is signed back in to the same trial, lands on Home, and finds all of its data as
they left it; N is the number of whole days until the trial ends, and never less than 1 while it has
not ended.

**AC-17: A saved trial that has ended by the device's clock is not offered**
**Given** a device holding a guest trial whose end has passed,
**When** the sign-in screen is shown,
**Then** the saved trial is discarded without asking the server, and "Continue guest trial" is not
offered.

**AC-18: A saved trial the server no longer accepts is discarded with a message**
**Given** a device holding a guest trial that the device believes is live but the server refuses — it
has ended or has been deleted,
**When** "Continue guest trial" is chosen,
**Then** the guest is not signed in, the saved trial is discarded, "Continue guest trial" is no longer
offered, and "Your guest trial has ended." is shown.

**AC-19: "Try as a guest" always starts a new trial**
**Given** a device holding a saved guest trial,
**When** "Try as a guest" is chosen,
**Then** a brand-new trial starts holding only the example, and it replaces the saved trial on this
device; the earlier trial is no longer offered here and is deleted on the server when its own 7 days
end.

**AC-20: Signing in as a member keeps the saved trial**
**Given** a device holding a saved guest trial,
**When** a member signs in, uses the app, and signs out,
**Then** the member sees only their own data while signed in, and afterwards the sign-in screen still
offers "Continue guest trial", which continues the same trial.

### Edge Cases

**EC-01**: **The exact moment the trial ends** — one second before it, the guest's requests succeed;
at it, they are refused (AC-05). The trial is over *at* its end time, not one tick after.

**EC-02**: **A trial has ended but has not been deleted yet** — deletion runs at particular moments
(see *Assumptions & Dependencies*), not continuously. In between, the ended guest is refused exactly as
in AC-05: access ends at the trial's end regardless of when the data is removed.

**EC-03**: **The cap is reached, but some of the counted trials have already ended** — ended trials are
deleted before the cap is checked, so they never hold a place a new visitor could use (AC-11).

**EC-04**: **The server restarts** — any trial that ended while it was down is deleted when it starts
again, so a stopped server does not keep ended trials alive (AC-06).

**EC-05**: **Two guests at once** — each sees only their own example and their own data; neither can
read or change the other's (AC-03).

**EC-06**: **A guest removes the example** — allowed; it is their data like any other, and the trial
carries on empty (AC-03).

**EC-07**: **How many days are left** — N counts whole days remaining, rounded down, and is shown as 1
for the last day: 6 days 23 hours left shows 6; 5 hours left shows 1 (AC-16).

**EC-08**: **A former guest is later invited** — the invitation goes to the person's real address and
creates an ordinary pending account with nothing from the trial in it; the trial is unaffected and is
deleted on its own schedule (AC-07).

**EC-09**: **A sign-in attempt names a guest's placeholder address with any password at all** — refused
without reaching the account, because a guest's address is not one a person can sign in with and a
guest holds no password to match (AC-07).

**EC-10**: **The device's clock disagrees with the server's** — the server decides: a trial the device
still offers but the server has ended is refused and discarded as in AC-18; a trial the device wrongly
believes has ended is discarded locally (AC-17) and is deleted on the server on its own schedule.

**EC-11**: **A guest signs out while the server cannot be reached** — the app still signs out, exactly
as it does for a member, and the trial is still offered for continuing: sign-out deletes nothing, so a
lost sign-out request loses nothing (AC-15).

**EC-12**: **A saved trial's guest is signed out because its trial ended while in use** — the app
returns to the sign-in screen as in AC-05, discards the saved trial, and shows "Your guest trial has
ended." (AC-05, AC-18).

### Requirements *(mandatory)*

#### Functional Requirements

- **FR-01**: The system must **accept** a request to start a guest trial from a caller presenting no
  credentials, with nothing to submit (AC-01; SRS US-02-03; constitution API-08).
- **FR-02**: The system must **create** a guest account that is usable immediately, has no real email
  address and no password, and whose trial ends exactly 7 days after it starts (AC-01, AC-07; SRS §1.3;
  SEC-12).
- **FR-03**: The system must **seed** each new trial with exactly one example: a wallet "Example
  wallet" in VND opened at 500,000.00, a category "Food" of type expense, and one expense of 50,000.00
  noted "Example: lunch" against them, recorded through the same rules a member's own entries follow,
  so the wallet's balance is 450,000.00 (AC-02).
- **FR-04**: The system must **sign the guest in** for the whole trial — the session it issues lasts
  until the trial ends, not 60 minutes — and **report** the trial's end time with it (AC-01, AC-04;
  SEC-12's exception to SEC-06).
- **FR-05**: The system must **refuse** every request from a guest whose trial has ended, with the
  generic unauthenticated outcome, whether or not the trial has been deleted yet (AC-05, EC-01, EC-02).
- **FR-06**: The system must **delete** every ended trial together with all the wallets, categories,
  budgets and transactions it owns, and nothing else (AC-06).
- **FR-07**: The system must **run** that deletion when it starts up, each time a trial is started, and
  on an operator's command (AC-06, EC-03, EC-04).
- **FR-08**: The system must **refuse** to sign in to, invite, or promote a guest account by
  credentials, and must never send a guest email (AC-07, EC-09; SEC-12).
- **FR-09**: The system must **exclude** guests from the ADMIN's list of users and from its total
  (AC-08).
- **FR-10**: The system must **refuse** a sixth trial start from the same client address within one
  hour with a "too many requests" outcome (AC-10; SDS §7.3).
- **FR-11**: The system must **refuse** a trial start while 200 trials are live with a "not available
  right now" outcome (AC-11; SDS §7.3).
- **FR-12**: The system must **create** the guest account and its example in one atomic operation
  (AC-12; SRS NFR-05).
- **FR-13**: The system must **record** an audit entry when a trial starts and when an ended trial is
  deleted, with counts for a deletion, and never a credential (AC-13; constitution LA-01).
- **FR-14**: The app must **offer** "Try as a guest" on the sign-in screen, **show** the trial notice
  on every screen while a guest is signed in, and **hide** the Family section from a guest (AC-01,
  AC-09, AC-14).
- **FR-15**: The system must **end** a guest's session on sign-out exactly as it ends a member's —
  deleting nothing, and leaving the guest's session usable for continuing the trial until the trial
  ends (AC-15, AC-16; SS-US-02 unchanged).
- **FR-16**: The app must **keep** the most recently started guest trial on the device as its one saved
  trial — replacing any earlier one when a new trial starts, and keeping it through sign-out and through
  a member's sign-in — and **discard** it once it has ended by the device's clock or the server refuses
  it (AC-15, AC-17, AC-18, AC-19, AC-20, EC-12).
- **FR-17**: The app must **offer** "Continue guest trial — N days left" on the sign-in screen while a
  saved trial has not ended, and on choosing it **confirm** with the server that the trial is still live
  before signing the guest back in (AC-16, AC-18, EC-07, EC-10).

#### Business Rules

- **BR-01**: A guest trial lasts exactly 7 days from the moment it starts. It is over *at* that moment
  (EC-01), and over for every purpose — access, then deletion (AC-05, AC-06).
- **BR-02**: A guest is never upgraded. No path turns a guest account, or anything it owns, into a
  member's (SRS §1.3, US-02-03; SEC-12).
- **BR-03**: A guest is never emailed and never signed into with credentials: its address is a
  reserved placeholder that can receive nothing, and it holds no password (AC-07; SEC-12).
- **BR-04**: A guest's data is its own, under exactly the ownership rules every member's data follows
  (AC-03; SRS FR-02).
- **BR-05**: A guest is not a member of the family: it does not appear to the ADMIN and cannot act as
  one (AC-08, AC-09).
- **BR-06**: Starting a trial is limited per client (5 per hour) and in total (200 live trials), and a
  refused start creates nothing (AC-10, AC-11).
- **BR-07**: Only the end of its 7 days deletes a trial. Signing out never does (AC-15; SEC-12;
  product-owner ruling 2026-10-26).
- **BR-08**: A device holds at most one saved guest trial — the one most recently started on it
  (AC-19).

#### Key Entities

- **User** *(extended)*: A guest is a User with the guest role. It differs from a member in exactly
  three ways: it was not invited, it holds no real email or password, and it has a trial end time after
  which it is refused and deleted (SRS §1.5, v2.4.0).
- **Wallet, Category, Budget, Transaction** *(unchanged)*: Owned by a guest exactly as by a member,
  and deleted with the guest when its trial ends.
- **Saved guest trial** *(on the device, not stored by the system)*: The one guest session a device
  keeps after its guest signs out — enough to continue the trial and to know when it ends.

### Success Criteria *(mandatory)*

- **SC-01**: A visitor with no invitation can be using the real app, with an example in front of them,
  in one tap.
- **SC-02**: A guest is never interrupted by a sign-in prompt during their trial, is never left unsure
  that they are on a trial or when it ends, and can step away and come back to it on the same phone in
  one tap.
- **SC-03**: Seven days after a trial starts, nothing of it remains reachable, and once the deletion has
  run, nothing of it remains stored.
- **SC-04**: No guest ever receives an email, signs in with a password, appears in the family's list of
  users, or becomes a member.
- **SC-05**: Nobody on the internet can fill the family's server with trials faster than 5 per hour from
  one address, or beyond 200 live trials in total.

### Assumptions & Dependencies

- **SS-US-01, SS-US-02 and the wallet, category, budget, transaction and report stories exist first.**
  A guest uses all of them unchanged, including SS-US-02's sign-out, and the example is created through
  the same rules a member's own wallet, category and expense follow. All are implemented and verified.
- **The client address the server sees must be the real visitor's.** The live server is reached
  through Tailscale Funnel (ENV-06); AC-10's per-client limit is only meaningful if the address the
  limit counts is the visitor's, not the tunnel's. The live log already records public visitor
  addresses, which suggests it is — to be confirmed at the Implement step, recorded in `plan.md`.
- **Whoever holds the device can continue its saved trial.** That is the product owner's choice
  (2026-10-26): a trial holds only trial data, it ends on its own after 7 days, and a visitor can always
  start a new one — only invited members get permanent accounts. The saved trial is kept in the same
  device storage as an ordinary session.
- **No upgrade is a product-owner ruling, not a gap.** A guest wanting in is invited to their real
  address (UM-US-01) and starts fresh (EC-08).
- **One example, not a tour.** The product owner ruled one example wallet with one example transaction;
  no other seeded data, tips, or walkthrough are in scope.
