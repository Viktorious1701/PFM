# Feature Specification: User Management & Onboarding (UM)

> **Feature:** SRS §6 Feature-01 · SDS §5.2 (UM)
> **Spec:** [spec.md](spec.md)
> **Stories in this file:** UM-US-01 *(implemented, verified — 86 tests, nothing skipped, 98% coverage, TC-22 confirmed by real Gmail delivery)* · UM-US-02 *(specified)* · UM-US-03 *(pending)*

---

## Source *(scope extraction — CLAUDE.md §1 scope rule)*

Only the sections below entered the working context for UM-US-01.

**SRS §6 Feature-01 · US-01-01 — Invite a User via Email [MVP]**
> * **As an** Admin / Account Owner
> * **I want to** invite a user by entering their email address
> * **So that** only real, verified people receive an invitation link to create an account.
>
> ```gherkin
> Scenario: Successfully send an email invitation
>   When the Admin enters email "family.member@gmail.com"
>   And the Admin clicks "Send Invitation"
>   Then the System creates a User record with status "PENDING"
>   And the System generates a token with a 24-hour TTL
>   And the System dispatches an activation email via Gmail SMTP
>   And the System displays message "Invitation sent successfully"
>
> Scenario: Reject invitation for duplicate active email
>   Given an existing ACTIVE User with email "family.member@gmail.com"
>   Then the System does not create a new User
>   And the System displays error "An account with this email already exists"
>
> Scenario: Reject invitation for invalid email format
>   When the Admin enters email "invalid-email-format"
>   Then the System displays validation error "Please enter a valid email address"
> ```

**SRS §2 FR-01 — User Onboarding & Management**
> The System shall allow authorized users to invite new users via email. The System shall generate a secure token with a TTL and dispatch an activation email via Gmail SMTP. Non-activated (`PENDING`) accounts shall not be permitted to log in until activated.

**SRS §3 NFR-01, NFR-04** · **§5 BF-02 steps 1–3** · **SDS §5.2.1 UM-US-01 (ADMIN)**
> 1. Validates email format and checks for existing active accounts.
> 2. Generates a secure random token (`secrets.token_urlsafe`) with a 24-hour TTL.
> 3. Persists invitation state and dispatches an email via Gmail SMTP.

### Out of scope for this story

UM-US-02 (activation) · UM-US-03 (list users) · SS-US-01/02 (login, logout) · Features 03–11 (wallets, categories, budgets, transactions, reporting, notifications, dashboard) · SRS §6 Feature-10/11 placeholders · SDS-only stories UM-US-04, UM-US-05, DC-US-01, DC-US-02.

Deliberately excluded from *this* story even though adjacent: what happens when the invited user opens the link (UM-US-02), and how the ADMIN sees the resulting list (UM-US-03).

---

## UM-US-01: Invite a User via Email

### User Scenarios & Testing *(mandatory)*

As an **ADMIN**, I want to invite a prospective family member by entering their email address so that only real, verified people receive an activation link, and no account can exist without a working mailbox behind it.

**Acceptance Criteria**:

**AC-01: Successfully send an email invitation**
**Given** an authenticated ADMIN,
**When** the ADMIN submits a well-formed email address that belongs to no existing account,
**Then** the system creates a user record with status `PENDING`, creates an invitation carrying a secure token that expires 24 hours from creation, dispatches an activation email containing the activation link to that address, and returns a success result carrying the new user's identifier, email, status, and token expiry.

**AC-02: Reject an email that already belongs to an ACTIVE account**
**Given** an `ACTIVE` user already exists with the submitted email address,
**When** an authenticated ADMIN submits that same address,
**Then** the system creates no user and no invitation, dispatches no email, and returns a conflict error stating that an account with this email already exists.

**AC-03: Reject a malformed email address**
**Given** an authenticated ADMIN,
**When** the ADMIN submits a value that is not a properly formatted email address,
**Then** the system creates nothing, dispatches no email, and returns a validation error identifying the email field.

**AC-04: Deny access to non-ADMIN callers**
**Given** an authenticated user whose role is not ADMIN,
**When** that user attempts to submit an invitation,
**Then** the system denies the request, creates nothing, dispatches no email, and returns a forbidden error.

**AC-05: Deny access to unauthenticated callers**
**Given** a caller presenting no credentials, or credentials that are invalid or expired,
**When** the caller attempts to submit an invitation,
**Then** the system denies the request before evaluating the payload, creates nothing, and returns an unauthenticated error.

**AC-06: Generate an unguessable token with a 24-hour TTL**
**Given** an authenticated ADMIN submits a valid invitation,
**When** the system generates the invitation token,
**Then** the token carries at least 128 bits of entropy, is unique across all invitations, and its expiry is exactly 24 hours after the moment of creation.

