# Test Cases: Transaction Management (TM)

> **Feature:** SRS §6 Feature-06 · SDS §5.6 (TM)
> **Spec:** [spec.md](spec.md) · **Plan:** [plan.md](plan.md)
> **Stories in this file:** TM-US-01 *(TC-01…TC-36)* · TM-US-02 *(TC-37…TC-72)*

---

## TM-US-01: Create a Transaction

### Quality Findings

Problems found while deriving test cases from `spec.md` and `plan.md`. Each one changes how a criterion can be asserted, so it is recorded rather than worked around silently.

#### QF-01

**Description.** AC-05/AC-07 require a wallet or category reference that does not exist at all and one that exists but belongs to a different User to produce "the same not-found outcome" — `plan.md` A8 (reusing BM-US-01 A6 unchanged) makes this true by construction, since `wallet_repo.get_owned_by_id()`/`category_repo.get_owned_by_id()` filter by `user_id` in the query itself and return `None` either way. A test that merely checks both cases return *some* `404` would not distinguish "genuinely identical" from "two different messages that both happen to carry status 404."

**Impact.** A weaker test could pass even if a future change accidentally made the two cases distinguishable — the same class of minor information leak about another User's data BM-US-01 QF-01 already flagged for this exact repository function.

**Recommendation.** `TC-08` and `TC-11` each compare the full response body of the ownership-mismatch case against the full response body of the corresponding not-found-at-all case (`TC-07`, `TC-10`) and assert they match exactly — `error_code`, `message`, and `details` all identical, not merely the status code.

#### QF-02

