# Test Cases: Financial Reporting (FR)

> **Feature:** SRS §6 Feature-07 · SDS §5.7 (FR)
> **Spec:** [spec.md](spec.md) · **Plan:** [plan.md](plan.md)
> **Stories in this file:** FR-US-01 *(TC-01…TC-28)*

> **Naming note carried from `spec.md`/`plan.md`:** every `FR-NN` below is a bare, local reference to
> `spec.md`'s own Functional Requirements — never `SRS FR-07` and never the `FR-US-01` story code.

---

## FR-US-01: View Summary Report

### Quality Findings

Problems found while deriving test cases from `spec.md` and `plan.md`. Each one changes how a
criterion can be asserted, so it is recorded rather than worked around silently. `QF` numbering starts
fresh at `QF-01` — this is the epic's first story, the same situation `TM-US-01` was in for its own
file (nothing to continue from).

#### QF-01

**Description.** `plan.md` A2 computes the period's upper bound by rolling the current month forward
one calendar month, with an explicit branch for December → January (`start_date.month == 12` →
increment the year and reset to January). Every other date-boundary test this codebase has written so
far (`BM-US-01` QF-03, `TM-US-02` A6) freezes the clock to an arbitrary instant, but none of them has
ever needed the clock frozen specifically to **December**, so no existing test in this codebase
exercises the year-rollover branch at all. A suite that only freezes the clock to, say, a March instant
would never distinguish a correct `month + 1` implementation from one that forgets the year-rollover
special case entirely (which would either crash on `date(2026, 13, 1)` or silently wrap to a nonsense
month).

**Impact.** The single line of month-rollover arithmetic `plan.md` A2 adds beyond `BM-US-01` A2's
plain `.replace(day=1)` is exactly the kind of one-branch, easy-to-get-half-right code most likely to
ship untested if no test specifically forces execution through it.

**Recommendation.** `TC-26` freezes the clock to a late-December instant and asserts both that a
transaction dated in the resulting January is excluded and that the reported `period` itself is still
the frozen December instant's own month — proving the rollover lands on the correct year, not merely
"some" following month.

#### QF-02