**AC-07: Create the invited account without credentials**
**Given** an authenticated ADMIN submits a valid invitation,
**When** the user record is created,
**Then** it holds the submitted email and status `PENDING`, carries no password and no full name, is assigned the non-privileged default role, and records which ADMIN issued the invitation.

**AC-08: Never expose the invitation token to the inviting ADMIN**
**Given** an authenticated ADMIN submits a valid invitation,
**When** the system returns the success result,
**Then** the result contains no invitation token in any form, and the raw token appears only inside the email delivered to the invited address.

**AC-09: Record an invitation audit event on success**
**Given** an authenticated ADMIN,
**When** an invitation is successfully created,
**Then** the system records an audit entry capturing the acting ADMIN, the timestamp, the invited email, and the outcome, without recording the token itself.

### Edge Cases

**EC-01**: **Email differing only by letter case or surrounding whitespace** — when the submitted address matches an existing `ACTIVE` account after case-folding and trimming (`Family.Member@Gmail.com`, `" family.member@gmail.com "`), the system treats it as the same address and rejects it under AC-02 rather than creating a second account.

**EC-02**: **Re-inviting an address that is still `PENDING`** — when the submitted address belongs to an existing `PENDING` user, the system does not create a duplicate user. It supersedes the outstanding invitation, issues a fresh token with a new 24-hour TTL, and dispatches a new email. This is the recovery path when an invitation expired or never arrived. The previously issued token stops working immediately.

**EC-03**: **Re-inviting an address whose invitation has expired** — behaves exactly as EC-02; expiry of the prior invitation is not an obstacle to re-inviting.

**EC-04**: **Email address exceeding the maximum supported length** — when the submitted address is longer than the system supports, it is rejected with a validation error rather than silently truncated.

**EC-05**: **Two ADMINs invite the same new address simultaneously** — only one user record and one usable invitation result; the second request receives a conflict error rather than creating a duplicate account.

**EC-06**: **Email delivery fails after the invitation is recorded** — the invitation remains recorded and the failure is logged for the operator. The invited address is still `PENDING`, so the ADMIN can recover by re-inviting (EC-02). The system never leaves a recorded invitation whose email silently vanished without a trace.

**EC-07**: **Email delivery is not configured** — when no mail credentials are available, the system surfaces a delivery failure rather than reporting success for an email that was never sent.

### Requirements *(mandatory)*

#### Functional Requirements

- **FR-01**: The system must **allow** an authenticated **ADMIN** to submit an email address in order to invite a new user (SRS FR-01, §6 US-01-01; SDS §5.2.1).
- **FR-02**: The system must **validate** that the submitted value is a properly formatted email address before any other processing (SRS §6 US-01-01 scenario 3; SDS §5.2.1 AC-1).
- **FR-03**: The system must **normalise** the submitted email — trimmed and case-folded — before any uniqueness comparison or persistence, so that one mailbox maps to exactly one account (EC-01).
- **FR-04**: The system must **reject** the invitation when the normalised email already belongs to a user in `ACTIVE` status (SRS §6 US-01-01 scenario 2; SDS §5.2.1 AC-1).
- **FR-05**: The system must **create** a user record with status `PENDING`, carrying no password and no full name, when the invitation is accepted (SRS §6 US-01-01 scenario 1).
- **FR-06**: The system must **assign** the invited user the non-privileged default role; privilege is never granted by invitation (SDS §5.2 role annotations).
- **FR-07**: The system must **record** which ADMIN issued each invitation.
- **FR-08**: The system must **generate** a cryptographically secure invitation token with at least **128 bits of entropy**, unique across all invitations (SRS NFR-04; SDS §5.2.1 AC-2).
- **FR-09**: The system must **set** the invitation expiry to exactly **24 hours** after creation (SRS §6 US-01-01 scenario 1; SDS §5.2.1 AC-2).
- **FR-10**: The system must **persist** the invitation as a record distinct from the user account, carrying its own lifecycle state (SDS §2.1, §4.3.3, §2.4.2).
- **FR-11**: The system must **supersede** any outstanding invitation for the same email when a new one is issued, so that at most one invitation for an address is usable at any time (EC-02, EC-03).
- **FR-12**: The system must **dispatch** an email to the invited address containing the activation link, via Gmail SMTP (SRS FR-01, §6 US-01-01 scenario 1; SDS §13).
- **FR-13**: The system must **exclude** the invitation token from every response returned to the inviting ADMIN (AC-08).
- **FR-14**: The system must **deny** the operation to any authenticated caller whose role is not ADMIN (SDS §5.2.1).
- **FR-15**: The system must **deny** the operation to unauthenticated callers, evaluating credentials before the payload (SRS FR-02; SDS §7.1.8).
- **FR-16**: The system must **return** the new user's identifier, email, status, and invitation expiry on success, together with a confirmation message (SRS §6 US-01-01 scenario 1; SDS §6.4.1).
- **FR-17**: The system must **record** an audit entry for every successful invitation, capturing actor, timestamp, invited email, and outcome — and never the token (SDS §7.1.10, §10.6).
- **FR-18**: The system must **enforce** email uniqueness under concurrent submissions, persisting only one account when the same new address is submitted simultaneously (EC-05).
- **FR-19**: The system must **respond** within the performance budget defined by SRS NFR-01, which requires that mail delivery not block the response (SRS NFR-01).
- **FR-20**: The system must **report** a delivery failure rather than success when mail dispatch is attempted and cannot be completed synchronously (EC-07).
- **FR-21**: The system must **log** a delivery failure that occurs after the invitation is recorded, leaving the invitation intact and re-invitable (EC-06).

