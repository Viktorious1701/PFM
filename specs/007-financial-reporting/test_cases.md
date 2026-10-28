# Test Cases: Financial Reporting (FR)

> **Feature:** SRS §6 Feature-07 · SDS §5.7 (FR)
> **Spec:** [spec.md](spec.md) · **Plan:** [plan.md](plan.md)
> **Stories in this file:** FR-US-01 *(TC-01…TC-28)* · FR-US-03 *(TC-29…TC-54)*

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

> **Re-run 2026-10-28, after FR-US-03 T-06** (`plan.md` FR-US-03 A11). All 28 functions now read
> the single `USD` entry of `currencies` and pass (`28 passed`; full suite `682 passed`). The map rows
> above stay as written. FR-US-03 superseded two of them, and their functions were renamed for what
> they now prove:
> TC-17 → `::test_response_exposes_exactly_the_documented_per_currency_fields` (asserts FR-US-03
> TC-40's outcome) and TC-18 → `::test_a_caller_who_owns_no_wallets_at_all_receives_200_with_no_currency_entries`
> (asserts FR-US-03 TC-37's outcome). Both PASS. See FR-US-03 *FR-US-01 test cases affected*.

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

---

## FR-US-03: Summary Report per Currency

> **IDs in this section are local to FR-US-03** — except `TC-NN` and `QF-NN`, which continue this
> epic file's numbering: FR-US-01 used `TC-01`…`TC-28` and `QF-01`…`QF-06`, so this story starts at
> `TC-29` and `QF-07` (the continuing convention `specs/006-transaction-management/test_cases.md`
> records and reasons for). `AC-NN`/`EC-NN` below are FR-US-03's own, from `spec.md`.

### Quality Findings

#### QF-07

**Description.** The per-currency totals query has the same "a missing group is not a zero row" trap
FR-US-01 QF-02 recorded, now once per `(currency, type)` pair — and the held-but-unused currency
(spec AC-07) reaches the service through a *different* source (the active-wallet read, `plan.md` A7)
with no totals row at all. A test that only checks "the currency is present" would pass against an
entry carrying `null` figures.

**Impact.** The zero-defaulting `plan.md` A5 requires could be wrong for exactly the entries that have
no transactions, which no other test exercises.

**Recommendation.** `TC-36`, `TC-44` and `TC-45` assert the exact string `"0.00"` for every absent
figure and an empty `top_categories` list, on a currency with **zero rows** of that type in the period.

#### QF-08

**Description.** `plan.md` A4 sorts currencies by code in the service. If a test creates its wallets
in alphabetical order, database insertion order and the promised order coincide, and a missing
`sorted(...)` would still pass.

**Impact.** AC-04's only guarantee could regress unnoticed.

**Recommendation.** `TC-32` creates the wallets in the order VND, EUR, USD — deliberately not
alphabetical — and asserts the exact sequence `["EUR", "USD", "VND"]` on two consecutive requests.

#### QF-09

**Description.** `plan.md` A6's window query is only proven *partitioned* by a scenario where an
unpartitioned `LIMIT 5` would give a visibly different answer. If every currency in a test has five or
fewer categories, a query that ranks globally and cuts at five overall could still return every row.

**Impact.** The defect the ruling exists to prevent — one currency's spending crowding out another's —
would survive the suite.

**Recommendation.** `TC-33` gives VND six spending categories whose totals are all numerically larger
than either of USD's two, so a global top five would contain only VND rows. It asserts VND has
exactly five (the sixth absent) **and** USD still has both of its own.

#### QF-10

**Description.** A cross-currency leak is easiest to miss when the leaked amount is small relative to
the right answer, or when one category is spent in only one currency.

**Impact.** A query grouped by category but not by currency would pass a test where each category
lives in one currency only.

**Recommendation.** `TC-30` uses amounts of very different magnitude (100,000.00 VND, 20.00 USD) and
asserts no field anywhere equals their sum; `TC-35` spends the **same** category in both currencies
and asserts each ranking carries its own currency's total for it.

#### QF-11

**Description.** This story reshapes FR-US-01's response. FR-US-01's test cases stay as written
(`CLAUDE.md` §1.1 rule 4), but two of them describe an outcome that no longer holds, and all of them
name top-level fields that move into `currencies[0]`.

**Impact.** Without a record, FR-US-01's TC text and its tests would disagree silently after T-06.

**Recommendation.** The table *FR-US-01 test cases affected* below maps every FR-US-01 TC to its fate.
`plan.md` T-06 re-points the test functions; their docstrings keep their FR-US-01 `TC-NN` and, for
TC-17/TC-18, also cite the superseding TC.

#### QF-12

**Description.** The `[UI]` criteria (AC-14…AC-16) are about *which currency* an amount is shown in.
`CLAUDE.md` §1.1 rule 0 forbids asserting visual design.

**Impact.** A currency-labelling assertion could drift into a styling assertion.

**Recommendation.** The e2e TCs assert only text content and containment: a block's heading text, the
currency marker inside an amount's text (`$` for USD, a trailing `đ` for VND, per
`mobile/src/utils/money.ts`), and which category names a block's breakdown contains. No colour, size,
width, or position is asserted — bar widths in particular are not tested.

### FR-US-01 test cases affected

| FR-US-01 TC | Fate | How |
| :-- | :-- | :-- |
| TC-01…TC-16, TC-19…TC-28 | Holds, re-pointed | Every flat-field assertion reads `currencies[0]`, whose `currency` is `"USD"` (all FR-US-01 tests build USD wallets) |
| TC-06, TC-16 | Holds, re-pointed | The caller owns an active USD wallet, so the zero-valued USD entry exists (spec AC-07) |
| TC-17 | **Superseded by TC-40** | Top-level keys are now exactly `period`, `currencies` |
| TC-18 | **Superseded by TC-37** | No wallets now yields `currencies: []`, not zero-valued flat figures |

### Acceptance Criteria Classification

| AC/EC | Title | Label | Rationale |
|---|---|---|---|
| AC-01 | Figures are reported separately for each currency | **[API]** | Response contract; the screen side is AC-14 |
| AC-02 | Amounts in different currencies are never added together | **[API]** | Aggregation contract; bounded by QF-10 |
| AC-03 | Wallets sharing a currency are combined into one entry | **[API]** | Aggregation contract |
| AC-04 | Currency entries appear in a fixed, repeatable order | **[API]** | Ordering contract; bounded by QF-08 (the screen follows response order, TC-50) |
| AC-05 | Top spending categories are ranked within each currency | **[API]** | Ranking contract; bounded by QF-09 |
| AC-06 | A category spent in two currencies appears in each ranking | **[API]** | Ranking contract; bounded by QF-10 |
| AC-07 | A held currency not used this month is reported at zero | **[BOTH]** | API zero entry; Home shows its block |
| AC-08 | Archived wallets keep counting for the month they were used in | **[API]** | Presence rule |
| AC-09 | Nothing to report is a valid, empty report | **[BOTH]** | API empty list; Home empty message |
| AC-10 | Deny access to unauthenticated callers | **[API]** | Authorization contract |
| AC-11 | Another User's data never appears, in any currency | **[API]** | Ownership contract |
| AC-12 | The response carries exactly the documented fields | **[API]** | Payload contract |
| AC-13 | The reporting period applies to every currency alike | **[API]** | Period rule |
| AC-14 | Home shows one analysis block per currency | **[UI]** | Screen behaviour |
| AC-15 | Each block shows its amounts in its own currency | **[UI]** | Screen behaviour; bounded by QF-12 |
| AC-16 | "Where the money went" lists only that currency's categories | **[UI]** | Screen behaviour |
| EC-01 | Income but no expenses in a currency | **[API]** | Boundary; bounded by QF-07 |
| EC-02 | Expenses but no income in a currency | **[API]** | Boundary; bounded by QF-07 |
| EC-03 | One currency saves while another overspends | **[API]** | Sign independence |
| EC-04 | Category archived after being spent against | **[API]** | Consistency with FR-US-01 |
| EC-05 | Only one currency held | **[BOTH]** | API one entry; Home one labelled block |
| EC-06 | No wallet in the app's default currency | **[API]** | No invented entry |
| EC-07 | Two currencies with identical figures | **[API]** | No merging |

### Coverage Matrix

| Story | AC/EC | Label | TC(s) | Test node id | Status |
|---|---|---|---|---|---|
| FR-US-03 | AC-01 | [API] | TC-29 | `::test_figures_are_reported_separately_for_vnd_and_usd` | PASS — 2026-10-28 |
| FR-US-03 | AC-02 | [API] | TC-30 | `::test_amounts_in_different_currencies_are_never_added_together` | PASS — 2026-10-28 |
| FR-US-03 | AC-03 | [API] | TC-31 | `::test_two_wallets_in_the_same_currency_form_one_entry` | PASS — 2026-10-28 |
| FR-US-03 | AC-04 | [API] | TC-32 | `::test_currency_entries_are_ordered_by_code_the_same_on_every_request` | PASS — 2026-10-28 |
| FR-US-03 | AC-05 | [API] | TC-33, TC-34 | `::test_each_currency_has_its_own_top_five_never_crowded_out_by_another` · `::test_tied_categories_within_one_currency_are_ordered_by_identifier` | PASS — 2026-10-28 |
| FR-US-03 | AC-06 | [API] | TC-35 | `::test_a_category_spent_in_two_currencies_ranks_in_each_with_its_own_total` | PASS — 2026-10-28 |
| FR-US-03 | AC-07 | [BOTH] | TC-36 · e2e TC-53 | `::test_a_held_currency_with_no_activity_this_month_is_a_zero_entry` · `home.spec.ts` › TC-53 | PASS — 2026-10-28 |
| FR-US-03 | AC-08 | [API] | TC-42 | `::test_archived_wallet_still_counts_this_month_but_archived_unused_currency_is_absent` | PASS — 2026-10-28 |
| FR-US-03 | AC-09 | [BOTH] | TC-37, TC-43 · e2e TC-54 | `::test_a_user_with_no_wallets_receives_an_empty_report` · `::test_a_user_with_only_archived_unused_wallets_receives_an_empty_report` · `home.spec.ts` › TC-54 | PASS — 2026-10-28 |
| FR-US-03 | AC-10 | [API] | TC-38 | `::test_an_unauthenticated_caller_is_denied_with_401` | PASS — 2026-10-28 |
| FR-US-03 | AC-11 | [API] | TC-39 | `::test_another_users_currency_and_amounts_never_appear` | PASS — 2026-10-28 |
| FR-US-03 | AC-12 | [API] | TC-40 | `::test_the_response_carries_exactly_the_documented_fields_at_every_level` | PASS — 2026-10-28 |
| FR-US-03 | AC-13 | [API] | TC-41 | `::test_the_period_applies_to_every_currency_alike` | PASS — 2026-10-28 |
| FR-US-03 | AC-14 | [UI] | e2e TC-50 | `home.spec.ts` › TC-50 | PASS — 2026-10-28 |
| FR-US-03 | AC-15 | [UI] | e2e TC-51 | `home.spec.ts` › TC-51 | PASS — 2026-10-28 |
| FR-US-03 | AC-16 | [UI] | e2e TC-52 | `home.spec.ts` › TC-52 | PASS — 2026-10-28 |
| FR-US-03 | EC-01 | [API] | TC-44 | `::test_a_currency_with_income_only_reports_zero_expenses` | PASS — 2026-10-28 |
| FR-US-03 | EC-02 | [API] | TC-45 | `::test_a_currency_with_expenses_only_reports_zero_income_and_negative_net_savings` | PASS — 2026-10-28 |
| FR-US-03 | EC-03 | [API] | TC-46 | `::test_net_savings_carry_their_own_sign_per_currency` | PASS — 2026-10-28 |
| FR-US-03 | EC-04 | [API] | TC-47 | `::test_a_category_archived_after_being_spent_against_still_ranks_in_its_currency` | PASS — 2026-10-28 |
| FR-US-03 | EC-05 | [BOTH] | TC-48 · e2e TC-53 | `::test_a_user_holding_only_eur_gets_exactly_one_eur_entry_and_nothing_invented` · `home.spec.ts` › TC-53 | PASS — 2026-10-28 |
| FR-US-03 | EC-06 | [API] | TC-48 | `::test_a_user_holding_only_eur_gets_exactly_one_eur_entry_and_nothing_invented` | PASS — 2026-10-28 |
| FR-US-03 | EC-07 | [API] | TC-49 | `::test_two_currencies_with_identical_figures_stay_two_entries` | PASS — 2026-10-28 |

> Every AC and EC has at least one TC; every `[UI]`/`[BOTH]` row has an e2e TC. Integration TCs go
> in `backend/tests/integration/test_fr_us_03_summary_per_currency.py` (`plan.md` T-07), e2e TCs in
> `mobile/e2e/home.spec.ts` (T-09). Node ids are filled at step 4. **Known coverage limit,
> accepted:** the window-function exactness (`plan.md` A6) is proven on SQLite only — PostgreSQL is
> not runnable here (constitution ENV-04), the same limit FR-US-01's matrix note records.

### Test Implementation Map *(filled at step 4)*

Integration TCs: `backend/tests/integration/test_fr_us_03_summary_per_currency.py`, one test
function per `TC-NN`, each naming its `TC-NN` in its docstring (`plan.md` FR-US-03 T-07). E2E TCs: `mobile/e2e/home.spec.ts`, each test title starting with its
`TC-NN` (T-09). Run on 2026-10-28: backend full suite `682 passed`; `ruff check`, `ruff format
--check`, `mypy app` clean; coverage TOTAL 99%, 100% on every file this story touched
(`schemas/report.py`, `transaction_repo.py`, `wallet_repo.py`, `report_service.py`,
`api/v1/reports.py`); `npm run typecheck` exit 0; full e2e suite `120 passed` (desktop + phone).

| TC | pytest node id / e2e test | Result |
|---|---|---|
| TC-29 | `backend/tests/integration/test_fr_us_03_summary_per_currency.py::test_figures_are_reported_separately_for_vnd_and_usd` | PASS — 2026-10-28 |
| TC-30 | `backend/tests/integration/test_fr_us_03_summary_per_currency.py::test_amounts_in_different_currencies_are_never_added_together` | PASS — 2026-10-28 |
| TC-31 | `backend/tests/integration/test_fr_us_03_summary_per_currency.py::test_two_wallets_in_the_same_currency_form_one_entry` | PASS — 2026-10-28 |
| TC-32 | `backend/tests/integration/test_fr_us_03_summary_per_currency.py::test_currency_entries_are_ordered_by_code_the_same_on_every_request` | PASS — 2026-10-28 |
| TC-33 | `backend/tests/integration/test_fr_us_03_summary_per_currency.py::test_each_currency_has_its_own_top_five_never_crowded_out_by_another` | PASS — 2026-10-28 |
| TC-34 | `backend/tests/integration/test_fr_us_03_summary_per_currency.py::test_tied_categories_within_one_currency_are_ordered_by_identifier` | PASS — 2026-10-28 |
| TC-35 | `backend/tests/integration/test_fr_us_03_summary_per_currency.py::test_a_category_spent_in_two_currencies_ranks_in_each_with_its_own_total` | PASS — 2026-10-28 |
| TC-36 | `backend/tests/integration/test_fr_us_03_summary_per_currency.py::test_a_held_currency_with_no_activity_this_month_is_a_zero_entry` | PASS — 2026-10-28 |
| TC-37 | `backend/tests/integration/test_fr_us_03_summary_per_currency.py::test_a_user_with_no_wallets_receives_an_empty_report` | PASS — 2026-10-28 |
| TC-38 | `backend/tests/integration/test_fr_us_03_summary_per_currency.py::test_an_unauthenticated_caller_is_denied_with_401` | PASS — 2026-10-28 (both parametrised cases: `no-header`, `invalid-bearer`) |
| TC-39 | `backend/tests/integration/test_fr_us_03_summary_per_currency.py::test_another_users_currency_and_amounts_never_appear` | PASS — 2026-10-28 |
| TC-40 | `backend/tests/integration/test_fr_us_03_summary_per_currency.py::test_the_response_carries_exactly_the_documented_fields_at_every_level` | PASS — 2026-10-28 |
| TC-41 | `backend/tests/integration/test_fr_us_03_summary_per_currency.py::test_the_period_applies_to_every_currency_alike` | PASS — 2026-10-28 |
| TC-42 | `backend/tests/integration/test_fr_us_03_summary_per_currency.py::test_archived_wallet_still_counts_this_month_but_archived_unused_currency_is_absent` | PASS — 2026-10-28 |
| TC-43 | `backend/tests/integration/test_fr_us_03_summary_per_currency.py::test_a_user_with_only_archived_unused_wallets_receives_an_empty_report` | PASS — 2026-10-28 |
| TC-44 | `backend/tests/integration/test_fr_us_03_summary_per_currency.py::test_a_currency_with_income_only_reports_zero_expenses` | PASS — 2026-10-28 |
| TC-45 | `backend/tests/integration/test_fr_us_03_summary_per_currency.py::test_a_currency_with_expenses_only_reports_zero_income_and_negative_net_savings` | PASS — 2026-10-28 |
| TC-46 | `backend/tests/integration/test_fr_us_03_summary_per_currency.py::test_net_savings_carry_their_own_sign_per_currency` | PASS — 2026-10-28 |
| TC-47 | `backend/tests/integration/test_fr_us_03_summary_per_currency.py::test_a_category_archived_after_being_spent_against_still_ranks_in_its_currency` | PASS — 2026-10-28 |
| TC-48 | `backend/tests/integration/test_fr_us_03_summary_per_currency.py::test_a_user_holding_only_eur_gets_exactly_one_eur_entry_and_nothing_invented` | PASS — 2026-10-28 |
| TC-49 | `backend/tests/integration/test_fr_us_03_summary_per_currency.py::test_two_currencies_with_identical_figures_stay_two_entries` | PASS — 2026-10-28 |
| TC-50 | `mobile/e2e/home.spec.ts` › TC-50 | PASS — 2026-10-28, desktop + phone |
| TC-51 | `mobile/e2e/home.spec.ts` › TC-51 | PASS — 2026-10-28, desktop + phone |
| TC-52 | `mobile/e2e/home.spec.ts` › TC-52 | PASS — 2026-10-28, desktop + phone |
| TC-53 | `mobile/e2e/home.spec.ts` › TC-53 | PASS — 2026-10-28, desktop + phone |
| TC-54 | `mobile/e2e/home.spec.ts` › TC-54 | PASS — 2026-10-28, desktop + phone |

Notes:

1. **Seen failing first.** Before T-01…T-05 existed, the integration file plus the re-pointed
   FR-US-01 file ran `46 failed, 4 passed`. The four that passed are `401`/`period` checks
   (TC-38's two cases, FR-US-01 TC-02 and TC-05), which this story leaves unchanged by design
   (`plan.md` FR-US-03 A10). Every other failure was `KeyError: 'currencies'` or the old flat key
   set. Before T-08, `home.spec.ts` ran against HEAD's `Dashboard.tsx` with `5 failed` (desktop),
   each on a missing `report-…` element.
2. **The guarding tests can fail.** Two mutations were applied by hand and then reverted. Dropping
   `partition_by` from the ranking window (a global top five) failed TC-33. Replacing the
   currency `sorted(...)` with insertion order failed TC-32 and TC-49. This shows QF-08 and QF-09
   catch the defects they were written for.
3. **TC-38 is two cases in one TC.** It runs as one parametrised test with two cases, so it
   reports as two passes.
4. **E2E titles TC-50…TC-54 also exist in `mobile/e2e/auth.spec.ts`**, which holds
   `specs/002-system-security`'s UI TCs (TC ids are per epic). The file name tells them apart. To run one, name
   both the file and the title: `npm run test:e2e -- home.spec.ts -g "TC-50 "`.
5. **SS-US-03 TC-61's test reads this report** and was re-pointed to the single `VND` entry
   (`plan.md` FR-US-03 A14, T-06). It passes in the full run, and SS-US-03 TC-61's own result is
   unchanged.

---

### TC-29: Figures are reported separately for VND and USD

- **US:** FR-US-03
- **Given:** An authenticated User owning a VND wallet with an income of `15000000.00` and an expense of `100000.00`, and a USD wallet with an income of `500.00` and an expense of `20.00`, all this month
- **When:** The User requests their summary report
- **Then:** The response is `200`; `currencies` has exactly two entries; the `VND` entry has `total_income` `"15000000.00"`, `total_expenses` `"100000.00"`, `net_savings` `"14900000.00"`; the `USD` entry has `"500.00"`, `"20.00"`, `"480.00"`; each entry's `top_categories` lists only categories spent in that currency
- **AC:** AC-01, FR-01, FR-03
- **Type:** integration

### TC-30: Amounts in different currencies are never added together

- **US:** FR-US-03
- **Given:** An authenticated User with an expense of `100000.00` from a VND wallet and an expense of `20.00` from a USD wallet this month, against two different categories
- **When:** The User requests their summary report
- **Then:** The `VND` entry's `total_expenses` is `"100000.00"` and the `USD` entry's is `"20.00"`; no value anywhere in the response equals `"100020.00"`
- **AC:** AC-02, FR-02, BR-02 *(assertion technique per QF-10)*
- **Type:** integration

### TC-31: Two wallets in the same currency form one entry

- **US:** FR-US-03
- **Given:** An authenticated User owning two VND wallets, with an expense of `30000.00` from one and `70000.00` from the other this month
- **When:** The User requests their summary report
- **Then:** `currencies` has exactly one entry, `VND`, with `total_expenses` `"100000.00"`
- **AC:** AC-03, FR-01
- **Type:** integration

### TC-32: Currency entries are ordered by code, the same on every request

- **US:** FR-US-03
- **Given:** An authenticated User who creates a VND wallet, then a EUR wallet, then a USD wallet, each with an expense this month
- **When:** The User requests their summary report twice
- **Then:** On both responses the sequence of `currency` values is exactly `["EUR", "USD", "VND"]`
- **AC:** AC-04, FR-06, BR-04 *(assertion technique per QF-08)*
- **Type:** integration

### TC-33: Each currency has its own top five, never crowded out by another

- **US:** FR-US-03
- **Given:** An authenticated User with VND expenses this month across six categories with distinct totals `600000.00` … `100000.00`, and USD expenses across two categories of `50.00` and `10.00`
- **When:** The User requests their summary report
- **Then:** The `VND` entry's `top_categories` has exactly five entries in descending total order and omits the `100000.00` category; the `USD` entry's has exactly its two categories, `50.00` then `10.00`, not padded
- **AC:** AC-05, FR-04 *(assertion technique per QF-09)*
- **Type:** integration

### TC-34: Tied categories within one currency are ordered by identifier

- **US:** FR-US-03
- **Given:** An authenticated User with two categories each carrying exactly `40.00` of USD expenses this month
- **When:** The User requests their summary report
- **Then:** Both appear in the `USD` entry's `top_categories`, the one with the smaller `category_id` first
- **AC:** AC-05, FR-04
- **Type:** integration

### TC-35: A category spent in two currencies ranks in each with its own total

- **US:** FR-US-03
- **Given:** An authenticated User with one category "Food", against which `0.10` and `0.20` were spent from a USD wallet and `50000.00` from a VND wallet this month
- **When:** The User requests their summary report
- **Then:** "Food" appears in the `USD` ranking with `total_amount` `"0.30"` and in the `VND` ranking with `"50000.00"` — exact string matches
- **AC:** AC-06, FR-02, FR-04, constitution VL-07 *(assertion technique per QF-10)*
- **Type:** integration

### TC-36: A held currency with no activity this month is a zero entry

- **US:** FR-US-03
- **Given:** An authenticated User owning an active EUR wallet with no transactions at all, and a VND wallet with an expense this month
- **When:** The User requests their summary report
- **Then:** `currencies` has a `EUR` entry with `total_income`, `total_expenses` and `net_savings` each exactly `"0.00"` and `top_categories` `[]`, alongside the `VND` entry
- **AC:** AC-07, FR-05, BR-03 *(assertion technique per QF-07)*
- **Type:** integration

### TC-37: A User with no wallets receives an empty report

- **US:** FR-US-03
- **Given:** An authenticated User who owns no wallets
- **When:** The User requests their summary report
- **Then:** The response is `200`, `period` is the first day of the current month, and `currencies` is exactly `[]`
- **AC:** AC-09, FR-07 *(supersedes FR-US-01 TC-18, per QF-11)*
- **Type:** integration

### TC-38: An unauthenticated caller is denied with 401

- **US:** FR-US-03
- **Given:** A caller presenting no `Authorization` header, and separately one presenting an invalid bearer token
- **When:** Each requests the summary report
- **Then:** Both responses are `401` with `error_code` `NOT_AUTHENTICATED` and no `currencies` field
- **AC:** AC-10, FR-08, constitution SEC-07
- **Type:** integration

### TC-39: Another User's currency and amounts never appear

- **US:** FR-US-03
- **Given:** User `A` owns a VND wallet with an expense of `100000.00`; User `B` owns a VND wallet with an expense of `100000.00` against a same-named category and a EUR wallet with an expense of `30.00`, all this month
- **When:** `A` requests their summary report
- **Then:** `A`'s `currencies` has only a `VND` entry with `total_expenses` `"100000.00"` (not `"200000.00"`) and no `EUR` entry
- **AC:** AC-11, FR-08, constitution SEC-08
- **Type:** integration

### TC-40: The response carries exactly the documented fields at every level

- **US:** FR-US-03
- **Given:** An authenticated User with one expense this month
- **When:** The User requests their summary report
- **Then:** Top-level keys are exactly `period`, `currencies`; each entry's keys are exactly `currency`, `total_income`, `total_expenses`, `net_savings`, `top_categories`; each ranked category's keys are exactly `category_id`, `category_name`, `total_amount`
- **AC:** AC-12, FR-09, constitution PF-03 *(supersedes FR-US-01 TC-17, per QF-11)*
- **Type:** integration

### TC-41: The period applies to every currency alike

- **US:** FR-US-03
- **Given:** The clock frozen to a mid-month instant; an authenticated User with, in each of a VND and a USD wallet, one expense dated this month and one dated in the previous month
- **When:** The User requests their summary report
- **Then:** `period` is the first day of the frozen month; each entry's `total_expenses` equals only its this-month expense
- **AC:** AC-13, FR-08
- **Type:** integration

### TC-42: An archived wallet's transactions this month still count, an archived unused currency does not appear

- **US:** FR-US-03
- **Given:** An authenticated User with a USD wallet that had an expense of `20.00` this month and was then archived, and a EUR wallet with no transactions that was archived; the User holds no other USD or EUR wallet
- **When:** The User requests their summary report
- **Then:** A `USD` entry exists with `total_expenses` `"20.00"`; no `EUR` entry exists
- **AC:** AC-08, FR-05, BR-03
- **Type:** integration

### TC-43: A User with only archived, unused wallets receives an empty report

- **US:** FR-US-03
- **Given:** An authenticated User whose only wallet is archived and has no transactions this month
- **When:** The User requests their summary report
- **Then:** The response is `200` and `currencies` is exactly `[]`
- **AC:** AC-09, FR-05, FR-07
- **Type:** integration

### TC-44: A currency with income only reports zero expenses

- **US:** FR-US-03
- **Given:** An authenticated User whose only transaction this month in USD is an income of `500.00`
- **When:** The User requests their summary report
- **Then:** The `USD` entry has `total_expenses` `"0.00"`, `net_savings` `"500.00"` and `top_categories` `[]`
- **AC:** EC-01, FR-03 *(assertion technique per QF-07)*
- **Type:** integration

### TC-45: A currency with expenses only reports zero income and negative net savings

- **US:** FR-US-03
- **Given:** An authenticated User whose only transaction this month in VND is an expense of `100000.00`
- **When:** The User requests their summary report
- **Then:** The `VND` entry has `total_income` `"0.00"` and `net_savings` `"-100000.00"`
- **AC:** EC-02, FR-03 *(assertion technique per QF-07)*
- **Type:** integration

### TC-46: Net savings carry their own sign per currency

- **US:** FR-US-03
- **Given:** An authenticated User with, this month, VND income `200000.00` and expense `50000.00`, and USD income `10.00` and expense `40.00`
- **When:** The User requests their summary report
- **Then:** The `VND` entry's `net_savings` is `"150000.00"` and the `USD` entry's is `"-30.00"` — neither offset by the other
- **AC:** EC-03, FR-02, FR-03
- **Type:** integration

### TC-47: A category archived after being spent against still ranks in its currency

- **US:** FR-US-03
- **Given:** An authenticated User who spent `25.00` USD against category "Gifts" this month and then archived "Gifts"
- **When:** The User requests their summary report
- **Then:** The `USD` entry's `top_categories` contains "Gifts" with `total_amount` `"25.00"`
- **AC:** EC-04, FR-04
- **Type:** integration

### TC-48: A User holding only EUR gets exactly one EUR entry and nothing invented

- **US:** FR-US-03
- **Given:** An authenticated User whose only wallet is in EUR, with an expense this month
- **When:** The User requests their summary report
- **Then:** `currencies` has exactly one entry and its `currency` is `"EUR"`; there is no `VND` entry
- **AC:** EC-05, EC-06, FR-05
- **Type:** integration

### TC-49: Two currencies with identical figures stay two entries

- **US:** FR-US-03
- **Given:** An authenticated User with an expense of `100.00` from a USD wallet and an expense of `100.00` from a EUR wallet this month
- **When:** The User requests their summary report
- **Then:** `currencies` has two entries, `EUR` then `USD`, each with `total_expenses` `"100.00"`
- **AC:** EC-07, FR-02
- **Type:** integration

---

## FR: UI test cases *(UI fast-track — CLAUDE.md §2)*

> The Home tab's analysis section, after `plan.md` FR-US-03 T-08. Each test arranges its own data
> through the API under a throwaway account, acts through the real screen, and lives in
> `mobile/e2e/home.spec.ts`, run with `npm run test:e2e` against the real backend. Visual design is
> never asserted (QF-12). Behaviour the screen cannot reach — another user's data, unauthenticated
> calls — stays covered by the integration TCs above.

### Coverage Matrix (UI)

| TC | US | AC | E2E test | Status |
| :-- | :-- | :-- | :-- | :-- |
| TC-50 | FR-US-03 | AC-14, AC-01, AC-04 | `mobile/e2e/home.spec.ts` › TC-50 | PASS — 2026-10-28, desktop + phone |
| TC-51 | FR-US-03 | AC-15 | `mobile/e2e/home.spec.ts` › TC-51 | PASS — 2026-10-28, desktop + phone |
| TC-52 | FR-US-03 | AC-16 | `mobile/e2e/home.spec.ts` › TC-52 | PASS — 2026-10-28, desktop + phone |
| TC-53 | FR-US-03 | AC-07, EC-05 | `mobile/e2e/home.spec.ts` › TC-53 | PASS — 2026-10-28, desktop + phone |
| TC-54 | FR-US-03 | AC-09 | `mobile/e2e/home.spec.ts` › TC-54 | PASS — 2026-10-28, desktop + phone |

### TC-50: Home shows one block per currency, in the report's order

- **US:** FR-US-03
- **Given:** A VND wallet with an expense of 100.000 đ and a USD wallet with an expense of $20.00, this month
- **When:** The Home tab is opened
- **Then:** The summary request is answered `200`; blocks `report-USD` and `report-VND` are shown, USD first; each heading reads its currency code; each block contains its income row, expenses row, net savings and spending breakdown
- **AC:** AC-14, AC-01, AC-04
- **Type:** e2e

### TC-51: Each block's amounts are in its own currency

- **US:** FR-US-03
- **Given:** The data of TC-50
- **When:** The Home tab is opened
- **Then:** Inside `report-USD`, the expenses amount reads `$20.00` and no amount ends in `đ`; inside `report-VND`, the expenses amount reads `100.000 đ` and no amount contains `$`
- **AC:** AC-15 *(assertion technique per QF-12)*
- **Type:** e2e

### TC-52: Each block's breakdown lists only its own currency's categories

- **US:** FR-US-03
- **Given:** An expense against "Food" from a VND wallet and against "Travel" from a USD wallet, this month
- **When:** The Home tab is opened
- **Then:** `report-VND-donut` contains "Food" and not "Travel"; `report-USD-donut` contains "Travel" and not "Food"
- **AC:** AC-16
- **Type:** e2e

### TC-53: A single held currency with no activity shows one zero block

- **US:** FR-US-03
- **Given:** One VND wallet and no transactions
- **When:** The Home tab is opened
- **Then:** Exactly one block, `report-VND`, is shown with heading `VND`; its income and expenses read `0 đ`; its breakdown reads "No spending recorded this month."
- **AC:** AC-07, EC-05
- **Type:** e2e

### TC-54: A user with nothing to report sees the empty message

- **US:** FR-US-03
- **Given:** A user with no wallets
- **When:** The Home tab is opened
- **Then:** `report-empty` is shown, reading that no income or expenses were recorded this month; no `report-` currency block is present
- **AC:** AC-09
- **Type:** e2e
