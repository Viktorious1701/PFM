# Feature Specification: Financial Reporting (FR)

> **Feature:** SRS §6 Feature-07 · SDS §5.7 (FR)
> **Spec:** [spec.md](spec.md)
> **Stories in this file:** FR-US-01 *(specified)*

---

## A naming note before anything else

This epic's own code is **FR** (Financial Reporting, SDS §5.7) — spelled identically to two other,
unrelated things this document must also cite. All three are kept distinct throughout, by always
writing the full form:

* **`SRS FR-07`** — SRS §2's system-wide Functional Requirement titled "Financial Reporting."
* **`FR-US-01`** / **`FR-US-02`** — SDS §5.7's two story codes (this dispatch is `FR-US-01` only).
* **`FR-01`, `FR-02`, …** (bare, no prefix) — this story's *own* local Functional Requirements,
  below, in the same `FR-NN` scheme every other epic file in `specs/` already uses for its own
  requirements. A bare `FR-NN` in this document always means one of *this story's* local
  requirements, never the SRS requirement or the SDS story code.

## Source *(scope extraction — CLAUDE.md §1 scope rule)*

Only the sections below entered the working context for FR-US-01.

**SRS §6 Feature-07 · US-07-01 — View Summary Report [MVP]**
> * **As an** Authenticated User
> * **I want to** view a monthly income vs. expense summary report
> * **So that** I can understand my savings rate and top spending categories.

No Gherkin scenario accompanies this story in `SRS.md` — unlike `BM-US-01`'s Create-Budget scenario,
there is no worked example with concrete numbers, and the As-a/I-want/So-that block above is the
entirety of the SRS's own text for `US-07-01`. The "a … report" phrasing (singular, present-tense) is
weighed in *Assumptions & Dependencies* below, against `SRS FR-07`'s own plural "trends" language
quoted next.

**SRS §2 — `SRS FR-07`: Financial Reporting**
> The System shall aggregate income and expense transactions to generate monthly summaries, net
> savings trends (`Income - Expenses`), and top category spending rankings.

**SRS §1.5 Conceptual Domain Model**
> **Wallet** — A named store of liquid money a User holds — cash, a bank account, a credit line —
> that Transactions move money into or out of (FR-03).
>
> **Category** — A label a User defines to classify money movement as one kind of income or expense,
> e.g. "Groceries" or "Salary" (FR-04).
>
> **Transaction** — A single recorded movement of money, in or out, against one Wallet and one
> Category, at a point in time (FR-06).
>
> | Relationship | Cardinality | Meaning |
> | :-- | :-- | :-- |
> | User owns Wallet | one User → many Wallets | A User may hold several Wallets — cash, bank, credit (FR-03) |
> | User defines Category | one User → many Categories | Categories belong to the User who created them, not to a shared list (FR-04) |
> | Wallet contains Transaction | one Wallet → many Transactions | Every Transaction moves money into or out of exactly one Wallet (FR-06) |
> | Category classifies Transaction | one Category → many Transactions | Every Transaction is tagged with exactly one Category (FR-06) |

Notably absent from this model: no `Report` or `Summary` entity exists anywhere in `SRS.md` §1.5's
nine-entity domain — confirmed by reading the full entity list and its relationship table. This story
introduces no new domain entity; its response is a computed projection over Transaction, Wallet, and
Category, not a stored row.

**SDS §1.5.1 Story ID Map**
> | SDS code | SRS id | Story | MVP |
> | FR-US-01…02 | US-07-01 | Financial reporting | ✔ (partial) |

The **"✔ (partial)"** marking is this document's own acknowledgement that `FR-US-01` and `FR-US-02`
*together* only partially realise `SRS FR-07`. This is the load-bearing citation for this story's
scope decision — see *Assumptions & Dependencies*.

**SDS §5.7 Financial Reporting (FR) — *SRS §6 Feature-07***
> #### 5.7.1 FR-US-01: View Summary Report (USER)
> * **Goal:** Display monthly income, total expenses, net savings, and top spending categories.
>
> #### 5.7.2 FR-US-02: View Category Expense Report (USER)
> * **Goal:** Display category-wise expense breakdown charts.

