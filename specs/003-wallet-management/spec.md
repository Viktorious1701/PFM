# Feature Specification: Wallet Management (WM)

> **Feature:** SRS §6 Feature-03 · SDS §5.3 (WM)
> **Spec:** [spec.md](spec.md)
> **Stories in this file:** WM-US-01 *(implemented, verified — 198 passed, 98% coverage)* · WM-US-02 *(implemented, verified — 302 passed, 99% coverage)* · WM-US-04 *(specified)*

---

## Source *(scope extraction — CLAUDE.md §1 scope rule)*

Only the sections below entered the working context for WM-US-01.

**SRS §6 Feature-03 · US-03-01 — Create a Wallet [MVP]**
> * **As an** Authenticated User
> * **I want to** create a new wallet with an initial balance
> * **So that** I can track spending across cash, bank, or card accounts.
>
> ```gherkin
> Feature: Create Wallet
>
>   Scenario: Create a wallet successfully
>     Given the User is logged in
>     When the User enters wallet name "Main Checking"
>     And the User selects wallet type "BANK"
>     And the User enters currency "USD"
>     And the User enters initial balance 1000.00
>     And the User clicks "Save Wallet"
>     Then the System creates a new wallet for the user
>     And the wallet balance is set to 1000.00
> ```

**SRS §1.5 Conceptual Domain Model**
> **Wallet** — A named store of liquid money a User holds — cash, a bank account, a credit line — that Transactions move money into or out of (FR-03).
>
> | Relationship | Cardinality | Meaning |
> | User owns Wallet | one User → many Wallets | A User may hold several Wallets — cash, bank, credit (FR-03) |

**SRS §2 FR-03 — Wallet Management**
> The System shall allow Users to create and manage multiple Wallets (e.g., Cash, Checking, Credit Card). Each wallet tracks name, type, currency, and current real-time balance.

**SRS §3 NFR-05 — Data Integrity & Monetary Precision**
> All monetary attributes and asset valuations must be stored using arbitrary-precision decimal representations (`DECIMAL(15,2)`). Balance updates must execute inside ACID-compliant database transaction blocks.

**SDS §5.3.1 WM-US-01: Create a Wallet (USER)**
> * **Goal:** Establish monetary containers (e.g., Checking, Cash, Credit Card).
> * **Acceptance Criteria:** Requires name, type, currency code, and initial balance.

**SDS §2.2 Domain Object**
> **Wallet:** Financial container holding funds (`id`, `user_id`, `name`, `type`, `balance`, `currency`).

**SDS §6.2.1 DTO Registry**
> **`WalletCreate`**: `{ "name": "string", "type": "string", "currency": "string", "initial_balance": 0.00 }`

**SDS §6.3 API Index / §6.5 API → User Story Traceability**
> **`WM-API-01`** `POST` `/api/v1/wallets` — Create a new wallet. Traced to WM-US-01.

**constitution.md VL-07**
> Monetary values use `Decimal` with `DECIMAL(15,2)` precision (SRS NFR-05). Never float.

### Out of scope for this story

WM-US-02 (list wallets) · WM-US-03 (view a wallet) · WM-US-04 (update a wallet) · WM-US-05 (delete a wallet) · UM-US-04/05, DC-US-01/02 · Features 04–11 · SRS §6 Feature-10/11 placeholders.

Deliberately excluded from *this* story even though adjacent: reading a wallet back through any `GET` endpoint (WM-US-02/03 — this story is verifiable only through what `POST /api/v1/wallets` itself returns and through direct inspection of the stored row), renaming or archiving a wallet (WM-US-04/05), and any transaction moving money into or out of a wallet (Feature-05, Transaction Management).

---

## WM-US-01: Create a Wallet

### User Scenarios & Testing *(mandatory)*

As an **authenticated User**, I want to create a new wallet by giving it a name, a type, a currency, and an initial balance, so that I can start tracking spending across cash, bank, or card accounts.

**Acceptance Criteria**:

**AC-01: Successfully create a wallet with all mandatory inputs**
**Given** an authenticated User,
**When** the User submits a wallet name, a wallet type, a currency, and an initial balance, all within their allowed bounds,
**Then** the system creates the wallet with a `balance` equal to the submitted initial balance, owned by the submitting User, and returns a success result carrying the wallet's identifier, owner, name, type, currency, and balance.

**AC-02: Deny access to unauthenticated callers**
**Given** a caller presenting no credentials, or credentials that are invalid or expired,
**When** the caller attempts to create a wallet,
**Then** the system denies the request before evaluating the payload, creates nothing, and returns an unauthenticated error.

**AC-03: Reject a missing or blank wallet name**
**Given** an authenticated User,
**When** the submitted name is absent, empty, or only whitespace,
**Then** the system creates nothing and returns a validation error identifying the name field.

**AC-04: Reject a wallet name exceeding the maximum supported length**
**Given** an authenticated User,
**When** the submitted name is longer than the system supports,
**Then** the system creates nothing and returns a validation error rather than truncating the name.

**AC-05: Reject a missing or blank wallet type**
**Given** an authenticated User,
**When** the submitted type is absent, empty, or only whitespace,
**Then** the system creates nothing and returns a validation error identifying the type field.

**AC-06: Reject a wallet type exceeding the maximum supported length**
**Given** an authenticated User,
**When** the submitted type is longer than the system supports,
**Then** the system creates nothing and returns a validation error rather than truncating the type.

**AC-07: Reject a currency value that is not a well-formed 3-letter code**
**Given** an authenticated User,
**When** the submitted currency is absent, is not exactly three letters, or is not entirely uppercase,
**Then** the system creates nothing and returns a validation error identifying the currency field.

**AC-08: Reject a missing initial balance**
**Given** an authenticated User,
**When** the initial balance is absent from the submission,
**Then** the system creates nothing and returns a validation error identifying the balance field.

**AC-09: Reject an initial balance carrying more than two decimal places**
**Given** an authenticated User,
**When** the submitted initial balance carries more than two digits after the decimal point,
**Then** the system creates nothing and returns a validation error rather than rounding or truncating the value.

**AC-10: A created wallet always belongs to the submitting User**
**Given** an authenticated User submits a valid wallet creation request,
**When** the wallet is created,
**Then** its owner is exactly the authenticated User who submitted the request, determined solely from the caller's own identity and never from any value in the request payload.

**AC-11: Return exactly the documented wallet fields**
**Given** an authenticated User submits a valid wallet creation request,
**When** the system returns the success result,
**Then** the result carries exactly the wallet's identifier, owner identifier, name, type, currency, and balance — no other field, and no data belonging to any other User.