**Description.** `plan.md` A4/A7 establish that a `TransactionType` absent from the totals query's
result (no matching rows at all, not rows summing to zero) must be defaulted to `Decimal("0.00")` in
`report_service.get_summary_report()`. A test asserting only "`total_expenses` is falsy" or "`==
0`" could pass against a buggy implementation that returns `None`, a bare `int` `0`, or an empty
string — none of which is the same observable contract as a JSON `"0.00"` `Decimal`-shaped value, and
none of which proves the *missing-key* code path (as opposed to a coincidentally-zero-summing one) was
actually exercised.

**Impact.** A loosely-written assertion would not prove the empty-aggregate defaulting `plan.md` A7's
own investigation flagged as a real trap is actually handled, only that some falsy-ish value came back.

**Recommendation.** `TC-19`/`TC-20` assert the JSON field's exact string form (`"0.00"`), constructed
so the relevant type has **zero rows of that type at all** in the period (the true missing-key path),
not merely a sum that happens to net to zero from offsetting positive and negative entries (which
cannot occur here anyway, since `amount` is always positive per `TM-US-01` BR-04 — recorded so a
future reader does not wonder why no such case is tested).

#### QF-03

**Description.** `plan.md` A5 requires a **specific, deterministic** tie-break (`category_id`
ascending) for categories with equal totals, not merely "some" stable order. A test that only checks
"both tied categories are present somewhere in `top_categories`" would pass even if the underlying
order were nondeterministic (e.g., dependent on database row-insertion order, which can vary run to
run) — it would not prove the *promised* order.

**Impact.** A regression that dropped the `category_id` secondary sort key (leaving only `ORDER BY
total DESC`) would produce a suite that still passes if it only checks set membership, silently
breaking the one exact-order guarantee `spec.md` AC-12 makes.

**Recommendation.** `TC-14` constructs two categories with **exactly equal** total expense amounts and
asserts the resulting list's exact positional order (the lexicographically/numerically smaller
`category_id` first), not just that both entries exist.

#### QF-04

**Description.** `plan.md` A5's `LIMIT 5` and "highest total first" claims are only genuinely tested by
a scenario with **more than five** distinct categories carrying different totals. A suite that only
ever creates five or fewer categories could never distinguish "correctly selects the top five" from "an
implementation bug that returns whatever five happen to exist" or "returns every category with no limit
applied at all" — the assertion would trivially pass either way once there are five or fewer rows to
begin with.

**Impact.** The single most important ranking behaviour this story has (FR-08's cap-and-select) would
be unverified by every other test in this suite, each of which necessarily uses a small, controlled
number of categories to keep its own scenario legible.

**Recommendation.** `TC-12` creates **six** categories with six distinct, non-overlapping expense
totals and asserts: (a) the response contains exactly five entries, (b) they are exactly the five
highest-total categories in descending order, and (c) the sixth (lowest-total) category is absent —
not merely that the response length is five.

#### QF-05

**Description.** `spec.md` AC-03 (aggregate across every wallet the caller owns) and AC-04 (exclude
another User's data) are two distinct claims that a naively-constructed test pair could each pass
*without either actually proving isolation*, the same class of risk `TM-US-02` QF-10 already flagged
for its own two queries. If Caller A's test data and Caller B's test data never share a category, a
period, or any other overlapping dimension, a service that forgot the `wallets.user_id` filter entirely
(silently summing every User's transactions system-wide) could still make Caller A's own total look
"correct" in isolation, purely because no other test's data happened to be present in the database at
that moment (this codebase's tests do not share fixtures across test functions — `constitution.md`
TST-08 — but nothing stops two tests running in the same suite from both existing in the same test
database file by the time either assertion runs).

**Impact.** `AC-03`/`AC-04` could both show "passing" tests while the underlying ownership join is
silently broken, if each test's own data happens not to overlap with any other test's.

**Recommendation.** `TC-28` constructs two Users, each owning a wallet, each recording an **EXPENSE
transaction against a category of the same name, for the same amount, in the same current period** —
maximally overlapping data designed specifically to make a missing ownership filter produce a
detectably wrong (roughly doubled) total for at least one of them — then asserts each User's own report
reflects only their own single transaction's amount, never the sum of both.

#### QF-06

**Description.** `plan.md` A7 records a scratch, out-of-repository empirical investigation confirming
`func.sum()`/`GROUP BY` preserve exact `Decimal` arithmetic through this codebase's real
`Numeric(15, 2)` columns — but a scratch script is not a regression test, and nothing in this
codebase's actual, permanent test suite currently proves the *real* `report_service`/`transaction_repo`
code path (as opposed to a standalone script) carries the same guarantee.

**Impact.** Without a permanent test using classic float-trap values, a future refactor (for instance,
one that introduces an intermediate `float` conversion for display formatting) could silently
reintroduce the exact drift `plan.md` A7 went to the trouble of ruling out, with nothing in CI to catch
it.

**Recommendation.** `TC-27` records several EXPENSE transactions whose amounts are classic
binary-float traps when summed naively (`0.10`, `0.20`, `19.99`, `0.01`, …) against the real endpoint
end-to-end, and asserts the returned `total_expenses` (and the affected category's `total_amount`)
equal the exact `Decimal` sum — not an approximately-equal or rounded comparison.

### Acceptance Criteria Classification

No summary-report screen exists in `mobile/` this round, and no SRS UXR names one (the same situation
`BM-US-01`'s own `test_cases.md` recorded). Every row below is `[API]`.

| AC/EC | Title | Label | Rationale |
|---|---|---|---|
| AC-01 | Successfully retrieve the current month's summary report | **[API]** | No UI surface exists or is named by any UXR this round |
| AC-02 | Deny access to unauthenticated callers | **[API]** | Backend authorization contract |
| AC-03 | Aggregate across every wallet the caller owns | **[API]** | Backend aggregation contract; bounded by QF-05 |
| AC-04 | Exclude another User's data | **[API]** | Backend ownership contract; bounded by QF-05 |
| AC-05 | The period is always the current calendar month, chosen by the system | **[API]** | Backend rule; bounded by QF-01 |
| AC-06 | A period with no transactions is a valid, zero-valued report, not an error | **[API]** | Backend rule; bounded by QF-02 |
| AC-07 | Total income reflects only income transactions in the period | **[API]** | Backend aggregation contract; bounded by QF-06 |
| AC-08 | Total expenses reflect only expense transactions in the period | **[API]** | Backend aggregation contract; bounded by QF-06 |
| AC-09 | Net savings is income minus expenses, and may be negative | **[API]** | Backend computed-field contract |
| AC-10 | Top spending categories rank by total expense amount, highest first, capped at five | **[API]** | Backend ranking contract; bounded by QF-04 |
| AC-11 | A category with no expense activity this period is omitted, not zero-padded | **[API]** | Backend rule |
| AC-12 | Tied categories are still ordered deterministically | **[API]** | Backend rule; bounded by QF-03 |
| AC-13 | Each ranked category is identified by name, not only by an opaque identifier | **[API]** | Response-payload contract |
| AC-14 | A transaction outside the current calendar month never affects the report | **[API]** | Backend boundary rule |
| AC-15 | The response carries exactly the documented fields | **[API]** | Response-payload contract |
| EC-01 | A caller who owns no wallets at all | **[API]** | Boundary condition, empty-not-error |
| EC-02 | A caller whose current-month transactions are entirely income | **[API]** | Boundary condition |
| EC-03 | A caller whose current-month transactions are entirely expense | **[API]** | Boundary condition |
| EC-04 | Exactly five distinct categories carry a nonzero expense total | **[API]** | Boundary value |
| EC-05 | More than five distinct categories carry a nonzero expense total | **[API]** | Boundary value; bounded by QF-04 |
| EC-06 | Fewer than five distinct categories carry a nonzero expense total | **[API]** | Boundary value |
| EC-07 | A transaction timestamped at the first instant of the current month | **[API]** | Boundary value, inclusive lower bound |
| EC-08 | A transaction timestamped at the first instant of the following month | **[API]** | Boundary value, exclusive upper bound |
| EC-09 | A transaction timestamped in the immediately preceding month | **[API]** | Boundary value |
| EC-10 | Total expenses exceed total income — net savings is negative | **[API]** | Computed-field boundary |
| EC-11 | Total income exceeds total expenses — net savings is positive | **[API]** | Computed-field boundary |
| EC-12 | Total income exactly equals total expenses — net savings is exactly zero | **[API]** | Computed-field boundary |

### Coverage Matrix

| AC/EC | Label | Integration TC(s) | E2E TC(s) |
|---|---|---|---|
| AC-01 | [API] | TC-01 | — |
| AC-02 | [API] | TC-02 | — |
| AC-03 | [API] | TC-03, TC-28 | — |
| AC-04 | [API] | TC-04, TC-28 | — |
| AC-05 | [API] | TC-05, TC-26 | — |
| AC-06 | [API] | TC-06 | — |
| AC-07 | [API] | TC-07, TC-27 | — |
| AC-08 | [API] | TC-08, TC-27 | — |
| AC-09 | [API] | TC-09 | — |
| AC-10 | [API] | TC-12 | — |
| AC-11 | [API] | TC-13 | — |
| AC-12 | [API] | TC-14 | — |
| AC-13 | [API] | TC-15 | — |
| AC-14 | [API] | TC-16 | — |
| AC-15 | [API] | TC-17 | — |
| EC-01 | [API] | TC-18 | — |
| EC-02 | [API] | TC-19 | — |
| EC-03 | [API] | TC-20 | — |
| EC-04 | [API] | TC-21 | — |
| EC-05 | [API] | TC-12 | — |
| EC-06 | [API] | TC-22 | — |
| EC-07 | [API] | TC-23 | — |
| EC-08 | [API] | TC-24 | — |
| EC-09 | [API] | TC-25 | — |
| EC-10 | [API] | TC-09 | — |
| EC-11 | [API] | TC-10 | — |
| EC-12 | [API] | TC-11 | — |

> Every AC and EC has at least one integration TC. There is no `[BOTH]` or `[UI]` row — no
> summary-report screen exists this round, and none is named by any SRS UXR. **Known coverage limit,
> accepted:** `plan.md` A7's PostgreSQL exactness claim is reasoned from documented SQL-standard
> behaviour, not independently tested — no Docker in this environment (constitution ENV-04) — so
> `TC-27`'s Decimal-precision proof is SQLite-only, the same environment limit every prior epic's own
> `test_cases.md` has already recorded for its own PostgreSQL-vs-SQLite claims.

### Test Implementation Map *(filled at step 4)*

All 28 test cases are implemented in
`backend/tests/integration/test_fr_us_01_view_summary_report.py`, one test function per `TC-NN`,
each carrying its `TC-NN` id in its docstring. Full suite run: `370 passed` (342 pre-existing + these
28), `ruff check`/`ruff format --check`/`mypy app` all clean, coverage 100% on every file this story
touched. See the Implement-step gate message for full pasted evidence.

| TC | pytest node id | Result |
|---|---|---|
| TC-01 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_authenticated_user_retrieves_a_populated_summary_report` | PASS |
| TC-02 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_unauthenticated_caller_is_denied_with_401_and_nothing_computed` | PASS |
| TC-03 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_report_aggregates_expense_transactions_across_two_wallets_the_same_user_owns` | PASS |
| TC-04 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_another_users_wallet_and_transactions_are_excluded` | PASS |
| TC-05 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_reports_period_is_the_first_day_of_the_frozen_instants_calendar_month` | PASS |
| TC-06 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_caller_with_no_transactions_this_month_receives_a_zero_valued_report` | PASS |
| TC-07 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_total_income_reflects_only_income_transactions` | PASS |
| TC-08 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_total_expenses_reflects_only_expense_transactions` | PASS |
| TC-09 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_net_savings_is_negative_when_expenses_exceed_income` | PASS |
| TC-10 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_net_savings_is_positive_when_income_exceeds_expenses` | PASS |
| TC-11 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_net_savings_is_exactly_zero_when_income_equals_expenses` | PASS |
| TC-12 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_top_spending_categories_select_and_order_the_highest_five_of_six` | PASS |
| TC-13 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_a_category_with_no_expense_activity_this_period_is_omitted` | PASS |
| TC-14 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_categories_tied_on_total_expense_amount_are_ordered_by_ascending_category_id` | PASS |
| TC-15 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_each_ranked_category_carries_both_an_identifier_and_a_name` | PASS |
| TC-16 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_a_transaction_dated_in_a_prior_month_never_affects_the_report` | PASS |
| TC-17 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_response_exposes_exactly_the_documented_fields` | PASS |
| TC-18 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_a_caller_who_owns_no_wallets_at_all_still_receives_a_zero_valued_report` | PASS |
| TC-19 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_a_caller_with_only_income_transactions_this_period_reports_zero_expenses` | PASS |
| TC-20 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_a_caller_with_only_expense_transactions_this_period_reports_zero_income` | PASS |
| TC-21 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_exactly_five_distinct_nonzero_expense_categories_all_appear` | PASS |
| TC-22 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_fewer_than_five_distinct_nonzero_expense_categories_are_never_padded` | PASS |
| TC-23 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_a_transaction_at_the_first_instant_of_the_current_month_is_included` | PASS |
| TC-24 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_a_transaction_at_the_first_instant_of_the_following_month_is_excluded` | PASS |
| TC-25 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_a_transaction_in_the_immediately_preceding_month_is_excluded` | PASS |
| TC-26 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_the_reporting_period_rolls_over_correctly_from_december_into_january` | PASS |
| TC-27 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_classic_float_trap_decimal_amounts_sum_exactly_end_to_end` | PASS |
| TC-28 | `backend/tests/integration/test_fr_us_01_view_summary_report.py::test_cross_wallet_aggregation_and_cross_user_isolation_with_overlapping_data` | PASS |