`FR-US-02` is a distinct, separately-numbered story (its own chart/visualisation concern) and is out
of scope for this dispatch.

**SDS §2.1 Domain Layer Traceability** *(reused, no change)*
> | **Wallet** | `wallets` | `WalletModel` | `WalletRead`, `WalletCreate` |
> | **Category** | `categories` | `CategoryModel` | `CategoryRead`, `CategoryCreate` |
> | **Transaction** | `transactions` | `TransactionModel` | `TransactionRead`, `TransactionCreate` |

**SDS §6.3 API Index and §6.5 API → User Story Traceability**

Checked directly: neither table has any row for Financial Reporting, `FR-US-01`, or `FR-US-02` —
every existing row belongs to `SS`, `UM`, `WM`, or `TM`. Unlike every prior story in this codebase,
there is no partial API Index entry to anchor to at all. See `plan.md` for how the endpoint path is
derived instead.

**constitution.md VL-07**
> Monetary values use `Decimal` with `DECIMAL(15,2)` precision (SRS NFR-05). Never float.

**constitution.md SEC-08**
> Queries for user-owned data filter on the authenticated `user_id` at the repository layer (SDS §7.2, SRS NFR-06).

**constitution.md PF-03**
> Responses are built from DTO projections — never a full ORM entity graph.

**constitution.md API-01 / API-06**
> All endpoints under `/api/v1`, lowercase, plural resource nouns … List endpoints accept `page` and
> `page_size`; default 25, maximum 100. Responses carry a total count.

### Out of scope for this story

`FR-US-02` (View Category Expense Report — a distinct, separately-numbered chart/visualisation story)
· any caller-supplied period, month, or year parameter · any wallet-level filter parameter · Budget
Management / Notification Handling (Features 05/08 — no budget or notification data is read or
computed here) · multi-period "trend" history (`SRS FR-07`'s own further language — see *Assumptions
& Dependencies*) · UM/SS/WM/CM/BM/TM stories, already specified in their own epic files · SRS §6
Feature-10/11 placeholders.

---

## FR-US-01: View Summary Report

### User Scenarios & Testing *(mandatory)*

As an **authenticated User**, I want to view a summary of my own total income, total expenses, net
savings, and top spending categories for the current calendar month, so that I can understand my
savings rate and where my money is going.

**Acceptance Criteria**:

**AC-01: Successfully retrieve the current month's summary report**
**Given** an authenticated User who owns at least one wallet with income and expense transactions recorded this month,
**When** the User requests their summary report,
**Then** the system returns a result carrying the current period, the User's total income, total expenses, net savings, and a ranking of their top spending categories for that period.

**AC-02: Deny access to unauthenticated callers**
**Given** a caller presenting no credentials, or credentials that are invalid or expired,
**When** the caller requests a summary report,
**Then** the system denies the request and returns an unauthenticated error, computing nothing.

**AC-03: Aggregate across every wallet the caller owns**
**Given** an authenticated User who owns more than one wallet, each with its own transactions this month,
**When** the User requests their summary report,
**Then** the returned figures reflect the combined transactions of every wallet that User owns — not just one of them.

**AC-04: Exclude another User's data**
**Given** two authenticated Users who each own a wallet and have recorded transactions this month,
**When** one User requests their summary report,
**Then** the returned figures reflect only that User's own transactions, with no trace of the other User's wallets, categories, or transactions.

**AC-05: The period is always the current calendar month, chosen by the system**
**Given** an authenticated User requests a summary report,
**When** the system computes the report,
**Then** the reported period is exactly the current calendar month, determined solely by the system — never a value the caller supplies.

**AC-06: A period with no transactions is a valid, zero-valued report, not an error**
**Given** an authenticated User who has recorded no transactions at all in the current month,
**When** that User requests their summary report,
**Then** the system returns a successful result with total income zero, total expenses zero, net savings zero, and no top spending categories — never an error.

**AC-07: Total income reflects only income transactions in the period**
**Given** an authenticated User with both income and expense transactions recorded this month,
**When** the User requests their summary report,
**Then** the reported total income equals the sum of only that User's income transactions dated within the current month.

