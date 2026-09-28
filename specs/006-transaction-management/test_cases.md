# Test Cases: Transaction Management (TM)

> **Feature:** SRS §6 Feature-06 · SDS §5.6 (TM)
> **Spec:** [spec.md](spec.md) · **Plan:** [plan.md](plan.md)
> **Stories in this file:** TM-US-01 *(TC-01…TC-36)*

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
