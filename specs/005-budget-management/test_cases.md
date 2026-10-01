# Test Cases: Budget Management (BM)

> **Feature:** SRS §6 Feature-05 · SDS §5.5 (BM)
> **Spec:** [spec.md](spec.md) · **Plan:** [plan.md](plan.md)
> **Stories in this file:** BM-US-01 *(TC-01…TC-26, implemented, verified — 245 passed, 99% coverage)* · BM-US-02 *(TC-27…TC-51, specified)*

---

## BM-US-01: Create a Budget

### Quality Findings

Problems found while deriving test cases from `spec.md` and `plan.md`. Each one changes how a criterion can be asserted, so it is recorded rather than worked around silently.

#### QF-01

**Description.** AC-04/AC-06 require a wallet or category reference that does not exist at all and one that exists but belongs to a different User to produce "the same not-found outcome" — `plan.md` A6 makes this true by construction, since `wallet_repo.get_owned_by_id()`/`category_repo.get_owned_by_id()` filter by `user_id` in the query itself and return `None` either way. A test that merely checks both cases return *some* `404` would not distinguish "genuinely identical" from "two different messages that both happen to carry status 404."

**Impact.** A weaker test could pass even if a future change accidentally made the two cases distinguishable — for instance, a message that says "wallet belongs to another account" only in the ownership-mismatch case, which would itself be a minor information leak about another User's data (constitution SEC-08's spirit, applied here per plan.md A6's SEC-10 note).

**Recommendation.** `TC-07` and `TC-10` each compare the full response body of the ownership-mismatch case against the full response body of the corresponding not-found-at-all case (`TC-06`, `TC-09`) and assert they match exactly — `error_code`, `message`, and `details` all identical, not merely the status code.

#### QF-02