**AC-08: Total expenses reflect only expense transactions in the period**
**Given** an authenticated User with both income and expense transactions recorded this month,
**When** the User requests their summary report,
**Then** the reported total expenses equals the sum of only that User's expense transactions dated within the current month.

**AC-09: Net savings is income minus expenses, and may be negative**
**Given** an authenticated User whose current-month expenses exceed their current-month income,
**When** the User requests their summary report,
**Then** the reported net savings equals total income minus total expenses exactly, and is a negative value.

**AC-10: Top spending categories rank by total expense amount, highest first, capped at five**
**Given** an authenticated User with expense transactions this month spread across more than five categories,
**When** the User requests their summary report,
**Then** the returned ranking lists at most five categories, ordered from the highest total expense amount to the lowest.

**AC-11: A category with no expense activity this period is omitted, not zero-padded**
**Given** an authenticated User who owns a category against which no expense transaction was recorded this month,
**When** the User requests their summary report,
**Then** that category does not appear anywhere in the top spending categories ranking.

**AC-12: Tied categories are still ordered deterministically**
**Given** an authenticated User with two categories whose current-month expense totals are exactly equal,
**When** the User requests their summary report,
**Then** both categories appear in the ranking in a stable, repeatable order rather than an order that could vary between identical requests.

**AC-13: Each ranked category is identified by name, not only by an opaque identifier**
**Given** an authenticated User whose summary report includes at least one ranked spending category,
**When** the User inspects that entry,
**Then** the entry carries both the category's identifier and its human-readable name.

**AC-14: A transaction outside the current calendar month never affects the report**
**Given** an authenticated User with a transaction dated in a month other than the current one,
**When** the User requests their summary report,
**Then** that transaction contributes to none of the reported figures.

**AC-15: The response carries exactly the documented fields**
**Given** an authenticated User requests their summary report,
**When** the system returns the result,
**Then** the result carries exactly the period, total income, total expenses, net savings, and the top spending categories ranking — no other field, and no data belonging to any other User.

### Edge Cases

**EC-01**: **A caller who owns no wallets at all** — still receives a successful, zero-valued summary report; owning no wallet is not an error condition for this story, the same "empty is not an error" treatment every list-shaped story in this codebase already gives an owner with nothing on record.

**EC-02**: **A caller whose current-month transactions are entirely income** — total expenses is zero and the top spending categories ranking is empty, without either being treated as missing or erroring.

**EC-03**: **A caller whose current-month transactions are entirely expense** — total income is zero.

**EC-04**: **Exactly five distinct categories carry a nonzero expense total this period** — all five appear in the ranking.

**EC-05**: **More than five distinct categories carry a nonzero expense total this period** — only the five with the highest totals appear; the rest are omitted, not truncated with any indication that more exist.

**EC-06**: **Fewer than five distinct categories carry a nonzero expense total this period** — exactly that many appear; the ranking is never padded with placeholder or zero-valued entries to reach five.

**EC-07**: **A transaction timestamped at the first instant of the current calendar month** — included in every figure it qualifies for.

**EC-08**: **A transaction timestamped at the first instant of the following calendar month** — excluded from every figure, even though it is only moments after the current month's last qualifying instant.

**EC-09**: **A transaction timestamped in the immediately preceding calendar month** — excluded from every figure.