### Edge Cases

**EC-01**: **Initial balance of exactly zero** — a submitted balance of `0.00` is accepted; a brand-new wallet is allowed to start empty.

**EC-02**: **Negative initial balance** — a submitted balance below zero is accepted. No acceptance criterion or business rule in this story restricts the sign of a wallet's balance, and a wallet of type `"CREDIT"` (or any other type the User names, per AC-05's free-text acceptance) legitimately begins already in debt.

**EC-03**: **Currency submitted in lowercase or mixed case** — `"usd"` or `"Usd"` is rejected under AC-07 rather than upper-cased and accepted; the system performs no case normalisation on this field.

**EC-04**: **Wallet name with surrounding whitespace** — `"  Main Checking  "` is stored trimmed, as `"Main Checking"`. Interior spacing is preserved as typed.

**EC-05**: **A wallet type outside the Gherkin's and SDS's own examples** — a value such as `"Piggy Bank"` or `"CREDIT_CARD"`, meeting only the length bound, is accepted. No enumerated list of valid types exists in either reference document (see `plan.md` A1).

**EC-06**: **More than one validation failure in a single submission** — when the name is blank and the currency is malformed in the same request, both problems are reported together in one response, not just the first one encountered.

**EC-07**: **Two wallets with the same name for the same User** — both are created successfully, each with its own identifier. No acceptance criterion or business rule requires wallet names to be unique, even for one User's own wallets.

**EC-08**: **Initial balance exceeding the total digit width of `DECIMAL(15,2)`** — a value with more than 13 digits before the decimal point (15 significant digits in total, per constitution VL-07) is rejected with a validation error, distinctly from AC-09's decimal-places check but under the same `Decimal(15,2)` rule.

### Requirements *(mandatory)*

#### Functional Requirements

- **FR-01**: The system must **allow** an authenticated User of any role to submit a wallet name, type, currency, and initial balance in order to create a new wallet (SRS §6 US-03-01; SDS §5.3.1).
- **FR-02**: The system must **deny** the operation to unauthenticated callers, evaluating credentials before the payload (constitution API-08; mirrors UM-US-01 FR-15, UM-US-03 FR-04).
- **FR-03**: The system must **require** a non-empty wallet name after trimming surrounding whitespace, and **reject** — rather than truncate — a name longer than the system supports (AC-03, AC-04, EC-04).
- **FR-04**: The system must **require** a non-empty wallet type, and **reject** — rather than truncate — a type longer than the system supports; the system enforces no closed list of valid type values (AC-05, AC-06, EC-05; `plan.md` A1).
- **FR-05**: The system must **require** the submitted currency to match a well-formed 3-letter uppercase code, and **reject** it otherwise, with no case-folding applied (AC-07, EC-03; `plan.md` A2).
- **FR-06**: The system must **require** the initial balance, **store** it as a `Decimal` value with at most two digits after the decimal point and at most fifteen significant digits in total, and **reject** — rather than round or truncate — a value carrying more of either (AC-08, AC-09, EC-08; constitution VL-07; `plan.md` A3).
- **FR-07**: The system must **accept** a zero or negative initial balance; no sign constraint is enforced (EC-01, EC-02; `plan.md` A4).
- **FR-08**: The system must **set** the wallet's owner to the authenticated caller's own identifier, never to any value supplied in the request payload (AC-10; constitution SEC-08).
- **FR-09**: The system must **store** the submitted initial balance as the wallet's `balance` (SDS §2.2, §6.2.1 — the create-time input and the stored column are distinct names for the same value).
- **FR-10**: The system must **return**, on success, exactly the wallet's identifier, owner identifier, name, type, currency, and balance (AC-11).
- **FR-11**: The system must **group** every validation failure from one submission into a single response rather than reporting only the first (EC-06; constitution VL-02).
- **FR-12**: The system must **impose no uniqueness constraint** on wallet name, including across two wallets owned by the same User (EC-07).

#### Business Rules

- **BR-01**: A wallet belongs to exactly one User, assigned at creation time from the authenticated caller's own identity (SRS §1.5 "User owns Wallet"; constitution SEC-08; FR-08).
- **BR-02**: A wallet's balance is a `Decimal` value with at most two decimal places and at most fifteen significant digits in total (`DECIMAL(15,2)`); a value exceeding either bound is refused, never rounded or truncated (constitution VL-07; FR-06, EC-08).
- **BR-03**: A wallet's initial balance may be zero or negative; no rule in this story requires it to be positive (FR-07).
- **BR-04**: Wallet type and currency are validated only against the bounds this story defines — a length bound for type, a 3-letter-uppercase shape for currency — and against no closed vocabulary of business-meaningful values (FR-04, FR-05).
- **BR-05**: Wallet names carry no uniqueness constraint, per-User or system-wide (FR-12).

#### Key Entities

- **Wallet**: A named store of liquid money a User holds — cash, a bank account, a credit line (SRS §1.5). Carries `id`, `user_id`, `name`, `type`, `currency`, and `balance` (SDS §2.2, §4.3.3). Created here for the first time; every other Wallet Management story (WM-US-02..05) reads or mutates a Wallet this story brings into existence.
- **User**: Reused from Feature-01/Feature-02 with no new column. The authenticated caller becomes the wallet's owner; no role restriction applies (any authenticated, `ACTIVE` User may create a wallet).

### Success Criteria *(mandatory)*

- **SC-01**: An authenticated User can create a wallet with a name, a type, a currency, and an initial balance in one call, and the response reflects exactly what was created.
- **SC-02**: No wallet can be created without an authenticated caller.
- **SC-03**: Every wallet's owner is exactly the User who created it — never a value supplied in the request, and never another User's identifier.
- **SC-04**: A wallet's initial balance is always stored at the precision the User specified — never silently rounded, truncated, or widened.
- **SC-05**: Malformed wallet-creation input — a missing or blank name, an over-long name or type, a malformed currency, a missing or over-precise balance — is rejected before anything is persisted, with every problem in one submission reported together.

### Assumptions & Dependencies