---

### TC-01: An authenticated User retrieves a populated summary report

- **US:** FR-US-01
- **Given:** An authenticated User who owns a wallet with both an income and an expense transaction recorded this month
- **When:** The User requests their summary report
- **Then:** The response is `200`; the body carries `period`, `total_income`, `total_expenses`, `net_savings`, and a non-empty `top_categories` list
- **AC:** AC-01, FR-01
- **Type:** integration

### TC-02: An unauthenticated caller is denied with 401

- **US:** FR-US-01
- **Given:** A caller presenting no `Authorization` header
- **When:** The caller requests the summary report
- **Then:** The response is `401` with `error_code` `NOT_AUTHENTICATED`
- **AC:** AC-02, FR-02
- **Type:** integration

### TC-03: The report aggregates transactions across two wallets the same User owns

- **US:** FR-US-01
- **Given:** An authenticated User who owns two wallets, each with an expense transaction recorded this month
- **When:** The User requests their summary report
- **Then:** `total_expenses` equals the sum of both wallets' expense transactions, not either wallet's alone
- **AC:** AC-03, FR-04
- **Type:** integration

### TC-04: Another User's wallet and transactions are excluded

- **US:** FR-US-01
- **Given:** Two authenticated Users, `A` and `B`, each owning a wallet with an expense transaction recorded this month
- **When:** `A` requests their summary report
- **Then:** `A`'s `total_expenses` reflects only `A`'s own transaction, with no contribution from `B`'s
- **AC:** AC-04, FR-04, constitution SEC-08
- **Type:** integration