#### Business Rules

- **BR-01**: An email address may correspond to at most one user account. Addresses are compared after trimming and case-folding (FR-03).
- **BR-02**: Only an `ACTIVE` account blocks a new invitation. A `PENDING` account is re-invitable (SRS §6 US-01-01 scenario 2 names only ACTIVE; EC-02).
- **BR-03**: At most one invitation per email address is usable at any moment; issuing a new one supersedes the previous (FR-11).
- **BR-04**: An invitation is valid strictly until its expiry instant; expiry is derived from the recorded timestamp and never from a stored flag (SRS NFR-04; SDS §2.4.2).
- **BR-05**: Only an ADMIN may invite. Invited users receive the non-privileged role and cannot themselves invite until an ADMIN grants that role — outside this story.
- **BR-06**: An invited account holds no credentials until activation. It cannot log in while `PENDING` (SRS FR-01).
- **BR-07**: The raw invitation token is disclosed to exactly one party — the invited mailbox. Never to the inviting ADMIN, never in a log, never in a response.
- **BR-08**: Creating the account and creating its invitation is a single atomic outcome. Neither may exist without the other (SRS NFR-05).

#### Key Entities

- **User**: The application account. Created by invitation in `PENDING` status with no credentials, and becomes usable only through activation (UM-US-02). Carries the role that governs what it may do. One user per email address.
- **Invitation**: The record of a single invitation attempt against an email address, carrying its secure token, its expiry instant, its lifecycle state, and the ADMIN who issued it. Distinct from the User so that the history of invitation attempts survives, and so that an expired attempt leaves the account untouched.
- **ADMIN / USER (role)**: ADMIN may invite and list users; USER is the non-privileged default granted to invited accounts.

### Success Criteria *(mandatory)*

- **SC-01**: An ADMIN can invite a new address and the invited person receives a real email containing a working activation link.
- **SC-02**: No account can come into existence without an invitation dispatched to a real mailbox — there is no self-registration path.
- **SC-03**: The system refuses to create a second account for an address that already has an `ACTIVE` one, including when the address differs only by case or whitespace.
- **SC-04**: An ADMIN whose invitation expired or never arrived can re-invite the same address and the newest link is the only one that works.
- **SC-05**: Non-ADMIN and unauthenticated callers cannot invite, and their attempts create nothing.
- **SC-06**: The invitation token never reaches anyone but the invited mailbox — not the inviting ADMIN, not a log file, not a response body.
- **SC-07**: Every invited account begins with no credentials, no name, the non-privileged role, and `PENDING` status.
- **SC-08**: Every successful invitation leaves an audit trail identifying who invited whom and when.
- **SC-09**: A mail-delivery failure never produces a silent success: it is either surfaced to the caller or recorded for the operator, and the invitation stays re-invitable.

### Assumptions & Dependencies

- **Authentication must exist before this story can be implemented.** AC-04 and AC-05 require an authenticated caller with a role, which is **SS-US-01 / US-02-01 (Login)** — a different epic, to be specified in `specs/002-system-security/`. UM-US-01 is *specified* first because it is the first story of this epic.
  - **Narrowed at the Implement step (`plan.md` A11).** What these ACs actually need is for a caller's identity and role to be *established*, not *issued*. Token **verification** therefore shipped with this story, and AC-04/AC-05 are satisfied and tested. The login **endpoint** did not, and remains SS-US-01's to deliver — so this story can be implemented and verified, but a human cannot obtain a token through the API until that story lands.
