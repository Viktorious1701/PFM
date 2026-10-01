# Feature Specification: Budget Management (BM)

> **Feature:** SRS §6 Feature-05 · SDS §5.5 (BM)
> **Spec:** [spec.md](spec.md)
> **Stories in this file:** BM-US-01 *(implemented, verified — 245 passed, 99% coverage)* · BM-US-02 *(specified)*

---

## Source *(scope extraction — CLAUDE.md §1 scope rule)*

Only the sections below entered the working context for BM-US-01.

**SRS §6 Feature-05 · US-05-01 — Create a Budget for a Wallet [MVP]**
> * **As an** Authenticated User
> * **I want to** set a monthly spending cap on a category
> * **So that** I am alerted before overspending.
>
> ```gherkin
> Feature: Create Budget
>
>   Scenario: Set a monthly category budget cap
>     Given the User is logged in
>     And the User has an existing category "Dining Out"
>     When the User sets a monthly limit of 200.00 for "Dining Out"
>     And the User clicks "Save Budget"
>     Then the System creates an active budget monitoring spending against 200.00
> ```

**SRS §1.5 Conceptual Domain Model**
> **Budget** — A spending limit a User sets for one Category within one Wallet, over a monthly period, that Transactions are measured against (FR-05).
>
> | Relationship | Cardinality | Meaning |
> | Wallet scoped_to Budget | one Wallet → many Budgets | A spending limit is set against one Wallet at a time (FR-05) |
> | Category applies_to Budget | one Category → many Budgets | A Budget's limit applies to spending in one Category (FR-05) |

**SRS §2 FR-05 — Budget Tracking & Overspending Alerts**
> The System shall allow Users to define spending caps (`Budget`) per Category and Wallet for a monthly timeframe. The System shall track spending against this limit and trigger visual warnings when thresholds (75%, 100%) are reached.

**SRS §3 NFR-05 — Data Integrity & Monetary Precision**
> All monetary attributes and asset valuations must be stored using arbitrary-precision decimal representations (`DECIMAL(15,2)`). Balance updates must execute inside ACID-compliant database transaction blocks.

**SDS §5.5.1 BM-US-01: Create a Budget for a Wallet (USER)**
> * **Goal:** Assign a spending limit to a category and wallet over a monthly period.

**SDS §2.1 Domain Layer Traceability**
> | **Budget** | `budgets` | `BudgetModel` | `BudgetRead`, `BudgetCreate` |

Neither DTO's shape is defined anywhere else in the SDS — §6.2.1's DTO Registry has no `Budget` entry at all (unlike `WalletCreate`, which is spelled out there). This story designs `BudgetCreate`/`BudgetRead` from scratch, the same situation WM-US-01 and CM-US-01 were each in for their own first DTO.

**SDS §2.2 Domain Object**
> **Budget:** Spending constraint attached to a wallet and category (`id`, `wallet_id`, `category_id`, `amount_limit`, `period`).

**SDS §4.3.3 Data Design — `BUDGETS` ERD**
> ```
> WALLETS ||--o{ BUDGETS : monitors
> CATEGORIES ||--o{ BUDGETS : targets
>
> BUDGETS {
>     uuid id PK
>     uuid wallet_id FK
>     uuid category_id FK
>     decimal amount_limit
>     date period
> }
> ```
> No `user_id` column — unlike `WALLETS` and `CATEGORIES`, which both carry one directly.

**constitution.md VL-07**
> Monetary values use `Decimal` with `DECIMAL(15,2)` precision (SRS NFR-05). Never float.

**constitution.md SEC-08**
> Queries for user-owned data filter on the authenticated `user_id` at the repository layer (SDS §7.2, SRS NFR-06).

**constitution.md VL-06**
> Referenced entities are verified to exist and be active before use — `404` if absent, `409` if present but in the wrong state.

**constitution.md VL-05**
> Uniqueness is enforced at two levels: a service-layer check returning `409` with a specific code, and a database unique index as the backstop.

### Out of scope for this story

BM-US-02 (list budgets) · BM-US-03 (view budget status & alerts — the 75%/100% threshold warnings) · BM-US-04 (update a budget) · BM-US-05 (delete a budget) · WM-US-02..05 · CM-US-02..05 · UM-US-04/05, DC-US-01/02 · Features 06–11 · SRS §6 Feature-10/11 placeholders.

Deliberately excluded from *this* story even though adjacent: computing or displaying spending progress against a budget's limit, and the 75%/100% threshold alerts FR-05's second sentence describes (BM-US-03 — this story only creates the budget row; it never reads a Transaction and never computes a percentage). The SDS §2.4.3 Budget Monitoring State machine's `DRAFT`/`NORMAL`/`WARNING`/`EXCEEDED`/`ARCHIVED` transitions are also out of scope — see *Assumptions & Dependencies*. Also excluded: reading a budget back through any `GET` endpoint (BM-US-02/03 — this story is verifiable only through what `POST /api/v1/budgets` itself returns and through direct inspection of the stored row), and updating or deleting a budget (BM-US-04/05).