### TC-05: The report's period is the current calendar month, from a frozen clock

- **US:** FR-US-01
- **Given:** An authenticated User, with the system clock frozen to a known instant
- **When:** The User requests their summary report
- **Then:** The returned `period` equals the first day of the frozen instant's calendar month
- **AC:** AC-05, FR-03, BR-02 *(assertion technique per QF-01)*
- **Type:** integration

### TC-06: A caller with no transactions this month receives a zero-valued report

- **US:** FR-US-01
- **Given:** An authenticated User who owns a wallet but has recorded no transactions at all this month
- **When:** The User requests their summary report
- **Then:** The response is `200`; `total_income` is `"0.00"`, `total_expenses` is `"0.00"`, `net_savings` is `"0.00"`, and `top_categories` is an empty list
- **AC:** AC-06, FR-05, FR-06
- **Type:** integration

### TC-07: Total income reflects only income transactions

- **US:** FR-US-01
- **Given:** An authenticated User with one income transaction and one expense transaction recorded this month, of different amounts
- **When:** The User requests their summary report
- **Then:** `total_income` equals exactly the income transaction's amount, not the sum of both
- **AC:** AC-07, FR-05
- **Type:** integration

### TC-08: Total expenses reflect only expense transactions

- **US:** FR-US-01
- **Given:** An authenticated User with one income transaction and one expense transaction recorded this month, of different amounts
- **When:** The User requests their summary report
- **Then:** `total_expenses` equals exactly the expense transaction's amount, not the sum of both
- **AC:** AC-08, FR-06
- **Type:** integration

