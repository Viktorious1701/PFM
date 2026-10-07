# Feature Specification: Transaction Management (TM)

> **Feature:** SRS §6 Feature-06 · SDS §5.6 (TM)
> **Spec:** [spec.md](spec.md)
> **Stories in this file:** TM-US-01 *(implemented, verified — 36/36 TC PASS)* · TM-US-02 *(implemented, verified — 36/36 TC PASS)* · TM-US-03 *(implemented, verified — 10/10 TC PASS)* · TM-US-04 *(implemented, verified — 30/30 TC PASS)* · TM-US-05 *(spec/design/quality drafted — not yet implemented)*

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

---

## TM-US-02: List Transactions

> **IDs in this section are local to TM-US-02.** `AC-01` below is not TM-US-01's `AC-01`; each
> story section numbers its own criteria, per `artifact-templates/spec-templates.md` and this
> epic file's own TM-US-01 precedent. Only `TC-NN` in `test_cases.md` runs continuously across the
> epic (`CLAUDE.md` §1.1 rule 4) — this story continues from `TC-37`.

### Source *(scope extraction — CLAUDE.md §1 scope rule)*

**SRS §6 Feature-06 · US-06-02 — quoted in full**
> #### US-06-02: View List of Transactions [MVP]

The line above is the entire SRS entry for this story — no "As a/I want/So that" statement, no
Gherkin scenario. The same thinness WM-US-02's own SRS entry (`US-03-02`) carried, and the expected
condition for this story per this repo's own precedent, not a transcription error or a source
contradiction — no `[NEEDS RULING]` follows from it.

**SDS §5.6.2 TM-US-02 (USER)**
> #### 5.6.2 TM-US-02: List Transactions (USER)
> * **Goal:** Query and filter logged transactions by wallet, category, or date range.

Unlike WM-US-02's own SDS entry ("Display all wallets owned by the logged-in user" — no filtering
language at all), this story's own goal sentence explicitly names three filter dimensions as this
story's own scope. See *Assumptions & Dependencies* for how that is resolved.

**SRS §1.5 Conceptual Domain Model**
> | Relationship | Cardinality | Meaning |
> | User owns Wallet | one User → many Wallets | A User may hold several Wallets — cash, bank, credit (FR-03) |
> | Wallet contains Transaction | one Wallet → many Transactions | Every Transaction moves money into or out of exactly one Wallet (FR-06) |
> | Category classifies Transaction | one Category → many Transactions | Every Transaction is tagged with exactly one Category (FR-06) |

The three relationships together are why this story's ownership scoping is transitive through two
hops rather than one: a User owns Wallets directly, a Transaction belongs to exactly one Wallet, and
a User may hold **more than one** Wallet — so "the caller's own transactions" means every Transaction
whose Wallet the caller owns, potentially spanning several Wallets at once.

**SDS §2.1 Domain Layer Traceability**
> | **Transaction** | `transactions` | `TransactionModel` | `TransactionRead`, `TransactionCreate` |

**SDS §6.3 API Index**
> | **TM-API-01** | `POST` | `/api/v1/transactions` | Record a transaction |

*(Observation, not acted on: unlike WM-API-02, SDS §6.3's API Index has no row at all for a
list-transactions endpoint — not merely missing from §6.5's traceability table the way WM-US-02
found for `WM-API-02`, but absent from the Index itself. A pre-existing gap in `SDS.md`, left as-is
— this dispatch's scope is limited to the three files in `specs/006-transaction-management/` and
does not extend to editing `SDS.md`.)*

**constitution.md API-06, PF-02, PF-04, SEC-08**
> **API-06** List endpoints accept `page` and `page_size`; default 25, maximum 100. Responses carry
> a total count.
> **PF-02** Columns used in `WHERE`, `JOIN`, or `ORDER BY` carry an index. No N+1 query patterns.
> **PF-04** List endpoints are always bounded (see API-06). No unbounded result set reaches a client.
> **SEC-08** Queries for user-owned data filter on the authenticated `user_id` at the repository
> layer (SDS §7.2, SRS NFR-06).

### Out of scope for this story

TM-US-01 (create a transaction) · TM-US-03 (view a single transaction) · TM-US-04 (update a
transaction) · TM-US-05 (delete a transaction) · BM-US-02..05 · WM-US-03..05 · CM-US-02..05 ·
UM-US-04/05, DC-US-01/02 · Features 07 (Financial Reporting), 08 (Notifications), 09 (Dashboard) ·
SRS §6 Feature-10/11 placeholders.

Deliberately excluded even though adjacent: viewing a single transaction's full detail beyond what
this list already carries (TM-US-03); editing or removing a transaction (TM-US-04/05); creating one
(TM-US-01, already delivered); any spending-vs-budget computation or the 75%/100% threshold alert
(BM-US-03's job, per TM-US-01's own Out-of-scope note); and sorting or filtering by anything other
than the dimensions named below — no free-text search, no amount-range filter, no filtering by
transaction type, since neither SRS nor SDS names any of those for this story.

### User Scenarios & Testing *(mandatory)*

As an **authenticated User**, I want to view the transactions logged against the wallets I own, and
narrow that view by wallet, category, or date range, so that I can review my own spending and income
history without paging through every wallet's activity by hand.

**Acceptance Criteria**:

**AC-01: Successfully list every transaction belonging to every wallet the caller owns**
**Given** an authenticated User who owns one or more wallets, each carrying one or more transactions,
**When** the User requests the list of transactions with no filter applied,
**Then** the system returns every transaction belonging to any wallet that User owns — regardless of
which of the User's own wallets it belongs to — each carrying its identifier, wallet reference,
category reference, amount, type, timestamp, and note, together with the total number of matching
transactions.

**AC-02: Return an empty list for a User with no transactions yet**
**Given** an authenticated User who owns no transactions — whether because they own no wallets at
all, or their wallets have none logged against them,
**When** the User requests the list,
**Then** the system returns an empty list of transactions together with a total of zero, not an
error.

**AC-03: Deny access to unauthenticated callers**
**Given** a caller presenting no credentials, or credentials that are invalid or expired,
**When** the caller attempts to list transactions,
**Then** the system denies the request before evaluating any query parameter, returns nothing, and
returns an unauthenticated error.

**AC-04: Bound and paginate the result by default**
**Given** an authenticated User,
**When** the User requests the list without specifying a page or page size,
**Then** the system returns at most 25 of that User's matching transactions on the first page,
together with the total number of matching transactions.

**AC-05: Accept an explicit page and page size within range**
**Given** an authenticated User,
**When** the User requests a specific page together with a page size up to the maximum of 100,
**Then** the system returns that page of the User's own matching transactions and the same accurate
total.

**AC-06: Reject a page or page size outside the allowed range**
**Given** an authenticated User,
**When** the requested page or page size is zero, negative, otherwise not a positive integer, or a
page size greater than 100,
**Then** the system rejects the request with a validation error identifying the offending parameter,
and returns no transactions.

**AC-07: A User only ever sees transactions belonging to wallets they own**
**Given** at least two Users, each owning one or more wallets with transactions logged against them,
**When** one of them requests the list,
**Then** the response's transactions are exactly the ones belonging to wallets owned by the
requesting User — none belonging to a wallet owned by any other User appears — and the reported
total counts only the requesting User's own matching transactions, never every transaction in the
system.

**AC-08: Return the list in a stable, most-recent-first order**
**Given** an authenticated User who owns two or more transactions, with nothing created, changed, or
removed in between,
**When** the User requests the same page more than once, or requests adjacent pages of one paging
sequence,
**Then** the system returns the transactions ordered from most recently created to least, and that
order is identical every time and consistent across those adjacent pages — including a deterministic
relative order for any two transactions recorded at the same instant.

**AC-09: Reuse the documented per-transaction fields, wrapped in a paginated envelope**
**Given** an authenticated User requests the list,
**When** the system returns the result,
**Then** each entry carries exactly the fields a created transaction already carries — identifier,
wallet reference, category reference, amount, type, timestamp, and note — no more, no other User's
data, and no field this story invents — and the overall response additionally carries the total
count, the page number, and the page size.

**AC-10: Narrow the list to one wallet**
**Given** an authenticated User who owns two or more wallets, each with transactions logged against
it,
**When** the User requests the list naming one of those wallets,
**Then** the system returns only the transactions belonging to that one wallet, and the reported
total counts only that wallet's matching transactions.

**AC-11: A wallet filter that does not resolve to the caller's own wallet yields an empty result, not an error**
**Given** an authenticated User,
**When** the User requests the list naming a wallet reference that matches no wallet at all, or
matches a wallet owned by a different User,
**Then** the system returns an empty list of transactions together with a total of zero in either
case — identically, with nothing in the response distinguishing the two.

**AC-12: Narrow the list to one category**
**Given** an authenticated User who owns transactions logged under two or more categories,
**When** the User requests the list naming one of those categories,
**Then** the system returns only the transactions logged under that one category, and the reported
total counts only that category's matching transactions.

**AC-13: A category filter that does not resolve to the caller's own category yields an empty result, not an error**
**Given** an authenticated User,
**When** the User requests the list naming a category reference that matches no category at all, or
matches a category owned by a different User,
**Then** the system returns an empty list of transactions together with a total of zero in either
case — identically, with nothing in the response distinguishing the two.

**AC-14: Narrow the list to a date range**
**Given** an authenticated User who owns transactions recorded at different times,
**When** the User requests the list naming a start of range, an end of range, or both,
**Then** the system returns only the transactions whose recorded time falls within the named range,
inclusive of a transaction recorded at exactly a named boundary.

**AC-15: Reject a date range whose start is after its end**
**Given** an authenticated User,
**When** the User requests the list naming both a start and an end of range, and the named start is
later than the named end,
**Then** the system rejects the request with a validation error, and returns no transactions.

**AC-16: Filters narrow the result together, never separately**
**Given** an authenticated User who owns transactions matching some, but not all, of several filter
dimensions at once,
**When** the User requests the list naming more than one filter at the same time,
**Then** the system returns only the transactions matching every named filter at once — never a
transaction that matches only some of them.

### Edge Cases

**EC-01**: **A page number beyond the last available page** — returns an empty list of transactions
together with the accurate, caller-scoped total, not a not-found error.

**EC-02**: **Page size at the exact maximum** — a page size of exactly 100 is accepted; 101 is
rejected under AC-06. The cap is a ceiling, not a target.

**EC-03**: **More transactions than fit on one page** — paging through every page with a fixed page
size returns every one of the caller's own matching transactions exactly once, with no duplicate and
no gap, in the same stable order AC-08 establishes.

**EC-04**: **A caller whose role is ADMIN, who also owns wallets and transactions** — sees, through
this endpoint, only the transactions belonging to wallets that caller owns. Nothing about this
endpoint grants an ADMIN visibility into another User's transactions; this route has no ADMIN-wide
sense at all — it is scoped to the caller regardless of role.

**EC-05**: **Only a start of range is named** — every transaction recorded at or after that instant
is included, with no upper limit.

**EC-06**: **Only an end of range is named** — every transaction recorded at or before that instant
is included, with no lower limit.