---

## BM-US-01: Create a Budget

### User Scenarios & Testing *(mandatory)*

As an **authenticated User**, I want to set a monthly spending limit against one of my own wallets and one of my own categories, so that I am alerted before overspending.

**Acceptance Criteria**:

**AC-01: Successfully create a budget with all mandatory inputs**
**Given** an authenticated User who owns a wallet and owns a category,
**When** the User submits that wallet, that category, and a positive amount limit within the system's supported precision,
**Then** the system creates a budget scoped to that wallet and that category, with its period set to the current calendar month, and returns a success result carrying the budget's identifier, wallet, category, amount limit, and period.

**AC-02: Deny access to unauthenticated callers**
**Given** a caller presenting no credentials, or credentials that are invalid or expired,
**When** the caller attempts to create a budget,
**Then** the system denies the request before evaluating the payload, creates nothing, and returns an unauthenticated error.

**AC-03: Reject a missing wallet reference**
**Given** an authenticated User,
**When** the submitted wallet reference is absent from the request,
**Then** the system creates nothing and returns a validation error identifying the wallet field.

**AC-04: Reject a wallet reference that does not resolve to the caller's own wallet**
**Given** an authenticated User,
**When** the submitted wallet reference matches no wallet at all, or matches a wallet owned by a different User,
**Then** the system creates nothing and returns the same not-found outcome in either case — the response gives no indication of which of the two happened.

**AC-05: Reject a missing category reference**
**Given** an authenticated User,
**When** the submitted category reference is absent from the request,
**Then** the system creates nothing and returns a validation error identifying the category field.

**AC-06: Reject a category reference that does not resolve to the caller's own category**
**Given** an authenticated User,
**When** the submitted category reference matches no category at all, or matches a category owned by a different User,
**Then** the system creates nothing and returns the same not-found outcome in either case — the response gives no indication of which of the two happened.

**AC-07: Reject a missing amount limit**
**Given** an authenticated User,
**When** the amount limit is absent from the submission,
**Then** the system creates nothing and returns a validation error identifying the amount limit field.

**AC-08: Reject an amount limit that is zero or negative**
**Given** an authenticated User,
**When** the submitted amount limit is zero or a negative value,
**Then** the system creates nothing and returns a validation error rather than treating it as a valid cap.

**AC-09: Reject an amount limit carrying more than two decimal places**
**Given** an authenticated User,
**When** the submitted amount limit carries more than two digits after the decimal point,
**Then** the system creates nothing and returns a validation error rather than rounding or truncating the value.

**AC-10: A created budget's period is always the current calendar month**
**Given** an authenticated User submits a valid budget creation request,
**When** the budget is created,
**Then** its period is exactly the first day of the calendar month in which the request was made, determined solely by the system — never by any value supplied in the request payload, and never left for the User to choose.

**AC-11: Reject a duplicate budget for the same wallet, category, and period**
**Given** an authenticated User who already has a budget covering a given wallet, category, and period,
**When** the same User submits another budget for that same wallet, that same category, and that same period,
**Then** the system creates nothing and returns a conflict error, leaving the existing budget unchanged.

**AC-12: Return exactly the documented budget fields**
**Given** an authenticated User submits a valid budget creation request,
**When** the system returns the success result,
**Then** the result carries exactly the budget's identifier, wallet reference, category reference, amount limit, and period — no other field, and no data belonging to any other User's wallet or category.

### Edge Cases

**EC-01**: **Amount limit at the smallest positive value** — a submitted amount limit of `0.01` is accepted; the boundary excluded by AC-08 is exactly zero and below, not any positive value however small.

**EC-02**: **Amount limit exceeding the total digit width of `DECIMAL(15,2)`** — a value with more than 13 digits before the decimal point (15 significant digits in total, per constitution VL-07) is rejected with a validation error, distinctly from AC-09's decimal-places check but under the same `Decimal(15,2)` rule.

**EC-03**: **More than one validation failure in a single submission** — when the amount limit is negative and the wallet reference is absent in the same request, both problems are reported together in one response, not just the first one encountered.

**EC-04**: **A period value submitted with the request** — the request body additionally carries a period-like value alongside the wallet, category, and amount limit; the created budget's period is still the current calendar month exactly as AC-10 describes, and the response carries no echo of the submitted value. This story's contract has no period field for a caller to populate (see *Assumptions & Dependencies*), so the extra key is silently ignored, never honoured.

**EC-05**: **A wallet reference belonging to a different, real User** — refused with the identical outcome AC-04 describes for a wallet reference that matches nothing at all; the two cases are not merely similar, they are indistinguishable in every observable part of the response.

**EC-06**: **A category reference belonging to a different, real User** — refused with the identical outcome AC-06 describes for a category reference that matches nothing at all; the two cases are not merely similar, they are indistinguishable in every observable part of the response.