### TC-09: Net savings is negative when expenses exceed income

- **US:** FR-US-01
- **Given:** An authenticated User whose current-month expense transactions total more than their income transactions
- **When:** The User requests their summary report
- **Then:** `net_savings` equals `total_income - total_expenses` exactly, and is negative
- **AC:** AC-09, EC-10, FR-07, BR-04
- **Type:** integration

### TC-10: Net savings is positive when income exceeds expenses

- **US:** FR-US-01
- **Given:** An authenticated User whose current-month income transactions total more than their expense transactions
- **When:** The User requests their summary report
- **Then:** `net_savings` equals `total_income - total_expenses` exactly, and is positive
- **AC:** EC-11, FR-07, BR-04
- **Type:** integration

### TC-11: Net savings is exactly zero when income equals expenses

- **US:** FR-US-01
- **Given:** An authenticated User whose current-month income transactions total exactly the same as their expense transactions
- **When:** The User requests their summary report
- **Then:** `net_savings` equals exactly `"0.00"`
- **AC:** EC-12, FR-07, BR-04
- **Type:** integration

### TC-12: Top spending categories select and order the highest five of six

- **US:** FR-US-01
- **Given:** An authenticated User with expense transactions across six distinct categories this month, each category's total strictly different from every other
- **When:** The User requests their summary report
- **Then:** `top_categories` contains exactly five entries, ordered from the highest total expense amount to the lowest, and the sixth (lowest-total) category does not appear anywhere in the list
- **AC:** AC-10, EC-05, FR-08 *(assertion technique per QF-04)*
- **Type:** integration

