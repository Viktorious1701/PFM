# Test Cases: Wallet Management (WM)

> **Feature:** SRS §6 Feature-03 · SDS §5.3 (WM)
> **Spec:** [spec.md](spec.md) · **Plan:** [plan.md](plan.md)
> **Stories in this file:** WM-US-01 *(TC-01…TC-22, all PASS)* · WM-US-02 *(TC-23…TC-39)*

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

---

## WM-US-02: List Wallets

> **IDs in this section are local to WM-US-02** — except `TC-NN`, which continues this epic file's
> own numbering: WM-US-01 used `TC-01`…`TC-22`, so this story continues from `TC-23`. **`QF-NN` also
> continues here** (WM-US-01 used `QF-01`…`QF-04`; this story continues from `QF-05`) — unlike
> `specs/001-user-onboarding/test_cases.md`, which explicitly resets `QF-NN` per story. Both are
> legitimate readings of `CLAUDE.md`'s ID schemes table, which names only `TC-NN` as continuous; this
> epic file adopts the continuing convention for `QF-NN` too, matching `artifact-templates/`'s own
> worked example (`PM-US-02`'s Quality Findings continue from `QF-08`, implying a prior story used
> `QF-01`…`QF-07` in the same file).

### Quality Findings

#### QF-05

**Description.** `plan.md` A3 requires the total-count query in `wallet_repo.list_owned()` to carry
the same `user_id` predicate as the bounded page query. The closest precedent, `user_repo.list_users()`
(UM-US-03), computes an entirely unfiltered count by design — that story lists every account
system-wide. A test that only checks the returned `items` are scoped to the caller would not catch a
copy-paste of `list_users()`'s count query that forgot to add the ownership predicate: `items` would
look correct while `total` silently leaked the system-wide wallet count.

**Impact.** A weaker test suite could pass with a `total` that counts every User's wallets, not just
the caller's — wrong, but not obviously wrong from `items` alone, especially in a test that seeds
wallets for only one User.

**Recommendation.** `TC-30` (ownership scoping) and `TC-31` (empty-for-one, populated-for-another)
both seed a **second** User's wallets alongside the caller's own, and assert `total` equals only the
caller's own count — distinct from the combined count across both Users — proving the count query is
scoped, not merely the item query.

#### QF-06

**Description.** `plan.md` A1 orders wallets by `id` because no `created_at` column exists (WM-US-01
A5). `id` is a randomly generated UUID (`app.models.user.new_uuid`), so its sort order has no
relationship to creation time. A test asserting only "the order is consistent" could pass even if a
future change swapped in a different, equally-arbitrary-but-different order (e.g. unindexed scan
order) — "stable within a single run" is a weaker claim than "actually sorted by `id`."

**Impact.** Without pinning the expected order to a concrete, independently-computable key, a test
could not tell "genuinely ordered by `id`" apart from "happened to come back in insertion order this
one time" — exactly the false impression of meaningful order `spec.md`'s Assumptions section warns
against.

**Recommendation.** `TC-32`/`TC-38` assert the returned order equals the wallets' own `id` values
sorted ascending as plain strings (computed independently in the test from the ids the creation calls
actually returned), not merely "some order that stays the same" — and both create the wallets in an
order that does **not** already match ascending `id` order, so the test cannot pass by coincidence if
the implementation actually sorted by insertion order instead of `id`.

#### QF-07

**Description.** `spec.md` EC-04 requires an ADMIN-role caller to see only their own wallets through
this endpoint, but no existing test in this codebase exercises an ADMIN account that also owns a
wallet — UM-US-03's ADMIN fixtures never create a wallet for the ADMIN, and WM-US-01's tests use a
generic authenticated caller without asserting on role.

**Impact.** Without a dedicated case, a future change that special-cased ADMIN visibility (plausible,
since UM-US-03 already established an ADMIN-sees-everything pattern for users) could pass every other
test in this file while silently breaking BR-01 for this endpoint specifically.

**Recommendation.** `TC-39` creates an ADMIN-role User with one wallet alongside a second User (any
role) with wallets of their own, and asserts the ADMIN's request returns exactly the ADMIN's own
wallet — never the other User's — despite the elevated role.

### Acceptance Criteria Classification

No wallet-list screen exists in `mobile/` this round, and no SRS UXR names one — the same basis
WM-US-01 used for its own all-`[API]` classification. Unlike UM-US-01/02/03's UXR-04 deferrals, this
story has no Gherkin at all, so there is no illustrative screen to defer against even conceptually.

