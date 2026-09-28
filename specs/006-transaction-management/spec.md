# Feature Specification: Transaction Management (TM)

> **Feature:** SRS §6 Feature-06 · SDS §5.6 (TM)
> **Spec:** [spec.md](spec.md)
> **Stories in this file:** TM-US-01 *(specified)*

---

## Source *(scope extraction — CLAUDE.md §1 scope rule)*

Only the sections below entered the working context for TM-US-01.

**SRS §6 Feature-06 · US-06-01 — Create a Transaction for a Wallet [MVP]**
> ```gherkin
> Feature: Create Transaction
>
>   Background:
>     Given the User is logged in
>     And the User has a wallet named "Main Checking" with balance 1000.00
>
>   Scenario: Create an expense transaction successfully
>     When the User selects transaction type "EXPENSE"
>     And the User enters amount 50.00
>     And the User selects category "Groceries"
>     And the User selects wallet "Main Checking"
>     And the User clicks "Save Transaction"
>     Then the System records the transaction
>     And the balance for "Main Checking" decreases to 950.00
>     And the System shows message "Transaction created successfully"
>
>   Scenario: Reject expense exceeding available balance (MVP Rule)
>     When the User selects transaction type "EXPENSE"
>     And the User enters amount 1500.00
>     And the User selects wallet "Main Checking"
>     And the User clicks "Save Transaction"
>     Then the System rejects the transaction
>     And the balance for "Main Checking" remains 1000.00
>     And the System shows error "Insufficient balance"
> ```

**SRS §1.5 Conceptual Domain Model**
> **Transaction** — A single recorded movement of money, in or out, against one Wallet and one Category, at a point in time (FR-06).
>
> | Relationship | Cardinality | Meaning |
> | Wallet contains Transaction | one Wallet → many Transactions | Every Transaction moves money into or out of exactly one Wallet (FR-06) |
> | Category classifies Transaction | one Category → many Transactions | Every Transaction is tagged with exactly one Category (FR-06) |

**SRS §2 FR-06 — Transaction Management**
> The System shall allow Users to log income and expense Transactions against a designated Wallet and Category. The System shall automatically recalculate and persist wallet balances atomically.

**SRS §2 FR-04 — Category Management** *(context for the type-consistency decision — see Assumptions & Dependencies, and `plan.md` A3)*
> The System shall support user-defined Categories classified as either `INCOME` or `EXPENSE` (e.g., Groceries, Rent, Salary, Utilities).

**SRS §3 NFR-05 — Data Integrity & Monetary Precision**
> All monetary attributes and asset valuations must be stored using arbitrary-precision decimal representations (`DECIMAL(15,2)`). Balance updates must execute inside ACID-compliant database transaction blocks.

**SDS §5.6.1 TM-US-01: Create a Transaction for a Wallet (USER)**
> * **Goal:** Log an income or expense transaction and atomically update wallet balances.

**SDS §2.1 Domain Layer Traceability**
> | **Transaction** | `transactions` | `TransactionModel` | `TransactionRead`, `TransactionCreate` |

**SDS §2.2 Domain Object**
> **Transaction:** Ledger entry representing monetary movement (`id`, `wallet_id`, `category_id`, `amount`, `type`, `timestamp`, `note`).

**SDS §6.2.1 DTO Registry**
> **`TransactionCreate`**: `{ "wallet_id": "UUID", "category_id": "UUID", "amount": 0.00, "type": "EXPENSE", "note": "string" }`

