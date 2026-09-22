# Test Cases: Wallet Management (WM)

> **Feature:** SRS §6 Feature-03 · SDS §5.3 (WM)
> **Spec:** [spec.md](spec.md) · **Plan:** [plan.md](plan.md)
> **Stories in this file:** WM-US-01 *(TC-01…TC-22)*

---

## WM-US-01: Create a Wallet

### Quality Findings

Problems found while deriving test cases from `spec.md` and `plan.md`. Each one changes how a criterion can be asserted, so it is recorded rather than worked around silently.

#### QF-01

**Description.** AC-10 requires the wallet's owner to be "determined solely from the caller's own identity and never from any value in the request payload." `plan.md` A7 makes this true by construction — `WalletCreate` declares no `user_id` field at all — but a test that only checks the *created* wallet's `user_id` equals the caller's id would not distinguish "the field doesn't exist" from "the field exists and was correctly overridden."

**Impact.** A weaker test could pass even if a future change accidentally added a `user_id` field to `WalletCreate` and wired it through unchecked.

**Recommendation.** `TC-17` asserts both halves: the wallet created through a normal request is owned by the caller, **and** a request that additionally includes an unexpected `user_id` key naming a different, real user in its JSON body still creates a wallet owned by the caller, not by the named other user — the extra key is silently ignored, never honoured.

#### QF-02

**Description.** AC-09 requires an over-precise `initial_balance` to be rejected, not rounded. The rejection is a Pydantic-native `decimal_max_places` constraint (`plan.md` A3), not a hand-written check, so the risk is asserting the wrong thing: a test could check only that *some* `422` came back without confirming which field it names, and a future refactor could silently swap in a rounding behaviour that also happens to return `422` for unrelated reasons.

**Impact.** A loosely-written assertion would not actually prove precision is preserved rather than silently rounded elsewhere before validation runs.

**Recommendation.** `TC-13` asserts the `422` response's `details` names the `initial_balance` field specifically, and — for the case where rounding could plausibly have been applied instead — that no `wallets` row was created at all, so there is no rounded value to find.

#### QF-03

**Description.** `plan.md` A1 records that `type` is deliberately unconstrained beyond a length bound — there is no enumerated vocabulary to validate against, because none exists in either reference document. This means no test can assert a full, closed set of accepted values.

**Impact.** Exhaustively testing "every valid type" is not possible, and attempting it would silently smuggle in a vocabulary nobody specified.

**Recommendation.** `TC-01`/`TC-02` use the Gherkin's own example (`"BANK"`) for the happy path, and `TC-22` separately proves a value **outside** both reference documents' examples (`"Piggy Bank"`) is still accepted — demonstrating the bound is length-only, not membership-based, without asserting a fabricated complete list.

#### QF-04

**Description.** `plan.md` A5 records that `wallets` has no `created_at` column, unlike every other table this codebase has built so far. This is a genuine gap in the SDS ERD, not a choice this story is empowered to fix.

**Impact.** No test in this file can assert an ordering guarantee, a "most recent wallet" query, or a `created_at` field on `WalletRead`, because none of those exist yet.

**Recommendation.** No test case asserts anything about wallet ordering or creation timestamps. `TC-18`'s exact-field-set assertion is written to *positively* confirm `created_at` is absent from the response, so a future accidental addition (without the ERD being aligned first) would be caught rather than silently welcomed.

### Acceptance Criteria Classification

No wallet-creation screen exists in `mobile/` this round, and no SRS UXR names one (unlike UM-US-01/02, where UXR-04 at least conceptually covers the deferred onboarding screen). Every row below is `[API]`.