**EC-10**: **Total expenses exceed total income this period** — net savings is negative (AC-09's general case, restated as its own boundary).

**EC-11**: **Total income exceeds total expenses this period** — net savings is positive.

**EC-12**: **Total income exactly equals total expenses this period** — net savings is exactly zero, not omitted or treated as a special case.

### Requirements *(mandatory)*

#### Functional Requirements

- **FR-01**: The system must **allow** an authenticated User of any role to request a summary report of their own financial activity, with no role restriction (SRS §6 US-07-01; SDS §5.7.1, tagged "(USER)").
- **FR-02**: The system must **deny** the request to unauthenticated callers, computing nothing (constitution API-08's default; mirrors every other protected endpoint in this codebase).
- **FR-03**: The system must **compute** the reporting period as the current calendar month, determined solely by the system clock, and must **accept no period-shaped value** from the caller (AC-05).
- **FR-04**: The system must **restrict** every figure in the report to transactions belonging to a wallet owned by the authenticated caller, aggregated across **every** wallet that caller owns — never a single wallet, and never another User's wallet (AC-03, AC-04; constitution SEC-08).
- **FR-05**: The system must **compute** total income as the sum of the caller's own income transactions dated within the period, or zero if none exist (AC-07, EC-02).
- **FR-06**: The system must **compute** total expenses as the sum of the caller's own expense transactions dated within the period, or zero if none exist (AC-08, EC-03).
- **FR-07**: The system must **compute** net savings as total income minus total expenses, which may be zero, positive, or negative (AC-09, EC-10, EC-11, EC-12).
- **FR-08**: The system must **rank** the caller's own expense transactions by category into a per-category total, ordered from the highest total to the lowest, and **return at most the five highest-ranked** categories, with a deterministic order for categories whose totals are equal (AC-10, AC-12, EC-04, EC-05, EC-06).
- **FR-09**: The system must **omit**, rather than include at a zero total, any category against which the caller recorded no expense transaction in the period (AC-11).
- **FR-10**: The system must **identify** each ranked category in the response by both its identifier and its human-readable name (AC-13).
- **FR-11**: The system must **return** exactly the documented fields on every successful response, and never a field belonging to another User's data (AC-15).

#### Business Rules

- **BR-01**: A report reflects only transactions belonging to a wallet the authenticated caller owns; ownership is transitive through the wallet, the same shape every other transaction-reading story in this codebase already uses (FR-04; constitution SEC-08).
- **BR-02**: The period is always the current calendar month, determined solely by the system clock — from its first instant up to, but excluding, the first instant of the following calendar month — never by client input (FR-03).
- **BR-03**: Total income and total expenses are each summed independently by transaction type; a type with no qualifying transactions in the period sums to zero rather than being left out of the response (FR-05, FR-06).
- **BR-04**: Net savings is total income minus total expenses; it carries no independent floor, ceiling, or validation of its own — it may legitimately be negative (FR-07).
- **BR-05**: The top spending categories ranking includes at most five categories, ordered by total expense amount descending and tie-broken deterministically, and never includes a category whose total for the period is zero (FR-08, FR-09).
- **BR-06**: This story reads only Wallets, Categories, and Transactions; it neither reads nor computes anything involving Budgets or Notifications (out of scope, mirrors the same boundary TM-US-01/TM-US-02 each recorded for themselves).

#### Key Entities

- **Transaction**: Reused from TM-US-01/TM-US-02 with no new field. Read-only for this story — every income and expense figure is derived by summing existing Transaction rows dated within the period (SRS §1.5; BR-01, BR-03).
- **Wallet**: Reused from WM-US-01 with no new field. Referenced, not owned, by this story — every Transaction this story reads is reached only through a wallet the requesting User owns (BR-01).
- **Category**: Reused from CM-US-01 with no new field. Referenced, not owned, by this story — the top spending categories ranking groups Transactions by their Category and reports each one's name (FR-10).
- **User**: Reused from Feature-01/Feature-02 with no new field. The authenticated caller's own ownership of the referenced Wallets is what scopes the entire report to them; no role restriction applies.
- No new domain entity is introduced. Unlike every prior story in this codebase, this story's response is a **computed projection**, not a persisted row — there is no `Report` or `Summary` table, model, or entity anywhere in `SRS.md` §1.5 or `SDS.md` §2.1's registries, confirmed by reading both directly.

### Success Criteria *(mandatory)*

- **SC-01**: An authenticated caller retrieves, in a single request, their own current month's total income, total expenses, net savings, and top spending categories.
- **SC-02**: No summary report can be retrieved by an unauthenticated caller.
- **SC-03**: A caller with no qualifying transactions in the period still receives a valid, zero-valued summary rather than an error.
- **SC-04**: The report never reflects a transaction, wallet, or category belonging to a different User.
- **SC-05**: Net savings always equals total income minus total expenses exactly, including when the result is negative or exactly zero.
- **SC-06**: The top spending categories ranking never exceeds five entries, never lists a category with a zero total for the period, and remains deterministically ordered even when totals tie.
- **SC-07**: Every response carries exactly the documented fields.

### Assumptions & Dependencies

- **Login (SS-US-01) is already implemented.** Every AC here presupposes an authenticated caller; this story adds no new authentication mechanism of its own.
- **Wallet creation (WM-US-01), Category creation (CM-US-01), and Transaction creation (TM-US-01/TM-US-02) may or may not already have produced data for the caller — every AC here must hold even when none of them have** (EC-01, AC-06). This story never requires a wallet, category, or transaction to exist as a precondition of its own success, unlike BM-US-01 (which requires a pre-existing wallet and category) — a summary report over nothing is still a valid, zero-valued report.
- **Scope: this story delivers a single-period snapshot, not multi-period trend history — the headline scope decision for this story, reasoned through rather than assumed.** `SRS FR-07`'s own text bundles three things: "monthly summaries," "net savings **trends**" (plural, implying more than one period), and "top category spending rankings." Read alone, "trends" could suggest `FR-US-01` itself must return a time series. It does not, for three independent reasons that agree with each other. First, `SDS §5.7.1`'s own goal sentence for *this specific story* — "Display monthly income, total expenses, net savings, and top spending categories" — names four figures, every one of them a single period's value, with no "trend," "history," or "over time" language anywhere in it; `SDS.md` is the technical realisation the AI may align to and design from (`CLAUDE.md` §1), and its own text for this story is unambiguous. Second, `SDS §1.5.1`'s story map marks `FR-US-01…02` together as only **"✔ (partial)"** against `SRS US-07-01` — the SDS's own author already flagged that these two stories do not fully realise `SRS FR-07`, which is a direct, documented acknowledgement that some remainder (the trend/history part) is intentionally left for a future, not-yet-numbered story, not silently dropped. Third, `FR-US-02` — the *other* SDS story sharing this requirement — is also single-period by its own goal text ("category-wise expense breakdown **charts**," no trend language either), so neither currently-numbered story claims the trend portion of `SRS FR-07`; there is no unclaimed single-period ground being left out by mistake. `SRS.md` §6's own US-07-01 text reinforces the same reading independently: "view **a** … summary report" is singular and present-tense, with no Gherkin walkthrough showing a person choosing or comparing multiple periods. **This is not escalated as `[NEEDS RULING]`**: `SRS.md` and `SDS.md` do not actually disagree here. `SDS.md` narrows `SRS FR-07`'s bundle across two stories and explicitly marks the result partial, which is exactly the "cut to the current story" scope discipline `CLAUDE.md` §1 already establishes, applied to a case where the two documents' own texts point the same way once read together rather than in isolation. Multi-period trend reporting is recorded here as a known, deliberate gap for a future story — not designed, not stubbed, and not silently absorbed into this one.
- **`FR-US-02` (View Category Expense Report) is a distinct, separately-numbered story** — a chart/visualisation concern over category-wise expense breakdown — and is out of scope for this dispatch.
- **No `SDS.md` §6.3 API Index entry exists for Financial Reporting at all**, confirmed by reading §6.3 and §6.5 directly — unlike every prior story, which had at least a partial entry to anchor to. The endpoint path is therefore invented from `constitution.md` API-01 alone; see `plan.md`.
- **This story is the first in this codebase whose response embeds a field sourced from an entity other than the one primarily being aggregated** — each top-category entry carries the Category's own `name`, not only its `id`. This is a deliberate, reasoned departure from the "no embedded foreign entity data" precedent `TM-US-01` A14 and `TM-US-02` A8 each established for a *transaction* list (where the category is a secondary reference the caller has other context for). Here the category **is** the primary subject of half the report, and — checked directly — no `GET /categories` endpoint exists anywhere in this codebase through which a caller could otherwise resolve a bare `category_id` to a name. Reasoned in full in `plan.md`.