- **Login (SS-US-01) is already implemented.** Unlike UM-US-01, which was specified before any authentication existed, this story is specified after `CurrentUserDep` (`backend/app/core/deps.py`) and the login endpoint are both real. AC-02 is fully implementable and testable against the live dependency chain, not merely designed against it.
- **No wallet `type` enumeration exists in either reference document.** The SRS Gherkin uses `"BANK"`; the SDS prose names `"Checking, Cash, Credit Card"` as examples in a different style. Treated as illustrative, not exhaustive — recorded as a decision in `plan.md` A1, not invented as a hidden business rule.
- **No currency format rule exists beyond the bare example `"USD"`.** This story validates only the 3-letter-uppercase *shape*, not membership in the real ISO 4217 list — recorded as a decision in `plan.md` A2. Validating against the actual currency list is a larger scope than any AC here authorises.
- **The `wallets` table's ERD (SDS §4.3.3) carries no `created_at` column** — unlike `users` and `invitations`, which both have one. This is very likely an oversight rather than a deliberate omission, but correcting it is a domain-model change (CLAUDE.md's "changes the domain model or ERD" threshold), not something this story may decide on its own. No `created_at` is added; `WalletRead` therefore cannot report a creation timestamp, and no ordering guarantee exists for a future list story. Recorded, not silently patched — see `plan.md` A5.
- **No audit event is required for wallet creation.** Constitution LA-04 names invitations, activations, and logins as the events this codebase audits; it does not name wallet creation, and no AC or FR here asks for one. Extending LA-04 to a fourth event type would itself be a rule change beyond this story's scope.
- **Reading a created wallet back is out of scope.** This story is verified through what `POST /api/v1/wallets` itself returns and through direct inspection of the stored row — there is no `GET` endpoint yet (WM-US-02/03).

---

## WM-US-02: List Wallets

> **IDs in this section are local to WM-US-02.** `AC-01` below is not WM-US-01's `AC-01`; each
> story section numbers its own criteria, per `artifact-templates/spec-templates.md`. Only
> `TC-NN` in `test_cases.md` runs continuously across the epic (`CLAUDE.md` §1.1 rule 4).

### Source *(scope extraction — CLAUDE.md §1 scope rule)*

**SRS §6 Feature-03 — the three headers surrounding this story, quoted in full**
> #### US-03-01: Create a Wallet [MVP]
> *(complete Gherkin scenario — already quoted in this file's WM-US-01 section above)*
>
> #### US-03-02: View List of Wallets [MVP]
>
> #### US-03-03: Update a Wallet

The line `#### US-03-02: View List of Wallets [MVP]` is quoted in full — it **is** the entire SRS
entry for this story. No "As a/I want/So that" statement, no Gherkin scenario, nothing else. This is
not the "under-illustrated Gherkin" situation reasoned through for WM-US-01 A1/A2 (a scenario existed
there, just not exhaustive) — there is no scenario here to read economy-of-example into. `US-03-03`
immediately below it is equally bare, so this thinness is specific to these two stories, not a
transcription error isolated to this one.

**SDS §5.3.2 WM-US-02 (USER)**
> #### 5.3.2 WM-US-02: List Wallets (USER)
> * **Goal:** Display all wallets owned by the logged-in user.

One sentence — the entire technical baseline for this story.

**SDS §2.1 Domain Layer Traceability**
> | **Wallet** | `wallets` | `WalletModel` | `WalletRead`, `WalletCreate` |

**SDS §6.3 API Index**
> | **WM-API-02** | `GET` | `/api/v1/wallets` | List user wallets |

*(Observation, not acted on: SDS §6.5's own API → User Story Traceability table lists `WM-API-01`
against WM-US-01 but has no corresponding row for `WM-API-02`/WM-US-02, even though §6.3 above lists
it. A small pre-existing gap in `SDS.md` itself, left as-is — this dispatch's scope is limited to the
three files in `specs/003-wallet-management/` and does not extend to editing `SDS.md`.)*

**constitution.md API-06, PF-04, SEC-08**
> **API-06** List endpoints accept `page` and `page_size`; default 25, maximum 100. Responses carry
> a total count.
> **PF-04** List endpoints are always bounded (see API-06). No unbounded result set reaches a client.
> **SEC-08** Queries for user-owned data filter on the authenticated `user_id` at the repository
> layer (SDS §7.2, SRS NFR-06).

### Out of scope for this story

WM-US-01 (create a wallet) · WM-US-03 (view a single wallet) · WM-US-04 (update a wallet) ·
WM-US-05 (delete a wallet) · UM-US-04/05, DC-US-01/02 · Features 04–11 · SRS §6 Feature-10/11
placeholders.

Deliberately excluded even though adjacent: filtering, searching, or sorting the list by anything
other than the fixed, stable order this story defines (neither SRS nor SDS names any other); viewing
a single wallet's full detail or transaction history (WM-US-03); renaming, retyping, or archiving a
wallet (WM-US-04/05); and any transaction moving money into or out of a wallet (SRS §6 Feature-06,
Transaction Management).

### User Scenarios & Testing *(mandatory)*

As an **authenticated User**, I want to view the list of wallets I own, so that I can see every
account I track — cash, bank, or card — without opening each one individually.

**Acceptance Criteria**:

**AC-01: Successfully list every wallet the caller owns**
**Given** an authenticated User who owns one or more wallets, of different types and currencies,
**When** the User requests the list of wallets,
**Then** the system returns every wallet owned by that User, each carrying its identifier, owner,
name, type, currency, and balance, together with the total number of wallets that User owns.

**AC-02: Return an empty list for a User with no wallets yet**
**Given** an authenticated User who owns no wallets,
**When** the User requests the list,
**Then** the system returns an empty list of wallets together with a total of zero, not an error.

**AC-03: Deny access to unauthenticated callers**
**Given** a caller presenting no credentials, or credentials that are invalid or expired,
**When** the caller attempts to list wallets,
**Then** the system denies the request before evaluating any query parameter, returns nothing, and
returns an unauthenticated error.

**AC-04: Bound and paginate the result by default**
**Given** an authenticated User,
**When** the User requests the list without specifying a page or page size,
**Then** the system returns at most 25 of that User's wallets on the first page, together with the
total number of wallets that User owns.

**AC-05: Accept an explicit page and page size within range**
**Given** an authenticated User,
**When** the User requests a specific page together with a page size up to the maximum of 100,
**Then** the system returns that page of the User's own wallets and the same accurate total.

**AC-06: Reject a page or page size outside the allowed range**
**Given** an authenticated User,
**When** the requested page or page size is zero, negative, otherwise not a positive integer, or a
page size greater than 100,
**Then** the system rejects the request with a validation error identifying the offending parameter,
and returns no wallets.

**AC-07: A User only ever sees their own wallets**
**Given** at least two Users, each owning one or more wallets,
**When** one of them requests the list,
**Then** the response's wallets are exactly the ones owned by the requesting User — none belonging to
any other User appears — and the reported total counts only the requesting User's own wallets, never
every wallet in the system.

**AC-08: Return the list in a stable, deterministic order**
**Given** an authenticated User who owns two or more wallets, with nothing created, changed, or
removed in between,
**When** the User requests the same page more than once, or requests adjacent pages of one paging
sequence,
**Then** the system returns the same wallets in the same relative order every time, consistently
across those adjacent pages.

**AC-09: Reuse the documented per-wallet fields, wrapped in a paginated envelope**
**Given** an authenticated User requests the list,
**When** the system returns the result,
**Then** each entry carries exactly the fields a created wallet already carries — identifier, owner
identifier, name, type, currency, and balance — no more, no other User's data, and no field this
story invents — and the overall response additionally carries the total count, the page number, and
the page size.

### Edge Cases

**EC-01**: **A page number beyond the last available page** — returns an empty list of wallets
together with the accurate, caller-scoped total, not a not-found error.

**EC-02**: **Page size at the exact maximum** — a page size of exactly 100 is accepted; 101 is
rejected under AC-06. The cap is a ceiling, not a target.

**EC-03**: **More wallets than fit on one page** — paging through every page with a fixed page size
returns every one of the caller's own wallets exactly once, with no duplicate and no gap, in the same
stable order AC-08 establishes.

**EC-04**: **A caller whose role is ADMIN, who also owns wallets** — sees, through this endpoint,
only the wallets that caller owns. Nothing about this endpoint grants an ADMIN visibility into
another User's wallets; unlike UM-US-03, which is deliberately ADMIN-wide, this route has no
ADMIN-wide sense at all — it is scoped to the caller regardless of role.

### Requirements *(mandatory)*

#### Functional Requirements

- **FR-01**: The system must **allow** an authenticated User of any role to retrieve the list of
  wallets they own (SDS §5.3.2; mirrors WM-US-01 FR-01's "any role" treatment).
- **FR-02**: The system must **include**, for every listed wallet, its identifier, owner identifier,
  name, type, currency, and balance — the same fields WM-US-01 already defined for a single created
  wallet (SDS §2.1, §6.2.1; WM-US-01 AC-11; constitution PF-03).
- **FR-03**: The system must **deny** the operation to unauthenticated callers, evaluating
  credentials before any query parameter (constitution API-08; mirrors WM-US-01 FR-02, UM-US-03
  FR-04).
- **FR-04**: The system must **accept** `page` and `page_size` query parameters, defaulting to page 1
  and page size 25 when omitted (constitution API-06).
- **FR-05**: The system must **reject** a `page` or `page_size` value that is not a positive integer,
  or a `page_size` greater than 100, with a validation error (constitution API-06, PF-04).
- **FR-06**: The system must **return**, alongside every page, the total number of wallets the caller
  owns (constitution API-06).
- **FR-07**: The system must **filter** every wallet query this endpoint issues — both the bounded
  page of items and the total count — to only the wallets owned by the authenticated caller
  (constitution SEC-08; plan.md A3).
- **FR-08**: The system must **order** the returned wallets by a stable, deterministic key,
  consistently across pages of the same request pattern (plan.md A1).
- **FR-09**: The system must **apply no filter** based on a wallet's type, currency, or balance —
  every wallet the caller owns appears somewhere in the paginated result (mirrors UM-US-03 FR-09's
  "no status filter," applied here to the absence of any type-based filter).
- **FR-10**: The system must **never include**, in either the returned wallets or the reported total,
  any wallet owned by a User other than the caller, regardless of the caller's role (constitution
  SEC-08; AC-07, EC-04).

#### Business Rules

- **BR-01**: Only the wallets owned by the authenticated caller are ever returned by this endpoint;
  no role — including ADMIN — grants visibility into another User's wallets through this route (SDS
  §5.3.2 "(USER)"; constitution SEC-08; EC-04).