**EC-07**: **A named start of range equal to a named end of range** — accepted, not rejected as an
empty or invalid range; a transaction recorded at exactly that instant is included, matching the
inclusive boundary AC-14 establishes.

**EC-08**: **Two transactions recorded at the same instant** — the list still places them in a
deterministic relative order, identical on every request, rather than leaving their relative order
to chance.

**EC-09**: **A wallet filter value that is not even a well-formed identifier** — a value such as
`"not-a-real-id"` produces the identical empty-result outcome AC-11 describes for a well-formed but
non-existent or not-owned reference. No separate malformed-identifier error exists.

**EC-10**: **A category filter value that is not even a well-formed identifier** — produces the
identical empty-result outcome AC-13 describes, for the same reason as EC-09.

**EC-11**: **A caller who owns more than one wallet, each with its own transactions** — an unfiltered
request returns transactions from every one of the caller's own wallets together, correctly ordered
as one combined, most-recent-first sequence rather than grouped or limited to a single wallet.

### Requirements *(mandatory)*

#### Functional Requirements

- **FR-01**: The system must **allow** an authenticated User of any role to retrieve the list of
  transactions belonging to wallets they own (SDS §5.6.2; mirrors TM-US-01 FR-01's "any role"
  treatment).
- **FR-02**: The system must **include**, for every listed transaction, its identifier, wallet
  reference, category reference, amount, type, timestamp, and note — the same fields TM-US-01
  already defined for a single created transaction (SDS §2.2; TM-US-01 AC-18; constitution PF-03).
- **FR-03**: The system must **deny** the operation to unauthenticated callers, evaluating
  credentials before any query parameter (constitution API-08; mirrors TM-US-01 FR-02, WM-US-02
  FR-03).
- **FR-04**: The system must **accept** `page` and `page_size` query parameters, defaulting to page 1
  and page size 25 when omitted (constitution API-06).
- **FR-05**: The system must **reject** a `page` or `page_size` value that is not a positive integer,
  or a `page_size` greater than 100, with a validation error (constitution API-06, PF-04).
- **FR-06**: The system must **return**, alongside every page, the total number of transactions
  matching the request (constitution API-06).
- **FR-07**: The system must **filter** every transaction query this endpoint issues — both the
  bounded page of items and the total count — to only transactions belonging to a wallet owned by the
  authenticated caller (constitution SEC-08; plan.md A2).
- **FR-08**: The system must **order** the returned transactions from most recently recorded to
  least, breaking a tie between two transactions recorded at the same instant by a second,
  deterministic key, consistently across pages of the same request pattern (plan.md A4).
- **FR-09**: The system must **accept** an optional wallet filter, narrowing the result to
  transactions belonging to that one wallet; a value that does not resolve to a wallet the caller owns
  — whether absent altogether or belonging to a different User — yields an empty result, never an
  error, with the two cases indistinguishable (AC-11, EC-09; plan.md A3).
- **FR-10**: The system must **accept** an optional category filter, narrowing the result to
  transactions logged under that one category; a value that does not resolve to a category the
  caller owns is treated identically to FR-09's wallet case (AC-13, EC-10; plan.md A3).
- **FR-11**: The system must **accept** an optional date-range filter expressed as a start, an end,
  or both, narrowing the result to transactions recorded within that range inclusive of either named
  boundary; either bound may be supplied alone (AC-14, EC-05, EC-06, EC-07).
- **FR-12**: The system must **reject**, with a validation error, a date-range filter whose named
  start is later than its named end (AC-15).
- **FR-13**: The system must **interpret** a date-range boundary carrying no explicit time zone as
  Coordinated Universal Time, consistent with every transaction's own timestamp already being
  recorded in Coordinated Universal Time (TM-US-01 BR-06; plan.md A6).
- **FR-14**: The system must **apply every supplied filter together** — a transaction is returned
  only when it matches every filter named in the request at once, never when it matches only some of
  them (AC-16).
- **FR-15**: The system must **never include**, in either the returned transactions or the reported
  total, any transaction belonging to a wallet owned by a User other than the caller, regardless of
  the caller's role or of any filter supplied (constitution SEC-08; AC-07, EC-04).

#### Business Rules

- **BR-01**: Only transactions belonging to a wallet owned by the authenticated caller are ever
  returned by this endpoint; no role — including ADMIN — grants visibility into another User's
  transactions through this route (SDS §5.6.2 "(USER)"; constitution SEC-08; EC-04).
