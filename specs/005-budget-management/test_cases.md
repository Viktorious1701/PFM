# Test Cases: Budget Management (BM)

> **Feature:** SRS §6 Feature-05 · SDS §5.5 (BM)
> **Spec:** [spec.md](spec.md) · **Plan:** [plan.md](plan.md)
> **Stories in this file:** BM-US-01 *(TC-01…TC-26)*

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

Not yet implemented. This section is populated at the Implement step (step 4), from `backend/tests/integration/test_bm_us_01_create_budget.py`, with each row's real pytest node id and PASS/FAIL/BLOCKED result (constitution DOD-07). No code exists yet — steps 1–3 (this story's scope) produce `spec.md`, `plan.md`, and this file only.

| TC | pytest node id | Result |
|---|---|---|
| TC-01 … TC-26 | *(pending T-10)* | *(pending)* |

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