| AC/EC | Title | Label | Rationale |
|---|---|---|---|
| AC-01 | Successfully list every wallet the caller owns | **[API]** | No UI surface exists or is named by any UXR this round |
| AC-02 | Return an empty list for a User with no wallets yet | **[API]** | Backend response-shape contract |
| AC-03 | Deny access to unauthenticated callers | **[API]** | Backend authorization contract |
| AC-04 | Bound and paginate the result by default | **[API]** | Query-parameter contract; unanchored to any SRS scenario (no Gherkin exists for this story) |
| AC-05 | Accept an explicit page and page size within range | **[API]** | Same reasoning as AC-04 |
| AC-06 | Reject a page or page size outside the allowed range | **[API]** | 422 `VALIDATION_ERROR` — backend validation concern |
| AC-07 | A User only ever sees their own wallets | **[API]** | Persistence/ownership contract; bounded by QF-05 |
| AC-08 | Return the list in a stable, deterministic order | **[API]** | Backend contract; bounded by QF-06 |
| AC-09 | Reuse the documented per-wallet fields, wrapped in a paginated envelope | **[API]** | Response-payload contract |
| EC-01 | A page number beyond the last available page | **[API]** | Boundary value |
| EC-02 | Page size at the exact maximum | **[API]** | Boundary value |
| EC-03 | More wallets than fit on one page | **[API]** | Cross-page completeness; bounded by QF-06 |
| EC-04 | A caller whose role is ADMIN, who also owns wallets | **[API]** | Ownership contract independent of role; bounded by QF-07 |

### Coverage Matrix

| AC/EC | Label | Integration TC(s) | E2E TC(s) |
|---|---|---|---|
| AC-01 | [API] | TC-23, TC-24 | — |
| AC-02 | [API] | TC-25, TC-31 | — |
| AC-03 | [API] | TC-26, TC-27 | — |
| AC-04 | [API] | TC-28 | — |
| AC-05 | [API] | TC-29 | — |
| AC-06 | [API] | TC-33, TC-34, TC-35 | — |
| AC-07 | [API] | TC-30, TC-31 | — |
| AC-08 | [API] | TC-32 | — |
| AC-09 | [API] | TC-24 | — |
| EC-01 | [API] | TC-36 | — |
| EC-02 | [API] | TC-37 | — |
| EC-03 | [API] | TC-38 | — |
| EC-04 | [API] | TC-39 | — |