- **BR-02**: A page never carries more than 100 wallets; the default when unspecified is 25 (FR-04,
  FR-05; mirrors UM-US-03 BR-03).
- **BR-03**: Wallets are ordered by a stable key, consistently across pages of the same request
  pattern; this story establishes no chronological ordering guarantee, because no creation timestamp
  exists on `Wallet` (FR-08; plan.md A1; see Assumptions & Dependencies).
- **BR-04**: The reported total always equals the count of wallets owned by the caller, never the
  system-wide wallet count (FR-06, FR-07, FR-10).
- **BR-05**: The endpoint applies no content-based filter — every wallet the caller owns is subject
  only to pagination, never to a filter on type, currency, or balance (FR-09).

#### Key Entities

- **Wallet**: A named store of liquid money a User holds — cash, a bank account, a credit line (SRS
  §1.5). Carries `id`, `user_id`, `name`, `type`, `currency`, and `balance` (SDS §2.2, §4.3.3;
  WM-US-01). This story only reads wallets WM-US-01 already created — it creates, renames, and
  deletes none.
- **User**: Reused from Feature-01/Feature-02 with no new column. The authenticated caller's own
  identifier is the only scope this story ever queries by (constitution SEC-08).

### Success Criteria *(mandatory)*

- **SC-01**: An authenticated User can retrieve every wallet they own, carrying the same per-wallet
  fields WM-US-01 already established, in one call.
- **SC-02**: No request to this endpoint can return an unbounded number of rows.
- **SC-03**: No User can see another User's wallet, or another User's wallet count, through this
  endpoint, regardless of role.
- **SC-04**: A User can page through their entire wallet set with an accurate total and no duplicated
  or skipped wallet.
- **SC-05**: A User with no wallets yet receives an empty list and a zero total, never an error.

### Assumptions & Dependencies

- **Login (SS-US-01) and WM-US-01 (Create a Wallet) are already implemented** — there is nothing to
  list otherwise, and both dependencies are real, not merely designed against, mirroring how UM-US-03
  depended on UM-US-01 (`specs/001-user-onboarding/spec.md` UM-US-03 Assumptions).

- **`SRS.md` §6 US-03-02 carries no Gherkin at all** — only the bare header. `SDS.md` §5.3.2 supplies
  exactly one sentence. Every AC above beyond the bare "list the caller's own wallets" goal
  (pagination, ordering, the empty case, the envelope shape) is derived from constitution
  API-06/PF-04/SEC-08 and from the UM-US-03 precedent, not from either reference document directly.
  Recorded once, here, rather than against each individual AC, because the situation is uniform
  across nearly all of them — this is the expected condition for this story, not a source
  contradiction, so no `[NEEDS RULING]` follows from it.