- **BR-02**: A page never carries more than 100 transactions; the default when unspecified is 25
  (FR-04, FR-05; mirrors TM-US-01's own pagination-free precedent extended from WM-US-02 BR-02).
- **BR-03**: Transactions are ordered from most recently recorded to least, with a deterministic
  tie-break for two transactions recorded at the same instant, consistently across pages of the same
  request pattern (FR-08; plan.md A4).
- **BR-04**: The reported total always equals the count of the caller's own matching transactions —
  scoped by ownership and narrowed by every filter supplied — never a system-wide or
  partially-filtered count (FR-06, FR-07, FR-14, FR-15).
- **BR-05**: A wallet or category filter that does not resolve to a row the caller owns is refused
  identically whether no such row exists at all or it exists and belongs to a different User — both
  produce an empty result, never an error and never a distinguishing signal (FR-09, FR-10).
- **BR-06**: A date-range filter's named start must not be later than its named end; a boundary
  carrying no explicit time zone is interpreted as Coordinated Universal Time (FR-12, FR-13).
- **BR-07**: Every filter supplied narrows the result; filters never widen it, and no filter narrows
  past — or substitutes for — the ownership scope BR-01 establishes (FR-14, FR-15).

#### Key Entities

- **Transaction**: A single recorded movement of money, in or out, against one Wallet and one
  Category, at a point in time (SRS §1.5; TM-US-01). This story only reads transactions TM-US-01
  already created — it creates, updates, and deletes none.
- **Wallet**: Reused from WM-US-01 with no new column. A User may own several (SRS §1.5 "User owns
  Wallet"), which is why this story's unfiltered result can span more than one wallet at once
  (EC-11) — the first list in this codebase whose ownership scope is not a single-column match on
  the listed entity itself, but transitive through the Wallet each Transaction belongs to.
- **Category**: Reused from CM-US-01 with no new column. Referenced by this story only as an
  optional filter and as a field already carried by each transaction; not itself queried for
  ownership by this story (see *Assumptions & Dependencies*).
- **User**: Reused from Feature-01/Feature-02 with no new column. The authenticated caller's own
  identifier is the only scope this story ever queries by, reached through the wallets the caller
  owns (constitution SEC-08).

### Success Criteria *(mandatory)*

- **SC-01**: An authenticated User can retrieve every transaction belonging to every wallet they
  own, across their whole matching set, in one paginated call.
- **SC-02**: No request to this endpoint can return an unbounded number of rows.
- **SC-03**: No User can see another User's transaction, or another User's transaction count,
  through this endpoint, regardless of role or of any filter supplied.
- **SC-04**: A User can page through their entire matching transaction set with an accurate total
  and no duplicated or skipped transaction.
- **SC-05**: A User with no matching transactions receives an empty list and a zero total, never an
  error.
- **SC-06**: A wallet, category, or date-range filter — alone or combined — narrows the result to
  exactly the transactions matching every filter supplied, and never surfaces a transaction outside
  the caller's own ownership scope regardless of what filter value is supplied, including a value
  that does not resolve to anything the caller owns.
- **SC-07**: The list is always returned most-recently-recorded first, with a deterministic,
  stable relative order — including between two transactions recorded at the same instant —
  consistent across repeated requests and adjacent pages.

### Assumptions & Dependencies

- **Login (SS-US-01) and TM-US-01 (Create a Transaction) are already implemented** — there is
  nothing to list otherwise, mirroring how WM-US-02 depended on WM-US-01 and UM-US-03 depended on
  UM-US-01.

- **`SRS.md` §6 US-06-02 carries no Gherkin at all** — only the bare header, the same condition
  WM-US-02's own SRS entry was in. `SDS.md` §5.6.2 supplies one sentence, but unlike WM-US-02's own
  one-sentence goal, this one explicitly names filtering as this story's own scope. Recorded once,
  here, rather than against each AC — this is the expected condition for this story, not a source
  contradiction, so no `[NEEDS RULING]` follows from it.

- **The filter-scope decision.** SDS §5.6.2's own goal sentence for *this* story — not a future one
  — names all three dimensions: "Query and filter logged transactions by wallet, category, or date
  range." Unlike WM-US-02 (whose own SDS goal said only "Display all wallets," naming no filter at
  all, so WM-US-02 correctly declared filtering out of scope), and unlike this same epic's own
  TM-US-03..05 (each a distinct, separately-numbered story for a distinct operation), there is no
  further, separately-numbered "Filter Transactions" story in SDS §5.6 for this language to belong
  to instead. Building fewer than all three dimensions now would mean declining current-story scope
  SDS names explicitly, with no source disagreement to justify the omission — the opposite failure
  from scope creep, but still a failure to align the delivered story to its own reference document
  (`CLAUDE.md` §1, "Aligning the SDS *to the code* is routine" runs the other way when the SDS
  already states the scope and the code is what has not caught up). All three are therefore built as
  independent, combinable, optional filters on this same endpoint. Full design in `plan.md` A1.

- **The ownership-filter design.** `TransactionModel` carries no `user_id` (TM-US-01 A11) — every
  ownership scope this story applies is transitive through `wallet_id` → the owning wallet's own
  `user_id`. Unlike WM-US-02 (a single-table `WHERE user_id = :caller_id`), this is the first list
  query in this codebase requiring a join to establish ownership, and it must scope both the bounded
  page and the total count identically — the same discipline WM-US-02 A3/`test_cases.md` QF-05
  established for a single-table filter, now extended to a join. A category filter needs no separate
  ownership join of its own: TM-US-01 BR-01 already guarantees, at creation time, that a
  transaction's `category_id` belongs to the same User who owns its `wallet_id` — so a category
  belonging to a different User can never match a transaction the wallet-ownership join already
  admits. Full design and its standing dependency on that invariant: `plan.md` A2.

- **The ordering decision.** Unlike `WalletModel` (no `created_at`, forcing WM-US-02 A1 to fall back
  to the primary key), `TransactionModel.timestamp` is a real, meaningful moment already established
  by TM-US-01 BR-06 as always the instant of creation. This story orders by it, most-recent-first —
  the natural reading of "view list of transactions" for a ledger, and the same direction UM-US-03
  already chose for `users.created_at` when a genuine creation timestamp was available. A
  most-recent-first order needs a deterministic tie-break for two transactions recorded at the same
  instant (EC-08) — full reasoning in `plan.md` A4.

- **The indexing decision.** TM-US-01's own `plan.md` domain-objects table flagged this by name:
  *"`timestamp` carries no index this story — TM-US-02 (list/filter, out of scope) is the story with
  an actual query to justify one."* This story is that story. Constitution PF-02 governs which
  column(s); full reasoning in `plan.md` A5.

- **The response envelope.** This story reuses `TransactionRead` **unchanged** as the per-item shape
  — no embedded wallet or category name — wrapped in a new envelope, `TransactionListRead { items,
  total, page, page_size }`, mirroring `WalletListRead` (WM-US-02 A2) and `UserListRead` (UM-US-03
  A6) exactly. Considered and rejected: enriching each item with its wallet's and category's own
  `name` for display convenience, which would break the unbroken precedent every existing list in
  this codebase follows (WM-US-02 A2, UM-US-03 A6) and the precedent TM-US-01 A14 itself set for
  `TransactionRead` ("no other entity's data folded in"), and which no source document asks for —
  SDS §5.6.2's own goal sentence is about filtering, not about response enrichment. Full reasoning:
  `plan.md` A8.

- **Reading a single transaction's full detail is out of scope.** This story is verified entirely
  through the list endpoint's own envelope; there is no `GET /transactions/{id}` yet (TM-US-03).

- **This story never reads or writes the `budgets` table**, for the same reason TM-US-01 already
  recorded: BM-US-03 owns spending-vs-budget computation, not this story, even though a listed
  Transaction is exactly the kind of record that computation eventually reads.

---

## TM-US-03: View a Transaction

> **IDs in this section are local to TM-US-03.** `AC-01` below is not TM-US-01's or TM-US-02's own
> `AC-01`; each story section numbers its own criteria, per `artifact-templates/spec-templates.md`
> and this epic file's own TM-US-01/TM-US-02 precedent. Only `TC-NN` in `test_cases.md` runs
> continuously across the epic (`CLAUDE.md` §1.1 rule 4) — this story continues from `TC-73`.

### Source *(scope extraction — CLAUDE.md §1 scope rule)*

**SRS §6 Feature-06 — searched in full; no entry for "view a single transaction" exists**
> `### Feature-06: Transaction Management` contains exactly three story headers: `#### US-06-01:
> Create a Transaction for a Wallet [MVP]` (with Gherkin, quoted in full in this file's TM-US-01
> section), a bare `#### US-06-02: View List of Transactions [MVP]`, and a bare `#### US-06-03:
> Update/Delete a Transaction` (no `[MVP]` tag, no Gherkin). There is no fourth header, and no entry
> of any kind for viewing one transaction by itself — thinner anchoring than even TM-US-02 had, which
> at least got a bare header of its own. Grounded instead in SRS §1.5's domain model and SRS §2
> FR-06's text directly, the same way BM-US-02/CM-US-02 grounded their own no-SRS-header situations
> (see *Assumptions & Dependencies*). Not a source contradiction, so no `[NEEDS RULING]` follows.

**SRS §1.5 Conceptual Domain Model**
> **Transaction** — A single recorded movement of money, in or out, against one Wallet and one
> Category, at a point in time (FR-06).
>
> | Relationship | Cardinality | Meaning |
> | Wallet contains Transaction | one Wallet → many Transactions | Every Transaction moves money
> into or out of exactly one Wallet (FR-06) |
> | Category classifies Transaction | one Category → many Transactions | Every Transaction is
> tagged with exactly one Category (FR-06) |

**SRS §2 FR-06 — Transaction Management**
> The System shall allow Users to log income and expense Transactions against a designated Wallet
> and Category. The System shall automatically recalculate and persist wallet balances atomically.

**SDS §5.6.3 TM-US-03: View a Transaction (USER)**
> **Goal:** View detailed information for a single transaction item.

One sentence — the same thinness every other Transaction Management story's own SDS goal carried
before it (TM-US-02's own Source section already made this observation for itself).

**SDS §6.3 API Index**
> No row exists for any single-transaction read endpoint — the same pre-existing gap TM-US-02's own
> Source section already found and left alone; this dispatch's scope is the three files in
> `specs/006-transaction-management/`, not `SDS.md`.

**SDS §2.2 Domain Object** *(reused, unchanged by this story)*
> **Transaction:** Ledger entry representing monetary movement (`id`, `wallet_id`, `category_id`,
> `amount`, `type`, `timestamp`, `note`).

**constitution.md SEC-08, VL-06**
> SEC-08: Queries for user-owned data filter on the authenticated `user_id` at the repository layer.
> VL-06: Referenced entities are verified to exist and be active before use — `404` if absent, `409`
> if present but in the wrong state.

**`specs/006-transaction-management/spec.md` TM-US-01 BR-01** *(this story's own inherited precedent)*
> "A transaction's wallet and its category must each belong to the authenticated caller; the
> transaction itself carries no owner column of its own, so its ownership is entirely transitive
> through `wallet_id` and `category_id`."

### Out of scope for this story

TM-US-01 (create a transaction) · TM-US-02 (list transactions) · TM-US-04 (update a transaction) ·
TM-US-05 (delete a transaction) · BM-US-02..05 · WM-US-03..05 · CM-US-03..05 · UM-US-04/05,
DC-US-01/02 · Features 07 (Financial Reporting), 08 (Notifications), 09 (Dashboard) · SRS §6
Feature-10/11 placeholders.

Deliberately excluded even though adjacent: changing or removing the viewed transaction
(TM-US-04/05); any field beyond the seven TM-US-01 already established — in particular, no embedded
wallet name, category name, or any other entity's data folded into the response, which stays a
client-side concern exactly as TM-US-02's own Assumptions already settled for the list endpoint; and
any spending-vs-budget computation or the 75%/100% threshold alert (BM-US-03's own job, per
TM-US-01/02's own Out-of-scope notes).

### User Scenarios & Testing *(mandatory)*

As an **authenticated User**, I want to view the full detail of one of my own transactions by its
own identifier, so that I can inspect a single entry from my spending or income history without
paging through the whole list to find it.

**Acceptance Criteria**:

**AC-01: Successfully view a transaction the caller owns**
**Given** an authenticated User who owns a wallet with a transaction logged against it,
**When** the User requests that transaction by its own identifier,
**Then** the system returns a success result carrying exactly that transaction's identifier, wallet
reference, category reference, amount, type, timestamp, and note, matching what was recorded.

**AC-02: Deny access to unauthenticated callers**
**Given** a caller presenting no credentials, or credentials that are invalid or expired,
**When** the caller attempts to view a transaction,
**Then** the system denies the request before evaluating the submitted reference, returns nothing,
and returns an unauthenticated error.

**AC-03: Reject a transaction reference that does not exist at all**
**Given** an authenticated User,
**When** the submitted transaction reference matches no transaction in the system,
**Then** the system returns a not-found error.

**AC-04: Reject a transaction reference belonging to a different User**
**Given** an authenticated User,
**When** the submitted transaction reference matches a transaction belonging to a wallet owned by a
different User,
**Then** the system returns the same not-found outcome AC-03 describes — the response gives no
indication of which of the two happened.

**AC-05: Return exactly the documented transaction fields**
**Given** an authenticated User successfully views one of their own transactions,
**When** the system returns the success result,
**Then** the result carries exactly the transaction's identifier, wallet reference, category
reference, amount, type, timestamp, and note — no other field, no embedded wallet or category name,
and no data belonging to any other User's wallet or category.

### Edge Cases

**EC-01**: **A transaction reference that is not even a well-formed identifier** — a value such as
`"not-a-real-id"` is refused with the same not-found outcome as a well-formed but non-existent
reference (AC-03). No separate malformed-identifier error exists; a reference either resolves to a
transaction the caller owns, or it does not, regardless of its shape.

**EC-02**: **A caller who owns one or more transactions of their own, attempting to view a different
User's transaction** — refused with the identical outcome AC-04 describes; owning some transaction
never entitles a caller to view another User's transaction.

**EC-03**: **A caller whose role is ADMIN, attempting to view a transaction they do not themselves
own** — refused exactly as EC-02 describes for any other caller. This endpoint has no ADMIN-wide
sense at all; it is scoped to the caller regardless of role, the same scoping TM-US-02 EC-04 already
established for the list endpoint.

### Requirements *(mandatory)*

#### Functional Requirements

- **FR-01**: The system must **allow** an authenticated User of any role to retrieve a single
  transaction they own by its own identifier (SDS §5.6.3; mirrors TM-US-01 FR-01, TM-US-02 FR-01).
- **FR-02**: The system must **deny** the operation to unauthenticated callers, evaluating
  credentials before the submitted reference (constitution API-08; mirrors TM-US-01 FR-02, TM-US-02
  FR-03).
- **FR-03**: The system must **require** the submitted transaction reference to resolve to a
  transaction belonging to a wallet owned by the authenticated caller, and **refuse** the request
  with an identical outcome whether no such transaction exists at all or it exists and belongs to a
  wallet owned by a different User (AC-03, AC-04, EC-01, EC-02; constitution SEC-08, VL-06).
- **FR-04**: The system must **never grant** greater visibility to a caller whose role is ADMIN —
  this operation is scoped to the caller regardless of role, with no role-wide view of another
  User's transactions (EC-03; mirrors TM-US-02 FR-15).
- **FR-05**: The system must **return**, on success, exactly the transaction's identifier,
  `wallet_id`, `category_id`, `amount`, `type`, `timestamp`, and `note` — the same seven fields
  TM-US-01 already established, no other field, and no other entity's data folded in (AC-05;
  constitution PF-03).

#### Business Rules

- **BR-01**: A transaction's ownership for this operation is established the same way TM-US-01 BR-01
  already established it for creation and TM-US-02 BR-01 for listing — entirely transitive through
  the transaction's own `wallet_id`, since the transaction carries no owner column of its own. A
  transaction reference that does not resolve to a row the caller owns is refused identically
  whether no such row exists at all or it exists and belongs to a different User (FR-03).
- **BR-02**: No role — including ADMIN — grants visibility into another User's transaction through
  this operation (FR-04).

#### Key Entities

- **Transaction**: A single recorded movement of money, in or out, against one Wallet and one
  Category, at a point in time (SRS §1.5; TM-US-01). This story only reads one transaction TM-US-01
  already created, identified by its own id — the first story in this codebase to fetch a single
  Transaction by its own identifier rather than creating one (TM-US-01) or listing many (TM-US-02);
  it creates, updates, and deletes none.
- **Wallet**: Reused from WM-US-01 with no new column. Referenced, not owned, by this story — a
  transaction's ownership for the purpose of this read is reached through `wallet_id`, the same path
  TM-US-01/02 already established.
- **Category**: Reused from CM-US-01 with no new column. Referenced by this story only as a field
  already carried by the transaction; not itself queried for ownership by this story, the same
  treatment TM-US-02 already gave it.
- **User**: Reused from Feature-01/Feature-02 with no new column. The authenticated caller's own
  identifier, reached through the wallet the viewed transaction belongs to, is the only scope this
  story ever queries by (constitution SEC-08).

### Success Criteria *(mandatory)*

- **SC-01**: An authenticated User can retrieve the full detail of any one of their own
  transactions, by its own identifier, in one call, and the response reflects exactly what is
  stored.
- **SC-02**: No transaction can be viewed without an authenticated caller.
- **SC-03**: A transaction can never be viewed by a User who does not own it — whether because the
  reference does not exist at all or belongs to someone else — refused identically in both cases,
  regardless of the caller's role.
- **SC-04**: The response for a single transaction always carries exactly the same seven fields a
  created or listed transaction already carries — no more, no fewer, and no other entity's data
  folded in.

### Assumptions & Dependencies

- **Login (SS-US-01) and TM-US-01 (Create a Transaction) are already implemented** — there is
  nothing to view otherwise, mirroring how TM-US-02 depended on the same two stories.
- **`SRS.md` §6 has no entry at all for this story** — not even a bare header the way TM-US-02's
  `US-06-02` got one. `US-06-03`'s own header ("Update/Delete a Transaction") is the closest-numbered
  SRS entry, and it names a different operation entirely. Grounded instead directly in SRS §1.5's
  domain model and SRS §2 FR-06's text, the same way BM-US-02/CM-US-02 grounded their own
  no-SRS-header stories. Recorded once, here, rather than against each AC — this is the expected
  condition for this story, not a source contradiction, so no `[NEEDS RULING]` follows from it.
- **This is the first single-resource "view by id" story in this codebase.** No WM/CM/BM epic has
  built one yet either: Budget's own `03` slot (BM-US-03) is a different kind of story (computed
  status/alerts over the list, not a fetch-one-by-id read), and WM-US-03/CM-US-03 are unbuilt. The
  closest shape-precedent is BM-US-04 (Update a Budget)'s own `get_owned_by_id()` — read for the
  *pattern* of "fetch one row scoped to the caller, refuse identically whether absent or not owned,"
  not because this story updates anything. Full design reasoning, stated in this story's own terms
  rather than assumed to transfer automatically from Budget's: `plan.md` A1.
- **The response reuses `TransactionRead` unchanged — no new DTO, no enrichment.** TM-US-01 A14 and
  TM-US-02 A8 already settled, for this exact entity, that no other entity's data is folded into a
  transaction response; this story adds nothing new to that reasoning, it simply applies again to a
  single-item read. Mobile-side name resolution is this app's own established pattern for exactly
  this gap — `mobile/app/(tabs)/transactions/index.tsx`'s own header comment states it directly:
  "`TransactionRead` carries only `wallet_id`/`category_id`... never a display name — so wallets and
  categories are fetched up front... [to render] each row's name/currency/glyph."
- **No transaction-detail screen exists in `mobile/` this round** — confirmed directly in
  `mobile/app/(tabs)/transactions/index.tsx`'s own source comments, which name this story by number
  as a screen that prototype deliberately does not build ("TM-US-03/04 (a transaction-detail screen)
  are out of scope"). No SRS UXR names a transaction-detail screen either.
- **This story never reads or writes the `budgets` table**, for the same reason TM-US-01/02 already
  recorded: BM-US-03 owns spending-vs-budget computation, not this story.

---

## TM-US-04: Update a Transaction

> **IDs in this section are local to TM-US-04.** `AC-01` below is not TM-US-01/02/03's own `AC-01`;
> each story section numbers its own criteria, per `artifact-templates/spec-templates.md` and this
> epic file's own TM-US-01/02/03 precedent. Only `TC-NN` (and `QF-NN`) in `test_cases.md` run
> continuously across the epic (`CLAUDE.md` §1.1 rule 4) — this story continues from `TC-83`/`QF-16`,
> confirmed by direct count of this file's own last entries (`TC-82`, `QF-15`).

### Source *(scope extraction — CLAUDE.md §1 scope rule)*

**SRS §6 Feature-06 — searched in full; confirmed still accurate**
> `### Feature-06: Transaction Management` contains exactly three story headers: `#### US-06-01:
> Create a Transaction for a Wallet [MVP]` (Gherkin, TM-US-01's own section), a bare `#### US-06-02:
> View List of Transactions [MVP]` (TM-US-02), and a bare `#### US-06-03: Update/Delete a
> Transaction` — **one combined header for both this story and TM-US-05**, no `[MVP]` tag, no
> Gherkin, no "As a/I want/So that" statement. There is no separate `US-06-04` header distinguishing
> update from delete the way SDS §5.6 does (SDS §5.6.4 "TM-US-04" vs §5.6.5 "TM-US-05", confirmed
> below). Not a source contradiction — the same thinness TM-US-02/03's own Source sections already
> found and worked around, now extended one header further: SRS bundles two SDS-distinct operations
> under one bare title. No `[NEEDS RULING]` follows; this story is grounded in SDS §5.6.4's own
> separate entry and in SRS §1.5/§2 FR-06's text directly, the same way TM-US-03 grounded itself when
> SRS had no entry of its own at all.

**SRS §1.5 Conceptual Domain Model**
> **Transaction** — A single recorded movement of money, in or out, against one Wallet and one
> Category, at a point in time (FR-06).
>
> | Relationship | Cardinality | Meaning |
> | Wallet contains Transaction | one Wallet → many Transactions | Every Transaction moves money
> into or out of exactly one Wallet (FR-06) |
> | Category classifies Transaction | one Category → many Transactions | Every Transaction is
> tagged with exactly one Category (FR-06) |

**SRS §2 FR-06 — Transaction Management**
> The System shall allow Users to log income and expense Transactions against a designated Wallet
> and Category. The System shall automatically recalculate and persist wallet balances atomically.

**SDS §5.6.4 TM-US-04: Update a Transaction (USER)**
> **Goal:** Edit transaction details and automatically recalculate wallet balances.

One sentence — the same thinness every other Transaction Management story's own SDS goal carried
before it. Unlike TM-US-02's own goal sentence (which named its three filter dimensions explicitly),
this one names no specific field — "transaction details" is read against SRS §1.5's own enumeration
of what a Transaction carries (`amount`, `type`, `category_id`, `note` — `wallet_id`/`id`/`timestamp`
excluded for the reasons in *Assumptions & Dependencies*), the same style of reading BM-US-04 A1 gave
its own equally bare "Adjust spending caps" goal.

**SDS §6.3 API Index**
> Confirmed stale, not a contract to match — the same pre-existing gap TM-US-02/03's own Source
> sections already found: it lists no row for any already-shipped Transaction endpoint beyond
> `TM-API-01` (create), so its silence on an update endpoint carries no meaning one way or the other.

**constitution.md API-03, API-05**
> API-03: HTTP status codes: `200` read/update … — an update response is `200`, not `201`.
> API-05: No generic `updateStatus` endpoint. Each business state transition gets its own explicit
> endpoint.

**constitution.md AR-06**
> Multi-entity writes execute in **one** transaction. Services never call `commit()`; the router owns
> the commit boundary.

**constitution.md VL-06, VL-07, SEC-08**
> VL-06: Referenced entities are verified to exist and be active before use — `404` if absent, `409`
> if present but in the wrong state.
> VL-07: Monetary values use `Decimal` with `DECIMAL(15,2)` precision. Never float.
> SEC-08: Queries for user-owned data filter on the authenticated `user_id` at the repository layer.

**`specs/005-budget-management/spec.md` BM-US-04 "Assumptions & Dependencies"** *(this story's own closest-shape precedent — the only prior "Update" story in this codebase, and the one this story's own wallet-immutability reasoning is weighed against)*
> "Only `amount_limit` is updatable; `wallet_id`, `category_id`, and `period` have no corresponding
> field on the request DTO at all... Accepting a new `wallet_id`/`category_id`/`period` would reopen
> BM-US-01 BR-05's uniqueness constraint in a materially harder form... None of that is asked for by
> any source, and the single-field reading leaves BR-05 structurally inapplicable here."

**`specs/004-category-management/spec.md` CM-US-04 "Assumptions & Dependencies"** *(the only prior
*multi*-field optional-update precedent in this codebase)*
> "All three fields are independently optional... At least one field must be given a non-None value or
> the request is refused — the first multi-field optional update contract in this codebase."

**`specs/006-transaction-management/spec.md` TM-US-01 "Business Rules"** *(this story's own inherited
precedent — the balance-mutation machinery this story runs twice per request)*
> BR-03: "A transaction's `type` must equal its referenced category's own `type`."
> BR-05: "An `EXPENSE` transaction is refused when its amount exceeds the wallet's current balance at
> the moment of the request... and never applies to an `INCOME` transaction."
> BR-07: "The new transaction row and the wallet's balance update are written as a single atomic
> unit; a failure anywhere in the operation leaves neither persisted."

### Out of scope for this story

TM-US-01/02/03 (create, list, view — all implemented) · TM-US-05 (delete a transaction) · changing a
transaction's wallet reference, reasoned through explicitly below rather than merely declined ·
BM-US-02..05 · WM-US-02..05 · CM-US-02..05 · UM-US-04/05, DC-US-01/02 · Features 07–11 · SRS §6
Feature-10/11 placeholders.

Deliberately excluded even though adjacent: **moving a transaction to a different wallet.** SDS
§5.6.4's own goal sentence is "edit transaction **details** and automatically recalculate **wallet**
balances" (singular wallet, not "wallets") — it describes one wallet's balance being recalculated,
not money moving between two. Re-targeting a transaction to a different wallet would mean reversing
its effect on the *old* wallet and applying it to a *different* wallet, a two-wallet balance
recalculation with its own ownership question (is the new wallet also the caller's own?) and no
source asks for it — the same "fewest invented rules" discipline BM-US-04 A1 already used to keep a
budget's wallet/category/period immutable, extended here to keep exactly one of a transaction's two
references immutable while leaving the other (`category_id`) genuinely editable, because nothing about
`category_id` carries the two-ledger-balance complication `wallet_id` does. Also excluded: deleting a
transaction (TM-US-05); recomputing or re-deriving any Budget's `amount_spent`, `progress_percentage`,
or `status` — those remain BM-US-02/BM-US-03's own read-time computations over whatever transactions
exist at read time, unaffected by this story except as a natural consequence of an edited amount/type
on the next such read, the same boundary TM-US-01's own Out-of-scope note already drew; and any
mobile/UI screen — confirmed directly in `mobile/app/(tabs)/transactions/index.tsx`'s own source
comments, which name "TM-US-03/04 (a transaction-detail screen)" together as out of scope for this
round's prototype.

### User Scenarios & Testing *(mandatory)*

As an **authenticated User**, I want to edit one or more of the details of a transaction I already
logged — its category, amount, type, or note — so that I can correct a mistake or reclassify an entry
without deleting and recreating it, with my wallet's balance always reflecting exactly the transaction
as it now stands rather than as it was originally recorded.

**Acceptance Criteria**:

**AC-01: Successfully update only the amount of an EXPENSE transaction**
**Given** an authenticated User who owns an `EXPENSE` transaction logged against one of their own
wallets,
**When** the User submits a new, positive amount for that transaction and no other field,
**Then** the system updates the transaction's amount, and the wallet's balance reflects exactly the
net effect of replacing the old amount's deduction with the new amount's deduction — never the sum of
both.

**AC-02: Successfully update only the amount of an INCOME transaction, regardless of the wallet's balance**
**Given** an authenticated User who owns an `INCOME` transaction logged against one of their own
wallets,
**When** the User submits a new, positive amount for that transaction and no other field,
**Then** the system updates the transaction's amount and the wallet's balance reflects exactly the net
effect of the change — accepted regardless of what the wallet's balance is at the time, exactly as an
`INCOME` transaction's amount was never balance-checked at creation. Unlike at creation time, other
transactions — including EXPENSEs that correctly passed their own sufficiency check against this
transaction's *original*, larger amount — may already exist by the time it is edited, so reducing an
INCOME transaction's amount after the fact can leave the wallet's `balance` negative with nothing to
catch it; this is not a new invalid state (WM-US-01 EC-02 already establishes a negative wallet
balance as representable and accepted), just a consequence worth naming explicitly here.

**AC-03: Successfully change a transaction's type from EXPENSE to INCOME**
**Given** an authenticated User who owns an `EXPENSE` transaction, and a category of their own typed
`INCOME`,
**When** the User submits `INCOME` as the new type together with that category,
**Then** the system reverses the expense's original effect on the wallet, applies the income's effect
instead, and the update always succeeds regardless of the wallet's balance.

**AC-04: Successfully change a transaction's type from INCOME to EXPENSE when the wallet can support it**
**Given** an authenticated User who owns an `INCOME` transaction, and a category of their own typed
`EXPENSE`,
**When** the User submits `EXPENSE` as the new type together with that category, and the wallet's
balance — once the income's original effect has been reversed — is at least the transaction's
(possibly also newly submitted) amount,
**Then** the system reverses the income's original effect, applies the expense's effect instead, and
returns success.

**AC-05: Successfully update only a transaction's category**
**Given** an authenticated User who owns a transaction, and a second category of their own whose type
agrees with that transaction's own existing, unchanged type,
**When** the User submits only the new category reference,
**Then** the system updates the transaction's category reference, and the amount, type, and the
wallet's balance are all left exactly as they were.

**AC-06: Successfully update only a transaction's note**
**Given** an authenticated User who owns a transaction,
**When** the User submits only a new note value,
**Then** the system updates the transaction's note, and the amount, type, category reference, and the
wallet's balance are all left exactly as they were.

**AC-07: Successfully update several fields together in one request**
**Given** an authenticated User who owns a transaction,
**When** the User submits a new category, a new amount, a new type, and a new note together in one
request, and the new category's type agrees with the new type, and the wallet can support the new
effective effect,
**Then** the system updates all four submitted fields, and the wallet's balance reflects exactly the
net effect of the transaction's new amount and new type — never an intermediate or partial state.

**AC-08: Deny access to unauthenticated callers**
**Given** a caller presenting no credentials, or credentials that are invalid or expired,
**When** the caller attempts to update a transaction,
**Then** the system denies the request before evaluating anything else, changes nothing, and returns
an unauthenticated error.

**AC-09: Reject an update to a transaction that does not exist at all**
**Given** an authenticated User,
**When** the submitted transaction reference matches no transaction in the system,
**Then** the system changes nothing and returns a not-found error.

**AC-10: Reject an update to a transaction belonging to a different User**
**Given** an authenticated User,
**When** the submitted transaction reference matches a transaction belonging to a wallet owned by a
different User,
**Then** the system changes nothing and returns the same not-found outcome AC-09 describes — the
response gives no indication of which of the two happened.

**AC-11: Reject a request that submits no field at all**
**Given** an authenticated User who owns a transaction,
**When** the User submits a request naming none of the transaction's editable fields,
**Then** the system changes nothing and returns a validation error, rather than treating the request as
a no-op success.

**AC-12: Reject a submitted category reference that does not resolve to the caller's own category**
**Given** an authenticated User who owns a transaction,
**When** the submitted category reference matches no category at all, or matches a category owned by
a different User,
**Then** the system changes nothing and returns the same not-found outcome in either case.

**AC-13: Reject a submitted amount that is zero, negative, or carries more than two decimal places**
**Given** an authenticated User who owns a transaction,
**When** the submitted amount is zero, a negative value, or carries more than two digits after the
decimal point,
**Then** the system changes nothing and returns a validation error rather than treating it as a valid
amount, rounding it, or truncating it.

**AC-14: Reject a submitted type that is not INCOME or EXPENSE**
**Given** an authenticated User who owns a transaction,
**When** the submitted type is any value other than `INCOME` or `EXPENSE`,
**Then** the system changes nothing and returns a validation error rather than accepting an
open-ended value.

**AC-15: Reject a submitted note exceeding the maximum supported length**
**Given** an authenticated User who owns a transaction,
**When** the submitted note is longer than the system supports,
**Then** the system changes nothing and returns a validation error rather than truncating the note.

**AC-16: Reject an update whose effective category and effective type disagree**
**Given** an authenticated User who owns a transaction,
**When** the category that would be in effect after this update (whichever was submitted, or the
transaction's own existing category if none was submitted) is typed differently from the type that
would be in effect after this update (whichever was submitted, or the transaction's own existing type
if none was submitted),
**Then** the system changes nothing and returns a conflict error — exactly the same rule creation
already enforces, applied again whenever the update actually changes which category or which type is
in effect.

**AC-17: Reject an update whose effective new effect would overdraw the wallet**
**Given** an authenticated User who owns a transaction,
**When** the type that would be in effect after this update is `EXPENSE`, and the amount that would be
in effect exceeds the wallet's balance once the transaction's current, stored effect has already been
reversed,
**Then** the system returns an error indicating insufficient balance, and the transaction's previously
stored amount, type, category, and note, together with the wallet's balance, are all left exactly as
they were before the request — nothing is left partially applied.

**AC-18: Return exactly the documented transaction fields**
**Given** an authenticated User successfully updates one of their own transactions,
**When** the system returns the success result,
**Then** the result carries exactly the transaction's identifier, wallet reference, category
reference, amount, type, timestamp, and note — the same seven fields every other Transaction
Management story already established, no other field, and no data belonging to any other User's
wallet or category.

### Edge Cases

**EC-01**: **A wallet reference submitted alongside other fields** — the request body additionally
carries a wallet-shaped value; the updated transaction's wallet reference remains exactly what it was
before the request, and the response carries no echo of the submitted value. This story's contract has
no field for a caller to populate it (see *Assumptions & Dependencies*), so the extra key is silently
ignored, never honoured — mirrors BM-US-04 EC-06's identical treatment of `wallet_id`/`category_id`/
`period`.

**EC-02**: **A note resubmitted identical to the value already stored** — accepted as an ordinary
successful update, not treated as a no-op error or rejected as unchanged (mirrors BM-US-04 EC-05's
"equal to the value the budget already holds").

**EC-03**: **A category-only change whose new category's type disagrees with the transaction's own,
unchanged type** — refused with AC-16's outcome, demonstrating that changing *only* the category still
triggers re-validation even though `type` itself was never named in this request.

**EC-04**: **A type-only change where the transaction's existing, unchanged category's type no longer
agrees with the newly submitted type** — refused with AC-16's outcome, demonstrating that the
transaction's existing category is still re-validated even though the caller never named it in this
request.

**EC-05**: **An amount resubmitted identical to the value already stored** — accepted as an ordinary
successful update (mirrors EC-02 for `amount`).

**EC-06**: **A reversal-then-reapplication that fails the reapplication step for insufficient balance**
— the transaction's previously stored amount, type, category, and note, and the wallet's own balance,
are left exactly as they were before the request; nothing about the attempt is left partially applied
(the same outcome AC-17 describes, stated here as its own edge case because it is the one place in this
story where a two-step wallet mutation could otherwise leave a half-finished state if it were not
reasoned through carefully).

**EC-07**: **A caller who owns one or more transactions of their own, attempting to update a different
User's transaction** — refused with the identical outcome AC-10 describes; owning some transaction
never entitles a caller to act on another User's transaction.

**EC-08**: **An EXPENSE amount updated to exactly equal the wallet's balance once the transaction's own
old effect has been reversed** — accepted; the boundary AC-17 excludes is an amount that *exceeds* that
balance, not one that exactly exhausts it, mirroring TM-US-01 EC-08's identical boundary at creation
time. The wallet's balance becomes exactly zero.

**EC-09**: **Updating only the note (or only the category, to another category of the same type) of a
transaction whose wallet has, in the meantime, been driven to a balance of exactly zero by other,
later transactions** — still succeeds, and the wallet's balance is unaffected by this update. Leaving
`amount` and `type` both unchanged means the reapplied effect is identical in kind and size to the
effect being reversed, which this story's own balance-recalculation rule (see *Assumptions &
Dependencies*) guarantees can never be refused — unrelated wallet activity that happened after this
transaction was created cannot retroactively make an unchanged amount/type combination unsupportable.

**EC-10**: **A submitted category reference that does not resolve to the caller's own category, in the
same request as a submitted amount that would separately have caused an insufficient-balance refusal**
— only the category-not-found error is returned (AC-12's outcome), never the insufficient-balance
error, and never both; this story's own fixed check order (see *Requirements*) is what makes that
deterministic rather than a coincidence of implementation, mirroring TM-US-01 EC-14.

**EC-11**: **An update whose effective category and effective type disagree, and whose effective amount
would independently exceed the wallet's balance, in the same request** — only the category-type-
mismatch error is returned (AC-16's outcome), never the insufficient-balance error, and never both,
mirroring TM-US-01 EC-11.

### Requirements *(mandatory)*

#### Functional Requirements

- **FR-01**: The system must **allow** an authenticated User of any role to submit any one or more of
  a new category reference, a new amount, a new type, and a new note, identifying the transaction to
  update by its own identifier (SDS §5.6.4).
- **FR-02**: The system must **deny** the operation to unauthenticated callers, evaluating credentials
  before anything else (constitution API-08; mirrors TM-US-01 FR-02, TM-US-03 FR-02).
- **FR-03**: The system must **require** the submitted transaction reference to resolve to a
  transaction belonging to a wallet owned by the authenticated caller, and **refuse** the request with
  an identical outcome whether no such transaction exists at all or it exists and belongs to a wallet
  owned by a different User (AC-09, AC-10, EC-07; constitution SEC-08, VL-06).
- **FR-04**: The system must **require** at least one of category reference, amount, type, or note to
  be submitted, and **reject** a request naming none of them with a validation error rather than
  treating it as a no-op success (AC-11).
- **FR-05**: The system must **accept no field at all** for the transaction's wallet reference; any
  wallet-shaped value submitted anyway is silently ignored, and the transaction's wallet never changes
  through this operation (EC-01; see *Assumptions & Dependencies*).
- **FR-06**: The system must, when a category reference is submitted, **require** it to resolve to a
  category owned by the authenticated caller, and **refuse** the request with an identical outcome
  whether no such category exists at all or it exists and is owned by a different User (AC-12;
  constitution SEC-08, VL-06).
- **FR-07**: The system must **determine** the category and the type that would be in effect after
  this update — whichever was submitted, or the transaction's own existing value when nothing was
  submitted for that field — and **require** the two to agree, exactly as transaction creation already
  requires (TM-US-01 BR-03); this re-validation **runs only when** the effective category or the
  effective type actually differs from the transaction's own stored row — when neither differs, the
  pairing is already known valid from the moment of creation and is not re-checked (AC-16, EC-03,
  EC-04).
- **FR-08**: The system must, when an amount is submitted, **require** it to be a `Decimal` value with
  at most two digits after the decimal point and at most fifteen significant digits in total, and
  strictly greater than zero — rejecting, never rounding or truncating, a value violating any of these
  (AC-13; constitution VL-07).
- **FR-09**: The system must, when a type is submitted, **require** it to be exactly `INCOME` or
  `EXPENSE` (AC-14).
- **FR-10**: The system must, when a note is submitted, **reject** — rather than truncate — one longer
  than the system supports (AC-15).
- **FR-11**: The system must **reverse** the transaction's current, stored effect on its wallet before
  applying anything new — adding back the amount of a stored `EXPENSE`, or subtracting back the amount
  of a stored `INCOME` — and this reversal must **never be refused**, regardless of the wallet's
  current balance, because it undoes a real effect already counted as having happened (AC-03, AC-04,
  EC-09).
- **FR-12**: The system must **apply** the effective new effect to the wallet exactly as creation
  already does — refusing, for an effective `EXPENSE`, when the effective amount exceeds the wallet's
  balance once the reversal in FR-11 has already taken place; never refusing an effective `INCOME`
  regardless of that balance (AC-01..AC-04, AC-17, EC-08, EC-09).
- **FR-13**: The system must, when FR-12 refuses the update, **leave** the transaction's previously
  stored fields and the wallet's balance exactly as they were before the request — the reversal in
  FR-11 is not left half-applied (AC-17, EC-06).
- **FR-14**: The system must, on success, **persist** exactly the field(s) actually submitted onto the
  transaction's own row, leaving every field not submitted exactly as it already was (AC-01..AC-07).
- **FR-15**: The system must **return**, on success, exactly the transaction's identifier, `wallet_id`,
  `category_id`, `amount`, `type`, `timestamp`, and `note` (AC-18).
- **FR-16**: The system must **evaluate** transaction ownership, then (only when a category reference
  is submitted) category ownership, then (only when the effective category or effective type actually
  changed) type-consistency, then the balance recalculation in FR-11/FR-12, in that fixed order, so
  that a request failing more than one of these reports only the first (EC-10, EC-11).

#### Business Rules

- **BR-01**: A transaction's wallet reference is immutable; no update performed through this operation
  ever changes which wallet a transaction belongs to (FR-05, EC-01).
- **BR-02**: A transaction's effective type must equal its effective category's own type — the
  identical rule creation already enforces (TM-US-01 BR-03) — re-validated whenever the effective
  category or the effective type actually changes relative to the transaction's stored row, and left
  unchecked otherwise because the stored pairing is already known valid from creation (FR-07, AC-16).
- **BR-03**: Updating a transaction always reverses its current, stored effect on its wallet and
  applies its new, effective effect — uniformly, regardless of how many or which of the four editable
  fields were actually submitted (FR-11, FR-12).
- **BR-04**: Reversing a transaction's current, stored effect never fails for insufficient balance,
  regardless of the wallet's balance at the time: undoing a previously applied `EXPENSE` always adds
  its amount back, and undoing a previously applied `INCOME` always subtracts its amount back (FR-11).
- **BR-05**: Applying the effective new effect follows the identical sufficiency rule transaction
  creation already establishes (TM-US-01 BR-05) — refused for an effective `EXPENSE` whose amount
  exceeds the wallet's balance once BR-04's reversal has already taken place, never refused for an
  effective `INCOME` (FR-12).
- **BR-06**: A refusal under BR-05 leaves nothing changed — the transaction's stored fields and the
  wallet's balance are exactly as they were before the request (FR-13).

#### Key Entities

- **Transaction**: A single recorded movement of money, in or out, against one Wallet and one
  Category, at a point in time (SRS §1.5; TM-US-01). The first Transaction Management story to mutate
  an existing Transaction row after its creation — `amount`, `type`, `category_id`, and `note` are
  each independently editable; `id`, `wallet_id`, and `timestamp` never change through this operation
  (BR-01; *Assumptions & Dependencies*).
- **Wallet**: Reused from WM-US-01 with no new column. The second story, after TM-US-01, to mutate an
  existing Wallet's `balance` — and the first to mutate the same Wallet's balance twice within one
  request, first reversing a transaction's old effect and then applying its new one (BR-03).
- **Category**: Reused from CM-US-01 with no new column. Referenced by this story both as an optional
  new value to adopt and, when neither it nor `type` changes, as the already-validated existing
  pairing this story deliberately does not re-check (BR-02).
- **User**: Reused from Feature-01/Feature-02 with no new column. The authenticated caller's own
  ownership of the transaction being updated, and of any newly submitted category, is what entitles
  them to perform this update; no role restriction applies.

### Success Criteria *(mandatory)*

- **SC-01**: An authenticated User can update any one or more of a transaction's category, amount,
  type, and note, and the response reflects exactly what the transaction now holds.
- **SC-02**: No transaction can be updated without an authenticated caller.
- **SC-03**: A transaction can never be updated by a User who does not own it, or using a category the
  User does not own — refused identically whether the reference is absent or belongs to someone else.
- **SC-04**: A transaction's wallet reference never changes through this operation, regardless of what
  is submitted.
- **SC-05**: A wallet's balance always reflects the net effect of a transaction's current, up-to-date
  amount and type — never the sum of an old and a new effect, and never a partially applied change.
- **SC-06**: Reversing a transaction's previously applied effect can never itself be refused for
  insufficient balance; only applying a *new*, larger, or newly-`EXPENSE` effect can be.
- **SC-07**: A refused update leaves the transaction's stored fields and the wallet's balance exactly
  as they were — observable both in the response and by reading the stored rows directly.
- **SC-08**: Malformed transaction-update input — no field submitted at all, an unresolvable category
  reference, a type disagreeing with the effective category's own type, a non-positive or over-precise
  amount, an invalid type, or an over-long note — is rejected before anything is persisted.

### Assumptions & Dependencies

- **Login (SS-US-01) and TM-US-01 (Create a Transaction) are already implemented** — there is nothing
  to update otherwise, mirroring every other story's own dependency on creation existing first.
  TM-US-03 (View) is not a hard dependency but is this story's own closest architectural precedent for
  looking a transaction up by its own id, scoped to the caller.

- **The scope question: which fields are editable.** Four candidates were weighed against SDS §5.6.4's
  own goal sentence ("Edit transaction details and automatically recalculate wallet balances") and
  against SRS §1.5's enumeration of what a Transaction carries (`id`, `wallet_id`, `category_id`,
  `amount`, `type`, `timestamp`, `note`):
  - **`wallet_id` is excluded.** "Transaction details" reads naturally as the transaction's own
    descriptive content — what it was for, how much, what kind — not which account it is filed under.
    Moving a transaction to a different wallet would mean reversing its effect on the *old* wallet and
    applying it to a *different* wallet: a two-wallet balance recalculation with its own ownership
    question (must the new wallet also belong to the caller? — certainly, but no source says so
    explicitly, because no source imagines this operation at all) and its own currency question (SDS
    §4.3.3's `wallets` ERD gives each wallet its own `currency` — moving a transaction between two
    wallets of different currencies would need a conversion rate no source provides). Keeping
    `wallet_id` immutable means every balance recalculation in this story touches exactly one wallet,
    the one the transaction already belongs to — the same "fewest invented rules" discipline BM-US-04
    A1 used to keep a budget's wallet/category/period immutable, applied here to exactly one of a
    transaction's two references rather than all three, because nothing about `category_id` carries
    `wallet_id`'s two-ledger complication.
  - **`id` and `timestamp` are excluded** for the obvious reason neither BM-US-04 nor CM-US-04 needed
    to state explicitly: an identifier is never user-settable, and TM-US-01 BR-06 already settles that
    a transaction's timestamp is permanently the moment of its creation — "update" has no bearing on
    either.
  - **`amount`, `type`, `category_id`, and `note` are the four editable fields**, each independently
    optional on the request — the same multi-field optional-update contract CM-US-04 first established
    in this codebase (`name`, `type`, `icon`, each independently optional, at least one required). All
    four are plausible readings of "transaction details": `amount` and `type` are the two fields that
    actually drive the balance recalculation that gives this story its own distinct complexity;
    `category_id` is reclassification, the most literal reading of "edit transaction details"; `note`
    is free-form annotation with no effect on anything else. Nothing in SDS §5.6.4 singles out a
    subset the way BM-US-04's own SDS goal ("adjust spending **caps**", plural of the one field
    `amount_limit`) pointed at exactly one field — here, every one of the four is as plausible as the
    others, so all four are built, matching CM-US-04's own "all three fields" precedent rather than
    BM-US-04's own "exactly one field" precedent.
  - **The coupling between `amount`, `type`, and `category_id`.** Unlike CM-US-04's three fields (which
    have no cross-field rule at all beyond "at least one must be given"), this story's three
    business-meaningful fields are coupled two ways: (a) `type` determines *which* wallet operation
    applies on reapplication — `EXPENSE` is sufficiency-checked, `INCOME` is not, the identical
    distinction TM-US-01 BR-05 draws at creation; and (b) whichever category is in effect (the
    submitted one, or the existing one if none was submitted) must have a `type` consistent with
    whichever transaction `type` is in effect (the submitted one, or the existing one if none was
    submitted) — the identical BR-03 rule creation already enforces, now stated over *effective* rather
    than merely *submitted* values, because a category-only update or a type-only update can each, on
    its own, make a previously-valid pairing invalid. A re-validation of this pairing is only actually
    *needed* when the effective category or the effective type differs from the transaction's own
    stored row — when neither differs, the original pairing is already known-valid from the moment
    `create_transaction()` first checked it (TM-US-01 FR-07), and re-running an identical check against
    unchanged inputs would prove nothing new. This is recorded as its own functional requirement
    (FR-07) precisely because skipping a check that would otherwise trivially re-confirm something
    already known is a deliberate design choice, not an oversight.

- **The balance recalculation always reverses then reapplies, uniformly, regardless of which fields
  changed.** Two designs were weighed. **(a)** Special-case the recalculation: skip any wallet mutation
  at all when neither `amount` nor `type` was submitted (a pure category/note edit), and otherwise
  compute a single net delta. **(b)** Always reverse the transaction's current stored effect, then
  always apply its new effective effect — two wallet operations every time, even when the net result
  is a no-op. Design (b) is chosen. It is the same "fewest invented rules" preference this codebase's
  other Update stories already used, applied to *logic* rather than to *scope*: a single algorithm that
  behaves correctly whether 1, 2, 3, or 4 fields changed is simpler to state, simpler to verify, and
  structurally incapable of the bug a hand-written special-case tree invites — forgetting one of the
  several field-combination branches a reverse-skipping design would need (amount-only, type-only,
  both, neither, each crossed with the category question). It also makes the reversal-then-reapplication
  machinery exercised on *every* successful update, not only the ones a human reviewer might expect
  "really" needed it, which is exactly the kind of uniform code path this project's own repeated
  "fewest invented rules" standard favors over a combinatorial special-case tree.

  This design is provably safe for the sub-case that might appear riskiest — updating only `category_id`
  and/or `note`, leaving `amount` and `type` both unchanged (EC-09). A wallet's balance can only ever be
  driven non-negative by a *conditional* `EXPENSE` decrement (whose own sufficiency check guarantees the
  result stays at or above zero) or increased by an unconditional `INCOME` increment — so once a stored
  `EXPENSE` transaction has been successfully created against a wallet at all, that wallet's balance is
  guaranteed never to have gone negative from that moment on. Consequently: reversing a stored `EXPENSE`
  (adding its amount back) always produces an intermediate balance at least equal to that same amount,
  so reapplying the *identical*, unchanged amount as an `EXPENSE` can never fail the sufficiency check —
  regardless of what unrelated activity has happened on the wallet since. And reversing a stored `INCOME`
  followed by reapplying it as `INCOME` again needs no sufficiency check at all, by BR-05. A category-only
  or note-only update therefore can **never** be refused for insufficient balance, no matter how low
  other, later transactions have since driven the wallet's balance — the only ways FR-12's sufficiency
  check can genuinely fail are a *larger* submitted amount, or a *type flip* from `INCOME` to `EXPENSE`
  (AC-04), both of which are real, correctly-refusable business situations, not artifacts of the uniform
  algorithm. This reasoning is the basis for EC-09 and is proven again, concretely, by `test_cases.md`
  TC-108/QF-19.

- **Reversing a transaction's current effect is unconditional, in both directions — this is new
  territory for `wallet_repo`.** TM-US-01 A9 built exactly one conditional balance mutation
  (`decrement_balance()`, EXPENSE only) and one unconditional one (`increment_balance()`, INCOME only)
  — the two operations creation ever needs. This story needs a *third*: an unconditional subtraction,
  used only to reverse a previously applied `INCOME`'s effect, because a reversal must never be refused
  (BR-04) and the existing `decrement_balance()` is conditional by design (TM-US-01 A9's own
  sufficiency-check-is-the-WHERE-clause reasoning), which is exactly the wrong behaviour for undoing a
  credit that was already counted as available. Reversing a previously applied `EXPENSE` needs no new
  function at all — adding its amount back is exactly `increment_balance()`, reused completely
  unchanged. Full design: `plan.md` A5.

- **A failed reapplication (FR-12/FR-13) is safe because nothing commits until the router does.**
  The reversal (FR-11) and the attempted reapplication (FR-12) are both flushed, not committed, within
  the same database session the service already runs in — the identical one-request-one-transaction
  discipline constitution AR-06 and TM-US-01 A10 already established for creation, now exercised across
  *two* wallet mutations plus a row update in a single request instead of one mutation plus one insert.
  When the reapplication step refuses, the service raises before the transaction's own row is ever
  touched; the already-flushed reversal is discarded along with everything else in the session the
  moment the exception reaches the database session's own rollback handling, which is a technical
  mechanism belonging to `plan.md`, not this conceptual document — see `plan.md` A6 for the concrete
  grounding.

- **A caller clears an existing note by submitting an empty string, not `null`.** This story's
  `note` field carries the identical "submitting nothing, or submitting an explicit null, both mean
  'leave unchanged'" convention WM-US-04/CM-US-04 already established for their own optional fields —
  inherited here unchanged, not newly decided. Because `note` (unlike `name`/`icon`) has never carried
  a non-blank requirement (TM-US-01 A6 permits an empty value in principle, though creation itself
  makes a blank note moot by simply treating an absent `note` as `null`), a caller who genuinely wants
  to blank out an existing note can do so by submitting an empty string, which is a real, distinct value
  from both "omitted" and "null" under this convention — no new rule is invented to support this, it
  falls out of `note` never having required non-blankness in the first place.

- **This story never reads or writes the `budgets` table**, for the same reason every prior
  Transaction Management story already recorded: BM-US-03 owns spending-vs-budget computation, not
  this story, even though an edited Transaction's new amount/type is exactly the kind of change that
  computation eventually reflects on its next read.

---

## TM-US-05: Delete a Transaction

> **IDs in this section are local to TM-US-05.** `AC-01` below is not TM-US-01/02/03/04's own `AC-01`;
> each story section numbers its own criteria, per `artifact-templates/spec-templates.md` and this
> epic file's own precedent. Only `TC-NN` (and `QF-NN`) in `test_cases.md` run continuously across the
> epic (`CLAUDE.md` §1.1 rule 4) — this story continues from `TC-113`/`QF-21`, confirmed by direct
> count of `test_cases.md`'s own last entries before this dispatch (`TC-112`, `QF-20`).

### Source *(scope extraction — CLAUDE.md §1 scope rule)*

**SRS §6 Feature-06 — searched in full; confirmed still accurate**
> `### Feature-06: Transaction Management` contains exactly three story headers, the same three
> TM-US-04's own Source section already found: `#### US-06-01: Create a Transaction for a Wallet
> [MVP]` (TM-US-01), a bare `#### US-06-02: View List of Transactions [MVP]` (TM-US-02), and a bare
> `#### US-06-03: Update/Delete a Transaction` — **one combined header for both TM-US-04 and this
> story**, no `[MVP]` tag, no Gherkin. There is no separate header distinguishing delete from update
> the way SDS §5.6 does (SDS §5.6.4 "TM-US-04" vs §5.6.5 "TM-US-05", confirmed below). Not a source
> contradiction — TM-US-04's own Source section already worked through this exact gap for the sibling
> half of the same bare header; this story is grounded in SDS §5.6.5's own separate entry and in SRS
> §1.5/§2 FR-06's text directly, the same way TM-US-04 grounded itself. No `[NEEDS RULING]` follows.

**SRS §1.5 Conceptual Domain Model**
> **Transaction** — A single recorded movement of money, in or out, against one Wallet and one
> Category, at a point in time (FR-06).
>
> | Relationship | Cardinality | Meaning |
> | Wallet contains Transaction | one Wallet → many Transactions | Every Transaction moves money
> into or out of exactly one Wallet (FR-06) |
> | Category classifies Transaction | one Category → many Transactions | Every Transaction is
> tagged with exactly one Category (FR-06) |

**SRS §2 FR-06 — Transaction Management**
> The System shall allow Users to log income and expense Transactions against a designated Wallet
> and Category. The System shall automatically recalculate and persist wallet balances atomically.

**SDS §5.6.5 TM-US-05: Delete a Transaction (USER)**
> **Goal:** Remove a transaction and reverse its impact on wallet balance.

Unlike BM-US-05's own SDS goal for the budget epic's equivalent story ("Remove an active budget
tracker" — no explicit side effect named), this goal sentence explicitly names the balance reversal as
part of *this* story's own job, not something left to be inferred the way BM-US-05 A1 had to read
"active" against silence elsewhere. This story is accordingly simpler than TM-US-04 in one respect and
no thinner in another: deletion only ever *reverses* a transaction's already-applied effect — there is
no "apply a new effect" step the way Update's reapplication needed, so there is no insufficient-balance
refusal possible at this story's own hands at all — while still carrying the identical reversal
mechanics TM-US-04 already built and proved.

**`specs/005-budget-management/plan.md` BM-US-05 "Gaps & Decisions"** *(this story's own closest-shape
precedent — the delete/204/hard-delete/idempotent-as-404 pattern reused below)*
> A2: "Hard delete — an actual row removal from `budgets`, no `is_deleted`/soft-delete/archival
> column... Confirmed directly against every model file in `backend/app/models/`: no table in this
> schema uses a soft-delete pattern."
> A4/A5: "`DELETE /api/v1/budgets/{budget_id}` — a verb-free path on the resource's own id... Success
> response is `204 No Content`, with no response body — not `200` with a minimal body... this is the
> first story in this codebase, in any epic, to need [`204`], since no `DELETE` endpoint has existed
> before this story."
> A8: "A second deletion request against an already-deleted budget is `404 BUDGET_NOT_FOUND` — the
> same outcome as a reference that never existed — not a distinct 'already deleted' error or a `204`
> no-op success."

**`specs/006-transaction-management/spec.md` TM-US-04 "Business Rules"** *(this story's own inherited
precedent — the reversal machinery this story runs once per request instead of TM-US-04's twice)*
> BR-03: "Updating a transaction always reverses its current, stored effect on its wallet and applies
> its new, effective effect."
> BR-04: "Reversing a transaction's current, stored effect never fails for insufficient balance,
> regardless of the wallet's balance at the time: undoing a previously applied `EXPENSE` always adds
> its amount back, and undoing a previously applied `INCOME` always subtracts its amount back."

**constitution.md API-03** *(already extended once, by BM-US-05, for exactly this shape of response — not
reopened here)*
> HTTP status codes: `200` read/update · `201` creation · `400` malformed or expired-token per SRS ·
> `401` unauthenticated · `403` authenticated but forbidden · `404` not found · `409` business conflict
> · `422` payload validation. *(No `204` listed — BM-US-05's own `plan.md` A5 already noted the gap
> and left a one-line suggestion for `constitution.md` to be amended the next time it is edited; this
> story is the second, not the first, to rely on the same unlisted-but-uncontradicted status code.)*

**constitution.md AR-06, SEC-08, VL-06**
> AR-06: Multi-entity writes execute in **one** transaction. Services never call `commit()`; the
> router owns the commit boundary.
> SEC-08: Queries for user-owned data filter on the authenticated `user_id` at the repository layer.
> VL-06: Referenced entities are verified to exist and be active before use — `404` if absent, `409`
> if present but in the wrong state.

**Confirmed directly against `backend/app/models/`** — no table in this schema carries a foreign key
to `transactions.id`. A Transaction has no children of its own, the identical situation BM-US-05 A3
already found for `budgets.id` — this story's deletion therefore has no cascade behaviour of any kind
to design.

### Out of scope for this story

TM-US-01/02/03/04 (create, list, view, update — all implemented) · soft-delete, archival, or any
"undo" of a deletion (reasoned through explicitly below, not merely declined) · cascading removal of
any other entity (no table in this schema references `transactions.id` — see *Source* and
*Assumptions & Dependencies*) · recomputing or re-deriving any Budget's `amount_spent`,
`progress_percentage`, or `status` — those remain BM-US-02/BM-US-03's own read-time computations over
whatever transactions exist at read time, unaffected by this story except as a natural consequence of
a deleted transaction's absence on the next such read · BM-US-01..05 · WM-US-02..05 · CM-US-02..05 ·
UM-US-04/05, DC-US-01/02 · Features 07–11 · SRS §6 Feature-10/11 placeholders.

Deliberately excluded even though adjacent: retaining a deleted transaction's row in any recoverable
form — this story's contract is a permanent removal, not a status change (see *Assumptions &
Dependencies*); any "insufficient balance" refusal of the deletion itself — deletion only ever reverses
an already-applied effect, and a reversal is never refused (see *Requirements*, *Assumptions &
Dependencies*); restricting which transactions may be deleted based on their type, amount, or age — no
source imposes one (see *Assumptions & Dependencies*); and any mobile/UI screen — confirmed directly in
`mobile/app/(tabs)/transactions/index.tsx`'s own source comments, which name only TM-US-03/04 as the
screens this round's prototype deliberately does not build, and no SRS UXR names a transaction-delete
screen either.

### User Scenarios & Testing *(mandatory)*

As an **authenticated User**, I want to permanently remove a transaction I no longer want recorded, so
that my wallet's balance reflects only the transactions I still consider real, with the transaction's
original effect undone exactly as if it had never been logged.

**Acceptance Criteria**:

**AC-01: Successfully delete an EXPENSE transaction**
**Given** an authenticated User who owns an `EXPENSE` transaction logged against one of their own
wallets,
**When** the User requests that transaction be deleted, identifying it by its own identifier,
**Then** the system permanently removes that transaction's record — it never again appears in any
subsequent listing or lookup the caller performs — and increases the wallet's balance by exactly the
transaction's amount, reversing the decrease the transaction originally caused.

**AC-02: Successfully delete an INCOME transaction, regardless of the wallet's current balance**
**Given** an authenticated User who owns an `INCOME` transaction logged against one of their own
wallets,
**When** the User requests that transaction be deleted,
**Then** the system permanently removes that transaction's record — it never again appears in any
subsequent listing or lookup — and decreases the wallet's balance by exactly the transaction's amount,
reversing the increase the transaction originally caused, accepted regardless of what the wallet's
balance is at the time of deletion.

**AC-03: Deny access to unauthenticated callers**
**Given** a caller presenting no credentials, or credentials that are invalid or expired,
**When** the caller attempts to delete a transaction,
**Then** the system denies the request before evaluating anything else, deletes nothing, and returns
an unauthenticated error.

**AC-04: Reject a deletion of a transaction that does not exist at all**
**Given** an authenticated User,
**When** the submitted transaction reference matches no transaction in the system,
**Then** the system deletes nothing and returns a not-found error.

**AC-05: Reject a deletion of a transaction belonging to a different User**
**Given** an authenticated User,
**When** the submitted transaction reference matches a transaction belonging to a wallet owned by a
different User,
**Then** the system deletes nothing and returns the same not-found outcome AC-04 describes — the
response gives no indication of which of the two happened.

**AC-06: A deleted transaction's category, and every other transaction, are left untouched**
**Given** an authenticated User successfully deletes one of their own transactions,
**When** the deletion completes,
**Then** that transaction's category, every other transaction logged against the same wallet, and
every transaction logged against any other wallet, all remain exactly as they were immediately before
the request — only the deleted transaction's own record and its own wallet's balance change.

**AC-07: Deleting a transaction a second time is refused as not found**
**Given** an authenticated User who has already deleted one of their own transactions,
**When** the User submits another request to delete that same transaction reference,
**Then** the system deletes nothing further — there is nothing left to delete — and returns the
identical not-found outcome AC-04 describes.

### Edge Cases

**EC-01**: **A transaction reference that is not even a well-formed identifier** — a value such as
`"not-a-real-id"` is refused with the same not-found outcome as a well-formed but non-existent
reference (AC-04). No separate malformed-identifier error exists; a reference either resolves to a
transaction the caller owns, or it does not, regardless of its shape.

**EC-02**: **A caller who owns one or more transactions of their own, attempting to delete a different
User's transaction** — refused with the identical outcome AC-05 describes; owning some transaction
never entitles a caller to act on another User's transaction.

**EC-03**: **Deleting an EXPENSE transaction whose wallet has, since that transaction was recorded, had
other transactions recorded against it** — the reversal still applies, scoped to only this
transaction's own amount; the wallet's resulting balance reflects every one of its other recorded
transactions' effects plus this reversal, never losing or double-counting any of them.

**EC-04**: **Deleting an INCOME transaction whose reversal would drive the wallet's balance to zero or
below** — accepted unconditionally; a reversal undoes a real effect already counted as having
happened, and is never refused for any reason related to the wallet's current balance, the identical
guarantee TM-US-04 BR-04 already established for a reversal performed as part of an update.

**EC-05**: **A transaction deleted successfully, immediately followed by a second deletion request
against that same reference** — refused with the identical not-found outcome AC-04/EC-01 describe;
there is nothing left to delete, and no distinct "already deleted" outcome exists.

### Requirements *(mandatory)*

#### Functional Requirements

- **FR-01**: The system must **allow** an authenticated User of any role to submit a transaction
  reference, identifying it by its own identifier, in order to delete that transaction (SDS §5.6.5;
  AC-01, AC-02).
- **FR-02**: The system must **deny** the operation to unauthenticated callers, evaluating credentials
  before anything else (constitution API-08; mirrors TM-US-01 FR-02, TM-US-04 FR-02).
- **FR-03**: The system must **require** the submitted transaction reference to resolve to a
  transaction belonging to a wallet owned by the authenticated caller, and **refuse** the request with
  an identical outcome whether no such transaction exists at all or it exists and belongs to a wallet
  owned by a different User (AC-04, AC-05, EC-01, EC-02; constitution SEC-08, VL-06).
- **FR-04**: The system must, on a successful deletion, **reverse** the transaction's current, stored
  effect on its wallet before removing its own row — adding back the amount of a stored `EXPENSE`, or
  subtracting back the amount of a stored `INCOME` — and this reversal must **never be refused**,
  regardless of the wallet's current balance, because it undoes a real effect already counted as having
  happened (AC-01, AC-02, EC-03, EC-04; mirrors TM-US-04 FR-11, BR-04).
- **FR-05**: The system must, once the reversal in FR-04 has been applied, **permanently remove** the
  transaction's own record; the removed row never again resolves through any lookup or listing
  performed by the caller (AC-01, AC-02).
- **FR-06**: The system must **impose no restriction** on which transactions may be deleted based on
  their type, amount, or age — any transaction the caller owns may be deleted, exactly as any other
  (see *Assumptions & Dependencies*).
- **FR-07**: The system must **never alter** any entity other than the deleted transaction's own row
  and its own wallet's balance — no other transaction, no category, and no other wallet is touched by
  a deletion (AC-06).
- **FR-08**: The system must **refuse** a repeated deletion of an already-deleted transaction with the
  identical not-found outcome a never-existed reference produces (AC-07, EC-05).

#### Business Rules

- **BR-01**: A transaction's ownership for this operation is established the same way every prior
  Transaction Management story already established it — entirely transitive through the transaction's
  own `wallet_id`, since the transaction carries no owner column of its own. A transaction reference
  that does not resolve to a row the caller owns is refused identically whether no such row exists at
  all or it exists and belongs to a different User (FR-03).
- **BR-02**: Deleting a transaction always reverses its current, stored effect on its wallet before the
  row is removed — unconditionally, regardless of the wallet's balance at the time: undoing a stored
  `EXPENSE` always adds its amount back, and undoing a stored `INCOME` always subtracts its amount back
  (FR-04).
- **BR-03**: Deleting a transaction changes exactly two things — the deleted transaction's own row
  (removed) and its own wallet's balance (adjusted by the reversal) — and nothing else (FR-07).
- **BR-04**: A transaction reference that no longer resolves to an existing row — whether because it
  never existed at all or because it was already deleted — is refused identically to one that never
  existed (FR-08).

#### Key Entities

- **Transaction**: A single recorded movement of money, in or out, against one Wallet and one
  Category, at a point in time (SRS §1.5; TM-US-01). The first Transaction Management story to remove
  a Transaction row entirely, rather than create (TM-US-01), list (TM-US-02), view (TM-US-03), or
  mutate the fields of one while keeping its row (TM-US-04).
- **Wallet**: Reused from WM-US-01 with no new column. The third story, after TM-US-01 (one mutation)
  and TM-US-04 (two mutations per request), to mutate an existing Wallet's `balance` — this time
  exactly once per request, through a reversal only, with no reapplication step to follow it (BR-02).
- **Category**: Reused from CM-US-01 with no new column. Referenced by this story only incidentally —
  to confirm it is left unaffected by a deletion (AC-06) — never queried for ownership by this story.
- **User**: Reused from Feature-01/Feature-02 with no new column. The authenticated caller's own
  ownership of the transaction being deleted, reached through the wallet it belongs to, is what
  entitles them to delete it; no role restriction applies.

### Success Criteria *(mandatory)*

- **SC-01**: An authenticated User can delete any one of their own transactions, and it never again
  appears in any listing or lookup the caller performs.
- **SC-02**: No transaction can be deleted without an authenticated caller.
- **SC-03**: A transaction can never be deleted by a User who does not own it — refused identically
  whether the reference does not exist at all or belongs to someone else.
- **SC-04**: Deleting a transaction always reverses exactly its own effect on its own wallet, exactly
  once, and that reversal is never refused for any reason related to the wallet's current balance.
- **SC-05**: Deleting a transaction never changes any other transaction, any category, or any other
  wallet.
- **SC-06**: A repeated deletion attempt against an already-deleted transaction is refused identically
  to a reference that never existed.

### Assumptions & Dependencies

- **Login (SS-US-01) and TM-US-01 (Create a Transaction) are already implemented** — there is nothing
  to delete otherwise. TM-US-03 (View) is this story's own closest architectural precedent for looking
  a transaction up by its own id, scoped to the caller, and is reused completely unchanged
  (`transaction_repo.get_owned_by_id()`, `TransactionNotFoundError`) — see `plan.md` for the concrete
  reuse.

- **This story is simpler than TM-US-04, not harder.** Deleting a transaction only ever *reverses* its
  stored effect on its wallet; there is no "reapply a new effect" step the way Update needed (TM-US-04
  BR-03), so there is no insufficient-balance refusal possible through this operation at all — the
  reversal mechanics themselves (TM-US-04 BR-03/BR-04/BR-05: adding back a stored `EXPENSE` via
  `increment_balance()`, subtracting back a stored `INCOME` via
  `decrement_balance_unconditional()` — both built by TM-US-01/TM-US-04 A5 and never refused) are
  reused completely unchanged, run exactly once per request instead of TM-US-04's reverse-then-reapply
  pair.

- **The delete/204/hard-delete/idempotent-as-404 pattern is inherited from BM-US-05**
  (`specs/005-budget-management/plan.md` BM-US-05 A2/A4/A5/A8), the budget epic's own `DELETE
  /resource/{id}` → `204 No Content` precedent — crossed here with TM-US-04's own reversal mechanics
  rather than re-derived from first principles. Full design: `plan.md`.

- **No cascade behaviour exists to design.** Confirmed directly against every model file in
  `backend/app/models/`: no table in this schema carries a foreign key to `transactions.id` — a
  Transaction has no children of its own, the identical situation BM-US-05 A3 already found for
  `budgets.id`.

- **No restriction based on a transaction's type, amount, or age.** Nothing in SRS/SDS or the built
  system gives a reason a caller should be unable to delete any transaction they own, regardless of
  whether it is an `EXPENSE` or `INCOME`, how large its amount is, or how long ago it was recorded —
  the same "nothing restricts it, so nothing is invented" reading BM-US-05 A1 already carried forward
  from BM-US-04's own settled period-independence ruling, adapted here since Transaction has no period
  concept to begin with.

- **This story never reads or writes the `budgets` table**, for the same reason every prior
  Transaction Management story already recorded: BM-US-03 owns spending-vs-budget computation, not
  this story, even though a deleted Transaction's absence is exactly the kind of change that
  computation eventually reflects on its next read.