- **A bootstrap ADMIN is required.** Registration is invitation-only, so with no `ACTIVE` ADMIN in the database nobody can authenticate to issue the first invitation. Closing that cycle is a dependency of implementation, not a requirement of this story.
- **Working Gmail credentials are required for verification.** AC-01 and SC-01 depend on real mail delivery, which needs a Gmail account with 2FA and an App Password. Automated tests substitute a mail double; the Deploy step requires the real thing.
- **Role vocabulary comes from the SDS.** The SRS names the actor "Admin / Account Owner" without defining a role model; SDS §5.2 supplies `ADMIN` and `USER`. Treated as an elaboration, not a conflict. *(SRS §2 FR-01 was aligned at v2.1.0 to name the three account statuses, so the status vocabulary no longer depends on the SDS alone; the role vocabulary still does.)*
- **The activation link's destination is out of scope.** This story is complete when a correctly-formed link is delivered. What that link does belongs to UM-US-02.
- **Notifications are not in scope.** SRS FR-08 mentions notifying on invitation; SRS §6 Feature-08 owns that, and no notification requirement is drawn into this story.

---

## UM-US-02: Activate a User Account

> **IDs in this section are local to UM-US-02.** `AC-01` below is not UM-US-01's `AC-01`; each story section numbers its own criteria, per `artifact-templates/spec-templates.md`. Only `TC-NN` in `test_cases.md` runs continuously across the epic (`CLAUDE.md` §1.1 rule 4).

### Source *(scope extraction — CLAUDE.md §1 scope rule)*

**SRS §6 Feature-01 · US-01-02 — Activate User Account [MVP]**
> * **As an** Invited User
> * **I want to** click the activation link from my email and set my password
> * **So that** I can activate my account and log in safely.
>
> ```gherkin
> Scenario: Successfully activate account within TTL
>   Given an invited User has a token "valid-uuid-token" with status "PENDING"
>   And the token expiration time is in the future
>   When the User accesses the activation link with token "valid-uuid-token"
>   And the User enters full name "Jane Doe"
>   And the User enters password "SecurePassword123!"
>   And the User clicks "Activate Account"
>   Then the System hashes the password using a secure algorithm
>   And the System updates User status to "ACTIVE"
>   And the System invalidates the token "valid-uuid-token"
>   And the System redirects the User to the Login screen with message "Account activated successfully"
>
> Scenario: Reject activation when token is expired
>   Given an invited User has a token "expired-token"
>   And the token expiration time has passed
>   When the User accesses the activation link with token "expired-token"
>   Then the System displays error "Invitation link has expired. Please request a new invitation."
>   And the account status remains "PENDING"
> ```

**SDS §5.2.2 UM-US-02 (GUEST/USER)**
> * **Goal:** Allow an invited user to set their full name and password to activate their account.
> 1. Validates token existence and checks `expires_at > CURRENT_TIMESTAMP`.
> 2. Hashes password using `argon2` or `bcrypt`.
> 3. Updates user state to `ACTIVE` and invalidates the activation token.

**SRS §5 BF-02 steps 4–6**
> 4. User accesses activation endpoint with token.
> 5. System verifies `NOW() < token_expires_at`.
> 6. User submits password; status transitions to `ACTIVE`; token is invalidated.

**SRS §3 NFR — security baseline** · **SRS §4 UXR-04** · **SDS §7.1.5 password policy** · **SDS §6.4.2 UM-API-02**

### Out of scope for this story

UM-US-03 (list users) · SS-US-01/02 (login, logout) · Features 03–11 · SRS §6 Feature-10/11 placeholders · SDS-only stories UM-US-04, UM-US-05, DC-US-01, DC-US-02.

Deliberately excluded even though adjacent:

- **Logging in.** SRS US-01-02 ends by *directing* the activated user to the login screen. Issuing a session is SS-US-01's job, so activation returns no token (AC-09).
- **Reactivating a `DEACTIVATED` account.** Restoring withdrawn access belongs to SDS §5.2.5 UM-US-05, out of MVP scope. Here it is simply refused (EC-07).
- **Password reset / change.** No SRS story in round 1 covers it.
- **Resending an invitation.** That is UM-US-01's re-invite path (its EC-02), already built.

### User Scenarios & Testing *(mandatory)*

As an **invited person**, I want to open the link from my invitation email and choose my name and password, so that my account becomes usable and nobody but me ever knows the credential that unlocks it.

**Acceptance Criteria**:

**AC-01: Successfully activate an account within its TTL**
**Given** a `PENDING` user whose outstanding invitation has not yet expired,
**When** the invited person submits that invitation's token together with a full name and a password meeting the password policy,
**Then** the system sets the user's status to `ACTIVE`, stores the submitted full name, stores the password in irreversible hashed form, marks the invitation `ACCEPTED`, and returns a success result directing the person to log in.