> Every AC and EC has at least one integration TC. There is no `[BOTH]` or `[UI]` row — no
> wallet-list screen exists this round, and no SRS UXR names one (WM-US-01's own precedent).
> **Known coverage limits, accepted:** the sort key (`id`) carries no chronological meaning, so no
> test asserts anything about creation order — only that the order matches an independently-computed
> ascending sort of the returned ids (QF-06).

---

### TC-23: An authenticated User lists every wallet they own — 200 with all wallets and an accurate total

- **US:** WM-US-02
- **Given:** An authenticated User who owns three wallets of different types and currencies, created via `POST /api/v1/wallets`
- **When:** The User requests the list of wallets
- **Then:** The response is `200`; `items` contains all three wallets, each carrying `id`, `user_id` equal to the caller's id, `name`, `type`, `currency`, and `balance`; `total` is `3`
- **AC:** AC-01, FR-01, FR-02, FR-06, FR-09, BR-05
- **Type:** integration

### TC-24: The response item exposes exactly the six documented fields, wrapped in the paginated envelope

- **US:** WM-US-02
- **Given:** An authenticated User with one existing wallet
- **When:** The User requests the list of wallets
- **Then:** The response is `200`; the top-level body exposes exactly the keys `items`, `total`, `page`, `page_size`; each entry in `items` exposes **exactly** the keys `id`, `user_id`, `name`, `type`, `currency`, `balance` — no more, and in particular no field this story invents
- **AC:** AC-01, AC-09, FR-02, PF-03
- **Type:** integration

### TC-25: A User with no wallets yet receives an empty list and a zero total

- **US:** WM-US-02
- **Given:** An authenticated User who owns no wallets
- **When:** The User requests the list of wallets
- **Then:** The response is `200`, not an error; `items` is an empty list and `total` is `0`
- **AC:** AC-02, FR-01
- **Type:** integration

### TC-26: An unauthenticated or invalid-credential caller is denied with 401

- **US:** WM-US-02
- **Given:** A caller presenting no `Authorization` header, and separately a caller presenting an expired token
- **When:** Each attempts to list wallets
- **Then:** Both responses are `401` with `error_code` `NOT_AUTHENTICATED`; no `items` are returned
- **AC:** AC-03, FR-03
- **Type:** integration

### TC-27: Credentials are evaluated before any query parameter

- **US:** WM-US-02
- **Given:** A caller presenting no credentials
- **When:** The list is requested with an out-of-range `page` value (`page=0`)
- **Then:** The response is `401` `NOT_AUTHENTICATED`, not `422` — an unauthenticated caller learns nothing about the validity of their query parameters, mirroring UM-US-03 TC-61's ordering
- **AC:** AC-03, FR-03
- **Type:** integration

### TC-28: The default page is 1 of size 25, with an accurate total

- **US:** WM-US-02
- **Given:** An authenticated User and three existing wallets they own
- **When:** The list is requested with no `page` or `page_size` supplied
- **Then:** The response is `200`; `page` is `1`, `page_size` is `25`, `items` contains all three wallets, and `total` is `3`
- **AC:** AC-04, FR-04, FR-06, BR-02
- **Type:** integration

### TC-29: An explicit page and page size within range return that page and an accurate total

- **US:** WM-US-02
- **Given:** An authenticated User and five wallets they own
- **When:** The list is requested with `page=2` and `page_size=2`
- **Then:** The response is `200`; `page` is `2`, `page_size` is `2`, `items` contains exactly two of the User's own wallets, and `total` is `5`
- **AC:** AC-05, FR-04, FR-06
- **Type:** integration

### TC-30: A User only ever sees their own wallets, never another User's

- **US:** WM-US-02
- **Given:** Two authenticated Users, `A` (two wallets) and `B` (three wallets)
- **When:** `A` requests the list of wallets
- **Then:** The response is `200`; `items` contains exactly `A`'s two wallets — none of `B`'s three — and `total` is `2`, not `5`
- **AC:** AC-07, FR-07, FR-10, BR-01, BR-04 *(assertion technique per QF-05)*
- **Type:** integration

### TC-31: The reported total counts only the caller's own wallets, even when it is the smaller number

- **US:** WM-US-02
- **Given:** Two authenticated Users, `A` (no wallets) and `B` (four wallets)
- **When:** `A` requests the list of wallets
- **Then:** The response is `200`; `items` is empty and `total` is `0` — not `4`, and not any count reflecting `B`'s wallets
- **AC:** AC-02, AC-07, FR-07, FR-10, BR-04 *(assertion technique per QF-05)*
- **Type:** integration

### TC-32: The list is returned in a stable order matching the wallets' ids sorted ascending

- **US:** WM-US-02
- **Given:** An authenticated User who creates five wallets in an order that does not already match ascending id order (confirmed from the ids the creation calls actually returned)
- **When:** The User requests the list of wallets twice, with nothing created, changed, or removed in between
- **Then:** Both responses return the same five wallets in the same relative order, and that order equals the five ids sorted ascending as strings — not the order the wallets were created in
- **AC:** AC-08, FR-08, BR-03 *(assertion technique per QF-06)*
- **Type:** integration

### TC-33: A `page` that is not a positive integer is rejected with 422

- **US:** WM-US-02
- **Given:** An authenticated User
- **When:** The list is requested with `page` set to each of `0`, `-1`, and `"abc"` in turn
- **Then:** Each response is `422` with `error_code` `VALIDATION_ERROR` and a `details.fields` entry locating `page`; no `items` are returned
- **AC:** AC-06, FR-05, BR-02
- **Type:** integration

### TC-34: A `page_size` that is not a positive integer is rejected with 422

- **US:** WM-US-02
- **Given:** An authenticated User
- **When:** The list is requested with `page_size` set to each of `0`, `-1`, and `"abc"` in turn
- **Then:** Each response is `422` with `error_code` `VALIDATION_ERROR` and a `details.fields` entry locating `page_size`; no `items` are returned
- **AC:** AC-06, FR-05, BR-02
- **Type:** integration

### TC-35: A `page_size` above the maximum is rejected with 422

- **US:** WM-US-02
- **Given:** An authenticated User
- **When:** The list is requested with `page_size=101`
- **Then:** The response is `422` `VALIDATION_ERROR` identifying `page_size`; the request is not silently capped at 100
- **AC:** AC-06, EC-02, FR-05, BR-02
- **Type:** integration

### TC-36: A page beyond the last available page returns an empty list with the accurate total

- **US:** WM-US-02
- **Given:** An authenticated User and three wallets they own
- **When:** The list is requested with `page=5` and `page_size=25`
- **Then:** The response is `200`, not `404`; `items` is an empty list and `total` is still `3`
- **AC:** EC-01, FR-06
- **Type:** integration

### TC-37: A `page_size` of exactly 100 is accepted

- **US:** WM-US-02
- **Given:** An authenticated User
- **When:** The list is requested with `page_size=100`
- **Then:** The response is `200` — the cap is a ceiling, not a target: 100 is honoured, only 101 is rejected (TC-35)
- **AC:** EC-02, FR-05
- **Type:** integration

### TC-38: Paging through every page returns every wallet exactly once, in stable order

- **US:** WM-US-02
- **Given:** An authenticated User and five wallets they own, created in an order that does not already match ascending id order
- **When:** Every page is fetched in turn with `page_size=2` (`page=1`, `page=2`, `page=3`)
- **Then:** The concatenation of all three pages' `items` contains every one of the five wallets exactly once, with no duplicate and no gap, in the same ascending-id order TC-32 established, stable across the page boundaries
- **AC:** EC-03, FR-08, BR-03 *(assertion technique per QF-06)*
- **Type:** integration

### TC-39: An ADMIN-role caller who also owns a wallet sees only their own through this endpoint

- **US:** WM-US-02
- **Given:** An authenticated User whose role is `ADMIN` and owns one wallet, and a second User (any role) who owns two wallets of their own
- **When:** The ADMIN requests the list of wallets
- **Then:** The response is `200`; `items` contains exactly the ADMIN's own one wallet — never either of the other User's — and `total` is `1`
- **AC:** EC-04, FR-10, BR-01 *(assertion technique per QF-07)*
- **Type:** integration