| AC/EC | Title | Label | Rationale |
|---|---|---|---|
| AC-01 | Successfully create a wallet with all mandatory inputs | **[API]** | No UI surface exists or is named by any UXR this round |
| AC-02 | Deny access to unauthenticated callers | **[API]** | Backend authorization contract |
| AC-03 | Reject a missing or blank wallet name | **[API]** | Payload validation |
| AC-04 | Reject a wallet name exceeding the maximum length | **[API]** | Payload validation |
| AC-05 | Reject a missing or blank wallet type | **[API]** | Payload validation |
| AC-06 | Reject a wallet type exceeding the maximum length | **[API]** | Payload validation |
| AC-07 | Reject a malformed currency value | **[API]** | Payload validation |
| AC-08 | Reject a missing initial balance | **[API]** | Payload validation |
| AC-09 | Reject an over-precise initial balance | **[API]** | Payload validation; bounded by QF-02 |
| AC-10 | A created wallet always belongs to the submitting User | **[API]** | Persistence/ownership contract; bounded by QF-01 |
| AC-11 | Return exactly the documented wallet fields | **[API]** | Response-payload contract; bounded by QF-04 |
| EC-01 | Initial balance of exactly zero | **[API]** | Boundary value |
| EC-02 | Negative initial balance | **[API]** | Backend rule (absence of a sign constraint) |
| EC-03 | Currency submitted in lowercase or mixed case | **[API]** | Payload validation |
| EC-04 | Wallet name with surrounding whitespace | **[API]** | Persistence-shape (trimming) |
| EC-05 | A wallet type outside either document's own examples | **[API]** | Backend rule; bounded by QF-03 |
| EC-06 | More than one validation failure in a single submission | **[API]** | Backend validation-grouping contract |
| EC-07 | Two wallets with the same name for the same User | **[API]** | Backend rule (absence of a uniqueness constraint) |
| EC-08 | Initial balance exceeding the `DECIMAL(15,2)` total digit width | **[API]** | Payload validation, distinct from AC-09's decimal-places check |

### Coverage Matrix

| AC/EC | Label | Integration TC(s) | E2E TC(s) |
|---|---|---|---|
| AC-01 | [API] | TC-01, TC-02 | — |
| AC-02 | [API] | TC-03 | — |
| AC-03 | [API] | TC-04, TC-05 | — |
| AC-04 | [API] | TC-06 | — |
| AC-05 | [API] | TC-07, TC-08 | — |
| AC-06 | [API] | TC-09 | — |
| AC-07 | [API] | TC-10, TC-11 | — |
| AC-08 | [API] | TC-12 | — |
| AC-09 | [API] | TC-13 | — |
| AC-10 | [API] | TC-17 | — |
| AC-11 | [API] | TC-18 | — |
| EC-01 | [API] | TC-15 | — |
| EC-02 | [API] | TC-16 | — |
| EC-03 | [API] | TC-11 | — |
| EC-04 | [API] | TC-05, TC-21 | — |
| EC-05 | [API] | TC-22 | — |
| EC-06 | [API] | TC-20 | — |
| EC-07 | [API] | TC-19 | — |
| EC-08 | [API] | TC-14 | — |

> Every AC and EC has at least one integration TC. There is no `[BOTH]` or `[UI]` row — no wallet-creation screen exists this round, and none is named by any SRS UXR (unlike UM-US-01/02, which at least deferred against UXR-04). **Known coverage limits, accepted:** `type`'s bound is length-only, not membership-based, so no test asserts a closed set of valid values (QF-03); `wallets` has no `created_at`, so no ordering or timestamp assertion is possible (QF-04).

### Test Implementation Map *(filled at step 4)*

All under `backend/tests/integration/test_wm_us_01_create_wallet.py`. Run one with
`uv run pytest -k <fragment>`.