- **The ordering decision.** `WalletModel` has no `created_at` column — SDS §4.3.3's ERD lists
  `wallets` with exactly `id`, `user_id`, `name`, `type`, `balance`, `currency`, and WM-US-01
  `plan.md` A5 already flagged the gap and deliberately left it unfixed, reasoning that adding a
  column the ERD does not list is a domain-model change this codebase requires stopping to ask about,
  not something a single story may decide unilaterally (`CLAUDE.md` §1, "contradicts the domain model
  (SDS §2) or ERD (§4.3.3)"). That reasoning still applies here. Unlike UM-US-03, which could reach
  for `created_at DESC` because `users.created_at` already existed for reasons unrelated to that story
  (audit trail, uniqueness support) and because SRS's own Gherkin for that story named "creation date"
  as a column to display — this story has neither a column nor a source document naming any order at
  all. Adding `created_at` now, solely to give this story a sort key, would still be exactly the ERD
  change `CLAUDE.md` reserves for the user's own decision, and no AC in either reference document asks
  for chronological order specifically — only *a* list, full stop. This story therefore orders by the
  one key every wallet already has, unconditionally, without any schema change: the primary key `id`
  (`ORDER BY id ASC` — ascending only because the two directions are otherwise equally arbitrary over
  random UUIDs). This satisfies everything pagination correctness actually requires — a total,
  stable, gap-free, duplicate-free order across pages (AC-08, EC-03) — at the acknowledged cost of
  carrying no chronological or otherwise human-meaningful signal: two wallets created seconds apart in
  either order will not reliably appear "newest first" or "oldest first." That limitation is accepted
  and recorded, not silently shipped (`plan.md` A1; `test_cases.md` QF-06). If a future story needs
  creation-order (or any other explicit sort), adding `created_at` — or a narrower, purpose-built
  ordering column — is that story's own decision to raise, exactly as WM-US-01 `plan.md` A5 already
  anticipated for "a future list story."

- **Pagination combined with ownership filtering, for the first time in this codebase.** UM-US-03 is
  the only precedent for `page`/`page_size` (constitution API-06), but it lists every account
  system-wide — an ADMIN-only, unscoped query. WM-US-01 is the only precedent for filtering by owner
  (constitution SEC-08), but only as a single-row lookup (`wallet_repo.get_owned_by_id`) with nothing
  to paginate. This story combines both for the first time: the bounded page of items *and* the total
  count must each carry the same `user_id` predicate, or the reported total would silently mean
  something different from what the items show (`plan.md` A3; `test_cases.md` QF-05 records the
  specific risk of copying UM-US-03's `list_users` shape without also copying WM-US-01's ownership
  predicate onto the count query).

- **The response envelope.** `SDS.md` §6.2.1's DTO registry never enumerated `WalletRead`'s fields
  directly (only `WalletCreate`'s); the six-field shape in use today (`id`, `user_id`, `name`, `type`,
  `currency`, `balance`) was itself settled during WM-US-01's own Design step, per §2.1's traceability
  row naming `WalletRead` as Wallet's read DTO. This story reuses that DTO **unchanged** as the
  per-item shape — no new or missing field — and wraps it in a new envelope, `WalletListRead {
  items, total, page, page_size }`, mirroring `UserListRead` exactly (UM-US-03 `plan.md` A6). Neither
  envelope is in SDS's registry; both exist to satisfy constitution API-06, which predates either
  being made concrete.

- **No wallet `type`/`currency` vocabulary question to re-litigate.** WM-US-01 already settled that
  `type` and `currency` carry no closed enum (its own `plan.md` A1, A2). This story only reads
  existing rows through fields already validated at creation time; it introduces no new validation
  surface for either.

- **Reading a single wallet's full detail, and any transaction history, is out of scope.** This story
  is verified through the list endpoint's own envelope; there is no `GET /wallets/{id}` yet
  (WM-US-03).

---

## WM-US-04: Update a Wallet

> **IDs in this section are local to WM-US-04.** `AC-01` below is not WM-US-01's or WM-US-02's own
> `AC-01`; each story section numbers its own criteria, per `artifact-templates/spec-templates.md` and
> this codebase's own WM-US-02/BM-US-04 precedent. Only `TC-NN` (and `QF-NN`) in `test_cases.md` run
> continuously across the epic (`CLAUDE.md` §1.1 rule 4).

### Source *(scope extraction — CLAUDE.md §1 scope rule)*

**SRS §6 Feature-03 — searched in full; confirmed bare**
> #### US-03-03: Update a Wallet

The entire SRS entry for this story is that one header line — no "As a/I want/So that" statement, no
`[MVP]` tag, no Gherkin scenario. This is the identical situation WM-US-02's own Source section already
documented for `US-03-02` immediately above it in the SRS; this story's own header is equally bare,
confirming the thinness is a property of both of these two stories, not a transcription accident
isolated to one.

**SDS §5.3.4 WM-US-04: Update a Wallet (USER)**
> **Goal:** Rename or update configuration for a wallet.

One sentence — the same thinness WM-US-02's own SDS goal carried, and the same thinness BM-US-02/03/04
each found in their own corner of Budget Management.

**SDS §2.1 Domain Layer Traceability**
> | **Wallet** | `wallets` | `WalletModel` | `WalletRead`, `WalletCreate` |

**SDS §6.3 API Index** *(checked directly, not assumed)*
> Lists exactly `WM-API-01` (`POST /api/v1/wallets`) and `WM-API-02` (`GET /api/v1/wallets`) — no
> `WM-API-03`/`WM-API-04` row exists at all. The identical "confirmed stale, not a contract to match"
> situation BM-US-04's own Source section found in its own epic's API index; reconciling the whole
> table is not this story's job.

**constitution.md API-03, API-05, SEC-08, VL-06**
> API-03: HTTP status codes: `200` read/update · `201` creation · ... — an update response is `200`, not
> `201`.
> API-05: No generic `updateStatus` endpoint. Each business state transition gets its own explicit
> endpoint (`/users/activate`, not `PATCH /users/{id}` with a status field).
> SEC-08: Queries for user-owned data filter on the authenticated `user_id` at the repository layer.
> VL-06: Referenced entities are verified to exist and be active before use — `404` if absent, `409` if
> present but in the wrong state.

**`specs/005-budget-management/spec.md` BM-US-04 "Acceptance Criteria"** *(this story's own directly-reused
precedent, cited the same way BM-US-02 cited CM-US-02's)*
> AC-03/AC-04: "the system changes nothing and returns the same not-found outcome ... the response gives
> no indication of which of the two happened."

**`specs/005-budget-management/plan.md` BM-US-04 A1** *(this story's own directly-reused scoping
precedent)*
> "Only `amount_limit` is updatable ... Accepting a new `wallet_id`/`category_id`/`period` would reopen
> BM-US-01 BR-05's uniqueness constraint in a materially harder form ... None of that is asked for by any
> source ... Same 'fewest invented rules' discipline as BM-US-01 A2."

**`backend/app/schemas/transaction.py` `TransactionRead`/`TransactionModel`** *(confirmed directly, not
assumed)*
> Exactly seven fields: `id`, `wallet_id`, `category_id`, `amount`, `type`, `timestamp`, `note` — **no
> currency field of any kind.** Every transaction's amount is interpreted entirely through whichever
> currency its own `wallet_id` currently resolves to.

**`backend/app/repositories/wallet_repo.py` `get_owned_by_id()`, `decrement_balance()`,
`increment_balance()`** *(confirmed directly)*
> `get_owned_by_id` already exists, built for BM-US-01's own referenced-wallet check (SEC-08-scoped,
> collapsing not-found and not-owned to the identical `None`). `decrement_balance`/`increment_balance`
> are the **only** two functions in this codebase that ever change a stored wallet's `balance`, and both
> are called exclusively from Transaction creation/deletion (TM-US-01) — never from any Wallet
> Management story.

### Out of scope for this story

WM-US-01 (create a wallet) · WM-US-02 (list wallets) · WM-US-03 (view a single wallet — still
unspecified; this story does not depend on it, see *Assumptions & Dependencies*) · WM-US-05 (delete a
wallet) · UM-US-04/05, DC-US-01/02 · Features 04–11 · SRS §6 Feature-10/11 placeholders.

Deliberately excluded even though adjacent: changing a wallet's `currency` or its `balance` (reasoned
through explicitly below, not merely declined — see *Assumptions & Dependencies*); any transaction moving
money into or out of a wallet (Feature-06, Transaction Management — this story touches no transaction
data and reads none); and any mobile/UI screen, for the same reason WM-US-01/02 and every Budget
Management story gave their own endpoints — no SRS UXR names one this round, and `mobile/` stays a
fixture-driven prototype scoped to UM-US-01 only (`CLAUDE.md` §5).