**Description.** AC-11 requires an over-precise `amount` to be rejected, not rounded. The rejection is a Pydantic-native `decimal_max_places` constraint (mirrors WM-US-01 A3/BM-US-01's reused mechanism), not a hand-written check, so the risk is asserting the wrong thing: a test could check only that *some* `422` came back without confirming which field it names, or without confirming the wallet's balance was never touched.

**Impact.** A loosely-written assertion would not actually prove precision is preserved rather than silently rounded elsewhere before validation runs, and — new to this story versus WM-US-01/BM-US-01 — would not prove the wallet's balance was left untouched by a rejected transaction.

**Recommendation.** `TC-17` asserts the `422` response's `details` names the `amount` field specifically, that no `transactions` row was created, and that the wallet's balance is unchanged from before the attempt.

#### QF-03

**Description.** `plan.md` A5 records that `timestamp` is computed from `app.core.clock.utcnow()`, never accepted from the request — the same technique BM-US-01 A2/QF-03 established for `period`. A test that asserts only "the response includes *a* timestamp" would not prove the value is the *actual* moment of creation, and a test that computes "now" independently inside the test body risks flaking or drifting from the application's own notion of "now" (constitution TST-06: "Time comes from the patched clock seam; no reliance on ordering, sleeps, or network").

**Impact.** An unfrozen test cannot assert an exact value, only an approximate range, which would not catch a regression that silently ignored the clock seam and used a slightly different time source.

**Recommendation.** `TC-21` and `TC-28` both monkeypatch `app.core.clock.utcnow` to a fixed instant before submitting a transaction, then assert `timestamp` equals that fixed instant exactly — the same clock-seam technique BM-US-01's `TC-03`/`TC-19` already used for a creation-time value.

#### QF-04

**Description.** `plan.md` A9 records that the insufficient-balance check is a single conditional `UPDATE ... WHERE balance >= amount`, chosen specifically because it closes a genuine two-concurrent-writer race that a read-then-compare-in-Python design would not. UM-US-01/UM-US-02's own `test_cases.md` QF-02 already established that this codebase's test database (SQLite, `StaticPool`, single-threaded test execution — constitution ENV-03) serialises writers, so a literal "two requests race, only one wins" integration test cannot be constructed in this environment; writing one that appears to pass would prove serialisation, not conflict handling.

**Impact.** The race-safety property that motivates the entire design in `plan.md` A9 cannot be directly exercised by this suite.

**Recommendation.** Split the criterion exactly as UM-US-01/02 did. `TC-20` (insufficient balance) and `TC-31` (exact-balance boundary) between them prove the conditional UPDATE's *single-request* correctness deterministically — the mechanism itself, exercised once, behaves exactly as `plan.md` A9 specifies. True concurrent-writer verification (two simultaneous EXPENSE requests against the same wallet, only one succeeding) is deferred to a PostgreSQL run, per constitution ENV-03, and is recorded here as a known coverage limit rather than silently assumed covered.

#### QF-05

**Description.** `plan.md` A11 records that `transactions` has no `user_id` column, unlike `wallets`/`categories` (both carry one). A test asserting only that the documented fields are *present* would not prove `user_id` is *absent*.

**Impact.** A future change that accidentally started returning an owner field (perhaps copied from another resource's `Read` schema, or from the `WalletModel`/`CategoryModel` rows this story's service already holds in memory) would pass a weak test and quietly begin leaking a field this story's contract never promised.

**Recommendation.** `TC-24`'s exact-field-set assertion positively confirms the response has exactly seven keys and, in particular, no `user_id` — the same technique WM-US-01 QF-04, CM-US-01 QF-04, and BM-US-01 QF-05 each used for their own easy-to-accidentally-leak fields.

#### QF-06

**Description.** `plan.md` A4/FR-18/BR-02 establish a fixed four-step check order — wallet ownership, category ownership, category-type consistency, then (EXPENSE only) balance sufficiency — but this order is only *observable* when a single request fails more than one check at once. Unlike BM-US-01 (a three-step order provable by exactly one multi-failure pairing), this story's order has four steps and, per `plan.md` A4, exactly two of the three adjacent pairings are even constructible: wallet-vs-category (both absent at once) and type-vs-balance (a wrongly-typed category whose amount would also exceed the balance). The middle pairing — a category-ownership failure competing with a type mismatch — cannot be constructed at all, because a type mismatch is not a coherent failure unless the category was already found.

**Impact.** Without dedicated multi-failure tests for the two constructible pairings, a future refactor could silently reorder those two adjacent steps without any single-failure test catching the change, even though `spec.md` records the order as a rule (BR-02), not an implementation detail.

**Recommendation.** `TC-36` submits a request where *both* the wallet and category references are invalid, and asserts the response is `TRANSACTION_WALLET_NOT_FOUND` specifically. `TC-34` submits a request that is both wrongly typed *and* would separately fail the balance check, and asserts the response is `TRANSACTION_CATEGORY_TYPE_MISMATCH` specifically, never `TRANSACTION_INSUFFICIENT_BALANCE`. The category-ownership-versus-type-mismatch pairing is left untested for the structural reason above, exactly as BM-US-01's own coverage matrix recorded its analogous category-versus-uniqueness gap.

#### QF-07

**Description.** FR-13/BR-07 require the transaction row and the wallet's balance update to be written as a single atomic unit — constitution AR-06's guarantee. This is not directly observable through the HTTP boundary as an abstract "atomicity" property; what is observable is that a request which fails *after* both entities are successfully loaded (the only point in the fixed check order where a write could plausibly have partially happened) leaves neither the transaction row nor the balance change behind.

**Impact.** A test suite that only checks "the happy path leaves both a transaction row and an updated balance" would not by itself rule out a partial-write bug reachable only through a late-stage failure — the specific failure mode AR-06 exists to prevent.

**Recommendation.** `TC-20` (insufficient balance) is the load-bearing witness: it is the only refusal in this story reachable after wallet ownership, category ownership, and type consistency have all already succeeded, and its `Then` clause asserts both that no `transactions` row exists for the attempt *and* that the wallet's `balance` is bit-for-bit unchanged from before the request — proving the two writes really do rise and fall together rather than merely usually appearing together.

#### QF-08

**Description.** `note` (`plan.md` A6) is this codebase's first **optional** field on any Create DTO — every prior story's DTO (`WalletCreate`, `CategoryCreate`, `BudgetCreate`) required every one of its fields. A test that only checks "creation succeeds when `note` is omitted" would not by itself prove the *response* renders the field as JSON `null` rather than omitting the key entirely or defaulting to an empty string — three different wire representations a client would need to handle differently.

**Impact.** A weak assertion here could hide a regression that silently changed `note`'s absent-value representation, which downstream (TM-US-02/03, out of scope) would be a breaking response-shape change for any client already handling today's shape.

**Recommendation.** `TC-23` asserts the response body's `note` key is both **present** and **exactly `null`** — not merely "falsy" — when no note was submitted.

### Acceptance Criteria Classification

No transaction-creation screen exists in `mobile/` this round (`CLAUDE.md` §5 — the prototype covers only UM-US-01's invite screen). SRS UXR-01 names low-friction transaction entry as a future UI concern, not a testable surface this round, the same situation WM-US-01/CM-US-01/BM-US-01's own `test_cases.md` each recorded. Every row below is `[API]`.

| AC/EC | Title | Label | Rationale |
|---|---|---|---|
| AC-01 | Successfully create an expense transaction with a sufficient balance | **[API]** | No UI surface exists or is named by any UXR this round |
| AC-02 | Successfully create an income transaction regardless of balance | **[API]** | Same |
| AC-03 | Deny access to unauthenticated callers | **[API]** | Backend authorization contract |
| AC-04 | Reject a missing wallet reference | **[API]** | Payload validation |
| AC-05 | Reject a wallet reference that does not resolve to the caller's own wallet | **[API]** | Persistence/ownership contract; bounded by QF-01 |
| AC-06 | Reject a missing category reference | **[API]** | Payload validation |
| AC-07 | Reject a category reference that does not resolve to the caller's own category | **[API]** | Persistence/ownership contract; bounded by QF-01 |
| AC-08 | Reject a transaction whose type does not match its category's type | **[API]** | Backend conflict rule |
| AC-09 | Reject a missing amount | **[API]** | Payload validation |
| AC-10 | Reject an amount that is zero or negative | **[API]** | Payload validation |
| AC-11 | Reject an amount carrying more than two decimal places | **[API]** | Payload validation; bounded by QF-02 |
| AC-12 | Reject a missing transaction type | **[API]** | Payload validation |
| AC-13 | Reject a transaction type that is not INCOME or EXPENSE | **[API]** | Payload validation |
| AC-14 | Reject an expense transaction whose amount exceeds the wallet's current balance | **[API]** | Backend conflict rule; bounded by QF-04, QF-07 |
| AC-15 | A created transaction's timestamp is always the moment of creation | **[API]** | Backend rule; bounded by QF-03 |
| AC-16 | Reject a note exceeding the maximum supported length | **[API]** | Payload validation |
| AC-17 | A transaction may be created with no note at all | **[API]** | Response-payload contract; bounded by QF-08 |
| AC-18 | Return exactly the documented transaction fields | **[API]** | Response-payload contract; bounded by QF-05 |
| EC-01 | Amount at the smallest positive value | **[API]** | Boundary value |
| EC-02 | Amount exceeding the `DECIMAL(15,2)` total digit width | **[API]** | Payload validation, distinct from AC-11's decimal-places check |
| EC-03 | More than one validation failure in a single submission | **[API]** | Backend validation-grouping contract |
| EC-04 | A timestamp value submitted with the request | **[API]** | Structural-ignore contract; bounded by QF-03 |
| EC-05 | A wallet reference belonging to a different, real User | **[API]** | Persistence/ownership contract; bounded by QF-01 |
| EC-06 | A category reference belonging to a different, real User | **[API]** | Persistence/ownership contract; bounded by QF-01 |
| EC-07 | A wallet or category reference that is not a well-formed identifier | **[API]** | Backend rule (no separate format validation) |
| EC-08 | An expense amount exactly equal to the wallet's current balance | **[API]** | Boundary value |
| EC-09 | An income transaction accepted despite a zero or negative balance | **[API]** | Backend rule |
| EC-10 | An expense rejected outright against a non-positive balance | **[API]** | Backend rule |
| EC-11 | Category-type mismatch takes priority over insufficient balance | **[API]** | Backend check-ordering contract; bounded by QF-06 |
| EC-12 | Two identical transactions both accepted | **[API]** | Backend rule (no uniqueness) |
| EC-13 | No note supplied at all | **[API]** | Response-payload contract; bounded by QF-08 |
| EC-14 | Both wallet and category references invalid in the same request | **[API]** | Backend check-ordering contract; bounded by QF-06 |

### Coverage Matrix

| AC/EC | Label | Integration TC(s) | E2E TC(s) |
|---|---|---|---|
| AC-01 | [API] | TC-01, TC-02 | — |
| AC-02 | [API] | TC-03, TC-04 | — |
| AC-03 | [API] | TC-05 | — |
| AC-04 | [API] | TC-06 | — |
| AC-05 | [API] | TC-07, TC-08 | — |
| AC-06 | [API] | TC-09 | — |
| AC-07 | [API] | TC-10, TC-11 | — |
| AC-08 | [API] | TC-12, TC-13 | — |
| AC-09 | [API] | TC-14 | — |
| AC-10 | [API] | TC-15, TC-16 | — |
| AC-11 | [API] | TC-17 | — |
| AC-12 | [API] | TC-18 | — |
| AC-13 | [API] | TC-19 | — |
| AC-14 | [API] | TC-20 | — |
| AC-15 | [API] | TC-21, TC-28 | — |
| AC-16 | [API] | TC-22 | — |
| AC-17 | [API] | TC-23 | — |
| AC-18 | [API] | TC-24 | — |
| EC-01 | [API] | TC-25 | — |
| EC-02 | [API] | TC-26 | — |
| EC-03 | [API] | TC-27 | — |
| EC-04 | [API] | TC-28 | — |
| EC-05 | [API] | TC-08 | — |
| EC-06 | [API] | TC-11 | — |
| EC-07 | [API] | TC-29, TC-30 | — |
| EC-08 | [API] | TC-31 | — |
| EC-09 | [API] | TC-32 | — |
| EC-10 | [API] | TC-33 | — |
| EC-11 | [API] | TC-34 | — |
| EC-12 | [API] | TC-35 | — |
| EC-13 | [API] | TC-23 | — |
| EC-14 | [API] | TC-36 | — |

> Every AC and EC has at least one integration TC. There is no `[BOTH]` or `[UI]` row — no transaction-creation screen exists this round, and none is named by any SRS UXR. **Known coverage limits, accepted:** true concurrent-writer verification of the balance-sufficiency race (`plan.md` A9) is not constructible under this environment's SQLite test database (QF-04) and is deferred to a PostgreSQL run, mirroring UM-US-01/02's own QF-02. FR-18/BR-02's fixed check order is proven for two of its three adjacent pairings (`TC-36` wallet-before-category, `TC-34` type-before-balance); the category-ownership-versus-type-mismatch pairing has no dedicated multi-failure test because the two conditions can never simultaneously hold (QF-06). This story never touches `budgets` (spec *Out of scope*), so no test here exercises the SDS §2.4.3 Budget Monitoring State machine.

### Test Implementation Map *(filled at step 4)*

Populated at the Implement dispatch (steps 4–6). All 36 test cases are implemented in
`backend/tests/integration/test_tm_us_01_create_transaction.py`, one test per `TC-NN`, each
carrying its `TC-NN` id in its docstring. Full suite run: `281 passed` (36 of them this story's),
`ruff check`/`ruff format --check` clean, `mypy app` clean, coverage 100% on every file this story
added or modified (`app/models/transaction.py`, `app/schemas/transaction.py`,
`app/repositories/transaction_repo.py`, `app/repositories/wallet_repo.py`,
`app/services/transaction_service.py`, `app/core/errors.py`, `app/api/v1/transactions.py`,
`app/api/v1/router.py`), 99% overall. Live `curl` walkthrough against a running server executed
per CLAUDE.md §2 Step 5 — see the Implement dispatch's gate report for the full request/response
transcript. No failures were found at Verification; nothing here required root-causing.

| TC | pytest node id | Result |
|---|---|---|
| TC-01 | `tests/integration/test_tm_us_01_create_transaction.py::test_authenticated_user_creates_expense_transaction_201_with_created_transaction_and_note` | PASS |
| TC-02 | `tests/integration/test_tm_us_01_create_transaction.py::test_creating_expense_transaction_persists_one_row_and_decreases_balance_by_exact_amount` | PASS |
| TC-03 | `tests/integration/test_tm_us_01_create_transaction.py::test_authenticated_user_creates_income_transaction_201_with_created_transaction` | PASS |
| TC-04 | `tests/integration/test_tm_us_01_create_transaction.py::test_creating_income_transaction_persists_one_row_and_increases_balance_by_exact_amount` | PASS |
| TC-05 | `tests/integration/test_tm_us_01_create_transaction.py::test_unauthenticated_caller_is_denied_with_401` | PASS |
| TC-06 | `tests/integration/test_tm_us_01_create_transaction.py::test_a_missing_wallet_reference_is_rejected_with_422` | PASS |
| TC-07 | `tests/integration/test_tm_us_01_create_transaction.py::test_a_wallet_reference_matching_no_wallet_at_all_is_rejected_with_404` | PASS |
| TC-08 | `tests/integration/test_tm_us_01_create_transaction.py::test_a_wallet_reference_belonging_to_a_different_user_is_rejected_identically_to_not_found` | PASS |
| TC-09 | `tests/integration/test_tm_us_01_create_transaction.py::test_a_missing_category_reference_is_rejected_with_422` | PASS |
| TC-10 | `tests/integration/test_tm_us_01_create_transaction.py::test_a_category_reference_matching_no_category_at_all_is_rejected_with_404` | PASS |
| TC-11 | `tests/integration/test_tm_us_01_create_transaction.py::test_a_category_reference_belonging_to_a_different_user_is_rejected_identically_to_not_found` | PASS |
| TC-12 | `tests/integration/test_tm_us_01_create_transaction.py::test_expense_transaction_against_income_typed_category_is_rejected_with_409` | PASS |
| TC-13 | `tests/integration/test_tm_us_01_create_transaction.py::test_income_transaction_against_expense_typed_category_is_rejected_with_409` | PASS |
| TC-14 | `tests/integration/test_tm_us_01_create_transaction.py::test_a_missing_amount_is_rejected_with_422` | PASS |
| TC-15 | `tests/integration/test_tm_us_01_create_transaction.py::test_an_amount_of_exactly_zero_is_rejected_with_422` | PASS |
| TC-16 | `tests/integration/test_tm_us_01_create_transaction.py::test_a_negative_amount_is_rejected_with_422` | PASS |
| TC-17 | `tests/integration/test_tm_us_01_create_transaction.py::test_an_amount_with_three_decimal_places_is_rejected_not_rounded` | PASS |
| TC-18 | `tests/integration/test_tm_us_01_create_transaction.py::test_a_missing_transaction_type_is_rejected_with_422` | PASS |
| TC-19 | `tests/integration/test_tm_us_01_create_transaction.py::test_a_transaction_type_other_than_income_or_expense_is_rejected_with_422` | PASS |
| TC-20 | `tests/integration/test_tm_us_01_create_transaction.py::test_expense_amount_exceeding_wallet_balance_is_rejected_with_409_and_nothing_persists` | PASS |
| TC-21 | `tests/integration/test_tm_us_01_create_transaction.py::test_created_transactions_timestamp_is_moment_of_creation_from_frozen_clock` | PASS |
| TC-22 | `tests/integration/test_tm_us_01_create_transaction.py::test_a_note_longer_than_500_characters_is_rejected_with_422` | PASS |
| TC-23 | `tests/integration/test_tm_us_01_create_transaction.py::test_transaction_created_with_no_note_succeeds_and_returned_note_is_null` | PASS |
| TC-24 | `tests/integration/test_tm_us_01_create_transaction.py::test_response_exposes_exactly_the_seven_documented_fields` | PASS |
| TC-25 | `tests/integration/test_tm_us_01_create_transaction.py::test_an_amount_of_exactly_0_01_is_accepted` | PASS |
| TC-26 | `tests/integration/test_tm_us_01_create_transaction.py::test_an_amount_exceeding_15_total_digits_is_rejected` | PASS |
| TC-27 | `tests/integration/test_tm_us_01_create_transaction.py::test_multiple_validation_failures_in_one_submission_are_reported_together` | PASS |
| TC-28 | `tests/integration/test_tm_us_01_create_transaction.py::test_a_timestamp_submitted_in_the_request_body_is_silently_ignored` | PASS |
| TC-29 | `tests/integration/test_tm_us_01_create_transaction.py::test_a_malformed_wallet_reference_is_rejected_with_same_outcome_as_not_found` | PASS |
| TC-30 | `tests/integration/test_tm_us_01_create_transaction.py::test_a_malformed_category_reference_is_rejected_with_same_outcome_as_not_found` | PASS |
| TC-31 | `tests/integration/test_tm_us_01_create_transaction.py::test_expense_amount_exactly_equal_to_balance_is_accepted_leaving_balance_at_zero` | PASS |
| TC-32 | `tests/integration/test_tm_us_01_create_transaction.py::test_income_transaction_accepted_even_when_wallet_balance_is_negative` | PASS |
| TC-33 | `tests/integration/test_tm_us_01_create_transaction.py::test_expense_against_wallet_already_at_zero_balance_is_rejected_regardless_of_amount` | PASS |
| TC-34 | `tests/integration/test_tm_us_01_create_transaction.py::test_category_type_mismatch_takes_priority_over_independently_failing_balance_check` | PASS |
| TC-35 | `tests/integration/test_tm_us_01_create_transaction.py::test_two_identical_transactions_are_both_accepted_as_independent_ledger_entries` | PASS |
| TC-36 | `tests/integration/test_tm_us_01_create_transaction.py::test_wallet_ownership_is_checked_before_category_ownership_when_both_invalid` | PASS |

---

### TC-01: An authenticated User creates an EXPENSE transaction with a sufficient balance — 201 with the created transaction, note included

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet with balance `1000.00` and owns an `EXPENSE`-typed category
- **When:** A transaction is submitted with that wallet's id, that category's id, `amount` `50.00`, `type` `"EXPENSE"`, and `note` `"Weekly grocery run"`
- **Then:** The response is `201`; the body carries `id`, `wallet_id` equal to the submitted wallet, `category_id` equal to the submitted category, `amount` `50.00`, `type` `"EXPENSE"`, a `timestamp`, and `note` equal to exactly `"Weekly grocery run"` — proving a submitted note round-trips unchanged, not just that the key exists (distinct from TC-23's omitted-note case)
- **AC:** AC-01, FR-15, FR-16
- **Type:** integration

### TC-02: Creating an EXPENSE transaction persists exactly one row and decreases the wallet's balance by the exact amount

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet with balance `1000.00` and an `EXPENSE`-typed category
- **When:** An `EXPENSE` transaction of `50.00` is submitted successfully
- **Then:** Exactly one `transactions` row exists carrying the submitted `wallet_id`, `category_id`, `amount`, and `type`; the wallet's `balance` row (inspected directly — no `GET` endpoint exists yet) now reads `950.00`
- **AC:** AC-01, FR-01, FR-11, FR-13
- **Type:** integration

### TC-03: An authenticated User creates an INCOME transaction — 201 with the created transaction

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet and owns an `INCOME`-typed category
- **When:** A transaction is submitted with that wallet's id, that category's id, `amount` `500.00`, and `type` `"INCOME"`
- **Then:** The response is `201`; the body carries `id`, `wallet_id`, `category_id`, `amount` `500.00`, `type` `"INCOME"`, a `timestamp`, and `note`
- **AC:** AC-02, FR-01, FR-16
- **Type:** integration

### TC-04: Creating an INCOME transaction persists exactly one row and increases the wallet's balance by the exact amount

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet with balance `100.00` and an `INCOME`-typed category
- **When:** An `INCOME` transaction of `500.00` is submitted successfully
- **Then:** Exactly one `transactions` row exists carrying the submitted fields; the wallet's `balance` row now reads `600.00`
- **AC:** AC-02, FR-01, FR-12, FR-13
- **Type:** integration

### TC-05: An unauthenticated caller is denied with 401

- **US:** TM-US-01
- **Given:** A caller presenting no `Authorization` header
- **When:** A transaction is submitted with an otherwise valid payload
- **Then:** The response is `401` with `error_code` `NOT_AUTHENTICATED`; no `transactions` row is created and no wallet balance changes
- **AC:** AC-03, FR-02
- **Type:** integration

### TC-06: A missing wallet reference is rejected with 422

- **US:** TM-US-01
- **Given:** An authenticated User who owns a category
- **When:** A transaction is submitted with the `wallet_id` field absent
- **Then:** The response is `422` `VALIDATION_ERROR` identifying the `wallet_id` field; nothing is persisted
- **AC:** AC-04, FR-03
- **Type:** integration

### TC-07: A wallet reference matching no wallet at all is rejected with 404 TRANSACTION_WALLET_NOT_FOUND

- **US:** TM-US-01
- **Given:** An authenticated User and a category they own
- **When:** A transaction is submitted with a `wallet_id` that matches no wallet in the system
- **Then:** The response is `404` with `error_code` `TRANSACTION_WALLET_NOT_FOUND`; nothing is persisted
- **AC:** AC-05, FR-04
- **Type:** integration

### TC-08: A wallet reference belonging to a different User is rejected with the identical outcome as TC-07

- **US:** TM-US-01
- **Given:** Two authenticated Users `A` and `B`, where `B` owns a wallet and `A` owns a category
- **When:** `A` submits a transaction with `B`'s `wallet_id` and `A`'s own `category_id`
- **Then:** The response is `404`; its `error_code`, `message`, and `details` are identical to TC-07's response; nothing is persisted
- **AC:** AC-05, EC-05, FR-04 *(assertion technique per QF-01)*
- **Type:** integration

### TC-09: A missing category reference is rejected with 422

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet
- **When:** A transaction is submitted with the `category_id` field absent
- **Then:** The response is `422` `VALIDATION_ERROR` identifying the `category_id` field; nothing is persisted
- **AC:** AC-06, FR-05
- **Type:** integration

### TC-10: A category reference matching no category at all is rejected with 404 TRANSACTION_CATEGORY_NOT_FOUND

- **US:** TM-US-01
- **Given:** An authenticated User and a wallet they own
- **When:** A transaction is submitted with a `category_id` that matches no category in the system
- **Then:** The response is `404` with `error_code` `TRANSACTION_CATEGORY_NOT_FOUND`; nothing is persisted
- **AC:** AC-07, FR-06
- **Type:** integration

### TC-11: A category reference belonging to a different User is rejected with the identical outcome as TC-10

- **US:** TM-US-01
- **Given:** Two authenticated Users `A` and `B`, where `B` owns a category and `A` owns a wallet
- **When:** `A` submits a transaction with `A`'s own `wallet_id` and `B`'s `category_id`
- **Then:** The response is `404`; its `error_code`, `message`, and `details` are identical to TC-10's response; nothing is persisted
- **AC:** AC-07, EC-06, FR-06 *(assertion technique per QF-01)*
- **Type:** integration

### TC-12: An EXPENSE transaction against an INCOME-typed category is rejected with 409 TRANSACTION_CATEGORY_TYPE_MISMATCH

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet and owns a category typed `INCOME`
- **When:** An `EXPENSE` transaction is submitted against that wallet and that category
- **Then:** The response is `409` with `error_code` `TRANSACTION_CATEGORY_TYPE_MISMATCH`; the wallet's balance is unchanged and nothing is persisted
- **AC:** AC-08, FR-07, BR-03
- **Type:** integration

### TC-13: An INCOME transaction against an EXPENSE-typed category is rejected with 409 TRANSACTION_CATEGORY_TYPE_MISMATCH

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet and owns a category typed `EXPENSE`
- **When:** An `INCOME` transaction is submitted against that wallet and that category
- **Then:** The response is `409` with `error_code` `TRANSACTION_CATEGORY_TYPE_MISMATCH`; the wallet's balance is unchanged and nothing is persisted
- **AC:** AC-08, FR-07, BR-03
- **Type:** integration

### TC-14: A missing amount is rejected with 422

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet and a category
- **When:** A transaction is submitted with the `amount` field absent
- **Then:** The response is `422` `VALIDATION_ERROR` identifying the `amount` field; nothing is persisted
- **AC:** AC-09, FR-08
- **Type:** integration

### TC-15: An amount of exactly zero is rejected with 422

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet and a category
- **When:** A transaction is submitted with `amount` `0.00`
- **Then:** The response is `422` `VALIDATION_ERROR` identifying the `amount` field; nothing is persisted
- **AC:** AC-10, FR-09, BR-04
- **Type:** integration

### TC-16: A negative amount is rejected with 422

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet and a category
- **When:** A transaction is submitted with `amount` `-50.00`
- **Then:** The response is `422` `VALIDATION_ERROR` identifying the `amount` field; nothing is persisted
- **AC:** AC-10, FR-09, BR-04
- **Type:** integration

### TC-17: An amount with three decimal places is rejected, not rounded

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet and a category
- **When:** A transaction is submitted with `amount` `100.005`
- **Then:** The response is `422` `VALIDATION_ERROR` whose `details` names `amount`; no `transactions` row is created and the wallet's balance is unchanged — so there is no rounded `100.01` or truncated `100.00` value to find
- **AC:** AC-11, BR-04, FR-08 *(assertion technique per QF-02)*
- **Type:** integration

### TC-18: A missing transaction type is rejected with 422

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet and a category
- **When:** A transaction is submitted with the `type` field absent
- **Then:** The response is `422` `VALIDATION_ERROR` identifying the `type` field; nothing is persisted
- **AC:** AC-12, FR-10
- **Type:** integration

### TC-19: A transaction type other than INCOME or EXPENSE is rejected with 422

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet and a category
- **When:** A transaction is submitted with `type` `"TRANSFER"`
- **Then:** The response is `422` `VALIDATION_ERROR` identifying the `type` field; nothing is persisted
- **AC:** AC-13, FR-10
- **Type:** integration

### TC-20: An EXPENSE transaction whose amount exceeds the wallet's current balance is rejected with 409, and nothing persists

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet with balance `1000.00` and an `EXPENSE`-typed category
- **When:** An `EXPENSE` transaction of `1500.00` is submitted
- **Then:** The response is `409` with `error_code` `TRANSACTION_INSUFFICIENT_BALANCE`; the wallet's `balance` row is still exactly `1000.00`, and no `transactions` row exists for this attempt
- **AC:** AC-14, FR-11, BR-05 *(also the load-bearing atomicity witness, QF-07)*
- **Type:** integration

### TC-21: The created transaction's timestamp is the moment of creation, computed from a frozen clock

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet and a category, with the system clock frozen to a known instant
- **When:** A transaction is submitted successfully
- **Then:** The created transaction's `timestamp` equals the frozen instant exactly
- **AC:** AC-15, FR-14, BR-06 *(assertion technique per QF-03)*
- **Type:** integration

### TC-22: A note longer than 500 characters is rejected with 422

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet and a category
- **When:** A transaction is submitted with a `note` of 501 characters
- **Then:** The response is `422` `VALIDATION_ERROR` identifying the `note` field; nothing is persisted
- **AC:** AC-16, FR-15
- **Type:** integration

### TC-23: A transaction created with no note at all succeeds, and the returned note is null

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet and a category
- **When:** A transaction is submitted with the `note` field entirely absent from the request body
- **Then:** The response is `201`; the body's `note` key is present and its value is exactly `null` — not an empty string and not the key omitted
- **AC:** AC-17, EC-13, FR-15 *(assertion technique per QF-08)*
- **Type:** integration

### TC-24: The response exposes exactly the seven documented fields

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet and a category
- **When:** A transaction is submitted successfully
- **Then:** The response body's keys are exactly `id`, `wallet_id`, `category_id`, `amount`, `type`, `timestamp`, `note` — no more, and in particular no `user_id` (plan.md A11, QF-05)
- **AC:** AC-18, FR-16
- **Type:** integration

### TC-25: An amount of exactly 0.01 is accepted

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet and a category
- **When:** A transaction is submitted with `amount` `0.01`
- **Then:** The response is `201`; the created transaction's `amount` is `0.01`
- **AC:** EC-01, FR-09
- **Type:** integration

### TC-26: An amount exceeding 15 total digits is rejected

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet and a category
- **When:** A transaction is submitted with an `amount` of 14 integer digits and 2 decimal places (16 significant digits total)
- **Then:** The response is `422` `VALIDATION_ERROR`; nothing is persisted — constitution VL-07's `DECIMAL(15,2)` bound is enforced by the DTO before the service runs
- **AC:** EC-02, BR-04, FR-08
- **Type:** integration

### TC-27: Multiple validation failures in one submission are reported together

- **US:** TM-US-01
- **Given:** An authenticated User
- **When:** A transaction is submitted with the `wallet_id` field absent and `amount` `-50.00` in the same request
- **Then:** The response is a single `422` whose `details` identifies both the `wallet_id` and the `amount` fields — not just the first one encountered
- **AC:** EC-03, FR-17
- **Type:** integration

### TC-28: A timestamp submitted in the request body is silently ignored

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet and a category, with the system clock frozen to a known instant
- **When:** A transaction is submitted with an otherwise valid payload that additionally includes a timestamp-shaped key (`"timestamp": "2020-01-01T00:00:00Z"`) in the JSON body
- **Then:** The response is `201`; the created transaction's `timestamp` equals the frozen instant, never `2020-01-01T00:00:00Z`
- **AC:** AC-15, EC-04, FR-14, BR-06
- **Type:** integration

### TC-29: A wallet reference that is not a well-formed identifier is rejected with the same outcome as a well-formed but non-existent one

- **US:** TM-US-01
- **Given:** An authenticated User and a category they own
- **When:** A transaction is submitted with `wallet_id` `"not-a-real-id"`
- **Then:** The response is `404` `TRANSACTION_WALLET_NOT_FOUND`, identical to TC-07's response; nothing is persisted
- **AC:** EC-07, FR-04
- **Type:** integration

### TC-30: A category reference that is not a well-formed identifier is rejected with the same outcome as a well-formed but non-existent one

- **US:** TM-US-01
- **Given:** An authenticated User and a wallet they own
- **When:** A transaction is submitted with `category_id` `"not-a-real-id"`
- **Then:** The response is `404` `TRANSACTION_CATEGORY_NOT_FOUND`, identical to TC-10's response; nothing is persisted
- **AC:** EC-07, FR-06
- **Type:** integration

### TC-31: An EXPENSE amount exactly equal to the wallet's current balance is accepted, leaving the balance at exactly zero

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet with balance `1000.00` and an `EXPENSE`-typed category
- **When:** An `EXPENSE` transaction of `1000.00` is submitted
- **Then:** The response is `201`; the wallet's `balance` row now reads exactly `0.00`
- **AC:** EC-08, FR-11, BR-05
- **Type:** integration

### TC-32: An INCOME transaction is accepted even when the wallet's current balance is zero or negative

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet with balance `-50.00` (reachable per WM-US-01 EC-02) and an `INCOME`-typed category
- **When:** An `INCOME` transaction of `20.00` is submitted
- **Then:** The response is `201`; the wallet's `balance` row now reads `-30.00`
- **AC:** EC-09, FR-12, BR-05
- **Type:** integration

### TC-33: An EXPENSE transaction against a wallet whose balance is already zero or negative is rejected regardless of amount

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet with balance `0.00` and an `EXPENSE`-typed category
- **When:** An `EXPENSE` transaction of `0.01` (the smallest possible positive amount) is submitted
- **Then:** The response is `409` `TRANSACTION_INSUFFICIENT_BALANCE`; the wallet's balance is still `0.00`
- **AC:** EC-10, FR-11, BR-05
- **Type:** integration

### TC-34: A category-type mismatch takes priority over an independently-failing balance check in the same request

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet with balance `10.00` and owns a category typed `INCOME`
- **When:** An `EXPENSE` transaction of `500.00` is submitted against that wallet and that category — a request that would independently fail both the type-consistency check and the balance-sufficiency check
- **Then:** The response is `409` `TRANSACTION_CATEGORY_TYPE_MISMATCH` — never `TRANSACTION_INSUFFICIENT_BALANCE`, and never both; the wallet's balance is unchanged
- **AC:** EC-11, BR-02, FR-18 *(assertion technique per QF-06)*
- **Type:** integration

### TC-35: Two transactions with identical wallet, category, amount, and type are both accepted as independent ledger entries

- **US:** TM-US-01
- **Given:** An authenticated User who owns a wallet and an `EXPENSE`-typed category
- **When:** The same `EXPENSE` transaction of `25.00` against that wallet and category is submitted twice, back-to-back
- **Then:** Both responses are `201`, each with its own distinct `id`; two separate `transactions` rows exist, and the wallet's balance reflects both decrements
- **AC:** EC-12, FR-19
- **Type:** integration

### TC-36: Wallet ownership is checked before category ownership when both references are invalid in the same request

- **US:** TM-US-01
- **Given:** An authenticated User
- **When:** A transaction is submitted with a `wallet_id` matching no wallet at all and a `category_id` matching no category at all, in the same request
- **Then:** The response is `404` `TRANSACTION_WALLET_NOT_FOUND` — never `TRANSACTION_CATEGORY_NOT_FOUND`, and never both
- **AC:** EC-14, BR-02, FR-18 *(assertion technique per QF-06)*
- **Type:** integration

---

## TM-US-02: List Transactions

> **IDs in this section are local to TM-US-02** — except `TC-NN`, which continues this epic file's
> own numbering: TM-US-01 used `TC-01`…`TC-36`, so this story continues from `TC-37`. **`QF-NN` also
> continues here**, from `QF-09` (TM-US-01 used `QF-01`…`QF-08`). This is the first point in this
> epic file where the reset-vs-continue choice actually has to be made — TM-US-01 was the file's
> first story, so nothing distinguished the two conventions for it. This codebase currently has both
> conventions in active use: `specs/001-user-onboarding/test_cases.md` resets `QF-NN` per story
> (its own header, at each of UM-US-02 and UM-US-03, says so explicitly), while
> `specs/003-wallet-management/test_cases.md` continues it, reasoning explicitly from
> `artifact-templates/test-case-templates.md`'s own worked example — `PM-US-02`'s Quality Findings
> section there starts at `QF-08`, which only makes sense if a prior story (`PM-US-01`, not shown in
> that excerpt) already used `QF-01`…`QF-07` in the same file. Re-inspecting
> `test-case-templates.md` directly (not merely trusting WM-US-02's own citation of it) confirms
> this: the excerpt genuinely starts numbering at `QF-08`. Between the two existing conventions, this
> file adopts the **continuing** one — matching the template's own worked example directly, and
> matching this codebase's more recently-established precedent (WM-US-02, the same list-endpoint
> precedent story cited throughout this story's own `spec.md`/`plan.md`). Both are legitimate
> readings of `CLAUDE.md`'s ID schemes table, which names only `TC-NN` as continuous; this is simply
> the epic file where the choice is made explicit, the same way WM-US-02 made it explicit for its own
> file.

### Quality Findings

#### QF-09

**Description.** `plan.md` A4 orders transactions by `timestamp` descending, tie-broken by `id`
ascending. `TransactionCreate` accepts no client-supplied timestamp (TM-US-01 A5) — every
`timestamp` comes from `app.core.clock.utcnow()` at the moment the service runs — so a test that
creates several transactions in a normal, sequential loop would have their `timestamp` values land
in the *same* order as their creation calls, the same trap WM-US-02 QF-06 already identified for its
own sort key: such a test cannot distinguish "genuinely sorted by `timestamp`" from "happened to come
back in insertion/rowid order this one time," because the two orders coincide by construction.

**Impact.** Without deliberately decoupling creation order from timestamp order, a future change that
silently dropped the `ORDER BY` (returning rows in whatever order the database happens to produce)
could pass an order test that never exercised the one case where the two orders disagree.

**Recommendation.** `TC-50` monkeypatches `app.core.clock.utcnow` to a distinct, explicit instant
immediately before each of several creation calls, deliberately creating the transactions in an order
that does **not** match descending-timestamp order (e.g. create the earliest instant first, the
latest instant last), then asserts the list comes back ordered by the frozen instants — not by
creation sequence — the same "prove it against an independently-computable key, constructed
out-of-order" technique QF-06 used there, applied here to a real timestamp instead of an arbitrary id.

#### QF-10

**Description.** `plan.md` A2 requires the total-count query and the bounded page query in
`transaction_repo.list_owned()` to carry the identical join-plus-predicate — a join to `wallets`
rather than a single-table `WHERE`, which is a structurally different (and, per the dispatching
brief, structurally sharper) risk than WM-US-02's own single-column case (`test_cases.md` QF-05
there): a bug here could plausibly scope the join correctly for `items` while a differently-written
count query omits the join (or the predicate) entirely, or the reverse, and the two mistakes would
look different from each other in a way a single "check `items` only" or "check `total` only" test
would not catch.

**Impact.** A weak test suite could pass with `items` correctly scoped but `total` silently counting
every User's transactions system-wide (or vice versa) — exactly the "items look right, total quietly
means something else" failure QF-05 warned about for a single table, now possible in two independent
ways because two things (the join and the predicate) both have to be right in both queries.

**Recommendation.** `TC-49` seeds a second User's own wallet and transactions alongside the caller's,
and asserts `total` equals only the caller's own matching count, distinct from the combined
system-wide count — proving the *count* query is join-scoped, not merely the item query. `TC-72`
does the same for a **filter** rather than plain ownership: with a wallet filter applied, `total`
must equal only that wallet's matching count, not the caller's full cross-wallet total — proving the
count query applies the *same* filter predicate as the item query, not only the ownership predicate.

#### QF-11

**Description.** `plan.md` A3 requires a `wallet_id`/`category_id` filter that does not resolve to a
row the caller owns — whether absent altogether, malformed, or belonging to a different User — to
produce the *identical* empty result in every case. A test that only checks "some filter value that
doesn't match anything returns an empty list" would not prove the three sub-cases are actually
indistinguishable from one another, the same class of gap TM-US-01 QF-01 flagged for a create-time
reference, now applied to a filter parameter.

**Impact.** A future change that let a foreign-but-real wallet/category id produce a response
detectably different from a nonexistent one (even subtly — a different `message` string, a different
`details` shape) would leak whether a given id belongs to a real, different User, the exact
enumeration risk SEC-10 exists to prevent, while still passing a weaker test.

**Recommendation.** `TC-58` compares the full response body of a wallet filter naming a different
User's real wallet against `TC-57`'s response for a wallet filter naming nothing at all, and asserts
they are identical — not merely both empty. `TC-61` does the same comparison for a category filter
against `TC-60`. `TC-70`/`TC-71` extend the same comparison to a malformed (not well-formed
identifier) filter value, per EC-09/EC-10.

#### QF-12

**Description.** `plan.md` A2 deliberately omits a second join to `categories`, relying instead on
TM-US-01 BR-01's creation-time invariant that a transaction's `category_id` always already belongs to
the same User who owns its `wallet_id` — meaning no `transactions` row violating that invariant can
exist through the public API today. A test suite that never even attempts to construct such a row
cannot, by itself, distinguish "correctly relying on a real, enforced invariant" from "coincidentally
correct because nothing ever tried to break it."

**Impact.** If a future story ever allowed reassigning a wallet's or a category's owner (no such
story exists today), this design could silently start leaking transactions through a category filter
without any test here catching the change, because no test exercises the boundary the invariant is
actually protecting.

**Recommendation.** Accept the structural proof over a constructed counter-example, the same
"known coverage limit, accepted" pattern TM-US-01 QF-04/QF-06 and WM-US-02 QF-08 already use in this
codebase for a case the public API cannot construct. `TC-61` is the closest available witness: User
`B`'s own category is filtered by User `A`, while `B`'s own transactions (which legitimately combine
`B`'s wallet with `B`'s category) exist in the system at the same time — proving the wallet-ownership
join alone already excludes `B`'s transactions from `A`'s result, without needing a second join to
prove it. `plan.md` A2 records the standing dependency explicitly so a future story that touches
wallet/category ownership reassignment knows to revisit this reasoning.

#### QF-13

**Description.** `plan.md` A6 requires a date-range boundary with no explicit time zone offset to be
interpreted as UTC. A test asserting only "a date-range filter narrows the result" would not prove
*which* time zone a naive value is actually interpreted as — a server accidentally using local time,
or silently rejecting naive input instead of normalising it, could still pass a loosely-written test.

**Impact.** A regression here would not fail loudly (no exception, no obviously-wrong status code) —
it would silently shift which transactions a naive date boundary matches, a class of bug that is easy
to miss in review and hard to notice in production.

**Recommendation.** `TC-67` submits the same filter boundary twice — once with no offset, once with
an explicit `Z`/UTC offset representing the identical instant — and asserts both requests return the
identical result set, proving the naive form is interpreted as UTC rather than as any other zone.

### Acceptance Criteria Classification

No transaction-list screen exists in `mobile/` this round (`CLAUDE.md` §5 — the prototype covers only
UM-US-01's invite screen), and no SRS UXR names one, the same basis TM-US-01/WM-US-02 each used for
their own all-`[API]` classification.

| AC/EC | Title | Label | Rationale |
|---|---|---|---|
| AC-01 | Successfully list every transaction belonging to every wallet the caller owns | **[API]** | No UI surface exists or is named by any UXR this round |
| AC-02 | Return an empty list for a User with no transactions yet | **[API]** | Backend response-shape contract |
| AC-03 | Deny access to unauthenticated callers | **[API]** | Backend authorization contract |
| AC-04 | Bound and paginate the result by default | **[API]** | Query-parameter contract; unanchored to any SRS scenario (no Gherkin exists for this story) |
| AC-05 | Accept an explicit page and page size within range | **[API]** | Same reasoning as AC-04 |
| AC-06 | Reject a page or page size outside the allowed range | **[API]** | 422 `VALIDATION_ERROR` — backend validation concern |
| AC-07 | A User only ever sees transactions belonging to wallets they own | **[API]** | Persistence/ownership contract; bounded by QF-10 |
| AC-08 | Return the list in a stable, most-recent-first order | **[API]** | Backend contract; bounded by QF-09 |
| AC-09 | Reuse the documented per-transaction fields, wrapped in a paginated envelope | **[API]** | Response-payload contract |
| AC-10 | Narrow the list to one wallet | **[API]** | Query-parameter contract; bounded by QF-10 |
| AC-11 | A wallet filter that does not resolve to the caller's own wallet yields an empty result | **[API]** | Persistence/ownership contract; bounded by QF-11 |
| AC-12 | Narrow the list to one category | **[API]** | Query-parameter contract |
| AC-13 | A category filter that does not resolve to the caller's own category yields an empty result | **[API]** | Persistence/ownership contract; bounded by QF-11, QF-12 |
| AC-14 | Narrow the list to a date range | **[API]** | Query-parameter contract; bounded by QF-13 |
| AC-15 | Reject a date range whose start is after its end | **[API]** | 422 `VALIDATION_ERROR` — backend validation concern |
| AC-16 | Filters narrow the result together, never separately | **[API]** | Backend combination-semantics contract |
| EC-01 | A page number beyond the last available page | **[API]** | Boundary value |
| EC-02 | Page size at the exact maximum | **[API]** | Boundary value |
| EC-03 | More transactions than fit on one page | **[API]** | Cross-page completeness; bounded by QF-09 |
| EC-04 | A caller whose role is ADMIN, who also owns wallets and transactions | **[API]** | Ownership contract independent of role |
| EC-05 | Only a start of range is named | **[API]** | Query-parameter contract |
| EC-06 | Only an end of range is named | **[API]** | Query-parameter contract |
| EC-07 | A named start of range equal to a named end of range | **[API]** | Boundary value |
| EC-08 | Two transactions recorded at the same instant | **[API]** | Backend tie-break contract; bounded by QF-09 |
| EC-09 | A wallet filter value that is not a well-formed identifier | **[API]** | Backend rule (no separate format validation); bounded by QF-11 |
| EC-10 | A category filter value that is not a well-formed identifier | **[API]** | Backend rule (no separate format validation); bounded by QF-11 |
| EC-11 | A caller who owns more than one wallet, each with its own transactions | **[API]** | Cross-wallet aggregation contract |

### Coverage Matrix

| AC/EC | Label | Integration TC(s) | E2E TC(s) |
|---|---|---|---|
| AC-01 | [API] | TC-37 | — |
| AC-02 | [API] | TC-39 | — |
| AC-03 | [API] | TC-40, TC-41 | — |
| AC-04 | [API] | TC-42 | — |
| AC-05 | [API] | TC-43 | — |
| AC-06 | [API] | TC-44, TC-45, TC-46 | — |
| AC-07 | [API] | TC-48, TC-49 | — |
| AC-08 | [API] | TC-50 | — |
| AC-09 | [API] | TC-38 | — |
| AC-10 | [API] | TC-56, TC-72 | — |
| AC-11 | [API] | TC-57, TC-58 | — |
| AC-12 | [API] | TC-59 | — |
| AC-13 | [API] | TC-60, TC-61 | — |
| AC-14 | [API] | TC-62, TC-67 | — |
| AC-15 | [API] | TC-66 | — |
| AC-16 | [API] | TC-68, TC-69 | — |
| EC-01 | [API] | TC-53 | — |
| EC-02 | [API] | TC-46, TC-47 | — |
| EC-03 | [API] | TC-52 | — |
| EC-04 | [API] | TC-54 | — |
| EC-05 | [API] | TC-63 | — |
| EC-06 | [API] | TC-64 | — |
| EC-07 | [API] | TC-65 | — |
| EC-08 | [API] | TC-51 | — |
| EC-09 | [API] | TC-57, TC-70 | — |
| EC-10 | [API] | TC-60, TC-71 | — |
| EC-11 | [API] | TC-55 | — |

> Every AC and EC has at least one integration TC. There is no `[BOTH]` or `[UI]` row — no
> transaction-list screen exists this round, and none is named by any SRS UXR. **Known coverage
> limits, accepted:** the category-ownership-via-transitivity design (`plan.md` A2) cannot be
> directly counter-example-tested because the public API cannot construct a transaction whose wallet
> and category belong to different Users — proven structurally instead (QF-12), mirroring TM-US-01
> QF-04/QF-06 and WM-US-02 QF-08's own accepted limits in this codebase. This story never touches
> `budgets` (spec *Out of scope*), so no test here exercises the SDS §2.4.3 Budget Monitoring State
> machine.

### Test Implementation Map *(filled at step 4)*

Populated at the Implement dispatch (steps 4–6), the same way TM-US-01's own map above was. All 36
test cases are implemented in `backend/tests/integration/test_tm_us_02_list_transactions.py`, one
test per `TC-NN`, each carrying its `TC-NN` id in its docstring — `TC-44`/`TC-45` are each one
`@pytest.mark.parametrize`d function covering three sub-cases (`0`, `-1`, `"abc"`), so the pytest
node id column lists all three per row. Tests were written first and observed failing with `405
Method Not Allowed` against the pre-implementation code (the `GET` route did not exist yet — same
red state WM-US-02's own dispatch found), confirmed by temporarily stashing the implementation
changes and running the suite before restoring them; then implemented until green. Full suite run:
`342 passed` (302 pre-existing + 40 of them this story's, since `TC-44`/`TC-45`'s parametrization
each contributes 3 pytest items for 1 `TC-NN`), `ruff check`/`ruff format --check` clean, `mypy app`
clean, coverage 100% on every file this story added or modified
(`app/models/transaction.py`, `app/schemas/transaction.py`, `app/repositories/transaction_repo.py`,
`app/services/transaction_service.py`, `app/api/v1/transactions.py`), 99% overall. Live `curl`
walkthrough against a running server executed per CLAUDE.md §2 Step 5 with two distinct real users —
see the Implement dispatch's gate report for the full request/response transcript. No failures were
found at Verification; nothing here required root-causing.

| TC | pytest node id | Result |
|---|---|---|
| TC-37 | `tests/integration/test_tm_us_02_list_transactions.py::test_authenticated_user_lists_every_transaction_belonging_to_every_wallet_they_own` | PASS |
| TC-38 | `tests/integration/test_tm_us_02_list_transactions.py::test_response_item_exposes_exactly_seven_fields_wrapped_in_paginated_envelope` | PASS |
| TC-39 | `tests/integration/test_tm_us_02_list_transactions.py::test_user_with_no_transactions_yet_receives_empty_list_and_zero_total` | PASS |
| TC-40 | `tests/integration/test_tm_us_02_list_transactions.py::test_unauthenticated_or_invalid_credential_caller_is_denied_with_401` | PASS |
| TC-41 | `tests/integration/test_tm_us_02_list_transactions.py::test_credentials_are_evaluated_before_any_query_parameter` | PASS |
| TC-42 | `tests/integration/test_tm_us_02_list_transactions.py::test_default_page_is_1_of_size_25_with_accurate_total` | PASS |
| TC-43 | `tests/integration/test_tm_us_02_list_transactions.py::test_explicit_page_and_page_size_within_range_return_that_page_and_accurate_total` | PASS |
| TC-44 | `tests/integration/test_tm_us_02_list_transactions.py::test_a_non_positive_or_non_integer_page_is_rejected_with_422[0]`, `[-1]`, `[abc]` | PASS |
| TC-45 | `tests/integration/test_tm_us_02_list_transactions.py::test_a_non_positive_or_non_integer_page_size_is_rejected_with_422[0]`, `[-1]`, `[abc]` | PASS |
| TC-46 | `tests/integration/test_tm_us_02_list_transactions.py::test_a_page_size_above_the_maximum_is_rejected_with_422` | PASS |
| TC-47 | `tests/integration/test_tm_us_02_list_transactions.py::test_a_page_size_of_exactly_100_is_accepted` | PASS |
| TC-48 | `tests/integration/test_tm_us_02_list_transactions.py::test_a_user_only_ever_sees_transactions_belonging_to_wallets_they_own` | PASS |
| TC-49 | `tests/integration/test_tm_us_02_list_transactions.py::test_reported_total_counts_only_callers_own_transactions_even_when_smaller` | PASS |
| TC-50 | `tests/integration/test_tm_us_02_list_transactions.py::test_list_is_returned_most_recently_recorded_first_proven_against_out_of_order_creation` | PASS |
| TC-51 | `tests/integration/test_tm_us_02_list_transactions.py::test_two_transactions_recorded_at_the_same_instant_have_deterministic_relative_order` | PASS |
| TC-52 | `tests/integration/test_tm_us_02_list_transactions.py::test_paging_through_every_page_returns_every_transaction_exactly_once_in_stable_order` | PASS |
| TC-53 | `tests/integration/test_tm_us_02_list_transactions.py::test_a_page_beyond_the_last_available_page_returns_empty_list_with_accurate_total` | PASS |
| TC-54 | `tests/integration/test_tm_us_02_list_transactions.py::test_admin_role_caller_who_also_owns_transactions_sees_only_their_own` | PASS |
| TC-55 | `tests/integration/test_tm_us_02_list_transactions.py::test_transactions_from_every_wallet_the_caller_owns_appear_together_correctly_ordered` | PASS |
| TC-56 | `tests/integration/test_tm_us_02_list_transactions.py::test_a_wallet_filter_narrows_the_list_to_exactly_that_wallets_transactions` | PASS |
| TC-57 | `tests/integration/test_tm_us_02_list_transactions.py::test_a_wallet_filter_matching_no_wallet_at_all_returns_an_empty_result_not_an_error` | PASS |
| TC-58 | `tests/integration/test_tm_us_02_list_transactions.py::test_a_wallet_filter_naming_a_different_users_real_wallet_matches_tc_57` | PASS |
| TC-59 | `tests/integration/test_tm_us_02_list_transactions.py::test_a_category_filter_narrows_the_list_to_exactly_that_categorys_transactions` | PASS |
| TC-60 | `tests/integration/test_tm_us_02_list_transactions.py::test_a_category_filter_matching_no_category_at_all_returns_an_empty_result_not_an_error` | PASS |
| TC-61 | `tests/integration/test_tm_us_02_list_transactions.py::test_a_category_filter_naming_a_different_users_real_category_matches_tc_60` | PASS |
| TC-62 | `tests/integration/test_tm_us_02_list_transactions.py::test_a_date_range_filter_with_both_bounds_narrows_to_transactions_recorded_within_it` | PASS |
| TC-63 | `tests/integration/test_tm_us_02_list_transactions.py::test_a_date_range_with_only_a_start_bound_includes_every_transaction_from_it_onward` | PASS |
| TC-64 | `tests/integration/test_tm_us_02_list_transactions.py::test_a_date_range_with_only_an_end_bound_includes_every_transaction_up_to_it` | PASS |
| TC-65 | `tests/integration/test_tm_us_02_list_transactions.py::test_a_date_range_whose_start_equals_its_end_includes_the_transaction_at_that_instant` | PASS |
| TC-66 | `tests/integration/test_tm_us_02_list_transactions.py::test_a_date_range_whose_start_is_after_its_end_is_rejected_with_422` | PASS |
| TC-67 | `tests/integration/test_tm_us_02_list_transactions.py::test_a_date_bound_with_no_explicit_time_zone_is_interpreted_as_utc` | PASS |
| TC-68 | `tests/integration/test_tm_us_02_list_transactions.py::test_a_wallet_filter_and_a_category_filter_combine_to_narrow_to_matching_both` | PASS |
| TC-69 | `tests/integration/test_tm_us_02_list_transactions.py::test_a_wallet_filter_and_a_date_range_filter_combine_to_narrow_to_matching_both` | PASS |
| TC-70 | `tests/integration/test_tm_us_02_list_transactions.py::test_a_malformed_wallet_filter_value_matches_tc_57` | PASS |
| TC-71 | `tests/integration/test_tm_us_02_list_transactions.py::test_a_malformed_category_filter_value_matches_tc_60` | PASS |
| TC-72 | `tests/integration/test_tm_us_02_list_transactions.py::test_a_wallet_filter_scopes_the_total_to_that_wallet_not_the_callers_full_total` | PASS |

---

### TC-37: An authenticated User lists every transaction belonging to every wallet they own — 200 with all transactions and an accurate total

- **US:** TM-US-02
- **Given:** An authenticated User who owns one wallet and one category, with three transactions logged against that wallet via `POST /api/v1/transactions`
- **When:** The User requests the list of transactions with no filter applied
- **Then:** The response is `200`; `items` contains all three transactions, each carrying `id`, `wallet_id` equal to the caller's wallet, `category_id`, `amount`, `type`, `timestamp`, and `note`; `total` is `3`
- **AC:** AC-01, FR-01, FR-02, FR-06, FR-15
- **Type:** integration

### TC-38: The response item exposes exactly the seven documented fields, wrapped in the paginated envelope

- **US:** TM-US-02
- **Given:** An authenticated User with one existing transaction
- **When:** The User requests the list of transactions
- **Then:** The response is `200`; the top-level body exposes exactly the keys `items`, `total`, `page`, `page_size`; each entry in `items` exposes **exactly** the keys `id`, `wallet_id`, `category_id`, `amount`, `type`, `timestamp`, `note` — no more, and in particular no field this story invents
- **AC:** AC-01, AC-09, FR-02, PF-03
- **Type:** integration

### TC-39: A User with no transactions yet receives an empty list and a zero total

- **US:** TM-US-02
- **Given:** An authenticated User who owns a wallet and a category, but no transactions
- **When:** The User requests the list of transactions
- **Then:** The response is `200`, not an error; `items` is an empty list and `total` is `0`
- **AC:** AC-02, FR-01
- **Type:** integration

### TC-40: An unauthenticated or invalid-credential caller is denied with 401

- **US:** TM-US-02
- **Given:** A caller presenting no `Authorization` header, and separately a caller presenting an expired token
- **When:** Each attempts to list transactions
- **Then:** Both responses are `401` with `error_code` `NOT_AUTHENTICATED`; no `items` are returned
- **AC:** AC-03, FR-03
- **Type:** integration

### TC-41: Credentials are evaluated before any query parameter

- **US:** TM-US-02
- **Given:** A caller presenting no credentials
- **When:** The list is requested with an out-of-range `page` value (`page=0`)
- **Then:** The response is `401` `NOT_AUTHENTICATED`, not `422` — mirrors WM-US-02 TC-27/UM-US-03 TC-61's ordering
- **AC:** AC-03, FR-03
- **Type:** integration

### TC-42: The default page is 1 of size 25, with an accurate total

- **US:** TM-US-02
- **Given:** An authenticated User and three existing transactions they own
- **When:** The list is requested with no `page` or `page_size` supplied
- **Then:** The response is `200`; `page` is `1`, `page_size` is `25`, `items` contains all three transactions, and `total` is `3`
- **AC:** AC-04, FR-04, FR-06
- **Type:** integration

### TC-43: An explicit page and page size within range return that page and an accurate total

- **US:** TM-US-02
- **Given:** An authenticated User and five transactions they own
- **When:** The list is requested with `page=2` and `page_size=2`
- **Then:** The response is `200`; `page` is `2`, `page_size` is `2`, `items` contains exactly two of the User's own transactions, and `total` is `5`
- **AC:** AC-05, FR-04, FR-06
- **Type:** integration

### TC-44: A `page` that is not a positive integer is rejected with 422

- **US:** TM-US-02
- **Given:** An authenticated User
- **When:** The list is requested with `page` set to each of `0`, `-1`, and `"abc"` in turn
- **Then:** Each response is `422` with `error_code` `VALIDATION_ERROR` and a `details.fields` entry locating `page`; no `items` are returned
- **AC:** AC-06, FR-05, BR-02
- **Type:** integration

### TC-45: A `page_size` that is not a positive integer is rejected with 422

- **US:** TM-US-02
- **Given:** An authenticated User
- **When:** The list is requested with `page_size` set to each of `0`, `-1`, and `"abc"` in turn
- **Then:** Each response is `422` with `error_code` `VALIDATION_ERROR` and a `details.fields` entry locating `page_size`; no `items` are returned
- **AC:** AC-06, FR-05, BR-02
- **Type:** integration

### TC-46: A `page_size` above the maximum is rejected with 422

- **US:** TM-US-02
- **Given:** An authenticated User
- **When:** The list is requested with `page_size=101`
- **Then:** The response is `422` `VALIDATION_ERROR` identifying `page_size`; the request is not silently capped at 100
- **AC:** AC-06, EC-02, FR-05, BR-02
- **Type:** integration

### TC-47: A `page_size` of exactly 100 is accepted

- **US:** TM-US-02
- **Given:** An authenticated User
- **When:** The list is requested with `page_size=100`
- **Then:** The response is `200` — the cap is a ceiling, not a target: 100 is honoured, only 101 is rejected (TC-46)
- **AC:** EC-02, FR-05
- **Type:** integration

### TC-48: A User only ever sees transactions belonging to wallets they own, never another User's

- **US:** TM-US-02
- **Given:** Two authenticated Users, `A` (one wallet, two transactions) and `B` (one wallet, three transactions)
- **When:** `A` requests the list of transactions
- **Then:** The response is `200`; `items` contains exactly `A`'s two transactions — none of `B`'s three — and `total` is `2`, not `5`
- **AC:** AC-07, FR-07, FR-15, BR-01, BR-04 *(assertion technique per QF-10)*
- **Type:** integration

### TC-49: The reported total counts only the caller's own matching transactions, even when it is the smaller number

- **US:** TM-US-02
- **Given:** Two authenticated Users, `A` (a wallet with no transactions) and `B` (a wallet with four transactions)
- **When:** `A` requests the list of transactions
- **Then:** The response is `200`; `items` is empty and `total` is `0` — not `4`, and not any count reflecting `B`'s transactions
- **AC:** AC-02, AC-07, FR-07, FR-15, BR-04 *(assertion technique per QF-10)*
- **Type:** integration

### TC-50: The list is returned most-recently-recorded first, proven against deliberately out-of-order creation

- **US:** TM-US-02
- **Given:** An authenticated User who creates three transactions while the system clock is monkeypatched to three distinct, explicit instants in **non-chronological creation order** — the middle instant created first, the earliest instant created second, the latest instant created third
- **When:** The User requests the list of transactions
- **Then:** The response is `200`; `items` are ordered latest-instant, middle-instant, earliest-instant — matching the frozen timestamps' own chronological order, not the order the three creation calls were made in
- **AC:** AC-08, FR-08, BR-03 *(assertion technique per QF-09)*
- **Type:** integration

### TC-51: Two transactions recorded at the same instant are placed in a deterministic relative order

- **US:** TM-US-02
- **Given:** An authenticated User who creates two transactions while the system clock is monkeypatched to return the identical instant for both creation calls
- **When:** The User requests the list of transactions twice
- **Then:** Both responses place the two tied transactions in the identical relative order to each other — the one with the lexicographically smaller `id` first — on both requests
- **AC:** AC-08, EC-08, BR-03
- **Type:** integration

### TC-52: Paging through every page returns every transaction exactly once, in stable order

- **US:** TM-US-02
- **Given:** An authenticated User and five transactions they own, recorded at five distinct, known instants
- **When:** Every page is fetched in turn with `page_size=2` (`page=1`, `page=2`, `page=3`)
- **Then:** The concatenation of all three pages' `items` contains every one of the five transactions exactly once, with no duplicate and no gap, in the same most-recent-first order TC-50 established, stable across the page boundaries
- **AC:** EC-03, FR-08, BR-03
- **Type:** integration

### TC-53: A page beyond the last available page returns an empty list with the accurate total

- **US:** TM-US-02
- **Given:** An authenticated User and three transactions they own
- **When:** The list is requested with `page=5` and `page_size=25`
- **Then:** The response is `200`, not `404`; `items` is an empty list and `total` is still `3`
- **AC:** EC-01, FR-06
- **Type:** integration

### TC-54: An ADMIN-role caller who also owns wallets and transactions sees only their own through this endpoint

- **US:** TM-US-02
- **Given:** An authenticated User whose role is `ADMIN`, owning one wallet with one transaction, and a second User (any role) who owns a wallet with two transactions of their own
- **When:** The ADMIN requests the list of transactions
- **Then:** The response is `200`; `items` contains exactly the ADMIN's own one transaction — never either of the other User's — and `total` is `1`
- **AC:** EC-04, FR-15, BR-01
- **Type:** integration

### TC-55: Transactions from every wallet the caller owns appear together in one combined, correctly-ordered list

- **US:** TM-US-02
- **Given:** An authenticated User who owns two wallets, with transactions recorded against each at interleaved instants (not grouped by wallet)
- **When:** The User requests the list of transactions with no filter applied
- **Then:** The response is `200`; `items` contains every transaction from both wallets, ordered most-recently-recorded first across the combined set — not grouped by wallet and not limited to one wallet
- **AC:** AC-01, EC-11, FR-01, FR-08
- **Type:** integration

### TC-56: A wallet filter narrows the list to exactly that wallet's transactions

- **US:** TM-US-02
- **Given:** An authenticated User who owns two wallets, each with transactions logged against it
- **When:** The list is requested naming one of those wallets' `wallet_id`
- **Then:** The response is `200`; `items` contains only the transactions belonging to the named wallet, and `total` counts only that wallet's transactions
- **AC:** AC-10, FR-09
- **Type:** integration

### TC-57: A wallet filter matching no wallet at all returns an empty result, not an error

- **US:** TM-US-02
- **Given:** An authenticated User with existing transactions
- **When:** The list is requested naming a `wallet_id` that matches no wallet in the system
- **Then:** The response is `200`, not `404`; `items` is an empty list and `total` is `0`
- **AC:** AC-11, EC-09, FR-09, BR-05
- **Type:** integration

### TC-58: A wallet filter naming a different User's real wallet returns the identical outcome as TC-57

- **US:** TM-US-02
- **Given:** Two authenticated Users `A` and `B`, where `B` owns a wallet with transactions and `A` owns a wallet with transactions of their own
- **When:** `A` requests the list naming `B`'s `wallet_id`
- **Then:** The response is `200`; its `items`, `total`, `page`, and `page_size` are identical to TC-57's response — not merely both empty
- **AC:** AC-11, FR-09, BR-05 *(assertion technique per QF-11)*
- **Type:** integration

### TC-59: A category filter narrows the list to exactly that category's transactions

- **US:** TM-US-02
- **Given:** An authenticated User who owns two categories, each with transactions logged under it
- **When:** The list is requested naming one of those categories' `category_id`
- **Then:** The response is `200`; `items` contains only the transactions logged under the named category, and `total` counts only that category's transactions
- **AC:** AC-12, FR-10
- **Type:** integration

### TC-60: A category filter matching no category at all returns an empty result, not an error

- **US:** TM-US-02
- **Given:** An authenticated User with existing transactions
- **When:** The list is requested naming a `category_id` that matches no category in the system
- **Then:** The response is `200`, not `404`; `items` is an empty list and `total` is `0`
- **AC:** AC-13, EC-10, FR-10, BR-05
- **Type:** integration

### TC-61: A category filter naming a different User's real category returns the identical outcome as TC-60, even though that User's own transactions exist under it

- **US:** TM-US-02
- **Given:** Two authenticated Users `A` and `B`, where `B` owns a category with `B`'s own transactions logged under it (combining `B`'s own wallet and `B`'s own category), and `A` owns a wallet and transactions of their own
- **When:** `A` requests the list naming `B`'s `category_id`
- **Then:** The response is `200`; its `items`, `total`, `page`, and `page_size` are identical to TC-60's response — proving `B`'s transactions under that category never reach `A`'s result even though they genuinely exist
- **AC:** AC-13, FR-10, BR-05 *(assertion technique per QF-11, QF-12)*
- **Type:** integration

### TC-62: A date-range filter with both bounds narrows the list to transactions recorded within it

- **US:** TM-US-02
- **Given:** An authenticated User with three transactions recorded at three distinct, known instants, only the middle one falling inside a chosen range
- **When:** The list is requested with `date_from`/`date_to` naming that range
- **Then:** The response is `200`; `items` contains only the one transaction recorded inside the range, and `total` is `1`
- **AC:** AC-14, FR-11
- **Type:** integration

### TC-63: A date-range filter with only a start bound includes every transaction from that instant onward

- **US:** TM-US-02
- **Given:** An authenticated User with transactions recorded before and after a chosen instant
- **When:** The list is requested with only `date_from` naming that instant
- **Then:** The response is `200`; `items` contains every transaction recorded at or after that instant, and none recorded before it
- **AC:** EC-05, FR-11
- **Type:** integration

### TC-64: A date-range filter with only an end bound includes every transaction up to that instant

- **US:** TM-US-02
- **Given:** An authenticated User with transactions recorded before and after a chosen instant
- **When:** The list is requested with only `date_to` naming that instant
- **Then:** The response is `200`; `items` contains every transaction recorded at or before that instant, and none recorded after it
- **AC:** EC-06, FR-11
- **Type:** integration

### TC-65: A date range whose start equals its end includes a transaction recorded at exactly that instant

- **US:** TM-US-02
- **Given:** An authenticated User with one transaction recorded at a known instant
- **When:** The list is requested with `date_from` and `date_to` both naming that exact instant
- **Then:** The response is `200`; `items` contains the transaction recorded at that instant — the range is not treated as empty or invalid
- **AC:** EC-07, FR-11, BR-06
- **Type:** integration

### TC-66: A date range whose start is after its end is rejected with 422

- **US:** TM-US-02
- **Given:** An authenticated User
- **When:** The list is requested with `date_from` later than `date_to`
- **Then:** The response is `422` `VALIDATION_ERROR` with a `details.fields` entry locating `date_to`; no `items` are returned
- **AC:** AC-15, FR-12, BR-06
- **Type:** integration

### TC-67: A date bound with no explicit time zone is interpreted as UTC

- **US:** TM-US-02
- **Given:** An authenticated User with one transaction recorded at a known UTC instant
- **When:** The list is requested twice with a `date_from`/`date_to` range around that instant — once expressed with no time zone offset, once expressed with an explicit UTC (`Z`) offset representing the identical instant
- **Then:** Both responses return the identical `items` and `total` — the naive form matches the same transactions as its explicit-UTC equivalent
- **AC:** AC-14, FR-13, BR-06 *(assertion technique per QF-13)*
- **Type:** integration

### TC-68: A wallet filter and a category filter combine to narrow the result to transactions matching both

- **US:** TM-US-02
- **Given:** An authenticated User who owns two wallets and two categories, with a transaction that matches one wallet and one category, and other transactions that match only one of the two
- **When:** The list is requested naming both that wallet's `wallet_id` and that category's `category_id`
- **Then:** The response is `200`; `items` contains only the transaction matching both filters — never one matching only the wallet or only the category
- **AC:** AC-16, FR-14, BR-07
- **Type:** integration

### TC-69: A wallet filter and a date-range filter combine to narrow the result to transactions matching both

- **US:** TM-US-02
- **Given:** An authenticated User who owns two wallets, with transactions recorded at various instants against each
- **When:** The list is requested naming one wallet's `wallet_id` together with a date range that would separately match transactions in the *other* wallet too
- **Then:** The response is `200`; `items` contains only the named wallet's transactions that also fall inside the named range — never a transaction from the other wallet, even one recorded inside the same range
- **AC:** AC-16, FR-14, BR-07
- **Type:** integration

### TC-70: A wallet filter value that is not a well-formed identifier returns the same empty outcome as one that is well-formed but nonexistent

- **US:** TM-US-02
- **Given:** An authenticated User with existing transactions
- **When:** The list is requested with `wallet_id` `"not-a-real-id"`
- **Then:** The response is `200`, identical to TC-57's response; `items` is an empty list and `total` is `0`
- **AC:** EC-09, FR-09 *(assertion technique per QF-11)*
- **Type:** integration

### TC-71: A category filter value that is not a well-formed identifier returns the same empty outcome as one that is well-formed but nonexistent

- **US:** TM-US-02
- **Given:** An authenticated User with existing transactions
- **When:** The list is requested with `category_id` `"not-a-real-id"`
- **Then:** The response is `200`, identical to TC-60's response; `items` is an empty list and `total` is `0`
- **AC:** EC-10, FR-10 *(assertion technique per QF-11)*
- **Type:** integration

### TC-72: A wallet filter scopes the reported total to that wallet, not the caller's full cross-wallet total

- **US:** TM-US-02
- **Given:** An authenticated User who owns two wallets, one with two transactions and the other with three
- **When:** The list is requested naming the two-transaction wallet's `wallet_id`
- **Then:** The response is `200`; `total` is `2` — not `5`, the caller's combined cross-wallet total — proving the count query applies the same wallet filter the item query does
- **AC:** AC-10, FR-07 *(assertion technique per QF-10)*
- **Type:** integration