### TC-13: A category with no expense activity this period is omitted

- **US:** FR-US-01
- **Given:** An authenticated User who owns a category against which no expense transaction was recorded this month, alongside another category that does have expense transactions this month
- **When:** The User requests their summary report
- **Then:** `top_categories` includes the category with activity, and does not include the category with none
- **AC:** AC-11, FR-09
- **Type:** integration

### TC-14: Categories tied on total expense amount are ordered deterministically

- **US:** FR-US-01
- **Given:** An authenticated User with two categories whose current-month expense totals are exactly equal
- **When:** The User requests their summary report
- **Then:** Both categories appear in `top_categories`, in ascending `category_id` order relative to each other — not merely both present in some order
- **AC:** AC-12, FR-08, BR-05 *(assertion technique per QF-03)*
- **Type:** integration

### TC-15: Each ranked category carries both an identifier and a name

- **US:** FR-US-01
- **Given:** An authenticated User with at least one expense transaction against a named category this month
- **When:** The User requests their summary report
- **Then:** The corresponding `top_categories` entry carries both `category_id` equal to the category's id and `category_name` equal to the category's own name
- **AC:** AC-13, FR-10
- **Type:** integration

### TC-16: A transaction outside the current month never affects the report

- **US:** FR-US-01
- **Given:** An authenticated User with an expense transaction dated in the previous calendar month, and no transactions this month
- **When:** The User requests their summary report
- **Then:** `total_expenses` is `"0.00"` and `top_categories` is empty — the prior-month transaction contributes to nothing
- **AC:** AC-14, BR-02
- **Type:** integration

### TC-17: The response exposes exactly the five documented top-level fields

- **US:** FR-US-01
- **Given:** An authenticated User requests their summary report
- **When:** The response is returned
- **Then:** The body's top-level keys are exactly `period`, `total_income`, `total_expenses`, `net_savings`, `top_categories` — no more, and each `top_categories` entry's keys are exactly `category_id`, `category_name`, `total_amount`
- **AC:** AC-15, FR-11, constitution PF-03
- **Type:** integration

### TC-18: A caller who owns no wallets at all still receives a zero-valued report

- **US:** FR-US-01
- **Given:** An authenticated User who owns no wallets at all
- **When:** The User requests their summary report
- **Then:** The response is `200`, not `404`; every figure is zero-valued and `top_categories` is empty
- **AC:** EC-01
- **Type:** integration

### TC-19: A caller with only income transactions this period reports zero expenses

- **US:** FR-US-01
- **Given:** An authenticated User whose only transactions this month are income transactions
- **When:** The User requests their summary report
- **Then:** `total_expenses` is exactly `"0.00"` and `top_categories` is empty
- **AC:** EC-02, FR-06 *(assertion technique per QF-02 — the missing-key path, not a coincidental zero sum)*
- **Type:** integration