**SDS §4.3.3 Data Design — `TRANSACTIONS` ERD**
> ```
> WALLETS ||--o{ TRANSACTIONS : stores
> CATEGORIES ||--o{ TRANSACTIONS : classifies
>
> TRANSACTIONS {
>     uuid id PK
>     uuid wallet_id FK
>     uuid category_id FK
>     decimal amount
>     string type
>     timestamp timestamp
>     text note
> }
> ```
> No `user_id` column — the same ownerless shape as `BUDGETS` (SDS §4.3.3; BM-US-01's own precedent). `note` is typed `text`, distinctly from the `string` type `wallets.name`/`categories.name` each carry in their own ERD blocks (see Assumptions & Dependencies, and `plan.md` A6).

**SDS §6.3 API Index**
> | **TM-API-01** | `POST` | `/api/v1/transactions` | Record a transaction |

**constitution.md AR-06**
> Multi-entity writes execute in **one** transaction. Services never call `commit()`; the router owns the commit boundary.

**constitution.md VL-07**
> Monetary values use `Decimal` with `DECIMAL(15,2)` precision (SRS NFR-05). Never float.

**constitution.md VL-06**
> Referenced entities are verified to exist and be active before use — `404` if absent, `409` if present but in the wrong state.

**constitution.md SEC-08**
> Queries for user-owned data filter on the authenticated `user_id` at the repository layer (SDS §7.2, SRS NFR-06).

### Out of scope for this story

TM-US-02 (list transactions) · TM-US-03 (view a transaction) · TM-US-04 (update a transaction) · TM-US-05 (delete a transaction) · BM-US-02 (list budgets) · BM-US-03 (view budget status & the 75%/100% threshold alerts) · BM-US-04/05 · WM-US-02..05 · CM-US-02..05 · UM-US-04/05, DC-US-01/02 · Features 07 (Financial Reporting), 08 (Notifications), 09 (Dashboard) · SRS §6 Feature-10/11 placeholders.

Deliberately excluded from *this* story even though adjacent: reading the `budgets` table at all, computing spending-vs-limit progress, or evaluating the 75%/100% threshold SDS §2.4.3's Budget Monitoring State machine describes — that is entirely BM-US-03's job, and this story never queries `budgets` in either direction even though a Transaction is exactly the kind of event that state machine eventually reacts to. Also excluded: reading a created transaction back through any `GET` endpoint (TM-US-02/03 — this story is verifiable only through what `POST /api/v1/transactions` itself returns and through direct inspection of the stored `transactions` and `wallets` rows), updating or deleting a transaction (TM-US-04/05), and generating any Notification (Feature-08) even though FR-08 names "low wallet balances" as a future notification trigger this story's own balance changes could someday feed.

---

## TM-US-01: Create a Transaction

### User Scenarios & Testing *(mandatory)*

As an **authenticated User**, I want to log an income or expense transaction against one of my own wallets and one of my own categories, so that my wallet's balance always reflects my real spending and earning.

**Acceptance Criteria**:

**AC-01: Successfully create an expense transaction with a sufficient balance**
**Given** an authenticated User who owns a wallet with a specific current balance and owns an `EXPENSE`-typed category,
**When** the User submits an `EXPENSE` transaction against that wallet and that category with an amount that does not exceed the wallet's current balance,
**Then** the system records the transaction, decreases the wallet's balance by exactly the submitted amount, and returns a success result carrying the transaction's identifier, wallet, category, amount, type, timestamp, and note.

**AC-02: Successfully create an income transaction regardless of the wallet's current balance**
**Given** an authenticated User who owns a wallet and owns an `INCOME`-typed category,
**When** the User submits an `INCOME` transaction against that wallet and that category with a positive amount,
**Then** the system records the transaction, increases the wallet's balance by exactly the submitted amount, and returns a success result — regardless of what the wallet's balance was before the request.

**AC-03: Deny access to unauthenticated callers**
**Given** a caller presenting no credentials, or credentials that are invalid or expired,
**When** the caller attempts to create a transaction,
**Then** the system denies the request before evaluating the payload, creates nothing, and returns an unauthenticated error.

**AC-04: Reject a missing wallet reference**
**Given** an authenticated User,
**When** the submitted wallet reference is absent from the request,
**Then** the system creates nothing and returns a validation error identifying the wallet field.

**AC-05: Reject a wallet reference that does not resolve to the caller's own wallet**
**Given** an authenticated User,
**When** the submitted wallet reference matches no wallet at all, or matches a wallet owned by a different User,
**Then** the system creates nothing and returns the same not-found outcome in either case — the response gives no indication of which of the two happened.

**AC-06: Reject a missing category reference**
**Given** an authenticated User,
**When** the submitted category reference is absent from the request,
**Then** the system creates nothing and returns a validation error identifying the category field.

**AC-07: Reject a category reference that does not resolve to the caller's own category**
**Given** an authenticated User,
**When** the submitted category reference matches no category at all, or matches a category owned by a different User,
**Then** the system creates nothing and returns the same not-found outcome in either case — the response gives no indication of which of the two happened.

**AC-08: Reject a transaction whose type does not match its referenced category's own type**
**Given** an authenticated User who owns a wallet and owns a category,
**When** the submitted transaction type does not match that category's own type,
**Then** the system creates nothing, leaves the wallet's balance unchanged, and returns a conflict error — regardless of which of the two types (`INCOME` or `EXPENSE`) was submitted and which the category actually carries.

**AC-09: Reject a missing amount**
**Given** an authenticated User who owns a wallet and a category,
**When** the amount is absent from the submission,
**Then** the system creates nothing and returns a validation error identifying the amount field.

**AC-10: Reject an amount that is zero or negative**
**Given** an authenticated User who owns a wallet and a category,
**When** the submitted amount is zero or a negative value,
**Then** the system creates nothing and returns a validation error rather than treating it as a valid transaction.

**AC-11: Reject an amount carrying more than two decimal places**
**Given** an authenticated User who owns a wallet and a category,
**When** the submitted amount carries more than two digits after the decimal point,
**Then** the system creates nothing and returns a validation error rather than rounding or truncating the value.

**AC-12: Reject a missing transaction type**
**Given** an authenticated User who owns a wallet and a category,
**When** the transaction type is absent from the submission,
**Then** the system creates nothing and returns a validation error identifying the type field.

**AC-13: Reject a transaction type that is not INCOME or EXPENSE**
**Given** an authenticated User who owns a wallet and a category,
**When** the submitted transaction type is any value other than `INCOME` or `EXPENSE`,
**Then** the system creates nothing and returns a validation error rather than accepting an open-ended value.

**AC-14: Reject an expense transaction whose amount exceeds the wallet's current balance**
**Given** an authenticated User who owns a wallet with a specific current balance,
**When** the User submits an `EXPENSE` transaction whose amount exceeds that current balance,
**Then** the system creates nothing, leaves the wallet's balance unchanged, and returns an error indicating insufficient balance.

**AC-15: A created transaction's timestamp is always the moment of creation**
**Given** an authenticated User submits a valid transaction creation request,
**When** the transaction is created,
**Then** its timestamp is exactly the moment the system processed the request, determined solely by the system clock — never by any value supplied in the request payload, and never left for the User to choose.

**AC-16: Reject a note exceeding the maximum supported length**
**Given** an authenticated User who owns a wallet and a category,
**When** the submitted note is longer than the system supports,
**Then** the system creates nothing and returns a validation error rather than truncating the note.

**AC-17: A transaction may be created with no note at all**
**Given** an authenticated User who owns a wallet and a category,
**When** the User submits a transaction with the note field entirely absent,
**Then** the system creates the transaction successfully, and the returned note is explicitly absent (`null`) rather than an empty string or a default value.

**AC-18: Return exactly the documented transaction fields**
**Given** an authenticated User submits a valid transaction creation request,
**When** the system returns the success result,
**Then** the result carries exactly the transaction's identifier, wallet reference, category reference, amount, type, timestamp, and note — no other field, and no data belonging to any other User's wallet or category.

### Edge Cases

**EC-01**: **Amount at the smallest positive value** — a submitted amount of `0.01` is accepted; the boundary excluded by AC-10 is exactly zero and below, not any positive value however small.

**EC-02**: **Amount exceeding the total digit width of `DECIMAL(15,2)`** — a value with more than 13 digits before the decimal point (15 significant digits in total, per constitution VL-07) is rejected with a validation error, distinctly from AC-11's decimal-places check but under the same `Decimal(15,2)` rule.

**EC-03**: **More than one validation failure in a single submission** — when the amount is negative and the wallet reference is absent in the same request, both problems are reported together in one response, not just the first one encountered.

**EC-04**: **A timestamp value submitted with the request** — the request body additionally carries a timestamp-shaped value alongside the required fields; the created transaction's timestamp is still the moment of creation exactly as AC-15 describes, and the response carries no echo of the submitted value. This story's contract has no timestamp field for a caller to populate (see *Assumptions & Dependencies*), so the extra key is silently ignored, never honoured.

**EC-05**: **A wallet reference belonging to a different, real User** — refused with the identical outcome AC-05 describes for a wallet reference that matches nothing at all; the two cases are not merely similar, they are indistinguishable in every observable part of the response.

**EC-06**: **A category reference belonging to a different, real User** — refused with the identical outcome AC-07 describes for a category reference that matches nothing at all; the two cases are not merely similar, they are indistinguishable in every observable part of the response.

**EC-07**: **A wallet or category reference that is not even a well-formed identifier** — a value such as `"not-a-real-id"` is refused with the same not-found outcome as a well-formed but non-existent reference (AC-05/AC-07). No separate malformed-identifier error exists; a reference either resolves to a row the caller owns, or it does not, regardless of its shape.

**EC-08**: **An expense amount exactly equal to the wallet's current balance** — accepted; the boundary AC-14 excludes is an amount that *exceeds* the current balance, not one that exactly exhausts it. The wallet's balance becomes exactly zero.

**EC-09**: **An income transaction submitted against a wallet whose current balance is zero or negative** — accepted unconditionally; the insufficient-balance rule (AC-14) applies only to `EXPENSE` transactions, never to `INCOME`, regardless of the wallet's starting balance.

**EC-10**: **An expense transaction submitted against a wallet whose current balance is already zero or negative** — refused regardless of the submitted amount. Because every transaction amount is strictly positive (AC-10), any `EXPENSE` against a non-positive balance necessarily exceeds it; the rule applies exactly as uniformly to a wallet WM-US-01 permits to start negative (WM-US-01 EC-02) as to any other wallet — no wallet-type or wallet-history exception exists.

**EC-11**: **A transaction whose category type mismatches, and whose amount would independently exceed the wallet's balance, in the same request** — only the category-type-mismatch error is returned (AC-08's outcome), never the insufficient-balance error, and never both. FR-18/BR-02's fixed check order is what makes this deterministic rather than a coincidence of implementation.

