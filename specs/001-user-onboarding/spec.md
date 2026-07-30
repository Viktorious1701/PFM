# Feature Specification: User Management & Onboarding (UM)

> **Feature:** SRS §6 Feature-01 · SDS §5.2 (UM)
> **Spec:** [spec.md](spec.md)
> **Stories in this file:** UM-US-01 *(specified)* · UM-US-02, UM-US-03 *(pending)*

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

- **Authentication must exist before this story can be implemented.** AC-04 and AC-05 require an authenticated caller with a role, which is **SS-US-01 / US-02-01 (Login)** — a different epic, specified in `specs/002-system-security/`. UM-US-01 is *specified* first because it is the first story of this epic, but it cannot be *implemented* or verified before login exists.
- **A bootstrap ADMIN is required.** Registration is invitation-only, so with no `ACTIVE` ADMIN in the database nobody can authenticate to issue the first invitation. Closing that cycle is a dependency of implementation, not a requirement of this story.
- **Working Gmail credentials are required for verification.** AC-01 and SC-01 depend on real mail delivery, which needs a Gmail account with 2FA and an App Password. Automated tests substitute a mail double; the Deploy step requires the real thing.
- **Role vocabulary comes from the SDS.** The SRS names the actor "Admin / Account Owner" without defining a role model; SDS §5.2 supplies `ADMIN` and `USER`. Treated as an elaboration, not a conflict — see `docs/00-foundation/srs-sds-alignment.md`.
- **The activation link's destination is out of scope.** This story is complete when a correctly-formed link is delivered. What that link does belongs to UM-US-02.
- **Notifications are not in scope.** SRS FR-08 mentions notifying on invitation; SRS §6 Feature-08 owns that, and no notification requirement is drawn into this story.
