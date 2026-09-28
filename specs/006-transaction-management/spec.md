# Feature Specification: Transaction Management (TM)

> **Feature:** SRS §6 Feature-06 · SDS §5.6 (TM)
> **Spec:** [spec.md](spec.md)
> **Stories in this file:** TM-US-01 *(specified)* · TM-US-02 *(specified)*

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