### User Scenarios & Testing *(mandatory)*

As an **authenticated User**, I want to rename one of my own wallets, change its type, or both, so that I
can keep my wallet labels and organization accurate as my accounts or habits change, without losing the
wallet's balance or currency in the process.

**Acceptance Criteria**:

**AC-01: Successfully update a wallet's name, type, or both**
**Given** an authenticated User who owns a wallet,
**When** the User submits a new name, a new type, or both, each within the system's supported bounds,
**Then** the system updates exactly the submitted field(s), leaves that wallet's currency and balance
unchanged, and returns a success result carrying the wallet's identifier, owner, name, type, currency,
and balance.

**AC-02: Deny access to unauthenticated callers**
**Given** a caller presenting no credentials, or credentials that are invalid or expired,
**When** the caller attempts to update a wallet,
**Then** the system denies the request before evaluating anything else, changes nothing, and returns an
unauthenticated error.

**AC-03: Reject an update to a wallet that does not exist**
**Given** an authenticated User,
**When** the submitted wallet reference matches no wallet at all,
**Then** the system changes nothing and returns a not-found error.

**AC-04: Reject an update to a wallet owned by a different User**
**Given** an authenticated User,
**When** the submitted wallet reference matches a wallet owned by a different User,
**Then** the system changes nothing and returns the same not-found outcome AC-03 describes — the
response gives no indication of which of the two happened.

**AC-05: Reject a submission naming neither a new name nor a new type**
**Given** an authenticated User who owns a wallet,
**When** the submission carries neither a name nor a type to change,
**Then** the system changes nothing and returns a validation error, rather than treating the request as
a successful no-op.

**AC-06: Reject a blank or whitespace-only wallet name, when a name is submitted**
**Given** an authenticated User who owns a wallet,
**When** the submitted name is present but is empty or only whitespace,
**Then** the system changes nothing and returns a validation error identifying the name field.

**AC-07: Reject a wallet name exceeding the maximum supported length, when a name is submitted**
**Given** an authenticated User who owns a wallet,
**When** the submitted name is present and longer than the system supports,
**Then** the system changes nothing and returns a validation error rather than truncating the name.

**AC-08: Reject an empty wallet type, when a type is submitted**
**Given** an authenticated User who owns a wallet,
**When** the submitted type is present but empty,
**Then** the system changes nothing and returns a validation error identifying the type field.

**AC-09: Reject a wallet type exceeding the maximum supported length, when a type is submitted**
**Given** an authenticated User who owns a wallet,
**When** the submitted type is present and longer than the system supports,
**Then** the system changes nothing and returns a validation error rather than truncating the type.

**AC-10: A successful update changes only the submitted field(s) — currency and balance never change**
**Given** an authenticated User who successfully updates one of their own wallets,
**When** the update completes,
**Then** that wallet's currency and balance are identical to their values immediately before the request,
and any field not named in the submission is likewise identical to its value immediately before the
request.

**AC-11: Return exactly the documented wallet fields**
**Given** an authenticated User successfully updates a wallet,
**When** the system returns the success result,
**Then** the result carries exactly the wallet's identifier, owner identifier, name, type, currency, and
balance — no other field, and no data belonging to any other User.

### Edge Cases

**EC-01**: **Wallet name with surrounding whitespace, when submitted** — `"  Main Checking  "` is stored
trimmed, as `"Main Checking"`, the identical rule WM-US-01 EC-04 already established for creation.

**EC-02**: **A wallet type outside the Gherkin's and SDS's own examples, when submitted** — a value such
as `"Piggy Bank"` or `"CREDIT_CARD"`, meeting only the length bound, is accepted on update exactly as it
already is on creation (WM-US-01 EC-05, `plan.md` A1); this story introduces no closed vocabulary where
none existed before.

**EC-03**: **A wallet reference that is not even a well-formed identifier** — a value such as
`"not-a-real-id"` is refused with the same not-found outcome as a well-formed but non-existent reference
(AC-03). No separate malformed-identifier error exists; a reference either resolves to a wallet the
caller owns, or it does not, regardless of its shape.