**EC-07**: **A wallet or category reference that is not even a well-formed identifier** — a value such as `"not-a-real-id"` is refused with the same not-found outcome as a well-formed but non-existent reference (AC-04/AC-06). No separate malformed-identifier error exists; a reference either resolves to a row the caller owns, or it does not, regardless of its shape.

**EC-08**: **A second budget for the same wallet and category, in a different period** — accepted. AC-11's conflict applies only when wallet, category, *and* period all match an existing budget; a later month is a different budget, not a duplicate of this one.

**EC-09**: **A second budget for the same category and period, against a different wallet** — accepted. AC-11's conflict is scoped to one specific wallet, not to every wallet the User owns.

**EC-10**: **A second budget for the same wallet and period, against a different category** — accepted. AC-11's conflict is scoped to one specific category, not to every category the User owns.

**EC-11**: **Both the wallet reference and the category reference are invalid in the same request** — only the wallet failure is reported (AC-04's outcome); the category reference is never evaluated, and the response never names both problems at once. FR-13/BR-02's fixed check order is what makes this deterministic rather than a coincidence of implementation.

### Requirements *(mandatory)*

#### Functional Requirements

- **FR-01**: The system must **allow** an authenticated User of any role to submit a wallet reference, a category reference, and an amount limit in order to create a new budget (SRS §6 US-05-01; SDS §5.5.1).
- **FR-02**: The system must **deny** the operation to unauthenticated callers, evaluating credentials before the payload (constitution API-08; mirrors WM-US-01 FR-02, CM-US-01 FR-02).
- **FR-03**: The system must **require** a non-empty `wallet_id` (AC-03).
- **FR-04**: The system must **require** `wallet_id` to resolve to a wallet owned by the authenticated caller, and **refuse** the request with an identical outcome whether no such wallet exists at all or it exists and is owned by a different User (AC-04, EC-05, EC-07; constitution SEC-08, VL-06).
- **FR-05**: The system must **require** a non-empty `category_id` (AC-05).
- **FR-06**: The system must **require** `category_id` to resolve to a category owned by the authenticated caller, and **refuse** the request with an identical outcome whether no such category exists at all or it exists and is owned by a different User (AC-06, EC-06, EC-07; constitution SEC-08, VL-06).
- **FR-07**: The system must **require** the amount limit, **store** it as a `Decimal` value with at most two digits after the decimal point and at most fifteen significant digits in total, and **reject** — rather than round or truncate — a value carrying more of either (AC-07, AC-09, EC-02; constitution VL-07).
- **FR-08**: The system must **reject** an amount limit that is zero or negative (AC-08, EC-01).
- **FR-09**: The system must **set** the budget's period automatically to the first day of the calendar month in which the request is made, and **ignore** any period-shaped value submitted in the request body (AC-10, EC-04).
- **FR-10**: The system must **refuse** to create a budget for a `wallet_id`/`category_id`/`period` combination that an existing budget already covers, leaving the existing budget unchanged (AC-11, EC-08, EC-09, EC-10; constitution VL-05).
- **FR-11**: The system must **return**, on success, exactly the budget's identifier, `wallet_id`, `category_id`, amount limit, and period (AC-12).
- **FR-12**: The system must **group** every payload-validation failure from one submission into a single response rather than reporting only the first (EC-03; constitution VL-02).
- **FR-13**: The system must **evaluate** wallet ownership, then category ownership, then the duplicate-budget check, in that fixed order, so that when a request fails more than one of these checks at once, only the first failing one is ever reported (BR-02).

#### Business Rules

- **BR-01**: A budget's wallet and its category must each belong to the authenticated caller; the budget itself carries no owner column of its own, so its ownership is entirely transitive through `wallet_id` and `category_id` (SRS §1.5; SDS §2.2, §4.3.3; constitution SEC-08 extended one hop; FR-04, FR-06).
- **BR-02**: A `wallet_id` or `category_id` that does not resolve to a row the caller owns is refused identically whether no such row exists at all or it exists and belongs to a different User. Checks run in a fixed order — wallet ownership, then category ownership, then the duplicate-budget check — so a request failing more than one of these reports only the first (FR-04, FR-06, FR-13).
- **BR-03**: `amount_limit` is a `Decimal` value with at most two decimal places and at most fifteen significant digits in total, and it must be strictly greater than zero; a value violating any of these is refused, never rounded, truncated, or clamped (constitution VL-07; FR-07, FR-08).
- **BR-04**: A budget's `period` is always the first day of the calendar month in which it is created, determined solely by the system clock, never by client input (FR-09).
- **BR-05**: At most one budget may exist at a time for a given combination of `wallet_id`, `category_id`, and `period`; a request that would create a second is refused (FR-10).

#### Key Entities

- **Budget**: A spending limit a User sets for one Category within one Wallet, over a monthly period (SRS §1.5). Carries `id`, `wallet_id`, `category_id`, `amount_limit`, and `period` in this story (SDS §2.2, §4.3.3) — no owner column of its own; whoever owns the referenced `wallet_id` and `category_id` is the only sense in which a Budget has an owner (BR-01). Created here for the first time; every other Budget Management story (BM-US-02..05) reads or mutates a Budget this story brings into existence.
- **Wallet**: Reused from WM-US-01 with no new column. Referenced, not owned, by this story — a budget's `wallet_id` must resolve to a Wallet already owned by the submitting User (BR-01, BR-02).
- **Category**: Reused from CM-US-01 with no new column. Referenced, not owned, by this story — a budget's `category_id` must resolve to a Category already owned by the submitting User (BR-01, BR-02).
- **User**: Reused from Feature-01/Feature-02 with no new column. The authenticated caller's own ownership of the referenced Wallet and Category is what entitles them to budget against those rows; no role restriction applies (any authenticated, `ACTIVE` User may create a budget).

### Success Criteria *(mandatory)*

- **SC-01**: An authenticated User can create a budget against one of their own wallets and one of their own categories, with a positive monthly amount limit, in one call, and the response reflects exactly what was created.
- **SC-02**: No budget can be created without an authenticated caller.
- **SC-03**: A budget can never be created against a wallet or a category the caller does not own — whether because the reference does not exist at all, or because it belongs to someone else, the request is refused identically either way.
- **SC-04**: A budget's amount limit is always stored at the precision and sign the User specified — never silently rounded, truncated, defaulted, or permitted to be zero or negative.
- **SC-05**: A budget's period always reflects the calendar month in which it was created, never a value the client supplied.
- **SC-06**: At most one budget ever exists for the same wallet, category, and period combination at once.
- **SC-07**: Malformed budget-creation input — a missing or unresolvable wallet or category reference, a missing, non-positive, or over-precise amount limit — is rejected before anything is persisted, with every payload-validation problem in one submission reported together.

### Assumptions & Dependencies

- **Login (SS-US-01), Create a Wallet (WM-US-01), and Create a Category (CM-US-01) are already implemented.** This is the first story in the epic whose every acceptance criterion presupposes rows already created by two *different* prior stories at once: every AC here requires at least one Wallet and one Category already on record, owned by the authenticated caller.
- **The SRS Gherkin scenario names only a Category ("Dining Out"), never a Wallet — even though the story's own title ("Create a Budget for a Wallet") and SDS §5.5.1's goal ("a category and wallet") both name both.** Resolved by reading the Gherkin as an abbreviated illustrative example rather than a complete field list — the same treatment WM-US-01 gave its own Gherkin's `type` examples (`plan.md` A1). This reading holds because the SRS's *own* §1.5 conceptual domain model already draws both `Wallet scoped_to Budget` and `Category applies_to Budget` as required relationships, and the SDS's ERD (§4.3.3), domain object (§2.2), and class diagram (§2.3) agree unanimously that `wallet_id` and `category_id` are both required columns. There is no genuine cross-document conflict to escalate here — only one under-specified example sitting next to several fuller, mutually consistent sources — so `BudgetCreate` requires both fields. Recorded as `plan.md` A1.
- **No period value is ever accepted from the caller.** The SRS Gherkin shows the User entering only a category and a limit, with no month or period picker anywhere in the scenario, and SDS §5.5.1's goal describes "a monthly period" as a property the budget has, not a value the User selects. The system computes it as the first day of the current calendar month at creation time. Recorded as `plan.md` A2.
- **A duplicate budget for the same wallet, category, and period is refused — unlike WM-US-01/CM-US-01's own "no uniqueness" precedent for wallet and category names.** A duplicate wallet or category *name* is not actually ambiguous — two wallets both named "Savings" are simply two different accounts — but two active budgets covering the same wallet, category, and month would leave "the" spending limit governing that period undefined, which FR-05's own spending-tracking-and-threshold language presupposes is singular. This case was reasoned about on its own terms rather than pattern-matched to the prior stories' conclusion. Recorded as `plan.md` A3.
- **The SDS §2.4.3 Budget Monitoring State machine (`DRAFT → NORMAL → WARNING → EXCEEDED → ARCHIVED`) is not implemented by this story.** `budgets` carries no `status` column anywhere in the ERD, so every budget this story creates simply *is* — there is no draft or inactive state to be in. The Gherkin's "creates an **active** budget" describes the fact that it now exists and will be monitored going forward, not a stored value. Deriving and storing real progress state against that state machine is BM-US-03's concern. Recorded as `plan.md` A8.
- **Reading a created budget back is out of scope.** This story is verified through what `POST /api/v1/budgets` itself returns and through direct inspection of the stored row — there is no `GET` endpoint yet (BM-US-02/03).

---

## BM-US-02: List Budgets

> **IDs in this section are local to BM-US-02.** `AC-01` below is not BM-US-01's `AC-01`; each story
> section numbers its own criteria, per `artifact-templates/spec-templates.md` and this codebase's own
> CM-US-02/WM-US-02/TM-US-02 precedent. Only `TC-NN` (and `QF-NN`) in `test_cases.md` run continuously
> across the epic (`CLAUDE.md` §1.1 rule 4).

### Source *(scope extraction — CLAUDE.md §1 scope rule)*

**SRS §6 Feature-05 — searched in full; no entry for BM-US-02 exists**
> `### Feature-05: Budget Management` contains exactly one story, `#### US-05-01: Create a Budget for a Wallet [MVP]` (already quoted in full in this file's BM-US-01 section above), immediately followed by `### Feature-06: Transaction Management`. There is no `US-05-02` header at all, bare or otherwise — unlike WM-US-02, which at least inherited a bare `#### US-03-02: View List of Wallets [MVP]` header from its own feature section. This story is in the identical position `CM-US-02` was already in for its own listing story in this codebase — no bare header at all — the same, not a lesser, textual anchor than that precedent already worked from.

**SRS §1.5 Conceptual Domain Model**
> **Budget** — A spending limit a User sets for one Category within one Wallet, over a monthly period, that Transactions are measured against (FR-05).
>
> | Relationship | Cardinality | Meaning |
> | Wallet scoped_to Budget | one Wallet → many Budgets | A spending limit is set against one Wallet at a time (FR-05) |
> | Category applies_to Budget | one Category → many Budgets | A Budget's limit applies to spending in one Category (FR-05) |

**SRS §2 FR-05 — Budget Tracking & Overspending Alerts**
> The System shall allow Users to define spending caps (`Budget`) per Category and Wallet for a monthly timeframe. The System shall track spending against this limit and trigger visual warnings when thresholds (75%, 100%) are reached.

**SDS §5.5.2 BM-US-02: List Budgets (USER)**
> **Goal:** View active budgets and current progress percentages.

One sentence — the entire technical baseline for this story, the same thinness CM-US-02's and WM-US-02's own SDS goals had.

**SDS §2.1 Domain Layer Traceability**
> | **Budget** | `budgets` | `BudgetModel` | `BudgetRead`, `BudgetCreate` |

Neither DTO named here carries a spending figure or a percentage — this story's SDS §5.5.2 goal names "current progress percentages" as its own deliverable, but §2.1's registry has no `Budget`-list DTO at all to point to, the identical gap CM-US-02's own Source section already found for `CategoryListRead`.

**SDS §4.3.3 Data Design — `BUDGETS` ERD** *(reused from BM-US-01's own Source quote)*
> ```
> BUDGETS {
>     uuid id PK
>     uuid wallet_id FK
>     uuid category_id FK
>     decimal amount_limit
>     date period
> }
> ```
> No `user_id` column, and no `status` column — confirmed again here since this story's central question ("what does *active* mean with no status column to hold it") turns on exactly this absence.

**constitution.md API-06, PF-04, SEC-08, PF-02**
> **API-06** List endpoints accept `page` and `page_size`; default 25, maximum 100. Responses carry a total count.
> **PF-04** List endpoints are always bounded (see API-06). No unbounded result set reaches a client.
> **SEC-08** Queries for user-owned data filter on the authenticated `user_id` at the repository layer (SDS §7.2, SRS NFR-06).
> **PF-02** Columns used in `WHERE`, `JOIN`, or `ORDER BY` carry an index. No N+1 query patterns.

**constitution.md VL-07**
> Monetary values use `Decimal` with `DECIMAL(15,2)` precision (SRS NFR-05). Never float.

**`specs/005-budget-management/plan.md` BM-US-01 A8** *(this story's own inherited open question)*
> The SDS §2.4.3 Budget Monitoring State machine (`DRAFT → NORMAL → WARNING → EXCEEDED → ARCHIVED`) is not implemented by this story, and `budgets` gets no `status` column ... Deriving and persisting real progress against that state machine needs spending data this story never reads, which is BM-US-03's job.

**`specs/005-budget-management/spec.md` BM-US-01 "Out of scope for this story"** *(this story's own inherited open question)*
> Deliberately excluded from *this* story even though adjacent: computing or displaying spending progress against a budget's limit, and the 75%/100% threshold alerts FR-05's second sentence describes (BM-US-03 — this story only creates the budget row; it never reads a Transaction and never computes a percentage).

This story reconciles those two inherited notes against SDS §5.5.2's own literal goal text for *this specific* story — see *Assumptions & Dependencies*.

### Out of scope for this story

BM-US-01 (create a budget, already implemented) · BM-US-03 (view budget status & alerts — the `DRAFT`/`NORMAL`/`WARNING`/`EXCEEDED`/`ARCHIVED` state machine and the 75%/100% threshold-crossing alerts) · BM-US-04 (update a budget) · BM-US-05 (delete a budget) · WM-US-*, CM-US-*, UM-US-04/05, DC-US-01/02 · Features 06–11 · SRS §6 Feature-10/11 placeholders.

Deliberately excluded even though adjacent: classifying a budget into a named state (`WARNING`, `EXCEEDED`, …) or raising any alert when a threshold is crossed — this story returns the raw progress percentage only, leaving interpretation of that number to BM-US-03 (see *Assumptions & Dependencies*); filtering the list by wallet, category, or any other dimension (neither SRS nor SDS names one for this story, mirroring CM-US-02's own declination to filter by `type`); viewing a single budget's detail (no such story is named in this round); and updating or deleting a budget (BM-US-04/05).

### User Scenarios & Testing *(mandatory)*

As an **authenticated User**, I want to view my active budgets together with how much I have spent
against each one so far this month, so that I can see at a glance which spending caps I am approaching
or have already exceeded, without doing the arithmetic myself.

**Acceptance Criteria**:

**AC-01: Successfully list every active budget the caller owns, with its current spending progress**
**Given** an authenticated User who owns one or more budgets whose period is the current calendar month,
**When** the User requests the list of budgets,
**Then** the system returns every one of that User's budgets whose period is the current calendar month,
each carrying its identifier, wallet, category, amount limit, period, amount spent so far, and progress
percentage, together with the total number of such budgets that User owns.

**AC-02: Return an empty list for a User with no active budgets**
**Given** an authenticated User who owns no budget whose period is the current calendar month (whether
because they own no budget at all, or own only budgets from an earlier month),
**When** the User requests the list,
**Then** the system returns an empty list of budgets together with a total of zero, not an error.

**AC-03: Deny access to unauthenticated callers**
**Given** a caller presenting no credentials, or credentials that are invalid or expired,
**When** the caller attempts to list budgets,
**Then** the system denies the request before evaluating any query parameter, returns nothing, and
returns an unauthenticated error.

**AC-04: Bound and paginate the result by default**
**Given** an authenticated User,
**When** the User requests the list without specifying a page or page size,
**Then** the system returns at most 25 of that User's active budgets on the first page, together with
the total number of such budgets that User owns.

**AC-05: Accept an explicit page and page size within range**
**Given** an authenticated User,
**When** the User requests a specific page together with a page size up to the maximum of 100,
**Then** the system returns that page of the User's own active budgets and the same accurate total.

**AC-06: Reject a page or page size outside the allowed range**
**Given** an authenticated User,
**When** the requested page or page size is zero, negative, otherwise not a positive integer, or a
page size greater than 100,
**Then** the system rejects the request with a validation error identifying the offending parameter,
and returns no budgets.

**AC-07: A User only ever sees their own budgets**
**Given** at least two Users, each owning one or more budgets whose period is the current calendar
month,
**When** one of them requests the list,
**Then** the response's budgets are exactly the ones that User owns — none belonging to any other User
appears — and the reported total counts only the requesting User's own active budgets, never every
active budget in the system.

**AC-08: Return the list in a stable, deterministic order**
**Given** an authenticated User who owns two or more active budgets, with nothing created, changed, or
removed in between,
**When** the User requests the same page more than once, or requests adjacent pages of one paging
sequence,
**Then** the system returns the same budgets in the same relative order every time, consistently across
those adjacent pages.

**AC-09: Only budgets whose period is the current calendar month are ever listed**
**Given** an authenticated User who owns a budget created in an earlier calendar month, in addition to
one or more budgets whose period is the current calendar month,
**When** the User requests the list,
**Then** the earlier budget never appears in the response and is never counted in the total, while the
current-month budgets appear normally — determined solely by the system, never by any value the User
supplies.

**AC-10: Amount spent reflects only expense activity against that same budget's own wallet and category, within the current month**
**Given** an authenticated User with an active budget for a specific wallet and category, and one or
more expense transactions recorded against that same wallet and category within the current calendar
month,
**When** the User requests the list,
**Then** that budget's amount spent equals the sum of exactly those expense transactions — never a
transaction against a different wallet, a different category, dated outside the current month, or that
is not an expense.

**AC-11: A budget with no matching expense activity yet still appears, with nothing spent**
**Given** an authenticated User with an active budget against which no expense transaction has yet been
recorded this month,
**When** the User requests the list,
**Then** that budget still appears in the response, with its amount spent reported as exactly zero —
never omitted, and never an error.

**AC-12: Progress percentage reflects spending as a proportion of the amount limit, and may exceed it**
**Given** an authenticated User's active budget with a known amount limit and a known amount spent,
**When** the User requests the list,
**Then** that budget's progress percentage equals its amount spent divided by its amount limit,
expressed as a percentage — including a value greater than 100 when spending has already surpassed the
limit, never capped or clamped to 100.

**AC-13: Return exactly the documented budget fields, wrapped in a paginated envelope**
**Given** an authenticated User requests the list,
**When** the system returns the result,
**Then** each entry carries exactly the budget's identifier, wallet reference, category reference,
amount limit, period, amount spent, and progress percentage — no other field, and no data belonging to
any other User's budget — and the overall response additionally carries the total count, the page
number, and the page size.

### Edge Cases

**EC-01**: **A page number beyond the last available page** — returns an empty list of budgets together
with the accurate, caller-scoped total, not a not-found error.

**EC-02**: **Page size at the exact maximum** — a page size of exactly 100 is accepted; 101 is rejected
under AC-06. The cap is a ceiling, not a target.

**EC-03**: **More active budgets than fit on one page** — paging through every page with a fixed page
size returns every one of the caller's own active budgets exactly once, with no duplicate and no gap,
in the same stable order AC-08 establishes.

**EC-04**: **A caller whose role is ADMIN, who also owns budgets** — sees, through this endpoint, only
the budgets that caller owns. Nothing about this endpoint grants an ADMIN visibility into another
User's budgets.

**EC-05**: **An expense transaction recorded against a different wallet, or a different category, than
a given budget's own** — never contributes to that budget's amount spent, even when the caller owns
both the budget and the transaction's wallet or category.

**EC-06**: **A budget whose period is a calendar month before the current one** — the row remains on
record (this story creates, updates, and deletes nothing), but it never appears in the list and is
never counted in the total, for as long as the current month has moved past it.

**EC-07**: **Two or more active budgets that share the same wallet but different categories, or the
same category but different wallets** — each is listed as its own entry, with its own independently
computed amount spent and progress percentage.

**EC-08**: **A transaction timestamped at the first instant of the immediately preceding or following
calendar month** — excluded from every budget's amount spent, even though it is only moments outside
the current month's boundary.

**EC-09**: **An income transaction recorded against the same wallet and category as an active budget**
— never contributes to that budget's amount spent; only expense transactions count.

### Requirements *(mandatory)*

#### Functional Requirements

- **FR-01**: The system must **allow** an authenticated User of any role to retrieve the list of active
  budgets they own (SDS §5.5.2; mirrors BM-US-01 FR-01's "any role" treatment).
- **FR-02**: The system must **deny** the operation to unauthenticated callers, evaluating credentials
  before any query parameter (constitution API-08; mirrors BM-US-01 FR-02).
- **FR-03**: The system must **accept** `page` and `page_size` query parameters, defaulting to page 1
  and page size 25 when omitted (constitution API-06).
- **FR-04**: The system must **reject** a `page` or `page_size` value that is not a positive integer, or
  a `page_size` greater than 100, with a validation error (constitution API-06, PF-04).
- **FR-05**: The system must **return**, alongside every page, the total number of active budgets the
  caller owns (constitution API-06).
- **FR-06**: The system must **restrict** every budget query this endpoint issues — both the bounded
  page of items and the total count — to only budgets belonging to the caller, ownership being
  transitive through the budget's own wallet (constitution SEC-08; BR-01).
- **FR-07**: The system must **never include**, in either the returned budgets or the reported total,
  any budget belonging to a User other than the caller, regardless of the caller's role (constitution
  SEC-08; AC-07, EC-04).
- **FR-08**: The system must **order** the returned budgets by a stable, deterministic key, consistently
  across pages of the same request pattern (mirrors CM-US-02/WM-US-02 FR-08).
- **FR-09**: The system must **restrict** the list to budgets whose period is exactly the current
  calendar month, determined solely by the system clock — never by any value the caller supplies (AC-09,
  EC-06; BR-05).
- **FR-10**: The system must **compute**, for every listed budget, an amount spent equal to the sum of
  that budget's own wallet's and category's expense transactions dated within the current calendar month
  (AC-10, EC-05, EC-08, EC-09; BR-06).
- **FR-11**: The system must **default** amount spent to zero for a budget with no matching expense
  transaction, never omitting the budget and never treating it as an error (AC-11; BR-07).
- **FR-12**: The system must **compute** progress percentage as amount spent divided by amount limit,
  expressed as a percentage, permitting a value above 100 (AC-12; BR-08).
- **FR-13**: The system must **return**, for every listed budget, exactly its identifier, wallet
  reference, category reference, amount limit, period, amount spent, and progress percentage — and, for
  the overall response, exactly the total, page, and page size alongside the items (AC-13).

#### Business Rules

- **BR-01**: Only the budgets owned by the authenticated caller are ever returned by this endpoint;
  ownership is entirely transitive through the budget's own wallet and category, the same shape BM-US-01
  BR-01 established at creation time (SDS §5.5.2 "(USER)"; constitution SEC-08; EC-04).
- **BR-02**: A page never carries more than 100 budgets; the default when unspecified is 25 (FR-03,
  FR-04; mirrors CM-US-02/WM-US-02 BR-02).
- **BR-03**: Budgets are ordered by a stable key, consistently across pages of the same request pattern;
  this story establishes no chronological ordering guarantee, because no creation timestamp exists on
  `Budget` (FR-08; mirrors CM-US-02/WM-US-02 BR-03).
- **BR-04**: The reported total always equals the count of active budgets owned by the caller, never the
  system-wide count and never a count including a budget from a different period (FR-05, FR-06, FR-07,
  FR-09).
- **BR-05**: "Active" means the budget's period is exactly the current calendar month, determined solely
  by the system clock; a budget from any other month is excluded from every response this endpoint
  returns, though it remains on record unchanged (FR-09, AC-09, EC-06).
- **BR-06**: A budget's amount spent is computed independently, scoped to exactly that budget's own
  wallet and category, counting only expense-type transactions dated within the current calendar month;
  a transaction against a different wallet, a different category, a different type, or outside the
  current month never contributes (FR-10, EC-05, EC-08, EC-09).
- **BR-07**: A budget with no matching expense transaction reports an amount spent of exactly zero; this
  is never treated as an error or as a reason to omit the budget (FR-11, AC-11).
- **BR-08**: A budget's progress percentage carries no upper bound; it may legitimately exceed 100 once
  spending surpasses the amount limit (FR-12, AC-12).

#### Key Entities

- **Budget**: As BM-US-01 defined it, plus two fields computed only by this endpoint — amount spent and
  progress percentage — derived at read time from the caller's own Transactions and never persisted on
  the Budget row itself (SDS §5.5.2). This story reads a Budget; it creates, updates, and deletes none.
- **Wallet**: Reused unchanged. Referenced, not owned, by this story — a budget's ownership and its
  matching transactions are both reached through `wallet_id`.
- **Category**: Reused unchanged. Referenced the same way as Wallet.
- **Transaction**: Reused from Feature-06 with no new field. Read-only for this story — the first
  Budget Management story to read one. Every amount spent figure is derived by summing existing expense
  Transaction rows dated within the current month, matched to a Budget by its wallet and category.
- **User**: Reused. The authenticated caller's own ownership of the referenced Wallet — and,
  transitively, the Budget — is the only scope this story ever queries by.

### Success Criteria *(mandatory)*

- **SC-01**: An authenticated User can retrieve every active budget they own, each carrying an accurate
  spending progress figure, in one call.
- **SC-02**: No request to this endpoint can return an unbounded number of rows.
- **SC-03**: No User can see another User's budget, or another User's budget count, through this
  endpoint, regardless of role.
- **SC-04**: A User can page through their entire active-budget set with an accurate total and no
  duplicated or skipped budget.
- **SC-05**: A User with no active budgets receives an empty list and a zero total, never an error.
- **SC-06**: A budget's amount spent and progress percentage always reflect only that budget's own
  wallet, category, expense activity, and the current month — never another budget's, another User's,
  or another period's data.
- **SC-07**: A budget whose period is not the current calendar month never appears through this
  endpoint, though its stored row is never altered or removed by it.

### Assumptions & Dependencies

- **Login (SS-US-01), Create a Wallet (WM-US-01), Create a Category (CM-US-01), and Create a Budget
  (BM-US-01) are already implemented.** So are Create/List a Transaction (TM-US-01/TM-US-02) — this is
  the first Budget Management story whose acceptance criteria depend on Transaction data existing, since
  "amount spent" has no other source.
- **"Active" reads as "the budget's period equals the current calendar month," resolved the same way
  `FR-US-01`'s own summary report already resolved an identical absence of an explicit filter.**
  `budgets` carries no `status` column at all (BM-US-01 plan.md A8) — there is no draft or inactive
  state, so SDS §5.5.2's word "active" cannot mean a stored value. Two readings compete: "every budget
  ever created" (ignoring the word entirely), or "the budget whose period governs spending right now"
  (reading "active" the way the SRS's own domain model already uses the concept — a spending limit
  currently being measured against, SRS §1.5). The second reading is preferred because it is the only
  one under which "current progress percentages" (the same SDS sentence's second half) is well-defined
  for every listed row: a budget from a past month has no "current" period left to measure fresh
  transactions against, without inventing a second, unasked-for filter parameter letting the caller pick
  which past month to inspect. This mirrors `FR-US-01`'s own "the period is always the current calendar
  month, determined by the system clock, never client input" idiom, applied here to filter which rows
  appear rather than to bound a single computed report. Not escalated as `[NEEDS RULING]`: nothing in
  `SRS.md`/`SDS.md` disagrees with this reading, it only under-specifies — the same shape as BM-US-01
  A2's own period decision.
- **Computing the progress percentage belongs to this story, not BM-US-03 — narrowing what BM-US-01's
  own spec.md "Out of scope" note said.** BM-US-01's spec.md attributed "computing or displaying
  spending progress against a budget's limit" broadly to BM-US-03, written before this story's own SDS
  line existed to read closely. SDS §5.5.2's goal for *this* story explicitly names "current progress
  percentages" as its own deliverable, distinct from the SDS §2.4.3 state machine's `WARNING`/`EXCEEDED`
  classification and FR-05's "trigger visual warnings when thresholds (75%, 100%) are reached" — both of
  which are about *naming a state* and *raising an alert*, not about the underlying number. This story
  computes and returns the raw percentage; classifying it into a named state or raising an alert when a
  threshold is crossed remains BM-US-03's. This is reading SDS §5.5.2's own text for its own story
  precisely, not extending either reference document.
- **Budgets are never deleted or archived by this or any other currently implemented story.** A budget
  from an earlier month simply stops appearing here once the calendar has moved past it — its row is
  untouched, per BR-05.