**AC-02: Reject an expired token**
**Given** an invitation whose expiry instant has passed,
**When** its token is submitted,
**Then** the system activates nothing, leaves the user `PENDING`, leaves the invitation's stored state untouched, and returns an expiry error telling the person to request a new invitation.

**AC-03: Reject a token that matches no invitation**
**Given** a token value that corresponds to no invitation on record,
**When** it is submitted for activation, or its state is checked (AC-11),
**Then** the system changes nothing and refuses with the same outcome used for every other unusable token except expiry (AC-04, AC-05, EC-06, EC-07) — an unrecognised token is indistinguishable from one already used, superseded, or belonging to a user no longer `PENDING`. *(Reconciled with AC-11/EC-09 — see the note after EC-09.)*

**AC-04: Reject a token that has already been used**
**Given** an invitation already `ACCEPTED`,
**When** the same token is submitted a second time,
**Then** the system changes nothing and refuses with that same generic outcome (AC-03) — a token grants activation exactly once, and a second attempt is told no more than that it no longer works.

**AC-05: Reject a superseded token**
**Given** the address was re-invited, so an earlier invitation was superseded,
**When** the earlier token is submitted,
**Then** the system refuses it with that same generic outcome (AC-03). Only the most recently issued link can activate an account, and an older one is indistinguishable from any other unusable token.

**AC-06: Enforce the password policy**
**Given** an otherwise usable token,
**When** the submitted password fails any policy rule — too short, missing an uppercase letter, missing a digit, missing a special character, or longer than the maximum supported length,
**Then** the system activates nothing and returns a validation error identifying the password field.

**AC-07: Never expose the credential**
**Given** a successful activation,
**When** the result is returned and the operation is recorded,
**Then** the raw password appears in no response, no log entry and no audit record; the stored hash is never returned to any caller; and the submitted token is not echoed back.

**AC-08: Activate and invalidate as one atomic outcome**
**Given** a successful activation,
**When** the change is persisted,
**Then** the user's transition to `ACTIVE` and the invitation's transition to `ACCEPTED` either both take effect or neither does. A usable token must never survive a successful activation.

**AC-09: Do not establish a session**
**Given** a successful activation,
**When** the result is returned,
**Then** it carries no access token and no session of any kind — the person is directed to log in, which is a separate story.

**AC-10: Require a full name**
**Given** an otherwise usable token,
**When** the submitted full name is absent, empty, only whitespace, or longer than the account record can hold,
**Then** the system activates nothing and returns a validation error identifying the name field.

**AC-11: Report a token's usability without consuming it**
**Given** a token,
**When** the person's client asks for the token's state rather than submitting an activation,
**Then** the system reports exactly one of **`usable`**, **`expired`**, or **`not usable`** (serialised `not_usable`), and **changes nothing** — the token remains exactly as usable afterwards as it was before. `not usable` is reported identically regardless of the underlying reason: the token may match no invitation at all, one already used, one superseded, or one whose user is no longer `PENDING` — the check draws no distinction between them, and does not begin to draw one once that token also passes its TTL (EC-11). The state check and the activation attempt evaluate the same conditions in the same order (BR-02), so a client can never be told one thing by the check and another by the attempt. *(Reconciled with AC-03 — see the note after EC-09.)*

**AC-12: Accept the request without credentials**
**Given** a caller presenting no credentials at all,
**When** an activation is submitted or a token's state is requested,
**Then** the system processes the request. An invited person has no account yet, so requiring authentication would make activation impossible.

### Edge Cases

**EC-01**: **Full name with surrounding whitespace** — `"  Jane Doe  "` is stored trimmed. Interior spacing is preserved as typed; the system does not attempt to correct a person's name.

**EC-02**: **Password exactly at the policy boundary** — a password of exactly the minimum length carrying exactly one uppercase letter, one digit and one special character is **accepted**. The policy is a floor, not a target.

**EC-03**: **Password exceeding the maximum supported length** — rejected with a validation error rather than silently shortened. A credential that is quietly truncated would let a different, shorter password unlock the same account.

**EC-04**: **Non-ASCII full name** — a name such as `Đặng Ngọc Thịnh` is stored and returned exactly as submitted. Names are not transliterated, stripped of accents, or case-folded.

**EC-05**: **The same valid token submitted twice concurrently** — exactly one submission activates the account; the other is refused. Two callers must never both succeed against a single-use token.

**EC-06**: **Token belonging to a user who is already `ACTIVE`** — refused with the same generic outcome as AC-03. The account is already usable, and re-running activation would let a stale link overwrite a live password; whoever holds the token learns only that it does not work, not why.