**EC-04**: **Only a new name is submitted** — the wallet's type, currency, and balance remain exactly
what they were before the request.

**EC-05**: **Only a new type is submitted** — the wallet's name, currency, and balance remain exactly
what they were before the request.

**EC-06**: **Both a new name and a new type are submitted in the same request** — both change together;
currency and balance remain unchanged.

**EC-07**: **A currency or initial-balance-shaped value submitted alongside the name or type** — the
request body additionally carries a `currency`- or `initial_balance`/`balance`-shaped value; the updated
wallet's currency and balance remain exactly what they were before the request, and the response carries
no echo of the submitted value. This story's contract has no field for a caller to populate either (see
*Assumptions & Dependencies*), so the extra key is silently ignored, never honoured — the identical
treatment BM-US-04 EC-06 already gave an out-of-contract `wallet_id`/`category_id`/`period` value.

**EC-08**: **A caller who owns one or more wallets of their own, attempting to update a different User's
wallet** — refused with the identical outcome AC-04 describes; owning some wallet never entitles a caller
to act on another User's wallet.

**EC-09**: **More than one validation failure in a single submission** — when the submitted name is blank
and the submitted type is over-long in the same request, both problems are reported together in one
response, not just the first one encountered (the identical grouping rule WM-US-01 EC-06 already
established for creation).

### Requirements *(mandatory)*

#### Functional Requirements

- **FR-01**: The system must **allow** an authenticated User of any role to submit a new name, a new
  type, or both, identifying the wallet to update by its own identifier, in order to update that wallet
  (SDS §5.3.4).
- **FR-02**: The system must **deny** the operation to unauthenticated callers, evaluating credentials
  before anything else (constitution API-08; mirrors WM-US-01 FR-02).
- **FR-03**: The system must **require** the submitted wallet reference to resolve to a wallet owned by
  the authenticated caller, and **refuse** the request with an identical outcome whether no such wallet
  exists at all or it exists and is owned by a different User (AC-03, AC-04, EC-03, EC-08; constitution
  SEC-08, VL-06).
- **FR-04**: The system must **require** at least one of a new name or a new type to be present in the
  submission, and **reject** — rather than silently accept as a no-op — a submission naming neither
  (AC-05).
- **FR-05**: The system must, **when a name is submitted**, require it non-empty after trimming
  surrounding whitespace, and **reject** — rather than truncate — a name longer than the system supports
  (AC-06, AC-07, EC-01; the identical bound WM-US-01 FR-03 already established).
- **FR-06**: The system must, **when a type is submitted**, require it non-empty, and **reject** —
  rather than truncate — a type longer than the system supports; the system enforces no closed list of
  valid type values (AC-08, AC-09, EC-02; the identical bound WM-US-01 FR-04 already established,
  `plan.md` A1).
- **FR-07**: The system must **leave** the wallet's currency and balance unchanged by this operation, and
  **ignore** any currency- or balance-shaped value submitted in the request body — this story's contract
  declares no field capable of changing either (AC-10, EC-07).
- **FR-08**: The system must **return**, on success, exactly the wallet's identifier, owner identifier,
  name, type, currency, and balance (AC-11).
- **FR-09**: The system must **group** every validation failure from one submission into a single
  response rather than reporting only the first (EC-09; constitution VL-02).
- **FR-10**: The system must **apply only the submitted field(s)**; a field not named in the submission
  keeps its existing stored value exactly, with no side effect on any other field (EC-04, EC-05).

#### Business Rules

- **BR-01**: A wallet's name and type are the only fields mutable through this story's contract; its
  currency and balance are immutable through this operation (FR-07; see *Assumptions & Dependencies* for
  why both are excluded).
- **BR-02**: A wallet's ownership for this operation is established the same way WM-US-01 BR-01 already
  established it at creation — directly by the wallet's own identifier, scoped to the authenticated
  caller. A wallet reference that does not resolve to a row the caller owns is refused identically
  whether no such row exists at all or it exists and belongs to a different User (FR-03).
- **BR-03**: Name and type are validated by the identical rules WM-US-01 BR-04 already established for
  creation — a length bound for name (trimmed, non-empty, ≤100 characters) and for type (non-empty,
  ≤50 characters) — and against no closed vocabulary of business-meaningful values for type (FR-05,
  FR-06).
- **BR-04**: A submission naming neither a new name nor a new type is refused as invalid; this endpoint
  never treats the absence of both as a successful, no-op update (FR-04).

#### Key Entities

- **Wallet**: A named store of liquid money a User holds (SRS §1.5). Carries `id`, `user_id`, `name`,
  `type`, `currency`, and `balance` (SDS §2.2, §4.3.3; WM-US-01). This is the first story to **write** to
  an existing Wallet row rather than only creating or reading one — and, unlike BM-US-04's analogous
  first write to an existing Budget, only two of this entity's four non-identifier fields (`name`,
  `type`) are reachable through this story's contract; `currency` and `balance` stay exactly as WM-US-01
  set them, or as Transaction activity (Feature-06) has since changed `balance`.
- **User**: Reused from Feature-01/Feature-02 with no new column. The authenticated caller's own
  ownership of the wallet being updated is the only scope this story ever checks (constitution SEC-08).

### Success Criteria *(mandatory)*

- **SC-01**: An authenticated User can update the name, the type, or both, of one of their own wallets in
  one call, and the response reflects exactly the new value(s).
- **SC-02**: No wallet can be updated without an authenticated caller.
- **SC-03**: A wallet can never be updated by a User who does not own it — whether because the reference
  does not exist at all, or because it belongs to someone else, the request is refused identically either
  way.
- **SC-04**: A wallet's currency and balance never change as a result of this operation, no matter what a
  caller submits alongside the name or type.
- **SC-05**: A submission naming neither a new name nor a new type is always rejected, never silently
  accepted as a no-op success.

### Assumptions & Dependencies

- **Login (SS-US-01) and Create a Wallet (WM-US-01) are already implemented.** Every acceptance criterion
  here presupposes at least one wallet already on record, owned by the authenticated caller — the
  identical dependency shape BM-US-04 already declared on BM-US-01.