### TC-20: A caller with only expense transactions this period reports zero income

- **US:** FR-US-01
- **Given:** An authenticated User whose only transactions this month are expense transactions
- **When:** The User requests their summary report
- **Then:** `total_income` is exactly `"0.00"`
- **AC:** EC-03, FR-05 *(assertion technique per QF-02)*
- **Type:** integration

### TC-21: Exactly five distinct nonzero-expense categories all appear

- **US:** FR-US-01
- **Given:** An authenticated User with expense transactions across exactly five distinct categories this month, each with a nonzero total
- **When:** The User requests their summary report
- **Then:** `top_categories` contains exactly those five categories
- **AC:** EC-04, FR-08
- **Type:** integration

### TC-22: Fewer than five distinct nonzero-expense categories are never padded

- **US:** FR-US-01
- **Given:** An authenticated User with expense transactions across exactly two distinct categories this month
- **When:** The User requests their summary report
- **Then:** `top_categories` contains exactly those two entries — never padded with placeholder or zero-valued entries to reach five
- **AC:** EC-06, FR-08
- **Type:** integration

### TC-23: A transaction at the first instant of the current month is included

- **US:** FR-US-01
- **Given:** An authenticated User with the system clock frozen to a known instant, and an expense transaction timestamped at exactly the first instant of that frozen instant's calendar month
- **When:** The User requests their summary report
- **Then:** That transaction's amount is included in `total_expenses`
- **AC:** EC-07, BR-02
- **Type:** integration

### TC-24: A transaction at the first instant of the following month is excluded

- **US:** FR-US-01
- **Given:** An authenticated User with the system clock frozen to a known instant, and an expense transaction timestamped at exactly the first instant of the *following* calendar month
- **When:** The User requests their summary report
- **Then:** That transaction's amount is not included in `total_expenses`
- **AC:** EC-08, BR-02
- **Type:** integration

### TC-25: A transaction in the immediately preceding month is excluded

- **US:** FR-US-01
- **Given:** An authenticated User with the system clock frozen to a known instant, and an expense transaction timestamped in the calendar month immediately before that frozen instant's month
- **When:** The User requests their summary report
- **Then:** That transaction's amount is not included in `total_expenses`
- **AC:** EC-09, BR-02
- **Type:** integration

### TC-26: The reporting period rolls over correctly from December into January

- **US:** FR-US-01
- **Given:** The system clock frozen to a late-December instant, and an authenticated User with an expense transaction timestamped in the following January
- **When:** The User requests their summary report
- **Then:** The reported `period` is the frozen instant's own December, and the January-dated transaction's amount is not included in any figure
- **AC:** AC-05, BR-02 *(assertion technique per QF-01)*
- **Type:** integration

### TC-27: Classic float-trap decimal amounts sum exactly, end to end

- **US:** FR-US-01
- **Given:** An authenticated User with several expense transactions this month against the same category, with amounts `19.99`, `0.01`, `0.20`, and `0.10` (a sum that a binary-float accumulation would not reproduce exactly)
- **When:** The User requests their summary report
- **Then:** `total_expenses` and the corresponding `top_categories` entry's `total_amount` both equal exactly `"20.30"` — an exact string/decimal match, not an approximately-equal comparison
- **AC:** AC-07, AC-08, constitution VL-07 *(assertion technique per QF-06; SQLite only — see Coverage Matrix note)*
- **Type:** integration

### TC-28: Cross-wallet aggregation and cross-user isolation with overlapping data

- **US:** FR-US-01
- **Given:** Two authenticated Users, `A` and `B`, each owning one wallet and one category of the identical name, each recording one expense transaction of the identical amount this month
- **When:** Each User separately requests their own summary report
- **Then:** Each User's `total_expenses` equals exactly their own single transaction's amount — never the sum of both Users' transactions
- **AC:** AC-03, AC-04 *(assertion technique per QF-05)*
- **Type:** integration