| TC | pytest node id | Result |
|---|---|---|
| TC-01 | `test_authenticated_user_creates_a_wallet_201_with_created_wallet` | PASS |
| TC-02 | `test_creating_a_wallet_persists_exactly_one_row_with_submitted_fields` | PASS |
| TC-03 | `test_unauthenticated_caller_is_denied_with_401` | PASS |
| TC-04 | `test_a_missing_wallet_name_is_rejected_with_422` | PASS |
| TC-05 | `test_empty_or_whitespace_only_wallet_name_is_rejected_with_422` (2 params) | PASS |
| TC-06 | `test_a_wallet_name_exceeding_100_characters_is_rejected_not_truncated` | PASS |
| TC-07 | `test_a_missing_wallet_type_is_rejected_with_422` | PASS |
| TC-08 | `test_an_empty_wallet_type_is_rejected_with_422` | PASS |
| TC-09 | `test_a_wallet_type_exceeding_50_characters_is_rejected_not_truncated` | PASS |
| TC-10 | `test_a_malformed_currency_value_is_rejected_with_422` (4 params) | PASS |
| TC-11 | `test_a_lowercase_or_mixed_case_currency_is_rejected_not_folded_to_uppercase` (2 params) | PASS |
| TC-12 | `test_a_missing_initial_balance_is_rejected_with_422` | PASS |
| TC-13 | `test_an_initial_balance_with_three_decimal_places_is_rejected_not_rounded` | PASS |
| TC-14 | `test_an_initial_balance_exceeding_15_total_digits_is_rejected` | PASS |
| TC-15 | `test_an_initial_balance_of_exactly_zero_is_accepted` | PASS |
| TC-16 | `test_a_negative_initial_balance_is_accepted` | PASS |
| TC-17 | `test_created_wallet_is_always_owned_by_caller_never_by_payload_value` | PASS |
| TC-18 | `test_response_exposes_exactly_the_six_documented_fields` | PASS |
| TC-19 | `test_two_wallets_with_the_same_name_for_the_same_user_both_succeed` | PASS |
| TC-20 | `test_multiple_validation_failures_in_one_submission_are_reported_together` | PASS |
| TC-21 | `test_a_wallet_name_with_surrounding_whitespace_is_stored_trimmed` | PASS |
| TC-22 | `test_a_wallet_type_outside_either_reference_documents_examples_is_accepted` | PASS |