- **List Wallets (WM-US-02) is also already implemented, but is not a dependency of this story** — it is
  useful for *observing* the result of an update (and is used that way in this story's own verification),
  but no acceptance criterion here requires it. **View a Wallet (WM-US-03) remains unspecified** — unlike
  BM-US-04, which could cite three already-implemented predecessor stories in the same epic, this story's
  own epic has no single-wallet read endpoint yet. This is not a blocker: this story's own `PATCH`
  response already returns the updated wallet's full documented shape (AC-11), so nothing here needs a
  `GET /wallets/{id}` to verify against. Raised here rather than silently assumed, since every other
  "Update" story so far in this codebase (BM-US-04) could point to a complete chain of prior reads first.

- **Only `name` and `type` are updatable through this story's contract — `currency` and `balance` (the
  stored column `initial_balance` maps to at creation, WM-US-01 FR-09) are not, reasoned through
  explicitly rather than assumed, mirroring the discipline BM-US-04 used for its own three excluded
  fields:**

  - **`balance` is excluded because it is not an independent configuration value at all — it is a derived
    ledger total.** `backend/app/repositories/wallet_repo.py` confirms the **only** two functions in this
    codebase that ever change a stored wallet's `balance` are `decrement_balance()` and
    `increment_balance()`, both called exclusively from Transaction creation/deletion (TM-US-01) — never
    from any Wallet Management story, including this one's own direct predecessor WM-US-01, which merely
    *sets* the starting value once. Exposing `balance` as a directly-settable field here would let a
    caller silently move their own ledger to any value with no corresponding Transaction row — the
    system's own record of *why* the balance is what it is would then disagree with the balance itself,
    with nothing in the data model able to explain the discrepancy. SDS §5.3.4's own goal text — "Rename
    or update **configuration**" — supports this reading directly: a running balance is a *result*, not a
    piece of configuration, in a way `name` and `type` plainly are.

  - **`currency` is the harder case, and is excluded for a stronger reason than any field BM-US-04 had to
    exclude.** `backend/app/schemas/transaction.py` confirms `TransactionRead`/`TransactionModel` carry
    **no currency field of their own at all** — every transaction's `amount` is interpreted entirely
    through whichever currency its own `wallet_id` currently resolves to, at read time, with nothing
    anchoring a historical transaction to the currency that was in effect when it was recorded. Changing
    a wallet's `currency` after transactions already exist against it would not just change a label the
    way renaming a wallet does — it would silently re-denominate every one of that wallet's past
    transaction amounts, because there is no second, independent place any past amount's original
    currency is recorded. BM-US-04's own excluded fields (`wallet_id`, `category_id`, `period`) are
    foreign-key/identity fields whose exclusion prevents a *re-targeting* problem (which budget a
    transaction's cap applies to); `currency` here is worse in kind, not just degree — it would silently
    change the *meaning* of monetary values already persisted and already surfaced in prior responses,
    which reads as a data-integrity concern adjacent to SRS NFR-05 (Data Integrity & Monetary Precision)
    even though NFR-05's own text is about storage precision, not unit-of-account stability. Nothing in
    SRS §6 Feature-03, SDS §5.3.4's one-sentence goal, or SDS §2.2's domain-object description asks for
    `currency` to be editable, and "rename or update configuration" reads at least as naturally as
    "`name`/`type` only" as it does "every non-balance field" — so the narrower reading is taken, matching
    BM-US-04 A1's own "prefer the interpretation that invents the fewest additional rules" discipline.
    **No `[NEEDS RULING]` follows from this**, because this is a scope decision filling a genuine gap left
    by a one-sentence goal, not a resolution of a stated disagreement between SRS and SDS, or a change to
    a published contract or the domain model/ERD — the same basis BM-US-04 A1 itself used to settle an
    analogous question without escalating. If a future need for currency migration emerges (e.g.
    correcting a data-entry mistake), it is that future story's own decision to raise, with its own
    re-conversion or re-anchoring design — not something this story backs into by leaving the field open.

  - **No uniqueness re-validation risk exists for `name`/`type` the way BM-US-04 A1 had to reason through
    for Budget's triple key.** WM-US-01 BR-05 already established that wallet names carry no uniqueness
    constraint at all, per-User or system-wide (EC-07, `plan.md` A6) — so, unlike Budget's
    `(wallet_id, category_id, period)` uniqueness constraint, there is no existing constraint this
    story's updates could ever collide with. This endpoint's error catalog is `200`/`401`/`404`/`422`
    only, with no `409` of any kind, for a simpler reason than BM-US-04's own "structurally unreachable"
    `409` story: there was never a uniqueness rule here to reopen in the first place.

- **Partial-update semantics: both `name` and `type` are optional on the request, and either, or both, may
  be submitted — the first multi-field optional update in this codebase.** BM-US-04's own `BudgetUpdate`
  had exactly one field, so "is the field optional" and "is at least one field required" were the
  identical question there; here they are not. Both fields are modelled as optional (`None` means "leave
  this field's stored value unchanged," whether the key was omitted from the JSON body entirely or
  submitted explicitly as `null` — no distinct "clear the field" meaning exists for either, since both are
  non-nullable business fields with a mandatory non-empty value at the model layer, and inventing a
  clear-to-null behaviour neither field can actually hold would itself be a new rule no source asks for).
  A submission naming neither is still refused (AC-05, BR-04) — generalising BM-US-04 A6's own "a
  zero-field update is not a no-op `200`" stance from its one required field to this story's two optional
  ones, rather than silently allowing an empty `{}` body to return `200` with nothing changed.

- **`type`'s validation on update intentionally mirrors `WalletCreate.type`'s exact, already-shipped
  shape — length bound only, no trim/whitespace-rejection — rather than this story's own AC-08 inventing
  a stricter rule.** `backend/app/schemas/wallet.py` shows `WalletCreate.name` trims and rejects an
  empty-after-trim value via an explicit `field_validator`, but `WalletCreate.type` carries only
  `Field(min_length=1, max_length=50)`, with no equivalent whitespace check — so a single-space `type`
  value already passes validation uncaught at creation time, even though WM-US-01 spec.md's own AC-05
  wording says type must be rejected when "absent, empty, or only whitespace." That gap belongs to
  WM-US-01, which is already implemented and verified and out of this story's scope to correct; inventing
  stricter, asymmetric validation for `type` on update alone — rejecting on this endpoint what creation
  itself still accepts — would be a new, undiscussed inconsistency, not a fix. This story's own AC-08 is
  therefore worded to match what is actually enforced ("empty," not "blank or only whitespace"), unlike
  AC-06's name wording, which can honestly claim whitespace-only rejection because `name`'s existing
  validator already guarantees it. Recorded in full in `plan.md` A10 and `test_cases.md` QF-11.