**EC-07**: **Token belonging to a `DEACTIVATED` user** — refused with the same generic outcome as AC-03. Access was withdrawn deliberately, and an old invitation link must not restore it, nor explain why it failed. Reactivation is UM-US-05's concern.

**EC-08**: **Token submitted with altered surrounding characters** — a token differing from the issued value by so much as leading or trailing whitespace does not match. Unlike an email address, a token is compared exactly and is never normalised; guessing tolerance into a secret would widen the space of values that unlock an account. Such a token falls into AC-03's unrecognised case and is reported identically.

**EC-09**: **State requested for a token that is not currently usable** — reported as `expired` when the invitation is outstanding but past its TTL, and as the same generic `not usable` outcome in every other case (never issued, already used, superseded, or the user no longer `PENDING`) — indistinguishable from AC-03's unrecognised-token case. The request still changes nothing, including not advancing the invitation's stored state.

**EC-10**: **Token at the exact instant of expiry** — a token whose expiry equals the moment of use is treated as expired, not usable. The TTL is valid strictly *until* its expiry instant, consistent with UM-US-01 BR-04; one instant past creation-plus-24-hours is already too late.

**EC-11**: **Token that is expired *and* unusable for another reason** — a token that has been used, superseded, or belongs to a user no longer `PENDING`, *and* is also past its TTL, is reported as **`not usable`**, never as `expired`. The two conditions overlap constantly rather than exceptionally: every accepted or superseded invitation becomes expired 24 hours after it was issued, so this is the steady state of an old token, not a corner case. Reporting `expired` for it would make AC-04 and AC-05 hold only inside the first 24 hours and then quietly stop — whoever held a used link could tell "used" from "never issued" simply by waiting a day. `expired` is therefore reserved for a token that would otherwise have worked: outstanding, belonging to a `PENDING` user, and merely too late. See BR-02 for the resulting order of evaluation.

> **Reconciling AC-03, AC-11 and EC-09.** A first pass had AC-11's state check answering `usable` / `expired` / `already used` for any token, while AC-03 required an unrecognised token's error to give no sign of whether it ever existed — so an unrecognised token and an already-used one would have answered differently, and the check would have been an oracle for which raw values were ever issued as tokens. Resolved by **collapsing every non-expiry refusal reason into one indistinguishable outcome** (`not usable`): unrecognised (AC-03), already used (AC-04), superseded (AC-05), and wrong user state (EC-06, EC-07) all report identically, on both an activation attempt and a state check. `expired` alone stays distinguishable, for two reasons together: it is a benign, expected, time-bounded fact the person was already told about (the 24-hour TTL itself, UXR-04), and — unlike an email address, which is guessable and is the reason UM-US-01 needed a documented SEC-10 exemption to disclose it — an invitation token is a 256-bit unguessable secret (SEC-02). Reaching *any* reported state beyond silence requires already possessing the genuine token, which only its legitimate holder (or someone they shared it with) can do; naming the one additional reason `expired` therefore discloses nothing to anyone who does not already hold it. This narrows, rather than removes, the non-disclosure guarantee AC-03 originally claimed in full. It is recorded here, as a spec-level decision, because it changes three ACs' Then-clauses and an edge case — not merely an implementation choice that would belong in `plan.md` alone.
>
> **Amended at the design review (EC-11, BR-02).** The reconciliation above says *which* outcomes exist but not which one wins when a token fails two conditions at once — and the design's first pass answered that badly, by testing expiry before everything else. Because an accepted or superseded invitation is *also* expired a day later, that order would have reported `expired` for a reused link submitted the next day and `not usable` for the same link submitted within the TTL, so the indistinguishability this note establishes would have quietly expired along with the token. The fix is an explicit order of evaluation, now part of BR-02: outstanding-state, then user-state, then expiry **last**. `expired` therefore means "this token would have worked, and you are late" and nothing else, which is the narrow, benign disclosure the paragraph above argued was safe — while every other reason stays collapsed permanently rather than for twenty-four hours.

### Requirements *(mandatory)*

#### Functional Requirements