**EC-12**: **Two transactions submitted with identical wallet, category, amount, and type** — both are accepted as two independent ledger entries, each with its own identifier. No acceptance criterion or business rule requires transactions to be unique in any respect — unlike Budget's per-period uniqueness (BM-US-01 BR-05), a Transaction is a ledger entry, and repeating one (e.g. two identical coffee purchases on the same day) is an ordinary, expected occurrence.

**EC-13**: **No note supplied at all** — the request omits the `note` field entirely; creation still succeeds because `note` is not mandatory (AC-17), and the stored/returned value is `null`.

**EC-14**: **Both the wallet reference and the category reference are invalid in the same request** — only the wallet failure is reported (AC-05's outcome); the category reference is never evaluated, and the response never names both problems at once. FR-18's fixed check order is what makes this deterministic rather than a coincidence of implementation.

### Requirements *(mandatory)*

#### Functional Requirements

- **FR-01**: The system must **allow** an authenticated User of any role to submit a wallet reference, a category reference, an amount, a transaction type, and an optional note in order to create a new transaction (SRS §6 US-06-01; SDS §5.6.1).
- **FR-02**: The system must **deny** the operation to unauthenticated callers, evaluating credentials before the payload (constitution API-08; mirrors WM-US-01 FR-02, BM-US-01 FR-02).
- **FR-03**: The system must **require** a non-empty `wallet_id` (AC-04).
- **FR-04**: The system must **require** `wallet_id` to resolve to a wallet owned by the authenticated caller, and **refuse** the request with an identical outcome whether no such wallet exists at all or it exists and is owned by a different User (AC-05, EC-05, EC-07; constitution SEC-08, VL-06).
- **FR-05**: The system must **require** a non-empty `category_id` (AC-06).
- **FR-06**: The system must **require** `category_id` to resolve to a category owned by the authenticated caller, and **refuse** the request with an identical outcome whether no such category exists at all or it exists and is owned by a different User (AC-07, EC-06, EC-07; constitution SEC-08, VL-06).
- **FR-07**: The system must **require** the submitted transaction `type` to equal the referenced category's own `type`, and **refuse** the request when they disagree (AC-08; SRS FR-04, FR-06).
- **FR-08**: The system must **require** the amount, **store** it as a `Decimal` value with at most two digits after the decimal point and at most fifteen significant digits in total, and **reject** — rather than round or truncate — a value carrying more of either (AC-09, AC-11, EC-02; constitution VL-07).
- **FR-09**: The system must **reject** an amount that is zero or negative (AC-10, EC-01).
- **FR-10**: The system must **require** `type` to be exactly `INCOME` or `EXPENSE`, rejecting any other value (AC-12, AC-13).
- **FR-11**: The system must, for an **EXPENSE** transaction, **refuse** the request when the amount exceeds the wallet's current balance at the moment of the request, leaving the balance unchanged, and apply this rule uniformly to every wallet regardless of how its current balance was reached (AC-14, EC-08, EC-10).
- **FR-12**: The system must, for an **INCOME** transaction, **apply no balance-sufficiency check** — the transaction is accepted and the balance increased regardless of the wallet's current balance (AC-02, EC-09).
- **FR-13**: The system must **persist** the new transaction row and the wallet's updated balance as a single atomic unit — a failure at any point leaves neither the transaction nor the balance change persisted (SRS FR-06 "atomically"; constitution AR-06).
- **FR-14**: The system must **set** the transaction's timestamp automatically to the moment of creation, and **ignore** any timestamp-shaped value submitted in the request body (AC-15, EC-04).
- **FR-15**: The system must **accept** an optional `note`, and **reject** — rather than truncate — one longer than the system supports (AC-16, AC-17).
- **FR-16**: The system must **return**, on success, exactly the transaction's identifier, `wallet_id`, `category_id`, `amount`, `type`, `timestamp`, and `note` (AC-18).
- **FR-17**: The system must **group** every payload-validation failure from one submission into a single response rather than reporting only the first (EC-03; constitution VL-02).
- **FR-18**: The system must **evaluate** wallet ownership, then category ownership, then category-type consistency, then — for an EXPENSE transaction only — balance sufficiency, in that fixed order, so that when a request fails more than one of these checks at once, only the first failing one is ever reported (EC-11, EC-14; BR-02).
- **FR-19**: The system must **impose no uniqueness constraint** on transactions — repeated submissions with identical wallet, category, amount, and type are each accepted as independent ledger entries (EC-12).

#### Business Rules

- **BR-01**: A transaction's wallet and its category must each belong to the authenticated caller; the transaction itself carries no owner column of its own, so its ownership is entirely transitive through `wallet_id` and `category_id` (SRS §1.5; SDS §2.2, §4.3.3; constitution SEC-08 extended one hop; FR-04, FR-06 — the same shape BM-US-01 BR-01 established for Budget).
- **BR-02**: A `wallet_id` or `category_id` that does not resolve to a row the caller owns is refused identically whether no such row exists at all or it exists and belongs to a different User. Checks run in a fixed order — wallet ownership, category ownership, category-type consistency, then (EXPENSE only) balance sufficiency — so a request failing more than one of these reports only the first (FR-04, FR-06, FR-18).
- **BR-03**: A transaction's `type` must equal its referenced category's own `type` — a category typed `INCOME` may only back an `INCOME` transaction, and a category typed `EXPENSE` may only back an `EXPENSE` transaction; a mismatch is refused (FR-07).
- **BR-04**: `amount` is a `Decimal` value with at most two decimal places and at most fifteen significant digits in total, and it must be strictly greater than zero; a value violating any of these is refused, never rounded, truncated, or clamped (constitution VL-07; FR-08, FR-09).
- **BR-05**: An `EXPENSE` transaction is refused when its amount exceeds the wallet's current balance at the moment of the request; this rule applies uniformly to every wallet regardless of how its balance reached its current value, including a wallet already at a negative balance, and never applies to an `INCOME` transaction (FR-11, FR-12).
- **BR-06**: A transaction's `timestamp` is always the moment of creation, determined solely by the system clock, never by client input (FR-14).
- **BR-07**: The new transaction row and the wallet's balance update are written as a single atomic unit; a failure anywhere in the operation leaves neither persisted (FR-13; constitution AR-06).

#### Key Entities

- **Transaction**: A single recorded movement of money, in or out, against one Wallet and one Category, at a point in time (SRS §1.5). Carries `id`, `wallet_id`, `category_id`, `amount`, `type`, `timestamp`, and `note` in this story (SDS §2.2, §4.3.3) — no owner column of its own; whoever owns the referenced `wallet_id` and `category_id` is the only sense in which a Transaction has an owner (BR-01). Created here for the first time; every other Transaction Management story (TM-US-02..05) reads or mutates a Transaction this story brings into existence.
- **Wallet**: Reused from WM-US-01 with no new column. Referenced, not owned, by this story in the ordinary sense — but this is the first story to *mutate* an existing Wallet row (its `balance`) rather than only read or reference it; a transaction's `wallet_id` must resolve to a Wallet already owned by the submitting User (BR-01, BR-02).
- **Category**: Reused from CM-US-01 with no new column. Referenced, not owned, by this story — a transaction's `category_id` must resolve to a Category already owned by the submitting User, and that Category's own `type` must agree with the transaction's `type` (BR-01, BR-02, BR-03).
- **User**: Reused from Feature-01/Feature-02 with no new column. The authenticated caller's own ownership of the referenced Wallet and Category is what entitles them to log a transaction against those rows; no role restriction applies (any authenticated, `ACTIVE` User may create a transaction).

### Success Criteria *(mandatory)*

- **SC-01**: An authenticated User can create an `EXPENSE` or `INCOME` transaction against one of their own wallets and one of their own categories whose type agrees with the transaction's own type, and the response reflects exactly what was created.
- **SC-02**: No transaction can be created without an authenticated caller.
- **SC-03**: A transaction can never be created against a wallet or a category the caller does not own, or whose type disagrees with the transaction's own type — refused identically whether the reference is absent or belongs to someone else.
- **SC-04**: A wallet's balance always reflects the net effect of every transaction recorded against it — decreased by every `EXPENSE`, increased by every `INCOME` — and is never changed except together with the transaction that caused the change, nor left changed when that transaction is refused.
- **SC-05**: An `EXPENSE` transaction can never drive a wallet's balance below zero; an `INCOME` transaction is never blocked by the wallet's current balance, however low.
- **SC-06**: A transaction's timestamp always reflects the moment of its creation, never a value the client supplied.
- **SC-07**: Malformed transaction-creation input — a missing or unresolvable wallet or category reference, a type disagreeing with the category's own type, a missing, non-positive, or over-precise amount, a missing or invalid type, or an over-long note — is rejected before anything is persisted, with every payload-validation problem in one submission reported together.

### Assumptions & Dependencies

- **Login (SS-US-01), Create a Wallet (WM-US-01), and Create a Category (CM-US-01) are already implemented.** Every AC here presupposes at least one Wallet and one Category already on record, owned by the authenticated caller — the same dependency shape BM-US-01 had on two different prior stories at once.
- **FR-06 names both income and expense transactions; the SRS Gherkin illustrates only the EXPENSE path.** The Background sets up a wallet with balance 1000.00, and both of the Gherkin's own scenarios are `EXPENSE` — one a successful debit, one refused for insufficient balance. Nothing in the Gherkin shows an `INCOME` scenario. Resolved the same way WM-US-01 A1/BM-US-01 A1 read their own under-illustrated Gherkins: as an abbreviated example of the more interesting (rejection) path, not a complete enumeration of supported behaviour — FR-06's own first sentence ("log income **and** expense Transactions") is unambiguous, so supporting `INCOME` is reading a requirement already stated in full, not inventing one. Recorded as `plan.md` A1.
- **The insufficient-balance rule is scoped to `EXPENSE` transactions only, and applies uniformly to every wallet regardless of how its balance was reached.** Reasoning recorded in `plan.md` A2.
- **A transaction's `type` must agree with its referenced category's own `type`.** Reasoning recorded in `plan.md` A3.
- **No `timestamp` field exists on `TransactionCreate`; the system always sets it to the moment of creation**, the same treatment BM-US-01 A2 gave `period`. No source shows a person choosing a timestamp — the Gherkin has the User select type, amount, category, and wallet, then click "Save Transaction," with no date or time picker anywhere in either scenario. Recorded as `plan.md` A5.
- **`note` is optional and bounded at 500 characters**, not the 100-character bound WM-US-01/CM-US-01 settled on for `name`. Reasoning recorded in `plan.md` A6.
- **The balance-sufficiency check and the balance mutation are one atomic database write, not a read-then-compare-then-write sequence**, for the same race-safety reason `invitation_repo.mark_accepted()` (UM-US-02) already established for concurrent activation attempts. Reasoning recorded in `plan.md` A9; the same environment limit UM-US-01/UM-US-02 recorded for testing true write concurrency under SQLite (`test_cases.md` QF-02 there) applies again here and is recorded again in this story's own `test_cases.md` QF-04.
- **Reading a created transaction back is out of scope.** This story is verified through what `POST /api/v1/transactions` itself returns and through direct inspection of the stored `transactions` and `wallets` rows — there is no `GET` endpoint yet (TM-US-02/03).
- **This story never reads or writes the `budgets` table.** Computing spending-vs-budget progress or triggering a 75%/100% threshold alert is BM-US-03's job (SDS §2.4.3 Budget Monitoring State machine), out of scope here even though a Transaction is exactly the kind of event that state machine eventually reacts to.