**Description.** AC-09 requires an over-precise `amount_limit` to be rejected, not rounded. The rejection is a Pydantic-native `decimal_max_places` constraint (`plan.md` A4, reusing WM-US-01 A3's mechanism), not a hand-written check, so the risk is asserting the wrong thing: a test could check only that *some* `422` came back without confirming which field it names.

**Impact.** A loosely-written assertion would not actually prove precision is preserved rather than silently rounded elsewhere before validation runs — directly mirrors WM-US-01 QF-02.

**Recommendation.** `TC-17` asserts the `422` response's `details` names the `amount_limit` field specifically, and that no `budgets` row was created at all, so there is no rounded value to find.

#### QF-03

**Description.** `plan.md` A2 records that `period` is computed from `app.core.clock.utcnow()`, never accepted from the request. A test that asserts only "the response includes *a* period" would not prove the value is the *current* month, and a test that computes "today's month" independently inside the test body (rather than through the same clock seam the application uses) risks flaking at a month boundary or drifting from the application's own notion of "now" (constitution TST-06: "Time comes from the patched clock seam; no reliance on ordering, sleeps, or network").

**Impact.** An unfrozen test is either non-deterministic near midnight on the last day of a month, or requires duplicating month-arithmetic in the test file that could itself disagree with the implementation's arithmetic.

**Recommendation.** `TC-03`, `TC-19`, and `TC-23` all monkeypatch `app.core.clock.utcnow` to a fixed instant before creating a budget, then assert `period` equals that fixed instant's month with `day == 1` — the same clock-seam technique every existing TTL-related test in this codebase already uses (constitution TST-06), applied here for the first time to a *creation-time* value rather than an expiry comparison.

#### QF-04

**Description.** `plan.md` A3/BR-05 scope the uniqueness constraint to the *composite* key `(wallet_id, category_id, period)`. A test suite that only proves "the exact same triple is rejected" would not catch a uniqueness constraint implemented too broadly (e.g. scoped to `wallet_id` alone) or too narrowly (e.g. missing `period` from the database index while the service check has it).

**Impact.** A regression narrowing or widening the constraint's scope could pass a test suite that only exercises the positive (duplicate) case.

**Recommendation.** `TC-21`, `TC-22`, and `TC-23` each vary exactly one of the three key columns while holding the other two fixed, and assert creation *succeeds* — proving the constraint's boundary is exactly the three named columns together, not any subset of them, alongside `TC-20`'s positive (all-three-match) rejection case.

#### QF-05

**Description.** `plan.md` A7/A8 record that `budgets` has neither a `user_id` nor a `status` column, unlike every other table this codebase has built so far (`wallets`/`categories` both carry `user_id`; `invitations`/`users` carry a status-shaped column). A test asserting only that the documented fields are *present* would not prove these two are *absent*.

**Impact.** A future change that accidentally started returning an owner field or a status field (perhaps copied from another resource's `Read` schema) would pass a weak test and quietly begin leaking a field this story's contract never promised.

**Recommendation.** `TC-24`'s exact-field-set assertion is written to *positively* confirm the response has exactly five keys and, in particular, no `user_id` and no `status` — the same technique WM-US-01 QF-04 and CM-US-01 QF-04 used for `created_at` and `icon` respectively.

#### QF-06

**Description.** `plan.md` FR-13/BR-02 establish a fixed check order — wallet ownership, then category ownership, then the duplicate-budget check — but this order is only *observable* when a single request fails more than one check at once. Every other test case in this file exercises exactly one failure at a time, so none of them can distinguish a real fixed order from an implementation that happens to check things in a different order but still passes every single-failure test.

**Impact.** Without a dedicated multi-failure test, a future refactor could silently reorder the checks (for instance, checking category before wallet) without any existing test catching the change, even though `spec.md` records the order as a rule (BR-02), not an implementation detail.

**Recommendation.** `TC-26` submits a request where *both* the wallet reference and the category reference are invalid, and asserts the response is `BUDGET_WALLET_NOT_FOUND` specifically — never `BUDGET_CATEGORY_NOT_FOUND`, and never a response naming both.

### Acceptance Criteria Classification

No budget-creation screen exists in `mobile/` this round, and no SRS UXR names one (the same situation WM-US-01 and CM-US-01's own `test_cases.md` recorded). Every row below is `[API]`.

| AC/EC | Title | Label | Rationale |
|---|---|---|---|
| AC-01 | Successfully create a budget with all mandatory inputs | **[API]** | No UI surface exists or is named by any UXR this round |
| AC-02 | Deny access to unauthenticated callers | **[API]** | Backend authorization contract |
| AC-03 | Reject a missing wallet reference | **[API]** | Payload validation |
| AC-04 | Reject a wallet reference that does not resolve to the caller's own wallet | **[API]** | Persistence/ownership contract; bounded by QF-01 |
| AC-05 | Reject a missing category reference | **[API]** | Payload validation |
| AC-06 | Reject a category reference that does not resolve to the caller's own category | **[API]** | Persistence/ownership contract; bounded by QF-01 |
| AC-07 | Reject a missing amount limit | **[API]** | Payload validation |
| AC-08 | Reject an amount limit that is zero or negative | **[API]** | Payload validation |
| AC-09 | Reject an amount limit carrying more than two decimal places | **[API]** | Payload validation; bounded by QF-02 |
| AC-10 | A created budget's period is always the current calendar month | **[API]** | Backend rule; bounded by QF-03 |
| AC-11 | Reject a duplicate budget for the same wallet, category, and period | **[API]** | Backend conflict rule; bounded by QF-04 |
| AC-12 | Return exactly the documented budget fields | **[API]** | Response-payload contract; bounded by QF-05 |
| EC-01 | Amount limit at the smallest positive value | **[API]** | Boundary value |
| EC-02 | Amount limit exceeding the `DECIMAL(15,2)` total digit width | **[API]** | Payload validation, distinct from AC-09's decimal-places check |
| EC-03 | More than one validation failure in a single submission | **[API]** | Backend validation-grouping contract |
| EC-04 | A period value submitted with the request | **[API]** | Structural-ignore contract; bounded by QF-03 |
| EC-05 | A wallet reference belonging to a different, real User | **[API]** | Persistence/ownership contract; bounded by QF-01 |
| EC-06 | A category reference belonging to a different, real User | **[API]** | Persistence/ownership contract; bounded by QF-01 |
| EC-07 | A wallet or category reference that is not a well-formed identifier | **[API]** | Backend rule (no separate format validation) |
| EC-08 | A second budget for the same wallet and category, in a different period | **[API]** | Backend rule; bounded by QF-04 |
| EC-09 | A second budget for the same category and period, against a different wallet | **[API]** | Backend rule; bounded by QF-04 |
| EC-10 | A second budget for the same wallet and period, against a different category | **[API]** | Backend rule; bounded by QF-04 |
| EC-11 | Both the wallet and category references are invalid in the same request | **[API]** | Backend check-ordering contract; bounded by QF-06 |

### Coverage Matrix

| AC/EC | Label | Integration TC(s) | E2E TC(s) |
|---|---|---|---|
| AC-01 | [API] | TC-01, TC-02, TC-03 | — |
| AC-02 | [API] | TC-04 | — |
| AC-03 | [API] | TC-05 | — |
| AC-04 | [API] | TC-06, TC-07 | — |
| AC-05 | [API] | TC-08 | — |
| AC-06 | [API] | TC-09, TC-10 | — |
| AC-07 | [API] | TC-13 | — |
| AC-08 | [API] | TC-14, TC-15 | — |
| AC-09 | [API] | TC-17 | — |
| AC-10 | [API] | TC-03, TC-19 | — |
| AC-11 | [API] | TC-20 | — |
| AC-12 | [API] | TC-24 | — |
| EC-01 | [API] | TC-16 | — |
| EC-02 | [API] | TC-18 | — |
| EC-03 | [API] | TC-25 | — |
| EC-04 | [API] | TC-19 | — |
| EC-05 | [API] | TC-07 | — |
| EC-06 | [API] | TC-10 | — |
| EC-07 | [API] | TC-11, TC-12 | — |
| EC-08 | [API] | TC-23 | — |
| EC-09 | [API] | TC-21 | — |
| EC-10 | [API] | TC-22 | — |
| EC-11 | [API] | TC-26 | — |

> Every AC and EC has at least one integration TC. There is no `[BOTH]` or `[UI]` row — no budget-creation screen exists this round, and none is named by any SRS UXR. **Known coverage limits, accepted:** the SDS §2.4.3 Budget Monitoring State machine is not exercised here — `budgets` has no `status` column in this story (plan.md A8), so no test asserts anything about `DRAFT`/`NORMAL`/`WARNING`/`EXCEEDED`/`ARCHIVED`; that machine belongs to BM-US-03. FR-13/BR-02's fixed check order is proven only for the wallet-before-category case (TC-26); the category-before-uniqueness half of the same order has no dedicated multi-failure test because a category-ownership failure and a duplicate-budget conflict cannot both be constructed from the same single request (a duplicate check never runs until both ownership checks already passed).

### Test Implementation Map *(filled at step 4)*

All under `backend/tests/integration/test_bm_us_01_create_budget.py`. Run one with
`uv run pytest -k <fragment>`.

| TC | pytest node id | Result |
|---|---|---|
| TC-01 | `test_authenticated_user_creates_a_budget_201_with_created_budget` | PASS |
| TC-02 | `test_creating_a_budget_persists_exactly_one_row_with_submitted_fields_and_computed_period` | PASS |
| TC-03 | `test_created_budget_period_is_first_day_of_current_month_from_frozen_clock` | PASS |
| TC-04 | `test_unauthenticated_caller_is_denied_with_401` | PASS |
| TC-05 | `test_a_missing_wallet_reference_is_rejected_with_422` | PASS |
| TC-06 | `test_a_wallet_reference_matching_no_wallet_at_all_is_rejected_with_404` | PASS |
| TC-07 | `test_a_wallet_reference_belonging_to_a_different_user_is_rejected_identically_to_not_found` | PASS |
| TC-08 | `test_a_missing_category_reference_is_rejected_with_422` | PASS |
| TC-09 | `test_a_category_reference_matching_no_category_at_all_is_rejected_with_404` | PASS |
| TC-10 | `test_a_category_reference_belonging_to_a_different_user_is_rejected_identically_to_not_found` | PASS |
| TC-11 | `test_a_malformed_wallet_reference_is_rejected_with_same_outcome_as_not_found` | PASS |
| TC-12 | `test_a_malformed_category_reference_is_rejected_with_same_outcome_as_not_found` | PASS |
| TC-13 | `test_a_missing_amount_limit_is_rejected_with_422` | PASS |
| TC-14 | `test_an_amount_limit_of_exactly_zero_is_rejected_with_422` | PASS |
| TC-15 | `test_a_negative_amount_limit_is_rejected_with_422` | PASS |
| TC-16 | `test_an_amount_limit_of_exactly_0_01_is_accepted` | PASS |
| TC-17 | `test_an_amount_limit_with_three_decimal_places_is_rejected_not_rounded` | PASS |
| TC-18 | `test_an_amount_limit_exceeding_15_total_digits_is_rejected` | PASS |
| TC-19 | `test_a_period_submitted_in_the_request_body_is_silently_ignored` | PASS |
| TC-20 | `test_a_duplicate_budget_for_same_wallet_category_period_is_rejected_with_409` | PASS |
| TC-21 | `test_a_second_budget_same_category_and_period_different_wallet_is_accepted` | PASS |
| TC-22 | `test_a_second_budget_same_wallet_and_period_different_category_is_accepted` | PASS |
| TC-23 | `test_a_second_budget_same_wallet_and_category_different_period_is_accepted` | PASS |
| TC-24 | `test_response_exposes_exactly_the_five_documented_fields` | PASS |
| TC-25 | `test_multiple_validation_failures_in_one_submission_are_reported_together` | PASS |
| TC-26 | `test_wallet_ownership_is_checked_before_category_ownership_when_both_invalid` | PASS |

Full suite: `245 passed` (219 pre-existing + 26 new). `ruff check`/`ruff format --check` clean, `mypy app`
clean, coverage **99%** overall; `models/budget.py`, `schemas/budget.py`, `repositories/budget_repo.py`,
`services/budget_service.py`, and `api/v1/budgets.py` are all at **100%** (constitution DOD-03's floor is
80%). No defect found in the implementation while writing these tests — every TC passed against the first
version of the code; three targeted mutation checks (reversing the wallet/category check order, widening
the uniqueness scope to drop `period`, and diverging the not-found/not-owned response bodies) each
confirmed the corresponding TC-26/TC-23/TC-07 fails for the right reason before being reverted.

---

### TC-01: An authenticated User creates a budget with all mandatory inputs — 201 with the created budget

- **US:** BM-US-01
- **Given:** An authenticated User who owns a wallet and owns a category
- **When:** A budget is submitted with that wallet's id, that category's id, and `amount_limit` `200.00`
- **Then:** The response is `201`; the body carries `id`, `wallet_id` equal to the submitted wallet, `category_id` equal to the submitted category, `amount_limit` `200.00`, and `period` equal to the first day of the current calendar month
- **AC:** AC-01, FR-01, FR-11
- **Type:** integration

### TC-02: Creating a budget persists exactly one row with the submitted fields and computed period

- **US:** BM-US-01
- **Given:** An authenticated User who owns a wallet and a category
- **When:** A budget is submitted successfully
- **Then:** Exactly one `budgets` row exists carrying the submitted `wallet_id`, `category_id`, and `amount_limit`, with `period` equal to the first day of the current calendar month
- **AC:** AC-01, FR-01, FR-09
- **Type:** integration

### TC-03: The created budget's period is the first day of the current calendar month, computed from a frozen clock

- **US:** BM-US-01
- **Given:** An authenticated User who owns a wallet and a category, with the system clock frozen to a known instant
- **When:** A budget is submitted successfully
- **Then:** The created budget's `period` equals the first day of the frozen instant's calendar month
- **AC:** AC-01, AC-10, FR-09, BR-04 *(assertion technique per QF-03)*
- **Type:** integration

### TC-04: An unauthenticated caller is denied with 401

- **US:** BM-US-01
- **Given:** A caller presenting no `Authorization` header
- **When:** A budget is submitted with an otherwise valid payload
- **Then:** The response is `401` with `error_code` `NOT_AUTHENTICATED`; no `budgets` row is created
- **AC:** AC-02, FR-02
- **Type:** integration

### TC-05: A missing wallet reference is rejected with 422

- **US:** BM-US-01
- **Given:** An authenticated User
- **When:** A budget is submitted with the `wallet_id` field absent
- **Then:** The response is `422` `VALIDATION_ERROR` identifying the `wallet_id` field; nothing is persisted
- **AC:** AC-03, FR-03
- **Type:** integration

### TC-06: A wallet reference matching no wallet at all is rejected with 404 BUDGET_WALLET_NOT_FOUND

- **US:** BM-US-01
- **Given:** An authenticated User and a category they own
- **When:** A budget is submitted with a `wallet_id` that matches no wallet in the system
- **Then:** The response is `404` with `error_code` `BUDGET_WALLET_NOT_FOUND`; nothing is persisted
- **AC:** AC-04, FR-04
- **Type:** integration

### TC-07: A wallet reference belonging to a different User is rejected with the identical outcome as TC-06

- **US:** BM-US-01
- **Given:** Two authenticated Users `A` and `B`, where `B` owns a wallet and `A` owns a category
- **When:** `A` submits a budget with `B`'s `wallet_id` and `A`'s own `category_id`
- **Then:** The response is `404`; its `error_code`, `message`, and `details` are identical to TC-06's response; nothing is persisted
- **AC:** AC-04, EC-05, FR-04 *(assertion technique per QF-01)*
- **Type:** integration

### TC-08: A missing category reference is rejected with 422

- **US:** BM-US-01
- **Given:** An authenticated User
- **When:** A budget is submitted with the `category_id` field absent
- **Then:** The response is `422` `VALIDATION_ERROR` identifying the `category_id` field; nothing is persisted
- **AC:** AC-05, FR-05
- **Type:** integration

### TC-09: A category reference matching no category at all is rejected with 404 BUDGET_CATEGORY_NOT_FOUND

- **US:** BM-US-01
- **Given:** An authenticated User and a wallet they own
- **When:** A budget is submitted with a `category_id` that matches no category in the system
- **Then:** The response is `404` with `error_code` `BUDGET_CATEGORY_NOT_FOUND`; nothing is persisted
- **AC:** AC-06, FR-06
- **Type:** integration

### TC-10: A category reference belonging to a different User is rejected with the identical outcome as TC-09

- **US:** BM-US-01
- **Given:** Two authenticated Users `A` and `B`, where `B` owns a category and `A` owns a wallet
- **When:** `A` submits a budget with `A`'s own `wallet_id` and `B`'s `category_id`
- **Then:** The response is `404`; its `error_code`, `message`, and `details` are identical to TC-09's response; nothing is persisted
- **AC:** AC-06, EC-06, FR-06 *(assertion technique per QF-01)*
- **Type:** integration

### TC-11: A wallet reference that is not a well-formed identifier is rejected with the same outcome as a well-formed but non-existent one

- **US:** BM-US-01
- **Given:** An authenticated User and a category they own
- **When:** A budget is submitted with `wallet_id` `"not-a-real-id"`
- **Then:** The response is `404` `BUDGET_WALLET_NOT_FOUND`, identical to TC-06's response; nothing is persisted
- **AC:** EC-07, FR-04
- **Type:** integration

### TC-12: A category reference that is not a well-formed identifier is rejected with the same outcome as a well-formed but non-existent one

- **US:** BM-US-01
- **Given:** An authenticated User and a wallet they own
- **When:** A budget is submitted with `category_id` `"not-a-real-id"`
- **Then:** The response is `404` `BUDGET_CATEGORY_NOT_FOUND`, identical to TC-09's response; nothing is persisted
- **AC:** EC-07, FR-06
- **Type:** integration

### TC-13: A missing amount limit is rejected with 422

- **US:** BM-US-01
- **Given:** An authenticated User who owns a wallet and a category
- **When:** A budget is submitted with the `amount_limit` field absent
- **Then:** The response is `422` `VALIDATION_ERROR` identifying the `amount_limit` field; nothing is persisted
- **AC:** AC-07, FR-07
- **Type:** integration

### TC-14: An amount limit of exactly zero is rejected with 422

- **US:** BM-US-01
- **Given:** An authenticated User who owns a wallet and a category
- **When:** A budget is submitted with `amount_limit` `0.00`
- **Then:** The response is `422` `VALIDATION_ERROR` identifying the `amount_limit` field; nothing is persisted
- **AC:** AC-08, FR-08, BR-03
- **Type:** integration

### TC-15: A negative amount limit is rejected with 422

- **US:** BM-US-01
- **Given:** An authenticated User who owns a wallet and a category
- **When:** A budget is submitted with `amount_limit` `-50.00`
- **Then:** The response is `422` `VALIDATION_ERROR` identifying the `amount_limit` field; nothing is persisted
- **AC:** AC-08, FR-08, BR-03
- **Type:** integration

### TC-16: An amount limit of exactly 0.01 is accepted

- **US:** BM-US-01
- **Given:** An authenticated User who owns a wallet and a category
- **When:** A budget is submitted with `amount_limit` `0.01`
- **Then:** The response is `201`; the created budget's `amount_limit` is `0.01`
- **AC:** EC-01, FR-08
- **Type:** integration

### TC-17: An amount limit with three decimal places is rejected, not rounded

- **US:** BM-US-01
- **Given:** An authenticated User who owns a wallet and a category
- **When:** A budget is submitted with `amount_limit` `100.005`
- **Then:** The response is `422` `VALIDATION_ERROR` whose `details` names `amount_limit`; no `budgets` row is created — so there is no rounded `100.01` or truncated `100.00` value to find
- **AC:** AC-09, BR-03, FR-07 *(assertion technique per QF-02)*
- **Type:** integration

### TC-18: An amount limit exceeding 15 total digits is rejected

- **US:** BM-US-01
- **Given:** An authenticated User who owns a wallet and a category
- **When:** A budget is submitted with an `amount_limit` of 14 integer digits and 2 decimal places (16 significant digits total)
- **Then:** The response is `422` `VALIDATION_ERROR`; nothing is persisted — constitution VL-07's `DECIMAL(15,2)` bound is enforced by the DTO before the service runs
- **AC:** EC-02, BR-03, FR-07
- **Type:** integration

### TC-19: A period submitted in the request body is silently ignored

- **US:** BM-US-01
- **Given:** An authenticated User who owns a wallet and a category, with the system clock frozen to a known instant
- **When:** A budget is submitted with an otherwise valid payload that additionally includes a period-shaped key (`"period": "2020-01-01"`) in the JSON body
- **Then:** The response is `201`; the created budget's `period` equals the first day of the frozen instant's calendar month, never `"2020-01-01"`
- **AC:** AC-10, EC-04, FR-09, BR-04
- **Type:** integration

### TC-20: A duplicate budget for the same wallet, category, and period is rejected with 409

- **US:** BM-US-01
- **Given:** An authenticated User with an existing budget for a given wallet, category, and period
- **When:** The same User submits another budget for that same wallet, that same category, and (the clock still reading within the same month) the same period
- **Then:** The response is `409` with `error_code` `BUDGET_ALREADY_EXISTS`; exactly one `budgets` row exists for that combination — the original, unchanged
- **AC:** AC-11, FR-10, BR-05
- **Type:** integration

### TC-21: A second budget for the same category and period but a different wallet is accepted

- **US:** BM-US-01
- **Given:** An authenticated User with an existing budget for wallet `W1`, category `C1`, and the current period, and a second wallet `W2` the same User owns
- **When:** The User submits a budget for wallet `W2`, category `C1`, and the current period
- **Then:** The response is `201`; two `budgets` rows now exist — one for `W1`, one for `W2` — both against `C1` and the same period
- **AC:** EC-09, FR-10, BR-05 *(assertion technique per QF-04)*
- **Type:** integration

### TC-22: A second budget for the same wallet and period but a different category is accepted

- **US:** BM-US-01
- **Given:** An authenticated User with an existing budget for wallet `W1`, category `C1`, and the current period, and a second category `C2` the same User owns
- **When:** The User submits a budget for wallet `W1`, category `C2`, and the current period
- **Then:** The response is `201`; two `budgets` rows now exist — one for `C1`, one for `C2` — both against `W1` and the same period
- **AC:** EC-10, FR-10, BR-05 *(assertion technique per QF-04)*
- **Type:** integration

### TC-23: A second budget for the same wallet and category but a different period is accepted

- **US:** BM-US-01
- **Given:** An authenticated User with an existing budget for wallet `W1`, category `C1`, and the current period, with the system clock then advanced to the following calendar month
- **When:** The User submits another budget for wallet `W1` and category `C1`
- **Then:** The response is `201`; two `budgets` rows now exist for `W1`+`C1` — one for each of the two periods
- **AC:** EC-08, FR-10, BR-05 *(assertion technique per QF-03, QF-04)*
- **Type:** integration

### TC-24: The response exposes exactly the five documented fields

- **US:** BM-US-01
- **Given:** An authenticated User who owns a wallet and a category
- **When:** A budget is submitted successfully
- **Then:** The response body's keys are exactly `id`, `wallet_id`, `category_id`, `amount_limit`, `period` — no more, and in particular no `user_id` and no `status` (plan.md A7, A8, QF-05)
- **AC:** AC-12, FR-11
- **Type:** integration

### TC-25: Multiple validation failures in one submission are reported together

- **US:** BM-US-01
- **Given:** An authenticated User
- **When:** A budget is submitted with the `wallet_id` field absent and `amount_limit` `-50.00` in the same request
- **Then:** The response is a single `422` whose `details` identifies both the `wallet_id` and the `amount_limit` fields — not just the first one encountered
- **AC:** EC-03, FR-12
- **Type:** integration

### TC-26: Wallet ownership is checked before category ownership when both references are invalid in the same request

- **US:** BM-US-01
- **Given:** An authenticated User
- **When:** A budget is submitted with a `wallet_id` matching no wallet at all and a `category_id` matching no category at all, in the same request
- **Then:** The response is `404` `BUDGET_WALLET_NOT_FOUND` — never `BUDGET_CATEGORY_NOT_FOUND`, and never both
- **AC:** EC-11, BR-02, FR-13 *(assertion technique per QF-06)*
- **Type:** integration

---

## BM-US-02: List Budgets

> **IDs in this section are local to BM-US-02** — except `TC-NN`, which continues this epic file's own
> numbering: BM-US-01 used `TC-01`…`TC-26`, so this story continues from `TC-27`. **`QF-NN` also
> continues here** (BM-US-01 used `QF-01`…`QF-06`; this story continues from `QF-07`) — matching the
> continuing convention `specs/004-category-management/test_cases.md` (CM-US-02) and
> `specs/003-wallet-management/test_cases.md` (WM-US-02) both already adopted.

### Quality Findings

#### QF-07

**Description.** `plan.md` A3 requires the total-count query in `budget_repo.list_owned()` to carry the
same `wallets.user_id` join predicate as the bounded page query. A test that only checks the returned
`items` are scoped to the caller would not catch a copy-paste of an unfiltered (or differently-filtered)
count query: `items` would look correct while `total` silently leaked a count from across every User —
the exact risk `test_cases.md` QF-05 already named for `WalletModel`/`CategoryModel` and QF-10 extended
to a join for `TransactionModel`.

**Impact.** A weaker test suite could pass with a `total` that counts every User's active budgets, not
just the caller's — wrong, but not obviously wrong from `items` alone, especially in a test that seeds
budgets for only one User.

**Recommendation.** `TC-37` (ownership scoping) and `TC-38` (empty-for-one, populated-for-another) both
seed a **second** User's budgets alongside the caller's own, and assert `total` equals only the caller's
own count, distinct from the combined count across both Users.

#### QF-08

**Description.** `plan.md` A3 scopes ownership through a single `JOIN` on `wallets` only, relying on
BM-US-01's own fixed-order creation-time validation (FR-13/BR-02) to guarantee that a stored budget's
`category_id` always belongs to the same User as its `wallet_id`. This guarantee is structural — enforced
by the only code path that can ever write a `budgets` row — not something this endpoint's own test suite
can construct a counter-example for: there is no way, through the public API, to create a budget whose
wallet and category belong to two different Users, so no test here can directly exercise "a budget with
mismatched wallet/category ownership is still excluded."

**Impact.** No test in this file can assert the single-join design's safety net directly; only its
absence-of-need can be observed.

**Recommendation.** Accept the structural proof over a constructed counter-example — the same pattern
CM-US-02 QF-08 already used in this codebase for a case the public API cannot construct (there, a
"system category" with no owner). `TC-37`/`TC-38`'s ownership-scoping assertions are the closest
available witness: every budget this endpoint can possibly return already carries a `wallet_id` whose
owner is provably the caller, because BM-US-01's own creation path enforces it, not because a test
checked for the absence of a hypothetical mismatched row.

#### QF-09

**Description.** `plan.md` A4 records that `transaction_repo.get_expense_totals_by_wallet_category()`
carries the identical `GROUP BY` omits-empty-groups trap `get_summary_totals()`'s own docstring already
documents (FR-US-01). A test asserting only "the response includes *an* `amount_spent`" would not prove
a budget with zero matching expense transactions defaults to `0.00` rather than being omitted from the
list entirely, or the request erroring.

**Impact.** A missing-key bug in `budget_service.list_budgets()` (treating an absent dictionary entry as
"no such budget" instead of "zero spent") could silently drop every budget with no expense activity yet
— exactly the case AC-11 exists to guarantee against.

**Recommendation.** `TC-42` creates an active budget with **no** transaction recorded against its wallet
and category at all, and asserts the budget still appears in `items` with `amount_spent` exactly
`"0.00"` and a `progress_percentage` of `"0.00"` — not absent, not `null`, not an error.

#### QF-10

**Description.** `plan.md` A5 resolves "active" to "the budget's `period` equals the current calendar
month." A test suite that only ever creates budgets in the current month (as every BM-US-01 test already
does, since BM-US-01 itself only ever creates current-month budgets) could pass even if this endpoint
applied no period filter at all, or filtered on the wrong column — because every budget in every other
test's fixture data already happens to be in the current month.

**Impact.** Without a dedicated case constructing a budget whose `period` is a *different* month, a
regression that dropped the period filter entirely (returning every budget regardless of period) would
pass every other test in this file.

**Recommendation.** `TC-40` monkeypatches `app.core.clock.utcnow` to a fixed instant, creates a budget
(landing it in that fixed month), then advances the patched clock by a full calendar month before
requesting the list — the same clock-seam technique BM-US-01 TC-23 already used for a different purpose
(constitution TST-06) — and asserts that budget is absent from both `items` and `total`, while a second,
freshly-created budget in the new "current" month does appear.

#### QF-11

**Description.** `plan.md` A4's aggregate query groups spend by `(wallet_id, category_id)` specifically
so that one budget's spend never contaminates another's. A test asserting only one budget's own
`amount_spent` in isolation would not catch an aggregate query that summed across every wallet or every
category the caller owns, rather than scoping per exact pair — a bug that would only become visible once
a caller has *more than one* budget sharing exactly one, but not both, of the two dimensions.

**Impact.** A regression widening the `GROUP BY` (for instance, grouping by `wallet_id` alone) could pass
every single-budget test in this file while silently merging two different categories' spending into one
reported figure.

**Recommendation.** `TC-44` and `TC-47` each construct two budgets that deliberately share exactly one of
`wallet_id`/`category_id` while differing in the other, record an expense transaction against only one of
the two pairs, and assert the other budget's `amount_spent` remains exactly `"0.00"` — proving the
aggregate is scoped to the full pair, not either column alone.

#### QF-12

**Description.** `plan.md` A1 orders budgets by `id` because no `created_at` column exists (mirrors
CM-US-02 QF-06/WM-US-02 QF-06 for the identical reasoning). `id` is a randomly generated UUID, so its
sort order has no relationship to creation time. A test asserting only "the order is consistent" could
pass even if a future change swapped in a different, equally arbitrary order.

**Impact.** Without pinning the expected order to a concrete, independently-computable key, a test could
not tell "genuinely ordered by `id`" apart from "happened to come back in insertion order this one time."

**Recommendation.** `TC-39` asserts the returned order equals the budgets' own `id` values sorted
ascending as plain strings (computed independently in the test from the ids the creation calls actually
returned), created in an order that does **not** already match ascending `id` order.

### Acceptance Criteria Classification

No budget-list screen exists in `mobile/` this round, and no SRS UXR names one — the same basis BM-US-01
and CM-US-02 each used for their own all-`[API]` classification.

| AC/EC | Title | Label | Rationale |
|---|---|---|---|
| AC-01 | Successfully list every active budget the caller owns, with its current spending progress | **[API]** | No UI surface exists or is named by any UXR this round |
| AC-02 | Return an empty list for a User with no active budgets | **[API]** | Backend response-shape contract |
| AC-03 | Deny access to unauthenticated callers | **[API]** | Backend authorization contract |
| AC-04 | Bound and paginate the result by default | **[API]** | Query-parameter contract |
| AC-05 | Accept an explicit page and page size within range | **[API]** | Same reasoning as AC-04 |
| AC-06 | Reject a page or page size outside the allowed range | **[API]** | 422 `VALIDATION_ERROR` — backend validation concern |
| AC-07 | A User only ever sees their own budgets | **[API]** | Persistence/ownership contract; bounded by QF-07/QF-08 |
| AC-08 | Return the list in a stable, deterministic order | **[API]** | Backend contract; bounded by QF-12 |
| AC-09 | Only budgets whose period is the current calendar month are ever listed | **[API]** | Backend rule; bounded by QF-10 |
| AC-10 | Amount spent reflects only matching expense activity | **[API]** | Backend computation; bounded by QF-09/QF-11 |
| AC-11 | A budget with no matching expense activity yet still appears, with nothing spent | **[API]** | Response-shape contract; bounded by QF-09 |
| AC-12 | Progress percentage reflects spending as a proportion of the amount limit, may exceed it | **[API]** | Backend computation |
| AC-13 | Return exactly the documented budget fields, wrapped in a paginated envelope | **[API]** | Response-payload contract |
| EC-01 | A page number beyond the last available page | **[API]** | Boundary value |
| EC-02 | Page size at the exact maximum | **[API]** | Boundary value |
| EC-03 | More active budgets than fit on one page | **[API]** | Cross-page completeness; bounded by QF-12 |
| EC-04 | A caller whose role is ADMIN, who also owns budgets | **[API]** | Ownership contract independent of role |
| EC-05 | An expense transaction against a different wallet/category than a given budget's own | **[API]** | Backend rule; bounded by QF-11 |
| EC-06 | A budget whose period is a calendar month before the current one | **[API]** | Backend rule; bounded by QF-10 |
| EC-07 | Two or more active budgets sharing exactly one of wallet/category | **[API]** | Backend rule; bounded by QF-11 |
| EC-08 | A transaction timestamped at the month boundary | **[API]** | Boundary value |
| EC-09 | An income transaction against the same wallet/category as a budget | **[API]** | Backend rule |

### Coverage Matrix

| AC/EC | Label | Integration TC(s) | E2E TC(s) |
|---|---|---|---|
| AC-01 | [API] | TC-27 | — |
| AC-02 | [API] | TC-29, TC-38 | — |
| AC-03 | [API] | TC-30, TC-31 | — |
| AC-04 | [API] | TC-32 | — |
| AC-05 | [API] | TC-33 | — |
| AC-06 | [API] | TC-34, TC-35, TC-36 | — |
| AC-07 | [API] | TC-37, TC-38 | — |
| AC-08 | [API] | TC-39 | — |
| AC-09 | [API] | TC-40 | — |
| AC-10 | [API] | TC-41, TC-44, TC-45, TC-46 | — |
| AC-11 | [API] | TC-42 | — |
| AC-12 | [API] | TC-43 | — |
| AC-13 | [API] | TC-28 | — |
| EC-01 | [API] | TC-48 | — |
| EC-02 | [API] | TC-36, TC-49 | — |
| EC-03 | [API] | TC-50 | — |
| EC-04 | [API] | TC-51 | — |
| EC-05 | [API] | TC-44 | — |
| EC-06 | [API] | TC-40 | — |
| EC-07 | [API] | TC-47 | — |
| EC-08 | [API] | TC-46 | — |
| EC-09 | [API] | TC-45 | — |

> Every AC and EC has at least one integration TC. There is no `[BOTH]` or `[UI]` row — no budget-list
> screen exists this round, and none is named by any SRS UXR. **Known coverage limits, accepted:** the
> single-join ownership design (`plan.md` A3) cannot be counter-tested through the public API, because
> BM-US-01's own creation path makes a mismatched-ownership budget impossible to construct (QF-08); the
> sort key (`id`) carries no chronological meaning, so no test asserts anything about creation order —
> only that the order matches an independently-computed ascending sort of the returned ids (QF-12).

### Test Implementation Map *(filled at step 4)*

All planned under `backend/tests/integration/test_bm_us_02_list_budgets.py`. Not yet implemented —
node ids below are the planned test names; results are filled in at the Implement/Verification steps.

| TC | pytest node id (planned) | Result |
|---|---|---|
| TC-27 | `test_authenticated_user_lists_every_active_budget_they_own_with_computed_progress` | Pending |
| TC-28 | `test_response_item_exposes_exactly_seven_fields_wrapped_in_paginated_envelope` | Pending |
| TC-29 | `test_user_with_no_active_budgets_receives_empty_list_and_zero_total` | Pending |
| TC-30 | `test_unauthenticated_or_invalid_credential_caller_is_denied_with_401` | Pending |
| TC-31 | `test_credentials_are_evaluated_before_any_query_parameter` | Pending |
| TC-32 | `test_default_page_is_1_of_size_25_with_accurate_total` | Pending |
| TC-33 | `test_explicit_page_and_page_size_within_range_return_that_page_and_accurate_total` | Pending |
| TC-34 | `test_a_non_positive_or_non_integer_page_is_rejected_with_422` (3 params) | Pending |
| TC-35 | `test_a_non_positive_or_non_integer_page_size_is_rejected_with_422` (3 params) | Pending |
| TC-36 | `test_a_page_size_above_the_maximum_is_rejected_with_422` | Pending |
| TC-37 | `test_a_user_only_ever_sees_their_own_budgets_never_another_users` | Pending |
| TC-38 | `test_reported_total_counts_only_callers_own_active_budgets_even_when_smaller` | Pending |
| TC-39 | `test_list_is_returned_in_stable_order_matching_ids_sorted_ascending` | Pending |
| TC-40 | `test_a_budget_whose_period_is_a_past_month_is_excluded_while_current_month_one_appears` | Pending |
| TC-41 | `test_amount_spent_sums_only_expense_transactions_against_the_budgets_own_wallet_and_category` | Pending |
| TC-42 | `test_a_budget_with_no_matching_expense_transactions_reports_zero_spent_and_zero_progress` | Pending |
| TC-43 | `test_progress_percentage_may_exceed_100_when_spending_surpasses_the_limit` | Pending |
| TC-44 | `test_a_transaction_against_a_different_wallet_or_category_never_contributes_to_a_budgets_spend` | Pending |
| TC-45 | `test_an_income_transaction_never_contributes_to_a_budgets_amount_spent` | Pending |
| TC-46 | `test_a_transaction_at_the_month_boundary_is_excluded_from_amount_spent` | Pending |
| TC-47 | `test_budgets_sharing_exactly_one_of_wallet_or_category_have_independently_computed_spend` | Pending |
| TC-48 | `test_a_page_beyond_the_last_available_page_returns_an_empty_list_with_accurate_total` | Pending |
| TC-49 | `test_a_page_size_of_exactly_100_is_accepted` | Pending |
| TC-50 | `test_paging_through_every_page_returns_every_active_budget_exactly_once_in_stable_order` | Pending |
| TC-51 | `test_admin_role_caller_who_also_owns_a_budget_sees_only_their_own` | Pending |

---

### TC-27: An authenticated User lists every active budget they own, each with computed spending progress — 200

- **US:** BM-US-02
- **Given:** An authenticated User with two budgets whose period is the current calendar month, one of which has a recorded expense transaction against its own wallet and category this month
- **When:** The User requests the list of budgets
- **Then:** The response is `200`; `items` contains both budgets, each carrying `id`, `wallet_id`, `category_id`, `amount_limit`, `period`, `amount_spent`, `progress_percentage`; the budget with a recorded expense reports a nonzero `amount_spent`; `total` is `2`
- **AC:** AC-01, FR-01, FR-13
- **Type:** integration

### TC-28: The response item exposes exactly the seven documented fields, wrapped in the paginated envelope

- **US:** BM-US-02
- **Given:** An authenticated User with one active budget
- **When:** The User requests the list of budgets
- **Then:** The response is `200`; the top-level body exposes exactly the keys `items`, `total`, `page`, `page_size`; each entry in `items` exposes **exactly** the keys `id`, `wallet_id`, `category_id`, `amount_limit`, `period`, `amount_spent`, `progress_percentage` — no more, and in particular no `user_id` and no `status`
- **AC:** AC-01, AC-13, FR-13, PF-03
- **Type:** integration

### TC-29: A User with no active budgets receives an empty list and a zero total

- **US:** BM-US-02
- **Given:** An authenticated User who owns no budget at all
- **When:** The User requests the list of budgets
- **Then:** The response is `200`, not an error; `items` is an empty list and `total` is `0`
- **AC:** AC-02, FR-01
- **Type:** integration

### TC-30: An unauthenticated or invalid-credential caller is denied with 401

- **US:** BM-US-02
- **Given:** A caller presenting no `Authorization` header, and separately a caller presenting an expired token
- **When:** Each attempts to list budgets
- **Then:** Both responses are `401` with `error_code` `NOT_AUTHENTICATED`; no `items` are returned
- **AC:** AC-03, FR-02
- **Type:** integration

### TC-31: Credentials are evaluated before any query parameter

- **US:** BM-US-02
- **Given:** A caller presenting no credentials
- **When:** The list is requested with an out-of-range `page` value (`page=0`)
- **Then:** The response is `401` `NOT_AUTHENTICATED`, not `422`
- **AC:** AC-03, FR-02
- **Type:** integration

### TC-32: The default page is 1 of size 25, with an accurate total

- **US:** BM-US-02
- **Given:** An authenticated User and three active budgets they own
- **When:** The list is requested with no `page` or `page_size` supplied
- **Then:** The response is `200`; `page` is `1`, `page_size` is `25`, `items` contains all three budgets, and `total` is `3`
- **AC:** AC-04, FR-03, FR-05
- **Type:** integration

### TC-33: An explicit page and page size within range return that page and an accurate total

- **US:** BM-US-02
- **Given:** An authenticated User and five active budgets they own
- **When:** The list is requested with `page=2` and `page_size=2`
- **Then:** The response is `200`; `page` is `2`, `page_size` is `2`, `items` contains exactly two of the User's own active budgets, and `total` is `5`
- **AC:** AC-05, FR-03, FR-05
- **Type:** integration

### TC-34: A `page` that is not a positive integer is rejected with 422

- **US:** BM-US-02
- **Given:** An authenticated User
- **When:** The list is requested with `page` set to each of `0`, `-1`, and `"abc"` in turn
- **Then:** Each response is `422` with `error_code` `VALIDATION_ERROR` and a `details.fields` entry locating `page`; no `items` are returned
- **AC:** AC-06, FR-04, BR-02
- **Type:** integration

### TC-35: A `page_size` that is not a positive integer is rejected with 422

- **US:** BM-US-02
- **Given:** An authenticated User
- **When:** The list is requested with `page_size` set to each of `0`, `-1`, and `"abc"` in turn
- **Then:** Each response is `422` with `error_code` `VALIDATION_ERROR` and a `details.fields` entry locating `page_size`; no `items` are returned
- **AC:** AC-06, FR-04, BR-02
- **Type:** integration

### TC-36: A `page_size` above the maximum is rejected with 422

- **US:** BM-US-02
- **Given:** An authenticated User
- **When:** The list is requested with `page_size=101`
- **Then:** The response is `422` `VALIDATION_ERROR` identifying `page_size`; the request is not silently capped at 100
- **AC:** AC-06, EC-02, FR-04, BR-02
- **Type:** integration

### TC-37: A User only ever sees their own budgets, never another User's

- **US:** BM-US-02
- **Given:** Two authenticated Users, `A` (two active budgets) and `B` (three active budgets)
- **When:** `A` requests the list of budgets
- **Then:** The response is `200`; `items` contains exactly `A`'s two budgets — none of `B`'s three — and `total` is `2`, not `5`
- **AC:** AC-07, FR-06, FR-07, BR-01, BR-04 *(assertion technique per QF-07/QF-08)*
- **Type:** integration

### TC-38: The reported total counts only the caller's own active budgets, even when it is the smaller number

- **US:** BM-US-02
- **Given:** Two authenticated Users, `A` (no budgets) and `B` (four active budgets)
- **When:** `A` requests the list of budgets
- **Then:** The response is `200`; `items` is empty and `total` is `0` — not `4`, and not any count reflecting `B`'s budgets
- **AC:** AC-02, AC-07, FR-06, FR-07, BR-04 *(assertion technique per QF-07)*
- **Type:** integration

### TC-39: The list is returned in a stable order matching the budgets' ids sorted ascending

- **US:** BM-US-02
- **Given:** An authenticated User who creates five active budgets in an order that does not already match ascending id order (confirmed from the ids the creation calls actually returned)
- **When:** The User requests the list of budgets twice, with nothing created, changed, or removed in between
- **Then:** Both responses return the same five budgets in the same relative order, and that order equals the five ids sorted ascending as strings — not the order the budgets were created in
- **AC:** AC-08, FR-08, BR-03 *(assertion technique per QF-12)*
- **Type:** integration

### TC-40: A budget whose period is a past calendar month is excluded, while a current-month budget appears

- **US:** BM-US-02
- **Given:** An authenticated User, with the system clock frozen to a known instant, who creates a budget (landing it in that month); the clock is then advanced by one full calendar month and a second budget is created
- **When:** The User requests the list of budgets with the clock reading the second, later month
- **Then:** The response is `200`; `items` contains only the second budget; `total` is `1`; the first budget's row still exists in storage but appears in neither `items` nor `total`
- **AC:** AC-09, EC-06, FR-09, BR-05 *(assertion technique per QF-10)*
- **Type:** integration

### TC-41: Amount spent sums only expense transactions against the budget's own wallet and category, within the current month

- **US:** BM-US-02
- **Given:** An authenticated User with an active budget for wallet `W1`/category `C1`, and two expense transactions recorded against `W1`/`C1` this month totalling `75.50`
- **When:** The User requests the list of budgets
- **Then:** The response is `200`; that budget's `amount_spent` is exactly `75.50`
- **AC:** AC-10, FR-10, BR-06
- **Type:** integration

### TC-42: A budget with no matching expense transactions reports zero spent and zero progress, not an error

- **US:** BM-US-02
- **Given:** An authenticated User with an active budget against which no transaction of any kind has been recorded
- **When:** The User requests the list of budgets
- **Then:** The response is `200`; that budget appears in `items` with `amount_spent` exactly `"0.00"` and `progress_percentage` exactly `"0.00"` — not omitted, not `null`, not an error
- **AC:** AC-11, FR-11, BR-07 *(assertion technique per QF-09)*
- **Type:** integration

### TC-43: Progress percentage may exceed 100 when spending has surpassed the limit

- **US:** BM-US-02
- **Given:** An authenticated User with an active budget whose `amount_limit` is `100.00`, and an expense transaction of `150.00` recorded against that budget's own wallet and category this month
- **When:** The User requests the list of budgets
- **Then:** The response is `200`; that budget's `amount_spent` is `150.00` and `progress_percentage` is `150.00` — not capped or clamped to `100.00`
- **AC:** AC-12, FR-12, BR-08
- **Type:** integration

### TC-44: A transaction against a different wallet or a different category never contributes to a budget's amount spent

- **US:** BM-US-02
- **Given:** An authenticated User with two active budgets sharing the same wallet `W1` but different categories `C1`/`C2`, and an expense transaction recorded against `W1`/`C1` only
- **When:** The User requests the list of budgets
- **Then:** The response is `200`; the `C1` budget's `amount_spent` reflects the transaction; the `C2` budget's `amount_spent` remains exactly `"0.00"`
- **AC:** AC-10, EC-05, FR-10, BR-06 *(assertion technique per QF-11)*
- **Type:** integration

### TC-45: An income transaction never contributes to a budget's amount spent

- **US:** BM-US-02
- **Given:** An authenticated User with an active budget for wallet `W1`/category `C1`, and an income transaction recorded against `W1`/`C1` this month
- **When:** The User requests the list of budgets
- **Then:** The response is `200`; that budget's `amount_spent` remains exactly `"0.00"`
- **AC:** AC-10, EC-09, FR-10, BR-06
- **Type:** integration

### TC-46: A transaction timestamped at the immediately preceding or following calendar month's boundary is excluded from amount spent

- **US:** BM-US-02
- **Given:** An authenticated User with an active budget for wallet `W1`/category `C1`; one expense transaction timestamped at the first instant of the immediately preceding calendar month, and one at the first instant of the immediately following calendar month, both against `W1`/`C1`
- **When:** The User requests the list of budgets
- **Then:** The response is `200`; that budget's `amount_spent` remains exactly `"0.00"` — neither boundary transaction is counted
- **AC:** AC-10, EC-08, FR-10, BR-06
- **Type:** integration

### TC-47: Budgets sharing exactly one of wallet or category have independently computed amount spent

- **US:** BM-US-02
- **Given:** An authenticated User with an active budget for wallet `W1`/category `C1` and a second active budget for wallet `W2`/category `C1` (same category, different wallet), with an expense transaction recorded against `W1`/`C1` only
- **When:** The User requests the list of budgets
- **Then:** The response is `200`; the `W1`/`C1` budget's `amount_spent` reflects the transaction; the `W2`/`C1` budget's `amount_spent` remains exactly `"0.00"`
- **AC:** EC-07, FR-10, BR-06 *(assertion technique per QF-11)*
- **Type:** integration

### TC-48: A page beyond the last available page returns an empty list with the accurate total

- **US:** BM-US-02
- **Given:** An authenticated User and three active budgets they own
- **When:** The list is requested with `page=5` and `page_size=25`
- **Then:** The response is `200`, not `404`; `items` is an empty list and `total` is still `3`
- **AC:** EC-01, FR-05
- **Type:** integration

### TC-49: A `page_size` of exactly 100 is accepted

- **US:** BM-US-02
- **Given:** An authenticated User
- **When:** The list is requested with `page_size=100`
- **Then:** The response is `200`; the request is not rejected
- **AC:** EC-02, FR-04
- **Type:** integration

### TC-50: Paging through every page returns every active budget exactly once, in stable order

- **US:** BM-US-02
- **Given:** An authenticated User with five active budgets and a fixed `page_size` of `2`
- **When:** The User requests every page in sequence (`page=1`, `page=2`, `page=3`)
- **Then:** The concatenation of all three pages' `items` contains every one of the five budgets exactly once, with no duplicate and no gap, in the same order `TC-39` establishes
- **AC:** EC-03, FR-08, BR-03 *(assertion technique per QF-12)*
- **Type:** integration

### TC-51: An ADMIN-role caller who also owns a budget sees only their own

- **US:** BM-US-02
- **Given:** An ADMIN-role User with one active budget, alongside a second User (any role) with active budgets of their own
- **When:** The ADMIN requests the list of budgets
- **Then:** The response is `200`; `items` contains exactly the ADMIN's own budget — never the other User's — despite the elevated role
- **AC:** EC-04, BR-01
- **Type:** integration
