# Test Cases: Wallet Management (WM)

> **Feature:** SRS §6 Feature-03 · SDS §5.3 (WM)
> **Spec:** [spec.md](spec.md) · **Plan:** [plan.md](plan.md)
> **Stories in this file:** WM-US-01 *(TC-01…TC-22, all PASS)* · WM-US-02 *(TC-23…TC-39, all PASS)* · WM-US-04 *(TC-40…TC-59, all PASS)* · WM-US-03 *(TC-60…TC-70, spec'd — artifacts phase only, not yet implemented)*
> WM-US-04 *(TC-40…TC-59)*

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

### Test Implementation Map *(filled at step 4)*

All under `backend/tests/integration/test_wm_us_02_list_wallets.py`. Run one with
`uv run pytest -k <fragment>`.

| TC | pytest node id | Result |
|---|---|---|
| TC-23 | `test_authenticated_user_lists_every_wallet_they_own_with_accurate_total` | PASS |
| TC-24 | `test_response_item_exposes_exactly_six_fields_wrapped_in_paginated_envelope` | PASS |
| TC-25 | `test_user_with_no_wallets_yet_receives_empty_list_and_zero_total` | PASS |
| TC-26 | `test_unauthenticated_or_invalid_credential_caller_is_denied_with_401` | PASS |
| TC-27 | `test_credentials_are_evaluated_before_any_query_parameter` | PASS |
| TC-28 | `test_default_page_is_1_of_size_25_with_accurate_total` | PASS |
| TC-29 | `test_explicit_page_and_page_size_within_range_return_that_page_and_accurate_total` | PASS |
| TC-30 | `test_a_user_only_ever_sees_their_own_wallets_never_another_users` | PASS |
| TC-31 | `test_reported_total_counts_only_callers_own_wallets_even_when_smaller` | PASS |
| TC-32 | `test_list_is_returned_in_stable_order_matching_ids_sorted_ascending` | PASS |
| TC-33 | `test_a_non_positive_or_non_integer_page_is_rejected_with_422` (3 params) | PASS |
| TC-34 | `test_a_non_positive_or_non_integer_page_size_is_rejected_with_422` (3 params) | PASS |
| TC-35 | `test_a_page_size_above_the_maximum_is_rejected_with_422` | PASS |
| TC-36 | `test_a_page_beyond_the_last_available_page_returns_an_empty_list_with_accurate_total` | PASS |
| TC-37 | `test_a_page_size_of_exactly_100_is_accepted` | PASS |
| TC-38 | `test_paging_through_every_page_returns_every_wallet_exactly_once_in_stable_order` | PASS |
| TC-39 | `test_admin_role_caller_who_also_owns_a_wallet_sees_only_their_own` | PASS |

Full suite: `302 passed` (281 pre-existing + 21 new — 17 TCs, 2 parametrized with extra values —
TC-33/TC-34 each carry 3 param cases). `ruff check`/`ruff format --check` clean, `mypy app` clean,
coverage **99%** overall; `schemas/wallet.py`, `repositories/wallet_repo.py`,
`services/wallet_service.py`, and `api/v1/wallets.py` are all at **100%** (constitution DOD-03's floor
is 80%). No defect found in the implementation while writing these tests — every TC passed against
the first version of the code. Live-verification walkthrough (step 5) additionally confirmed ownership
scoping, pagination, and validation against a running server with two real, distinct users — see the
gate message for the full pasted `curl` transcript.

---

## WM-US-04: Update a Wallet

> **IDs in this section are local to WM-US-04** — except `TC-NN`, which continues this epic file's own
> numbering: WM-US-02 used `TC-23`…`TC-39`, so this story continues from `TC-40`. **`QF-NN` also
> continues here** (WM-US-01 used `QF-01`…`QF-04`, WM-US-02 used `QF-05`…`QF-07`; this story continues
> from `QF-08`). Confirmed by re-reading this file's actual current end before writing this section —
> not assumed from any prior summary.

### Quality Findings

#### QF-08

**Description.** AC-03/AC-04 require a wallet reference that does not exist at all and one that exists
but belongs to a different User to produce "the same not-found outcome" — mirrors BM-US-04 QF-16, now
applied to the wallet's own id instead of a budget's. `plan.md` A3 makes this true by construction, since
`wallet_repo.get_owned_by_id()` filters by `user_id` in the query itself and returns `None` either way. A
test that merely checks both cases return *some* `404` would not distinguish "genuinely identical" from
"two different messages that both happen to carry status 404."

**Impact.** A weaker test could pass even if a future change accidentally made the two cases
distinguishable — for instance, a message that only names "belongs to another account" in the
ownership-mismatch case, itself a minor information leak about another User's data.

**Recommendation.** `TC-46` compares the full response body of the ownership-mismatch case against
`TC-45`'s not-found-at-all case and asserts they match exactly — `error_code`, `message`, and `details`
all identical, not merely the status code.

#### QF-09

**Description.** AC-10's claim that currency and balance are unchanged, and that any unsubmitted field
keeps its exact prior value, could be satisfied by a test that only reads the `PATCH` response body — a
service bug that mutated the stored row's `currency`/`balance` (or the unsubmitted one of `name`/`type`)
while still constructing a response DTO from stale, pre-mutation in-memory values would pass such a test
undetected. The identical risk BM-US-04 QF-19 already named for Budget's own immutable fields.

**Impact.** A regression that let `update_wallet()` touch more than the submitted field(s) — for
instance, a careless refactor passing the whole payload into a generic ORM update, or a copy-paste error
applying `wallet.type = name` — could corrupt a wallet's stored data while every response-body-only test
kept passing.

**Recommendation.** `TC-55` asserts both the response body's `currency`/`balance` **and** the stored
`wallets` row's own `currency`/`balance` columns — read independently through the test's own `db`
session — match the wallet's values from immediately before the update. `TC-40`/`TC-41` additionally
assert the *unsubmitted* field (`type` when only `name` is sent, and vice versa) is unchanged in the
response itself.

#### QF-10

**Description.** AC-05/BR-04 require a submission naming neither a new name nor a new type to be
*refused*, not silently treated as a successful no-op. A test asserting only "the response is some kind
of error" would not distinguish that from a latent bug where an empty body is accepted and returns `200`
with the wallet completely unchanged — which would *also* leave "nothing changed" true, just via the
wrong mechanism (a silently-accepted no-op rather than a validation refusal).

**Impact.** A future refactor that "simplified" `WalletUpdate` by dropping the at-least-one-field
`model_validator` (plan.md A4) could silently turn this endpoint into an accidental no-op success path,
and a loosely-written test would not catch it.

**Recommendation.** `TC-48` asserts specifically that the response status is `422` with `error_code`
`VALIDATION_ERROR` — not `200` — for an empty-body submission, and that the target wallet's stored `name`
and `type` are unchanged, closing both the "wrong status" and "silently accepted" failure modes in one
test.

#### QF-11

**Description.** This story's own `spec.md` AC-08 is deliberately worded as "reject an **empty** wallet
type" rather than WM-US-01 AC-05's "absent, empty, or only whitespace" — because `WalletUpdate.type`
reuses `WalletCreate.type`'s exact, already-shipped validation shape (`Field(min_length=1,
max_length=50)` with no trim/whitespace-rejection validator, confirmed directly in
`backend/app/schemas/wallet.py`), and a single-space `type` value already passes `WalletCreate` uncaught
today. Writing a test asserting a whitespace-only `type` is rejected on **update** would fail against
this story's own planned implementation — not because of a defect this story introduces, but because of
a pre-existing WM-US-01 characteristic this story deliberately does not change (`plan.md` A10).

**Impact.** Without this note, a future reviewer could read a missing whitespace-only-`type` test case as
a coverage gap in this story, rather than as a deliberate mirror of an already-shipped, out-of-scope
characteristic.

**Recommendation.** No test case asserts that a whitespace-only `type` is rejected. `TC-51` covers only
the empty-string (`""`) case for `type`, matching exactly what WM-US-01's own `TC-08` already exercises
at creation — the same evidence boundary, not a narrower one invented for this story.

### Acceptance Criteria Classification

No wallet-update screen exists in `mobile/` this round, and no SRS UXR names one — the same basis every
prior Wallet Management story used for its own all-`[API]` classification.

| AC/EC | Title | Label | Rationale |
|---|---|---|---|
| AC-01 | Successfully update a wallet's name, type, or both | **[API]** | No UI surface exists or is named by any UXR this round |
| AC-02 | Deny access to unauthenticated callers | **[API]** | Backend authorization contract |
| AC-03 | Reject an update to a wallet that does not exist | **[API]** | Persistence/ownership contract; bounded by QF-08 |
| AC-04 | Reject an update to a wallet owned by a different User | **[API]** | Persistence/ownership contract; bounded by QF-08 |
| AC-05 | Reject a submission naming neither a new name nor a new type | **[API]** | Payload-contract/no-op risk; bounded by QF-10 |
| AC-06 | Reject a blank or whitespace-only wallet name, when submitted | **[API]** | Payload validation |
| AC-07 | Reject a wallet name exceeding the maximum length, when submitted | **[API]** | Payload validation |
| AC-08 | Reject an empty wallet type, when submitted | **[API]** | Payload validation; scope bounded by QF-11 |
| AC-09 | Reject a wallet type exceeding the maximum length, when submitted | **[API]** | Payload validation |
| AC-10 | A successful update changes only the submitted field(s) | **[API]** | Response/persistence contract; bounded by QF-09 |
| AC-11 | Return exactly the documented wallet fields | **[API]** | Response-payload contract |
| EC-01 | Wallet name with surrounding whitespace, when submitted | **[API]** | Persistence-shape (trimming) |
| EC-02 | A wallet type outside either document's own examples, when submitted | **[API]** | Backend rule (no closed vocabulary) |
| EC-03 | A wallet reference that is not a well-formed identifier | **[API]** | Backend rule (no separate format validation) |
| EC-04 | Only a new name is submitted | **[API]** | Partial-update contract |
| EC-05 | Only a new type is submitted | **[API]** | Partial-update contract |
| EC-06 | Both a new name and a new type are submitted together | **[API]** | Partial-update contract |
| EC-07 | A currency or initial-balance value submitted alongside name/type | **[API]** | Structural-ignore contract |
| EC-08 | A caller who owns a different wallet attempts to update another User's wallet | **[API]** | Persistence/ownership contract; bounded by QF-08 |
| EC-09 | More than one validation failure in a single submission | **[API]** | Backend validation-grouping contract |

### Coverage Matrix

| AC/EC | Label | Integration TC(s) | E2E TC(s) |
|---|---|---|---|
| AC-01 | [API] | TC-40, TC-41, TC-42, TC-43 | — |
| AC-02 | [API] | TC-44 | — |
| AC-03 | [API] | TC-45 | — |
| AC-04 | [API] | TC-46 | — |
| AC-05 | [API] | TC-48 | — |
| AC-06 | [API] | TC-49 | — |
| AC-07 | [API] | TC-50 | — |
| AC-08 | [API] | TC-51 | — |
| AC-09 | [API] | TC-52 | — |
| AC-10 | [API] | TC-55 | — |
| AC-11 | [API] | TC-57 | — |
| EC-01 | [API] | TC-54 | — |
| EC-02 | [API] | TC-53 | — |
| EC-03 | [API] | TC-47 | — |
| EC-04 | [API] | TC-40 | — |
| EC-05 | [API] | TC-41 | — |
| EC-06 | [API] | TC-42 | — |
| EC-07 | [API] | TC-56 | — |
| EC-08 | [API] | TC-59 | — |
| EC-09 | [API] | TC-58 | — |

> Every AC and EC has at least one integration TC. There is no `[BOTH]` or `[UI]` row — no wallet-update
> screen exists this round, and none is named by any SRS UXR. **Known coverage limits, accepted:**
> `type`'s own whitespace-only acceptance (a pre-existing WM-US-01 characteristic) is not re-tested as a
> rejection on update, matching what is actually enforced rather than AC-05's original wording (QF-11).

### Test Implementation Map *(filled at step 4)*

`backend/tests/integration/test_wm_us_04_update_wallet.py` — all 20 PASS.

| TC | pytest node id | Result |
|---|---|---|
| TC-40 | `test_wm_us_04_update_wallet.py::test_updating_only_the_name_returns_200_with_other_fields_unchanged` | PASS |
| TC-41 | `test_wm_us_04_update_wallet.py::test_updating_only_the_type_returns_200_with_other_fields_unchanged` | PASS |
| TC-42 | `test_wm_us_04_update_wallet.py::test_updating_both_name_and_type_together_changes_both_leaves_currency_and_balance` | PASS |
| TC-43 | `test_wm_us_04_update_wallet.py::test_updating_a_wallet_persists_the_new_values_on_the_same_single_row` | PASS |
| TC-44 | `test_wm_us_04_update_wallet.py::test_an_unauthenticated_or_expired_caller_is_denied_and_nothing_changes` | PASS |
| TC-45 | `test_wm_us_04_update_wallet.py::test_a_wallet_id_matching_no_wallet_is_rejected_with_404_wallet_not_found` | PASS |
| TC-46 | `test_wm_us_04_update_wallet.py::test_another_users_wallet_is_refused_with_a_body_identical_to_not_found` | PASS |
| TC-47 | `test_wm_us_04_update_wallet.py::test_a_malformed_wallet_id_gets_the_same_404_as_a_well_formed_unknown_one` | PASS |
| TC-48 | `test_wm_us_04_update_wallet.py::test_a_submission_naming_neither_name_nor_type_is_rejected_with_422` | PASS |
| TC-49 | `test_wm_us_04_update_wallet.py::test_a_blank_or_whitespace_only_name_when_submitted_is_rejected_with_422` | PASS |
| TC-50 | `test_wm_us_04_update_wallet.py::test_a_name_exceeding_100_characters_is_rejected_not_truncated` | PASS |
| TC-51 | `test_wm_us_04_update_wallet.py::test_an_empty_type_when_submitted_is_rejected_with_422` | PASS |
| TC-52 | `test_wm_us_04_update_wallet.py::test_a_type_exceeding_50_characters_is_rejected_not_truncated` | PASS |
| TC-53 | `test_wm_us_04_update_wallet.py::test_a_wallet_type_outside_either_reference_documents_examples_is_accepted_on_update` | PASS |
| TC-54 | `test_wm_us_04_update_wallet.py::test_a_name_with_surrounding_whitespace_is_stored_trimmed` | PASS |
| TC-55 | `test_wm_us_04_update_wallet.py::test_a_successful_update_leaves_currency_and_balance_unchanged_verified_against_storage` | PASS |
| TC-56 | `test_wm_us_04_update_wallet.py::test_a_currency_or_balance_value_submitted_alongside_name_or_type_is_silently_ignored` | PASS |
| TC-57 | `test_wm_us_04_update_wallet.py::test_the_response_exposes_exactly_the_six_documented_fields` | PASS |
| TC-58 | `test_wm_us_04_update_wallet.py::test_multiple_validation_failures_in_one_submission_are_reported_together` | PASS |
| TC-59 | `test_wm_us_04_update_wallet.py::test_a_caller_who_owns_a_different_wallet_cannot_update_another_users_wallet` | PASS |

Verified by: `uv run pytest tests/integration/test_wm_us_04_update_wallet.py -v` — 20 passed. Also
verified live via a real curl walkthrough against `uv run uvicorn` (step 5/6 evidence in this story's
gate message): name-only, type-only, and both-together updates; an empty-body `422`; a different
owner's wallet and a nonexistent id both `404` with byte-identical bodies; `currency`/`balance`
unchanged throughout.

---

### TC-40: An authenticated owner updates only a wallet's name — 200 with the updated wallet, other fields unchanged

- **US:** WM-US-04
- **Given:** An authenticated User who owns a wallet with `name` `"Main Checking"`, `type` `"BANK"`, `currency` `"USD"`, `balance` `500.00`
- **When:** `PATCH /api/v1/wallets/{id}` is sent with `name` `"Primary Checking"` only
- **Then:** The response is `200`; the body carries `id` unchanged, `name` `"Primary Checking"`, and `type`/`currency`/`balance` unchanged (`"BANK"`/`"USD"`/`500.00`)
- **AC:** AC-01, EC-04, FR-01, FR-05, FR-08, FR-10
- **Type:** integration

### TC-41: An authenticated owner updates only a wallet's type — 200 with the updated wallet, other fields unchanged

- **US:** WM-US-04
- **Given:** An authenticated User who owns a wallet with `name` `"Main Checking"`, `type` `"BANK"`, `currency` `"USD"`, `balance` `500.00`
- **When:** `PATCH /api/v1/wallets/{id}` is sent with `type` `"CREDIT"` only
- **Then:** The response is `200`; the body carries `type` `"CREDIT"`, and `name`/`currency`/`balance` unchanged (`"Main Checking"`/`"USD"`/`500.00`)
- **AC:** AC-01, EC-05, FR-01, FR-06, FR-08, FR-10
- **Type:** integration

### TC-42: An authenticated owner updates both name and type together — 200 with both changed, currency and balance unchanged

- **US:** WM-US-04
- **Given:** An authenticated User who owns a wallet with `name` `"Main Checking"`, `type` `"BANK"`, `currency` `"USD"`, `balance` `500.00`
- **When:** `PATCH /api/v1/wallets/{id}` is sent with `name` `"Primary Checking"` and `type` `"CREDIT"` together
- **Then:** The response is `200`; the body carries `name` `"Primary Checking"`, `type` `"CREDIT"`, and `currency`/`balance` unchanged
- **AC:** AC-01, EC-06, FR-01, FR-10
- **Type:** integration

### TC-43: Updating a wallet persists the new value(s) on the same single row

- **US:** WM-US-04
- **Given:** An authenticated User who owns a wallet
- **When:** The wallet's name and type are updated successfully
- **Then:** Direct inspection of the `wallets` row for that id shows the new `name` and `type`; exactly one row still exists for that wallet id
- **AC:** AC-01, FR-01
- **Type:** integration

### TC-44: An unauthenticated caller is denied with 401

- **US:** WM-US-04
- **Given:** A caller presenting no `Authorization` header
- **When:** A wallet update is submitted with an otherwise valid payload
- **Then:** The response is `401` with `error_code` `NOT_AUTHENTICATED`; the target wallet's stored `name`/`type` are unchanged
- **AC:** AC-02, FR-02
- **Type:** integration

### TC-45: A wallet_id matching no wallet at all is rejected with 404 WALLET_NOT_FOUND

- **US:** WM-US-04
- **Given:** An authenticated User
- **When:** `PATCH /api/v1/wallets/{id}` is sent with a `wallet_id` that matches no wallet in the system
- **Then:** The response is `404` with `error_code` `WALLET_NOT_FOUND`; nothing is changed
- **AC:** AC-03, FR-03
- **Type:** integration

### TC-46: A wallet_id belonging to a different User is rejected with the identical outcome as TC-45

- **US:** WM-US-04
- **Given:** Two authenticated Users `A` and `B`, where `B` owns a wallet
- **When:** `A` submits a `PATCH` against `B`'s `wallet_id`
- **Then:** The response is `404`; its `error_code`, `message`, and `details` are identical to TC-45's response; `B`'s wallet is unchanged
- **AC:** AC-04, FR-03 *(assertion technique per QF-08)*
- **Type:** integration

### TC-47: A malformed wallet reference gets the same 404 as a well-formed but non-existent one

- **US:** WM-US-04
- **Given:** An authenticated User
- **When:** `PATCH /api/v1/wallets/not-a-real-id` is sent with a valid payload
- **Then:** The response is `404` `WALLET_NOT_FOUND`, identical to TC-45's response
- **AC:** EC-03, FR-03
- **Type:** integration

### TC-48: A submission naming neither a new name nor a new type is rejected with 422

- **US:** WM-US-04
- **Given:** An authenticated User who owns a wallet
- **When:** A `PATCH` is submitted with an empty body (neither `name` nor `type`)
- **Then:** The response is `422` `VALIDATION_ERROR`, not `200`; the stored `name` and `type` are unchanged
- **AC:** AC-05, FR-04, BR-04 *(assertion technique per QF-10)*
- **Type:** integration

### TC-49: A blank or whitespace-only name, when submitted, is rejected with 422

- **US:** WM-US-04
- **Given:** An authenticated User who owns a wallet
- **When:** A `PATCH` is submitted with `name` `""` and, separately, `"   "`
- **Then:** Each response is `422` `VALIDATION_ERROR` identifying the `name` field; the stored `name` is unchanged
- **AC:** AC-06, FR-05
- **Type:** integration

### TC-50: A name exceeding 100 characters, when submitted, is rejected, not truncated

- **US:** WM-US-04
- **Given:** An authenticated User who owns a wallet
- **When:** A `PATCH` is submitted with a `name` of 101 characters
- **Then:** The response is `422` `VALIDATION_ERROR`; the name is not truncated and the stored `name` is unchanged
- **AC:** AC-07, FR-05
- **Type:** integration

### TC-51: An empty type, when submitted, is rejected with 422

- **US:** WM-US-04
- **Given:** An authenticated User who owns a wallet
- **When:** A `PATCH` is submitted with `type` `""`
- **Then:** The response is `422` `VALIDATION_ERROR` identifying the `type` field; the stored `type` is unchanged
- **AC:** AC-08, FR-06 *(scope bounded by QF-11 — no whitespace-only case is asserted)*
- **Type:** integration

### TC-52: A type exceeding 50 characters, when submitted, is rejected, not truncated

- **US:** WM-US-04
- **Given:** An authenticated User who owns a wallet
- **When:** A `PATCH` is submitted with a `type` of 51 characters
- **Then:** The response is `422` `VALIDATION_ERROR`; the type is not truncated and the stored `type` is unchanged
- **AC:** AC-09, FR-06
- **Type:** integration

### TC-53: A wallet type outside either reference document's own examples is still accepted on update

- **US:** WM-US-04
- **Given:** An authenticated User who owns a wallet
- **When:** A `PATCH` is submitted with `type` `"Piggy Bank"` — neither the Gherkin's `"BANK"` nor SDS §5.3.1's own examples
- **Then:** The response is `200`; the updated wallet's `type` is `"Piggy Bank"` exactly — demonstrating the bound is length-only, not a closed vocabulary, on update just as on creation (WM-US-01 plan.md A1)
- **AC:** EC-02, FR-06, BR-03
- **Type:** integration

### TC-54: A name with surrounding whitespace, when submitted, is stored trimmed

- **US:** WM-US-04
- **Given:** An authenticated User who owns a wallet
- **When:** A `PATCH` is submitted with `name` `"  Primary Checking  "`
- **Then:** The response is `200`; the persisted `name` is `"Primary Checking"` — interior spacing preserved, surrounding whitespace removed
- **AC:** EC-01, FR-05
- **Type:** integration

### TC-55: A successful update leaves currency and balance unchanged, verified against the stored row directly

- **US:** WM-US-04
- **Given:** An authenticated User who owns a wallet with `currency` `"USD"` and `balance` `750.25`
- **When:** The wallet's `name` is updated successfully
- **Then:** The response's `currency`/`balance` match their pre-update values; a direct read of the `wallets` row through the test's own `db` session confirms the stored `currency`/`balance` columns are unchanged
- **AC:** AC-10, FR-07, BR-01 *(assertion technique per QF-09)*
- **Type:** integration

### TC-56: A currency or balance value submitted alongside name/type is silently ignored

- **US:** WM-US-04
- **Given:** An authenticated User who owns a wallet with `currency` `"USD"` and `balance` `500.00`
- **When:** A `PATCH` is submitted with a valid `name` plus the extra keys `currency` (`"EUR"`) and `initial_balance` (`9999.00`)
- **Then:** The response is `200`; the updated wallet's `currency`/`balance` remain `"USD"`/`500.00` — never the submitted extra values
- **AC:** EC-07, FR-07
- **Type:** integration

### TC-57: The response exposes exactly the six documented fields

- **US:** WM-US-04
- **Given:** An authenticated User who owns a wallet
- **When:** The wallet's name or type is updated successfully
- **Then:** The response body's keys are exactly `id`, `user_id`, `name`, `type`, `currency`, `balance` — no more, and in particular no invented field
- **AC:** AC-11, FR-08
- **Type:** integration

### TC-58: Multiple validation failures in one submission are reported together

- **US:** WM-US-04
- **Given:** An authenticated User who owns a wallet
- **When:** A `PATCH` is submitted with `name` `""` and a `type` of 51 characters in the same request
- **Then:** The response is a single `422` whose `details` identifies both the `name` and the `type` fields — not just the first one encountered
- **AC:** EC-09, FR-09
- **Type:** integration

### TC-59: A caller who owns a different wallet of their own cannot update another User's wallet

- **US:** WM-US-04
- **Given:** Two authenticated Users, `A` (owns wallet `WA`) and `B` (owns wallet `WB`)
- **When:** `A` submits a `PATCH` against `WB`'s `wallet_id`
- **Then:** The response is `404` `WALLET_NOT_FOUND`, identical to TC-45/TC-46's responses; `WB`'s stored `name`/`type` are unchanged, and `A`'s own `WA` is also unaffected
- **AC:** EC-08, FR-03

---

## WM-US-03: View a Wallet

> **IDs in this section are local to WM-US-03** — except `TC-NN`, which continues this epic file's own
> numbering: WM-US-04 used `TC-40`…`TC-59`, so this story continues from `TC-60`. **`QF-NN` also
> continues here, from `QF-12`** — confirmed by direct count of this file's own entries, not assumed:
> WM-US-01 used `QF-01`…`QF-04` and WM-US-04 used `QF-05`…`QF-11`, so this file's own last `QF` entry is
> `QF-11`, not `QF-19`. (`QF-19` is BM-US-04's own number in a *different* epic file,
> `specs/005-budget-management/test_cases.md` — already cited by this file's own `QF-08` as a
> cross-epic precedent, never a number this file has used itself. Corrected here after re-reading this
> file directly, per `CLAUDE.md`'s instruction to confirm rather than assume.)

### Quality Findings

#### QF-12

**Description.** AC-03/AC-04 require a wallet reference that does not exist at all and one that
exists but belongs to a different User to produce "the same not-found outcome" — `plan.md` A3 makes
this true by construction, since `wallet_repo.get_owned_by_id()` filters by `user_id` in the query
itself and returns `None` either way. A test that merely checks both cases return *some* `404` would
not distinguish "genuinely identical" from "two different messages that both happen to carry status
404" — the same risk WM-US-04 QF-08/TM-US-03 QF-14/BM-US-04 QF-19 each already flagged for their own
ownership-collapse cases.

**Impact.** A weaker test could pass even if a future change accidentally made the two cases
distinguishable — the same class of minor information leak about another User's data those earlier
findings already warned against.

**Recommendation.** `TC-63` compares the full response body of the ownership-mismatch case against
`TC-62`'s not-found-at-all case and asserts they match exactly — `error_code`, `message`, and `details`
all identical, not merely the status code. `TC-69` extends the same comparison to a caller who owns a
wallet of their own but names someone else's.

#### QF-13

**Description.** AC-05 requires the response to carry exactly the six fields `WalletRead` already
fixes for a created (WM-US-01), listed (WM-US-02), or updated (WM-US-04) wallet — no more, no fewer,
and in particular no embedded transaction list, recent-transaction summary, or transaction count,
despite this endpoint's own SDS §5.3.3 goal naming "history" specifically — a materially more
pointed word than TM-US-03's own "detailed information" framing, which this same file's precedent
(`plan.md` TM-US-03 A3, cited there) already resolved the identical way for a thinner-worded goal. A
test asserting only that the documented fields are *present* would not prove no others were *also*
added — exactly the gap this story's own design reasoning (`spec.md` Assumptions & Dependencies)
depends on being enforced by more than prose.

**Impact.** A future change that accidentally enriched this specific endpoint — the exact temptation
this story's own `plan.md` A2 reasoned through and declined — would pass a weak test and quietly
diverge this story's response shape from WM-US-01/02/04's own shared precedent.

**Recommendation.** `TC-68` asserts the response body's keys are exactly `id`, `user_id`, `name`,
`type`, `currency`, `balance` — no more, and in particular no `transactions`/`transaction_count`/
`history` key of any kind — the same technique WM-US-04 TC-57/TM-US-03 TC-79 each already used for
their own easy-to-accidentally-leak or easy-to-accidentally-add fields.

### Acceptance Criteria Classification

No wallet-detail screen exists in `mobile/` this round — confirmed directly: `mobile/`'s own source
tree carries only an API client stub (`src/api/wallets.ts`) for wallets, no screen of any kind, the
same basis every prior Wallet Management story used for its own all-`[API]` classification. No SRS UXR
names one either.

| AC/EC | Title | Label | Rationale |
|---|---|---|---|
| AC-01 | Successfully view the detail of a wallet the caller owns | **[API]** | No UI surface exists or is named by any UXR this round |
| AC-02 | Deny access to unauthenticated callers | **[API]** | Backend authorization contract |
| AC-03 | Reject a wallet reference that does not exist at all | **[API]** | Persistence/ownership contract; bounded by QF-12 |
| AC-04 | Reject a wallet reference belonging to a different User | **[API]** | Persistence/ownership contract; bounded by QF-12 |
| AC-05 | Return exactly the documented wallet fields — no embedded transaction data | **[API]** | Response-payload contract; bounded by QF-13 |
| EC-01 | A wallet reference that is not a well-formed identifier | **[API]** | Backend rule (no separate format validation) |
| EC-02 | A caller who owns a different wallet attempts to view another User's wallet | **[API]** | Persistence/ownership contract; bounded by QF-12 |
| EC-03 | An ADMIN-role caller attempting to view a wallet they do not own | **[API]** | Ownership contract independent of role |
| EC-04 | Viewing a wallet with no transactions logged against it yet | **[API]** | Backend rule (this endpoint reads no transaction data at all) |

### Coverage Matrix

| AC/EC | Label | Integration TC(s) | E2E TC(s) |
|---|---|---|---|
| AC-01 | [API] | TC-60, TC-61 | — |
| AC-02 | [API] | TC-64, TC-70 | — |
| AC-03 | [API] | TC-62 | — |
| AC-04 | [API] | TC-63 | — |
| AC-05 | [API] | TC-61, TC-68 | — |
| EC-01 | [API] | TC-65 | — |
| EC-02 | [API] | TC-69 | — |
| EC-03 | [API] | TC-66 | — |
| EC-04 | [API] | TC-67 | — |

> Every AC and EC has at least one integration TC. There is no `[BOTH]` or `[UI]` row — no
> wallet-detail screen exists this round, and none is named by any SRS UXR. This story never issues a
> query against `transactions` (spec FR-06, EC-04), so no test here exercises `TransactionModel` or
> `transaction_repo` at all — the deliberate absence that TC-67 proves directly.

### Test Implementation Map *(filled at step 4)*

Not yet populated — this dispatch covers steps 1–3 (Spec, Design, Quality) only; no test code exists
yet for WM-US-03. `backend/tests/integration/test_wm_us_03_view_wallet.py` will be written at the
Implement dispatch (steps 4–6) from the test cases below, one test per `TC-NN`, each carrying its
`TC-NN` id in its docstring, following WM-US-01/02/04's own Test Implementation Map precedent in this
same file.

| TC | pytest node id | Result |
|---|---|---|
| TC-60 | *(not yet implemented)* | — |
| TC-61 | *(not yet implemented)* | — |
| TC-62 | *(not yet implemented)* | — |
| TC-63 | *(not yet implemented)* | — |
| TC-64 | *(not yet implemented)* | — |
| TC-65 | *(not yet implemented)* | — |
| TC-66 | *(not yet implemented)* | — |
| TC-67 | *(not yet implemented)* | — |
| TC-68 | *(not yet implemented)* | — |
| TC-69 | *(not yet implemented)* | — |
| TC-70 | *(not yet implemented)* | — |

---

### TC-60: An authenticated User views a wallet they own — 200 with the full detail

- **US:** WM-US-03
- **Given:** An authenticated User who owns a wallet with `name` `"Main Checking"`, `type` `"BANK"`, `currency` `"USD"`, `balance` `750.25`
- **When:** The User requests that wallet by its own `id`
- **Then:** The response is `200`; the body carries `id` equal to the wallet's own id, `user_id` equal to the caller's own id, `name` `"Main Checking"`, `type` `"BANK"`, `currency` `"USD"`, and `balance` `750.25`
- **AC:** AC-01, FR-01, FR-05
- **Type:** integration

### TC-61: Viewing a wallet reflects its current balance, including after Transaction activity has changed it

- **US:** WM-US-03
- **Given:** An authenticated User who owns a wallet with `initial_balance` `500.00`, against which one `EXPENSE` transaction of `100.00` has since been recorded (TM-US-01)
- **When:** The User requests that wallet by its own `id`
- **Then:** The response is `200`; `balance` is `400.00` — the current, Transaction-adjusted value, not the original `initial_balance` — and the response carries exactly the six documented fields
- **AC:** AC-01, AC-05, FR-01, FR-05
- **Type:** integration

### TC-62: A wallet_id matching no wallet at all is rejected with 404 WALLET_NOT_FOUND

- **US:** WM-US-03
- **Given:** An authenticated User
- **When:** The User requests a wallet by an `id` that matches no wallet in the system
- **Then:** The response is `404` with `error_code` `WALLET_NOT_FOUND`
- **AC:** AC-03, FR-03
- **Type:** integration

### TC-63: A wallet belonging to a different User is rejected with the identical outcome as TC-62

- **US:** WM-US-03
- **Given:** Two authenticated Users `A` and `B`, where `B` owns a wallet and `A` owns nothing of the kind
- **When:** `A` requests `B`'s wallet by its own `id`
- **Then:** The response is `404`; its `error_code`, `message`, and `details` are identical to TC-62's response
- **AC:** AC-04, FR-03 *(assertion technique per QF-12)*
- **Type:** integration

### TC-64: An unauthenticated caller is denied with 401

- **US:** WM-US-03
- **Given:** A caller presenting no `Authorization` header, and an existing wallet belonging to some other, real User
- **When:** The caller requests that wallet by its own `id`
- **Then:** The response is `401` with `error_code` `NOT_AUTHENTICATED`
- **AC:** AC-02, FR-02
- **Type:** integration

### TC-65: A malformed wallet reference is rejected with the same outcome as a well-formed but non-existent one

- **US:** WM-US-03
- **Given:** An authenticated User
- **When:** The User requests a wallet by the `id` value `"not-a-real-id"`
- **Then:** The response is `404` `WALLET_NOT_FOUND`, identical to TC-62's response
- **AC:** EC-01, FR-03
- **Type:** integration

### TC-66: An ADMIN-role caller cannot view another User's wallet through this endpoint

- **US:** WM-US-03
- **Given:** An authenticated User whose role is `ADMIN`, and a second User (any role) who owns a wallet of their own
- **When:** The ADMIN requests the other User's wallet by its own `id`
- **Then:** The response is `404` `WALLET_NOT_FOUND` — the same outcome any non-ADMIN caller would get; no role grants visibility through this endpoint
- **AC:** EC-03, FR-04
- **Type:** integration

### TC-67: A wallet with no transactions logged against it yet still views successfully

- **US:** WM-US-03
- **Given:** An authenticated User who owns a wallet created with `initial_balance` `250.00` and no transaction ever recorded against it
- **When:** The User requests that wallet by its own `id`
- **Then:** The response is `200`; `balance` is exactly `250.00` — an empty transaction history is not an error condition, and the endpoint issues no query against `transactions` at all
- **AC:** EC-04, FR-06
- **Type:** integration

### TC-68: The response exposes exactly the six documented fields — no embedded transaction data

- **US:** WM-US-03
- **Given:** An authenticated User who owns a wallet with one or more transactions logged against it
- **When:** The User requests that wallet by its own `id`
- **Then:** The response body's keys are exactly `id`, `user_id`, `name`, `type`, `currency`, `balance` — no more, and in particular no `transactions`, `transaction_count`, `history`, or any other embedded or computed field
- **AC:** AC-05, FR-05, FR-06 *(assertion technique per QF-13)*
- **Type:** integration

### TC-69: A caller who owns a wallet of their own cannot view a different User's wallet

- **US:** WM-US-03
- **Given:** Two authenticated Users `A` and `B`, where `A` owns one wallet of their own and `B` owns a separate wallet of their own
- **When:** `A` requests `B`'s wallet by its own `id`
- **Then:** The response is `404`; its `error_code`, `message`, and `details` are identical to TC-62's response — owning a wallet of their own gives `A` no access to `B`'s
- **AC:** EC-02, FR-03 *(assertion technique per QF-12)*
- **Type:** integration

### TC-70: Credentials are evaluated before the wallet reference is looked up

- **US:** WM-US-03
- **Given:** A caller presenting no credentials
- **When:** The caller requests a wallet by an `id` that does not match any wallet in the system
- **Then:** The response is `401` `NOT_AUTHENTICATED`, not `404` — mirrors TM-US-03 TC-82/TM-US-02 TC-41's own ordering
- **AC:** AC-02, FR-02
- **Type:** integration
- **Type:** integration