- **FR-01**: The system must **accept** an activation request carrying a token, a full name and a password, from a caller presenting no credentials (SRS §6 US-01-02; SDS §6.4.2; constitution API-08).
- **FR-02**: The system must **locate** the invitation corresponding to the submitted token, comparing the token exactly (EC-08).
- **FR-03**: The system must **refuse** activation when no invitation corresponds to the submitted token (AC-03).
- **FR-04**: The system must **refuse** activation when the invitation's expiry instant has passed, determined by comparison at the moment of the request (SRS §5 BF-02 step 5; AC-02).
- **FR-05**: The system must **refuse** activation when the invitation is not in its outstanding state — already accepted, or superseded by a later invitation (AC-04, AC-05).
- **FR-06**: The system must **refuse** activation when the invitation's user is not `PENDING` (EC-06, EC-07).
- **FR-07**: The system must **validate** the submitted password against the password policy before making any change (SDS §7.1.5; constitution VL-04; AC-06).
- **FR-08**: The system must **reject** a password exceeding the maximum supported length rather than truncating it (EC-03).
- **FR-09**: The system must **require** a non-empty full name after trimming (AC-10, EC-01).
- **FR-10**: The system must **store** the password using a strong one-way hash, never in recoverable form (SRS §3 security baseline; SDS §5.2.2 AC-2; AC-07).
- **FR-11**: The system must **set** the user's status to `ACTIVE` on success (SRS §6 US-01-02; SDS §5.2.2 AC-3).
- **FR-12**: The system must **record** the submitted full name on the user (SRS §6 US-01-02).
- **FR-13**: The system must **invalidate** the invitation on success so it cannot activate again (SRS §5 BF-02 step 6; constitution SEC-04; AC-04).
- **FR-14**: The system must **apply** the status change and the invalidation as a single atomic outcome (AC-08).
- **FR-15**: The system must **return** a success result confirming activation and directing the person to log in (SDS §6.4.2).
- **FR-16**: The system must **exclude** any session token from the activation result (AC-09).
- **FR-17**: The system must **exclude** the raw password, the stored hash, and the submitted token from every response, every **application log entry**, and every audit record (AC-07). *Scope note:* this covers the logs the system itself writes. It does **not** extend to the web server's access log, which records request URLs and therefore captures a token supplied as a query parameter by the state check (AC-11) — an accepted, documented exposure, bounded by the token being single-use and 24-hour-lived, and by the same token already travelling inside the URL of the activation link the invitation email delivers. Recorded in this story's `plan.md` A10 with the alternatives that were weighed and rejected.
- **FR-18**: The system must **record** an audit entry for every activation attempt **that is evaluated against a token** — successful or refused — capturing the affected account and the outcome, and never the credential (constitution LA-02, LA-04). *Scope note:* a request rejected for a malformed payload (AC-06, AC-10) is refused before any token is examined and produces **no** audit entry; such attempts are traceable through the request log, which records method, path and status without a body. Auditing them would mean emitting business events from the framework's validation layer, which the layering rules forbid. Recorded in `plan.md` F2.
- **FR-19**: The system must **report** a token's state on request as exactly one of `usable`, `expired`, or `not usable` (serialised `not_usable`), without altering it — where `not usable` collapses every non-expiry refusal reason so an unrecognised token cannot be distinguished from one already used, superseded, or belonging to a user no longer `PENDING`, **including when that token is also past its TTL** (AC-11, EC-09, EC-11, reconciled with AC-03).
- **FR-20**: The system must **ensure** that concurrent submissions of one token activate the account at most once (EC-05).
- **FR-21**: The system must **refuse** an activation whose password fails policy even when every other input is valid, leaving the token still usable so the person can retry (AC-06).
- **FR-22**: The system must **report** the same generic refusal for an unrecognised token (FR-03), an already-accepted or superseded token (FR-05), and a token whose user is no longer `PENDING` (FR-06) — never distinguishing among them, and never letting the passage of time turn one of them into a differently-reported case (EC-11) — while continuing to name expiry specifically (FR-04) for a token whose only defect is the clock (AC-03, AC-04, AC-05, EC-06, EC-07, EC-08, EC-11).
- **FR-23**: The system must **reject** a full name longer than the maximum the account record can hold, rather than accepting it and failing during persistence. *(Enforces the width the stored record already has; it does not settle what the limit ought to be — see `test_cases.md` QF-05.)*

#### Business Rules

- **BR-01**: An invitation token grants activation **exactly once**. Success consumes it (FR-13, SEC-04).
- **BR-02**: A token is usable only while **all** of the following hold: it matches an invitation, that invitation is outstanding, its user is `PENDING`, and its expiry has not passed. Failing any one makes it unusable. When more than one fails, **the reported reason is decided by a fixed order of evaluation: whether the invitation is outstanding, then whether its user is `PENDING`, then expiry — with expiry evaluated last.** So `expired` is reported only for a token that fails nothing except the clock, and every other failure reports `not usable` no matter how much time has also passed (EC-11). The order is part of the rule, not an implementation detail: a different order would narrow BR-10's guarantee to the first 24 hours of a token's life.
- **BR-03**: Expiry is evaluated by comparison at the moment of use, never read from a stored flag (constitution SEC-05; consistent with UM-US-01 BR-04).
- **BR-04**: Only the most recently issued invitation for an address is usable; earlier ones were superseded when it was issued (UM-US-01 FR-11).
- **BR-05**: A refused activation leaves every stored value untouched. In particular an expired token leaves its user `PENDING`, so the address remains re-invitable.
- **BR-06**: The raw password is known only to the person who submits it. It is never stored, logged, returned, or recoverable from what is stored.
- **BR-07**: Activation confers no session. Authentication is a separate act (AC-09).
- **BR-08**: Activation is available to unauthenticated callers by necessity, and is the only write operation in this epic that is (constitution API-08).
- **BR-09**: A password that satisfies every policy rule is accepted regardless of how it satisfies them; the policy defines a minimum, and no additional undocumented rule may reject a compliant password (EC-02).
- **BR-10**: A refusal names its reason only when the reason is expiry. Every other refusal — unrecognised token, already used, superseded, or user no longer `PENDING` — reports identically, because distinguishing them would let whoever holds a token learn more than whether it works; expiry is exempted because it is a fact already disclosed by the 24-hour TTL itself, and the token's entropy (SEC-02) makes the disclosure safe regardless of who is asking.