Full suite: `198 passed` (172 pre-existing + 26 new — 22 TCs, 4 parametrized with extra values).
`ruff check`/`ruff format --check` clean, `mypy app` clean, coverage **98%** overall; `models/wallet.py`,
`schemas/wallet.py`, `repositories/wallet_repo.py`, `services/wallet_service.py`, and
`api/v1/wallets.py` are all at **100%** (constitution DOD-03's floor is 80%). No defect found in the
implementation while writing these tests — every TC passed against the first version of the code.

---

### TC-01: An authenticated User creates a wallet — 201 with the created wallet

- **US:** WM-US-01
- **Given:** An authenticated User
- **When:** A wallet is submitted with `name` `"Main Checking"`, `type` `"BANK"`, `currency` `"USD"`, `initial_balance` `1000.00`
- **Then:** The response is `201`; the body carries `id`, `user_id` equal to the caller's id, `name` `"Main Checking"`, `type` `"BANK"`, `currency` `"USD"`, `balance` `1000.00`
- **AC:** AC-01, FR-01, FR-09, FR-10
- **Type:** integration

### TC-02: Creating a wallet persists exactly one row with the submitted fields

- **US:** WM-US-01
- **Given:** An authenticated User
- **When:** A wallet is submitted successfully
- **Then:** Exactly one `wallets` row exists carrying the submitted `name`, `type`, `currency`, and a `balance` equal to the submitted `initial_balance`, owned by the caller
- **AC:** AC-01, FR-01, FR-09
- **Type:** integration

### TC-03: An unauthenticated caller is denied with 401

- **US:** WM-US-01
- **Given:** A caller presenting no `Authorization` header
- **When:** A wallet is submitted with an otherwise valid payload
- **Then:** The response is `401` with `error_code` `NOT_AUTHENTICATED`; no `wallets` row is created
- **AC:** AC-02, FR-02
- **Type:** integration

### TC-04: A missing wallet name is rejected with 422

- **US:** WM-US-01
- **Given:** An authenticated User
- **When:** A wallet is submitted with the `name` field absent
- **Then:** The response is `422` `VALIDATION_ERROR` identifying the `name` field; nothing is persisted
- **AC:** AC-03, FR-03
- **Type:** integration

### TC-05: An empty or whitespace-only wallet name is rejected with 422

- **US:** WM-US-01
- **Given:** An authenticated User
- **When:** A wallet is submitted with `name` `""` and, separately, `"   "`
- **Then:** Each response is `422` `VALIDATION_ERROR` identifying the `name` field; nothing is persisted
- **AC:** AC-03, EC-04, FR-03
- **Type:** integration

### TC-06: A wallet name exceeding 100 characters is rejected, not truncated

- **US:** WM-US-01
- **Given:** An authenticated User
- **When:** A wallet is submitted with a `name` of 101 characters
- **Then:** The response is `422` `VALIDATION_ERROR`; the name is not truncated and nothing is persisted
- **AC:** AC-04, FR-03
- **Type:** integration

### TC-07: A missing wallet type is rejected with 422

- **US:** WM-US-01
- **Given:** An authenticated User
- **When:** A wallet is submitted with the `type` field absent
- **Then:** The response is `422` `VALIDATION_ERROR` identifying the `type` field; nothing is persisted
- **AC:** AC-05, FR-04
- **Type:** integration

### TC-08: An empty wallet type is rejected with 422

- **US:** WM-US-01
- **Given:** An authenticated User
- **When:** A wallet is submitted with `type` `""`
- **Then:** The response is `422` `VALIDATION_ERROR` identifying the `type` field; nothing is persisted
- **AC:** AC-05, FR-04
- **Type:** integration

### TC-09: A wallet type exceeding 50 characters is rejected, not truncated

- **US:** WM-US-01
- **Given:** An authenticated User
- **When:** A wallet is submitted with a `type` of 51 characters
- **Then:** The response is `422` `VALIDATION_ERROR`; the type is not truncated and nothing is persisted
- **AC:** AC-06, FR-04
- **Type:** integration

### TC-10: A malformed currency value is rejected with 422

- **US:** WM-US-01
- **Given:** An authenticated User
- **When:** A wallet is submitted with `currency` in turn `"US"`, `"USDD"`, `"12A"`, and `""`
- **Then:** Each response is `422` `VALIDATION_ERROR` identifying the `currency` field; nothing is persisted
- **AC:** AC-07, FR-05
- **Type:** integration

### TC-11: A lowercase or mixed-case currency is rejected, not folded to uppercase

- **US:** WM-US-01
- **Given:** An authenticated User
- **When:** A wallet is submitted with `currency` `"usd"` and, separately, `"Usd"`
- **Then:** Each response is `422` `VALIDATION_ERROR`; no wallet is created with `currency` `"USD"` — the value is not case-folded and accepted
- **AC:** AC-07, EC-03, FR-05
- **Type:** integration

### TC-12: A missing initial balance is rejected with 422

- **US:** WM-US-01
- **Given:** An authenticated User
- **When:** A wallet is submitted with the `initial_balance` field absent
- **Then:** The response is `422` `VALIDATION_ERROR` identifying the `initial_balance` field; nothing is persisted
- **AC:** AC-08, FR-06
- **Type:** integration

### TC-13: An initial balance with three decimal places is rejected, not rounded

- **US:** WM-US-01
- **Given:** An authenticated User
- **When:** A wallet is submitted with `initial_balance` `100.005`
- **Then:** The response is `422` `VALIDATION_ERROR` whose `details` names `initial_balance`; no `wallets` row is created — so there is no rounded `100.01` or truncated `100.00` value to find
- **AC:** AC-09, BR-02, FR-06 *(assertion technique per QF-02)*
- **Type:** integration

### TC-14: An initial balance exceeding 15 total digits is rejected

- **US:** WM-US-01
- **Given:** An authenticated User
- **When:** A wallet is submitted with an `initial_balance` of 14 integer digits and 2 decimal places (16 significant digits total)
- **Then:** The response is `422` `VALIDATION_ERROR`; nothing is persisted — constitution VL-07's `DECIMAL(15,2)` bound is enforced by the DTO before the service runs
- **AC:** EC-08, BR-02, FR-06
- **Type:** integration

### TC-15: An initial balance of exactly zero is accepted

- **US:** WM-US-01
- **Given:** An authenticated User
- **When:** A wallet is submitted with `initial_balance` `0.00`
- **Then:** The response is `201`; the created wallet's `balance` is `0.00`
- **AC:** EC-01, FR-07
- **Type:** integration

### TC-16: A negative initial balance is accepted

- **US:** WM-US-01
- **Given:** An authenticated User
- **When:** A wallet is submitted with `type` `"CREDIT"` and `initial_balance` `-250.00`
- **Then:** The response is `201`; the created wallet's `balance` is `-250.00`
- **AC:** EC-02, FR-07, BR-03
- **Type:** integration

### TC-17: A created wallet is always owned by the caller, never by a value in the payload

- **US:** WM-US-01
- **Given:** Two authenticated Users, `A` and `B`
- **When:** `A` submits a wallet with an otherwise valid payload that additionally includes an unrecognised `"user_id": "<B's id>"` key in the JSON body
- **Then:** The response is `201`; the created wallet's `user_id` equals `A`'s id, never `B`'s — the extra key is ignored, not honoured
- **AC:** AC-10, FR-08, BR-01 *(assertion technique per QF-01)*
- **Type:** integration

### TC-18: The response exposes exactly the six documented fields

- **US:** WM-US-01
- **Given:** An authenticated User
- **When:** A wallet is submitted successfully
- **Then:** The response body's keys are exactly `id`, `user_id`, `name`, `type`, `currency`, `balance` — no more, and in particular no `created_at` (plan.md A5, QF-04)
- **AC:** AC-11, FR-10
- **Type:** integration

### TC-19: Two wallets with the same name for the same User both succeed

- **US:** WM-US-01
- **Given:** An authenticated User with one existing wallet named `"Savings"`
- **When:** The same User submits another wallet also named `"Savings"`
- **Then:** The response is `201`; two `wallets` rows now exist for that User, both named `"Savings"`, with distinct ids
- **AC:** EC-07, FR-12, BR-05
- **Type:** integration

### TC-20: Multiple validation failures in one submission are reported together

- **US:** WM-US-01
- **Given:** An authenticated User
- **When:** A wallet is submitted with `name` `""` and `currency` `"usd"` in the same request
- **Then:** The response is a single `422` whose `details` identifies both the `name` and the `currency` fields — not just the first one encountered
- **AC:** EC-06, FR-11
- **Type:** integration

### TC-21: A wallet name with surrounding whitespace is stored trimmed

- **US:** WM-US-01
- **Given:** An authenticated User
- **When:** A wallet is submitted with `name` `"  Main Checking  "`
- **Then:** The response is `201`; the persisted `name` is `"Main Checking"` — interior spacing preserved, surrounding whitespace removed
- **AC:** EC-04, FR-03
- **Type:** integration

### TC-22: A wallet type outside either reference document's own examples is accepted

- **US:** WM-US-01
- **Given:** An authenticated User
- **When:** A wallet is submitted with `type` `"Piggy Bank"` — neither the Gherkin's `"BANK"` nor SDS §5.3.1's `"Checking, Cash, Credit Card"` examples
- **Then:** The response is `201`; the created wallet's `type` is `"Piggy Bank"` exactly — demonstrating the bound is length-only, not a closed vocabulary (plan.md A1, QF-03)
- **AC:** EC-05, FR-04, BR-04
- **Type:** integration