#### Key Entities

- **User**: Transitions `PENDING → ACTIVE` here, gaining a full name and a password hash. This is the only story that sets a password on an invited account.
- **Invitation**: Transitions `PENDING → ACCEPTED` here. Its token is the sole authorisation for the transition, and is spent in the process. `EXPIRED` remains derived, never written (UM-US-01 BR-04).

### Success Criteria *(mandatory)*

- **SC-01**: A person who receives an invitation email can follow its link, choose a name and password, and end up with a usable account.
- **SC-02**: An expired link cannot activate an account, and tells the person clearly to ask for a new invitation rather than failing opaquely.
- **SC-03**: A link works at most once. Re-using it, or using an older superseded link, never activates anything.
- **SC-04**: A weak password cannot become an account credential, and the person is told which rule they missed.
- **SC-05**: No credential the person submits is recoverable from the system afterwards — not from the database, not from a log, not from a response.
- **SC-06**: Activating an account never silently logs anyone in.
- **SC-07**: A person whose link has expired can be re-invited and the new link works, because the refused activation left their account untouched.
- **SC-08**: A client can tell a person their link has expired *before* asking them to type a password.
- **SC-09**: Every activation attempt leaves an audit trail identifying the account and the outcome.

### Assumptions & Dependencies

- **UM-US-01 must be implemented first.** Activation consumes an invitation, and there is no way to create one otherwise. UM-US-01 is complete and verified, so this dependency is satisfied.
- **The activation link's destination is this story's endpoint.** UM-US-01 delivers a link built from `ACTIVATION_URL_TEMPLATE`; until this story ships, that link resolves to nothing. Making it resolve is the point of this story.
- **Logging in afterwards requires SS-US-01.** SC-01 says the account is *usable*; proving a person can then log in needs the login endpoint, which is a different epic. This story is verifiable without it — the account's `ACTIVE` status and stored hash are observable directly.
- **The password policy comes from the SDS, not the SRS.** SRS §3 requires strong hashing but sets no composition rules; SDS §7.1.5 supplies minimum length, uppercase, digit and special character. Treated as an elaboration, consistent with how the role model was handled in UM-US-01.
- **A token pre-check that reports state without an activation attempt is in scope**, resolving a conflict between two reference documents: one names a public, read-only check for this purpose; the other's endpoint index named only the state-changing action. Ruled in favour of the more permissive document — the read serves UXR-04's one-page guidance, letting a client learn a link's outcome (AC-11) before asking someone to type a password (SC-08). The reference documents were aligned to match, so the conflict is closed rather than merely decided. The concrete contract is recorded in this story's `plan.md` *Gaps & Decisions*, not here.
- **The pre-check discloses the token to the access log, and this is accepted.** Delivering a link a person can simply follow means the token travels in a URL, so the server's access log records it. FR-17's guarantee is scoped to the logs this system writes; the residual exposure and the alternatives that were rejected are in `plan.md` A10. It is a narrower promise than the first draft made, stated here rather than left as an implementation surprise.
- **Four of these criteria have no scenario in the requirements baseline.** AC-04 (reuse), AC-05 (supersession), AC-06 (password policy) and AC-11 (the pre-check) derive from the technical baseline, the project rules, and UXR-04 — not from a Gherkin scenario in `SRS.md`, which covers only successful activation and expiry. The baseline was corrected where it contradicted itself but deliberately **not** extended, because adding scenarios to it is a requirements change rather than an alignment. Recorded in `plan.md` F1 so the gap stays visible.
- **A real mailbox is not required to verify this story.** Unlike UM-US-01, activation needs only a token, which a test can obtain from the invitation it created. Live SMTP is UM-US-01's concern and is already proven.
