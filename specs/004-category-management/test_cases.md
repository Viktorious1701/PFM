# Test Cases: Category Management (CM)

> **Feature:** SRS §6 Feature-04 · SDS §5.4 (CM)
> **Spec:** [spec.md](spec.md) · **Plan:** [plan.md](plan.md)
> **Stories in this file:** CM-US-01 *(TC-01…TC-17, all PASS)* · CM-US-02 *(TC-18…TC-34)*

---

## CM-US-01: Create a Category

### Quality Findings

Problems found while deriving test cases from `spec.md` and `plan.md`. Each one changes how a criterion can be asserted, so it is recorded rather than worked around silently.

#### QF-01

**Description.** AC-07 requires the category's owner to be "determined solely from the caller's own identity and never from any value in the request payload." `plan.md` A6 makes this true by construction — `CategoryCreate` declares no `user_id` field at all — but a test that only checks the *created* category's `user_id` equals the caller's id would not distinguish "the field doesn't exist" from "the field exists and was correctly overridden."

**Impact.** A weaker test could pass even if a future change accidentally added a `user_id` field to `CategoryCreate` and wired it through unchecked.

**Recommendation.** `TC-12` asserts both halves: the category created through a normal request is owned by the caller, **and** a request that additionally includes an unexpected `user_id` key naming a different, real user in its JSON body still creates a category owned by the caller, not by the named other user — the extra key is silently ignored, never honoured. Directly mirrors WM-US-01 QF-01.

#### QF-02

**Description.** AC-06 requires a category type that is not exactly `INCOME` or `EXPENSE` to be rejected. The rejection is Pydantic's own enum-membership validation against `CategoryType` (`plan.md` A2), not a hand-written check, so the risk is asserting the wrong thing: a test could check only that *some* `422` came back without confirming which field it names, and a future refactor could silently swap in case-folding or trimming that also happens to accept some near-miss values.

**Impact.** A loosely-written assertion would not actually prove the vocabulary stays closed and exact rather than being silently normalised somewhere before validation runs.

**Recommendation.** `TC-09`, `TC-10`, and `TC-11` each assert the `422` response's `details` names the `type` field specifically, and that no `categories` row was created at all — so there is no case-folded or trimmed value to find.

#### QF-03

**Description.** `plan.md` A4/A6 record that `icon` does not exist anywhere in `CategoryCreate` or `CategoryModel` this story, even though the SDS domain model (as aligned, G1) now names it as a real future Category attribute. A test asserting only that creation "succeeds" when `icon` is submitted would not prove the value is actually discarded rather than, say, silently accepted into some untyped column.

**Impact.** A weak test could pass even if a future change accidentally started persisting or echoing back an unrecognised `icon` key before CM-US-04 formally designs that capability.

**Recommendation.** `TC-13` submits an `icon` key alongside a valid payload and asserts the response contains no `icon` key at all — the same "prove the extra field is structurally impossible to honour" technique QF-01/TC-12 uses for `user_id`.

#### QF-04

**Description.** `plan.md` A4 records that `categories` has no `icon` column in this story, even though `SDS.md` §4.3.3's ERD was aligned (G1) to list one at the document level. This is a genuine, deliberate gap between the target domain model and what CM-US-01 itself builds — not something this story is authorised to close.

**Impact.** No test in this file can assert `icon` persistence or serialization, because no such column or field exists yet.

**Recommendation.** No test case asserts anything about `icon` storage. `TC-14`'s exact-field-set assertion is written to *positively* confirm `icon` is absent from the response, so a future accidental addition (without CM-US-04 formally adding the column first) would be caught rather than silently welcomed. Mirrors WM-US-01 QF-04's treatment of `created_at`.

### Acceptance Criteria Classification

No category-creation screen exists in `mobile/` this round, and no SRS UXR names one (the same situation WM-US-01's test_cases.md recorded for wallets). Every row below is `[API]`.

| AC/EC | Title | Label | Rationale |
|---|---|---|---|
| AC-01 | Successfully create a category with all mandatory inputs | **[API]** | No UI surface exists or is named by any UXR this round |
| AC-02 | Deny access to unauthenticated callers | **[API]** | Backend authorization contract |
| AC-03 | Reject a missing or blank category name | **[API]** | Payload validation |
| AC-04 | Reject a category name exceeding the maximum length | **[API]** | Payload validation |
| AC-05 | Reject a missing category type | **[API]** | Payload validation |
| AC-06 | Reject a category type value that is not exactly `INCOME`/`EXPENSE` | **[API]** | Payload validation; bounded by QF-02 |
| AC-07 | A created category always belongs to the submitting User | **[API]** | Persistence/ownership contract; bounded by QF-01 |
| AC-08 | Return exactly the documented category fields | **[API]** | Response-payload contract; bounded by QF-04 |
| EC-01 | Category type submitted in lowercase or mixed case | **[API]** | Payload validation; bounded by QF-02 |
| EC-02 | Category name with surrounding whitespace | **[API]** | Persistence-shape (trimming) |
| EC-03 | Two categories with the same name for the same User | **[API]** | Backend rule (absence of a uniqueness constraint) |
| EC-04 | More than one validation failure in a single submission | **[API]** | Backend validation-grouping contract |
| EC-05 | An unrecognised `icon` field submitted with the request | **[API]** | Structural-ignore contract; bounded by QF-03/QF-04 |
| EC-06 | Category type submitted with surrounding whitespace | **[API]** | Payload validation; bounded by QF-02 |

### Coverage Matrix

| AC/EC | Label | Integration TC(s) | E2E TC(s) |
|---|---|---|---|
| AC-01 | [API] | TC-01, TC-02, TC-03 | — |
| AC-02 | [API] | TC-04 | — |
| AC-03 | [API] | TC-05, TC-06 | — |
| AC-04 | [API] | TC-07 | — |
| AC-05 | [API] | TC-08 | — |
| AC-06 | [API] | TC-09, TC-10, TC-11 | — |
| AC-07 | [API] | TC-12 | — |
| AC-08 | [API] | TC-14 | — |
| EC-01 | [API] | TC-10 | — |
| EC-02 | [API] | TC-06, TC-17 | — |
| EC-03 | [API] | TC-15 | — |
| EC-04 | [API] | TC-16 | — |
| EC-05 | [API] | TC-13 | — |
| EC-06 | [API] | TC-11 | — |

> Every AC and EC has at least one integration TC. There is no `[BOTH]` or `[UI]` row — no category-creation screen exists this round, and none is named by any SRS UXR. **Known coverage limits, accepted:** `icon` has no column or field in this story's contract, so no test asserts its persistence or serialization (QF-04); the "system category" concept named only by CM-US-02's own (out-of-scope) goal is not tested here, since no AC in this story's own set requires it (spec.md Assumptions, `plan.md` A5).

### Test Implementation Map *(filled at step 4)*

All under `backend/tests/integration/test_cm_us_01_create_category.py`. Run one with
`uv run pytest -k <fragment>`.

| TC | pytest node id | Result |
|---|---|---|
| TC-01 | `test_authenticated_user_creates_an_expense_category_201_with_created_category` | PASS |
| TC-02 | `test_authenticated_user_creates_an_income_category_201_with_created_category` | PASS |
| TC-03 | `test_creating_a_category_persists_exactly_one_row_with_submitted_fields` | PASS |
| TC-04 | `test_unauthenticated_caller_is_denied_with_401` | PASS |
| TC-05 | `test_a_missing_category_name_is_rejected_with_422` | PASS |
| TC-06 | `test_empty_or_whitespace_only_category_name_is_rejected_with_422` | PASS |
| TC-07 | `test_a_category_name_exceeding_100_characters_is_rejected_not_truncated` | PASS |
| TC-08 | `test_a_missing_category_type_is_rejected_with_422` | PASS |
| TC-09 | `test_a_category_type_value_that_is_neither_income_nor_expense_is_rejected_with_422` (3 params) | PASS |
| TC-10 | `test_a_lowercase_or_mixed_case_category_type_is_rejected_not_case_folded` (2 params) | PASS |
| TC-11 | `test_a_category_type_with_surrounding_whitespace_is_rejected_not_trimmed` (2 params) | PASS |
| TC-12 | `test_created_category_is_always_owned_by_caller_never_by_payload_value` | PASS |
| TC-13 | `test_an_unrecognised_icon_field_submitted_with_the_request_is_silently_ignored` | PASS |
| TC-14 | `test_response_exposes_exactly_the_four_documented_fields` | PASS |
| TC-15 | `test_two_categories_with_the_same_name_for_the_same_user_both_succeed` | PASS |
| TC-16 | `test_multiple_validation_failures_in_one_submission_are_reported_together` | PASS |
| TC-17 | `test_a_category_name_with_surrounding_whitespace_is_stored_trimmed` | PASS |

Full suite: `219 passed` (198 pre-existing + 21 new — 17 TCs, 3 parametrized with extra values).
`ruff check`/`ruff format --check` clean, `mypy app` clean, coverage **99%** overall; `models/category.py`,
`schemas/category.py`, `repositories/category_repo.py`, `services/category_service.py`, and
`api/v1/categories.py` are all at **100%** (constitution DOD-03's floor is 80%). No defect found in the
implementation while writing these tests — every TC passed against the first version of the code.

---

### TC-01: An authenticated User creates an EXPENSE category — 201 with the created category

- **US:** CM-US-01
- **Given:** An authenticated User
- **When:** A category is submitted with `name` `"Groceries"`, `type` `"EXPENSE"`
- **Then:** The response is `201`; the body carries `id`, `user_id` equal to the caller's id, `name` `"Groceries"`, `type` `"EXPENSE"`
- **AC:** AC-01, FR-01, FR-06
- **Type:** integration

### TC-02: An authenticated User creates an INCOME category — 201 with the created category

- **US:** CM-US-01
- **Given:** An authenticated User
- **When:** A category is submitted with `name` `"Salary"`, `type` `"INCOME"`
- **Then:** The response is `201`; the body carries `id`, `user_id` equal to the caller's id, `name` `"Salary"`, `type` `"INCOME"`
- **AC:** AC-01, FR-01, FR-06
- **Type:** integration

### TC-03: Creating a category persists exactly one row with the submitted fields

- **US:** CM-US-01
- **Given:** An authenticated User
- **When:** A category is submitted successfully
- **Then:** Exactly one `categories` row exists carrying the submitted `name` and `type`, owned by the caller
- **AC:** AC-01, FR-01
- **Type:** integration

### TC-04: An unauthenticated caller is denied with 401

- **US:** CM-US-01
- **Given:** A caller presenting no `Authorization` header
- **When:** A category is submitted with an otherwise valid payload
- **Then:** The response is `401` with `error_code` `NOT_AUTHENTICATED`; no `categories` row is created
- **AC:** AC-02, FR-02
- **Type:** integration

### TC-05: A missing category name is rejected with 422

- **US:** CM-US-01
- **Given:** An authenticated User
- **When:** A category is submitted with the `name` field absent
- **Then:** The response is `422` `VALIDATION_ERROR` identifying the `name` field; nothing is persisted
- **AC:** AC-03, FR-03
- **Type:** integration

### TC-06: An empty or whitespace-only category name is rejected with 422

- **US:** CM-US-01
- **Given:** An authenticated User
- **When:** A category is submitted with `name` `""` and, separately, `"   "`
- **Then:** Each response is `422` `VALIDATION_ERROR` identifying the `name` field; nothing is persisted
- **AC:** AC-03, EC-02, FR-03
- **Type:** integration

### TC-07: A category name exceeding 100 characters is rejected, not truncated

- **US:** CM-US-01
- **Given:** An authenticated User
- **When:** A category is submitted with a `name` of 101 characters
- **Then:** The response is `422` `VALIDATION_ERROR`; the name is not truncated and nothing is persisted
- **AC:** AC-04, FR-03
- **Type:** integration

### TC-08: A missing category type is rejected with 422

- **US:** CM-US-01
- **Given:** An authenticated User
- **When:** A category is submitted with the `type` field absent
- **Then:** The response is `422` `VALIDATION_ERROR` identifying the `type` field; nothing is persisted
- **AC:** AC-05, FR-04
- **Type:** integration

### TC-09: A category type value that is neither INCOME nor EXPENSE is rejected with 422

- **US:** CM-US-01
- **Given:** An authenticated User
- **When:** A category is submitted with `type` in turn `"SAVINGS"`, `"TRANSFER"`, and `""`
- **Then:** Each response is `422` `VALIDATION_ERROR` whose `details` names the `type` field; nothing is persisted
- **AC:** AC-06, BR-02, FR-04 *(assertion technique per QF-02)*
- **Type:** integration

### TC-10: A lowercase or mixed-case category type is rejected, not case-folded

- **US:** CM-US-01
- **Given:** An authenticated User
- **When:** A category is submitted with `type` `"expense"` and, separately, `"Income"`
- **Then:** Each response is `422` `VALIDATION_ERROR` whose `details` names the `type` field; no category is created with `type` `"EXPENSE"` or `"INCOME"` — the value is not case-folded and accepted
- **AC:** AC-06, EC-01, FR-04 *(assertion technique per QF-02)*
- **Type:** integration

### TC-11: A category type with surrounding whitespace is rejected, not trimmed

- **US:** CM-US-01
- **Given:** An authenticated User
- **When:** A category is submitted with `type` `" EXPENSE"` and, separately, `"INCOME "`
- **Then:** Each response is `422` `VALIDATION_ERROR` whose `details` names the `type` field; nothing is persisted — unlike `name`, `type` receives no trimming
- **AC:** AC-06, EC-06, FR-04 *(assertion technique per QF-02)*
- **Type:** integration

### TC-12: A created category is always owned by the caller, never by a value in the payload

- **US:** CM-US-01
- **Given:** Two authenticated Users, `A` and `B`
- **When:** `A` submits a category with an otherwise valid payload that additionally includes an unrecognised `"user_id": "<B's id>"` key in the JSON body
- **Then:** The response is `201`; the created category's `user_id` equals `A`'s id, never `B`'s — the extra key is ignored, not honoured
- **AC:** AC-07, FR-05, BR-01 *(assertion technique per QF-01)*
- **Type:** integration

### TC-13: An unrecognised `icon` field submitted with the request is silently ignored

- **US:** CM-US-01
- **Given:** An authenticated User
- **When:** A category is submitted with an otherwise valid payload that additionally includes `"icon": "shopping-cart"` in the JSON body
- **Then:** The response is `201`; the created category is built from `name` and `type` alone, and the response body carries no `icon` key at all
- **AC:** EC-05, FR-09, BR-04 *(assertion technique per QF-03)*
- **Type:** integration

### TC-14: The response exposes exactly the four documented fields

- **US:** CM-US-01
- **Given:** An authenticated User
- **When:** A category is submitted successfully
- **Then:** The response body's keys are exactly `id`, `user_id`, `name`, `type` — no more, and in particular no `icon` (plan.md A4, QF-04)
- **AC:** AC-08, FR-06
- **Type:** integration

### TC-15: Two categories with the same name for the same User both succeed

- **US:** CM-US-01
- **Given:** An authenticated User with one existing category named `"Utilities"`
- **When:** The same User submits another category also named `"Utilities"` (type `"EXPENSE"` both times)
- **Then:** The response is `201`; two `categories` rows now exist for that User, both named `"Utilities"`, with distinct ids
- **AC:** EC-03, FR-08, BR-03
- **Type:** integration

### TC-16: Multiple validation failures in one submission are reported together

- **US:** CM-US-01
- **Given:** An authenticated User
- **When:** A category is submitted with `name` `""` and `type` `"SAVINGS"` in the same request
- **Then:** The response is a single `422` whose `details` identifies both the `name` and the `type` fields — not just the first one encountered
- **AC:** EC-04, FR-07
- **Type:** integration

### TC-17: A category name with surrounding whitespace is stored trimmed

- **US:** CM-US-01
- **Given:** An authenticated User
- **When:** A category is submitted with `name` `"  Groceries  "`, `type` `"EXPENSE"`
- **Then:** The response is `201`; the persisted `name` is `"Groceries"` — interior spacing preserved, surrounding whitespace removed
- **AC:** EC-02, FR-03
- **Type:** integration

---

## CM-US-02: List Categories

> **IDs in this section are local to CM-US-02** — except `TC-NN`, which continues this epic file's
> own numbering: CM-US-01 used `TC-01`…`TC-17`, so this story continues from `TC-18`. **`QF-NN` also
> continues here** (CM-US-01 used `QF-01`…`QF-04`; this story continues from `QF-05`) — matching the
> continuing convention `specs/003-wallet-management/test_cases.md` (WM-US-02) and
> `specs/006-transaction-management/test_cases.md` (TM-US-02) both already adopted, over
> `specs/001-user-onboarding/test_cases.md`'s reset-per-story convention. This is the first point in
> this epic file where the choice actually has to be made explicit — CM-US-01 was the file's first
> story, so nothing distinguished "reset" from "continue" for it.

### Quality Findings

#### QF-05

**Description.** `plan.md` A3 requires the total-count query in `category_repo.list_owned()` to carry
the same `user_id` predicate as the bounded page query. The closest precedent this codebase has for
computing a count without an ownership predicate is `user_repo.list_users()` (UM-US-03), which is
deliberately unfiltered — that story lists every account system-wide. A test that only checks the
returned `items` are scoped to the caller would not catch a copy-paste of an unfiltered count query:
`items` would look correct while `total` silently leaked the system-wide category count — the exact
risk `test_cases.md` QF-05 already named for `WalletModel` (WM-US-02) and QF-10 extended to a join for
`TransactionModel` (TM-US-02); here the risk is the plain single-table case again, one this story
shares structurally with WM-US-02 rather than TM-US-02.

**Impact.** A weaker test suite could pass with a `total` that counts every User's categories, not
just the caller's — wrong, but not obviously wrong from `items` alone, especially in a test that seeds
categories for only one User.

**Recommendation.** `TC-25` (ownership scoping) and `TC-26` (empty-for-one, populated-for-another)
both seed a **second** User's categories alongside the caller's own, and assert `total` equals only
the caller's own count, distinct from the combined count across both Users — proving the count query
is scoped, not merely the item query.

#### QF-06

**Description.** `plan.md` A1 orders categories by `id` because no `created_at` column exists
(mirrors WM-US-01 A5/WM-US-02 A1 for `wallets`). `id` is a randomly generated UUID
(`app.models.user.new_uuid`), so its sort order has no relationship to creation time. A test asserting
only "the order is consistent" could pass even if a future change swapped in a different, equally
arbitrary order (e.g. unindexed scan order) — "stable within a single run" is a weaker claim than
"actually sorted by `id`."

**Impact.** Without pinning the expected order to a concrete, independently-computable key, a test
could not tell "genuinely ordered by `id`" apart from "happened to come back in insertion order this
one time."

**Recommendation.** `TC-27`/`TC-33` assert the returned order equals the categories' own `id` values
sorted ascending as plain strings (computed independently in the test from the ids the creation calls
actually returned), and both create the categories in an order that does **not** already match
ascending `id` order, so the test cannot pass by coincidence if the implementation actually sorted by
insertion order instead of `id`. Directly mirrors WM-US-02 QF-06.

#### QF-07

**Description.** `spec.md` EC-04 requires an ADMIN-role caller to see only their own categories
through this endpoint, but no existing test in this codebase exercises an ADMIN account that also owns
a category — UM-US-03's ADMIN fixtures never create a category for the ADMIN, and CM-US-01's tests use
a generic authenticated caller without asserting on role.

**Impact.** Without a dedicated case, a future change that special-cased ADMIN visibility (plausible,
since UM-US-03 already established an ADMIN-sees-everything pattern for users) could pass every other
test in this file while silently breaking BR-01 for this endpoint specifically.

**Recommendation.** `TC-34` creates an ADMIN-role User with one category alongside a second User (any
role) with categories of their own, and asserts the ADMIN's request returns exactly the ADMIN's own
category — never the other User's — despite the elevated role. Directly mirrors WM-US-02 QF-07.

#### QF-08

**Description.** `plan.md` A7 records that no "system category" (a category with no owning User)
exists in this story's schema, even though SDS §5.4.2's own goal text names one ("system and
user-defined"). This is a genuine, deliberate scope boundary this story is not authorised to close
(`plan.md` A7) — not something this test suite can construct a counter-example for, because
`categories.user_id` is `NOT NULL` at the database level and no migration ever seeds an ownerless row.

**Impact.** No test in this file can assert "system category" retrieval, coexistence with user-owned
categories in the same list, or any distinguishing marker between the two — because no such row, and
no such marker, exists to construct.

**Recommendation.** Accept the structural proof over a constructed counter-example, the same "known
coverage limit, accepted" pattern TM-US-02 QF-12 and WM-US-01 QF-04 already use in this codebase for a
case the public API cannot construct. `TC-19`'s exact-field-set assertion (no field this story
invents, in particular nothing resembling an `is_system` marker) and `TC-25`/`TC-26`'s
ownership-scoping assertions together are the closest available witness: every category this endpoint
can possibly return already carries a real `user_id` equal to some caller's own id, because the column
enforces it, not because a test checked for the absence of a hypothetical second class of row.
`plan.md` A7 records the standing recommendation to reword SDS §5.4.2 so a future reader does not
re-open this question believing it is still unresolved.

### Acceptance Criteria Classification

No category-list screen exists in `mobile/` this round, and no SRS UXR names one — the same basis
CM-US-01 and WM-US-02 each used for their own all-`[API]` classification. This story has even less
SRS text than WM-US-02 to defer against (no bare header exists at all for it — see `spec.md` Source).

| AC/EC | Title | Label | Rationale |
|---|---|---|---|
| AC-01 | Successfully list every category the caller owns | **[API]** | No UI surface exists or is named by any UXR this round |
| AC-02 | Return an empty list for a User with no categories yet | **[API]** | Backend response-shape contract |
| AC-03 | Deny access to unauthenticated callers | **[API]** | Backend authorization contract |
| AC-04 | Bound and paginate the result by default | **[API]** | Query-parameter contract; unanchored to any SRS scenario (no SRS entry exists for this story) |
| AC-05 | Accept an explicit page and page size within range | **[API]** | Same reasoning as AC-04 |
| AC-06 | Reject a page or page size outside the allowed range | **[API]** | 422 `VALIDATION_ERROR` — backend validation concern |
| AC-07 | A User only ever sees their own categories | **[API]** | Persistence/ownership contract; bounded by QF-05 |
| AC-08 | Return the list in a stable, deterministic order | **[API]** | Backend contract; bounded by QF-06 |
| AC-09 | Reuse the documented per-category fields, wrapped in a paginated envelope | **[API]** | Response-payload contract; bounded by QF-08 |
| EC-01 | A page number beyond the last available page | **[API]** | Boundary value |
| EC-02 | Page size at the exact maximum | **[API]** | Boundary value |
| EC-03 | More categories than fit on one page | **[API]** | Cross-page completeness; bounded by QF-06 |
| EC-04 | A caller whose role is ADMIN, who also owns categories | **[API]** | Ownership contract independent of role; bounded by QF-07 |

### Coverage Matrix

| AC/EC | Label | Integration TC(s) | E2E TC(s) |
|---|---|---|---|
| AC-01 | [API] | TC-18, TC-19 | — |
| AC-02 | [API] | TC-20, TC-26 | — |
| AC-03 | [API] | TC-21, TC-22 | — |
| AC-04 | [API] | TC-23 | — |
| AC-05 | [API] | TC-24 | — |
| AC-06 | [API] | TC-28, TC-29, TC-30 | — |
| AC-07 | [API] | TC-25, TC-26 | — |
| AC-08 | [API] | TC-27 | — |
| AC-09 | [API] | TC-19 | — |
| EC-01 | [API] | TC-31 | — |
| EC-02 | [API] | TC-32 | — |
| EC-03 | [API] | TC-33 | — |
| EC-04 | [API] | TC-34 | — |

> Every AC and EC has at least one integration TC. There is no `[BOTH]` or `[UI]` row — no
> category-list screen exists this round, and no SRS UXR names one. **Known coverage limits,
> accepted:** the sort key (`id`) carries no chronological meaning, so no test asserts anything about
> creation order — only that the order matches an independently-computed ascending sort of the
> returned ids (QF-06); no test asserts "system category" retrieval, because no such row exists to
> construct (QF-08).

### Test Implementation Map *(filled at step 4)*

All under `backend/tests/integration/test_cm_us_02_list_categories.py`. Run one with
`uv run pytest -k <fragment>`.

| TC | pytest node id | Result |
|---|---|---|
| TC-18 | `test_authenticated_user_lists_every_category_they_own_with_accurate_total` | PASS |
| TC-19 | `test_response_item_exposes_exactly_four_fields_wrapped_in_paginated_envelope` | PASS |
| TC-20 | `test_user_with_no_categories_yet_receives_empty_list_and_zero_total` | PASS |
| TC-21 | `test_unauthenticated_or_invalid_credential_caller_is_denied_with_401` | PASS |
| TC-22 | `test_credentials_are_evaluated_before_any_query_parameter` | PASS |
| TC-23 | `test_default_page_is_1_of_size_25_with_accurate_total` | PASS |
| TC-24 | `test_explicit_page_and_page_size_within_range_return_that_page_and_accurate_total` | PASS |
| TC-25 | `test_a_user_only_ever_sees_their_own_categories_never_another_users` | PASS |
| TC-26 | `test_reported_total_counts_only_callers_own_categories_even_when_smaller` | PASS |
| TC-27 | `test_list_is_returned_in_stable_order_matching_ids_sorted_ascending` | PASS |
| TC-28 | `test_a_non_positive_or_non_integer_page_is_rejected_with_422` (3 params) | PASS |
| TC-29 | `test_a_non_positive_or_non_integer_page_size_is_rejected_with_422` (3 params) | PASS |
| TC-30 | `test_a_page_size_above_the_maximum_is_rejected_with_422` | PASS |
| TC-31 | `test_a_page_beyond_the_last_available_page_returns_an_empty_list_with_accurate_total` | PASS |
| TC-32 | `test_a_page_size_of_exactly_100_is_accepted` | PASS |
| TC-33 | `test_paging_through_every_page_returns_every_category_exactly_once_in_stable_order` | PASS |
| TC-34 | `test_admin_role_caller_who_also_owns_a_category_sees_only_their_own` | PASS |

Full suite: `391 passed` (370 pre-existing + 21 new — 17 TCs, 2 parametrized ×3 values each: TC-28,
TC-29). `ruff check`/`ruff format --check` clean, `mypy app` clean. Coverage measured at the Implement
step (see gate message) — every file this story touched (`schemas/category.py`,
`repositories/category_repo.py`, `services/category_service.py`, `api/v1/categories.py`) is reported
against constitution DOD-03's 80% floor. No defect found in the implementation while writing these
tests — every TC passed against the first version of the code; the only correction needed was a
`ruff format` pass on the test file itself (line-wrap style), not a behavioural fix.

---

### TC-18: An authenticated User lists every category they own — 200 with all categories and an accurate total

- **US:** CM-US-02
- **Given:** An authenticated User who owns three categories of both types, created via `POST /api/v1/categories`
- **When:** The User requests the list of categories
- **Then:** The response is `200`; `items` contains all three categories, each carrying `id`, `user_id` equal to the caller's id, `name`, and `type`; `total` is `3`
- **AC:** AC-01, FR-01, FR-02, FR-06, FR-09, BR-05
- **Type:** integration

### TC-19: The response item exposes exactly the four documented fields, wrapped in the paginated envelope

- **US:** CM-US-02
- **Given:** An authenticated User with one existing category
- **When:** The User requests the list of categories
- **Then:** The response is `200`; the top-level body exposes exactly the keys `items`, `total`, `page`, `page_size`; each entry in `items` exposes **exactly** the keys `id`, `user_id`, `name`, `type` — no more, and in particular no `icon` and no marker distinguishing a "system" category (plan.md A7, QF-08)
- **AC:** AC-01, AC-09, FR-02, PF-03
- **Type:** integration

### TC-20: A User with no categories yet receives an empty list and a zero total

- **US:** CM-US-02
- **Given:** An authenticated User who owns no categories
- **When:** The User requests the list of categories
- **Then:** The response is `200`, not an error; `items` is an empty list and `total` is `0`
- **AC:** AC-02, FR-01
- **Type:** integration

### TC-21: An unauthenticated or invalid-credential caller is denied with 401

- **US:** CM-US-02
- **Given:** A caller presenting no `Authorization` header, and separately a caller presenting an expired token
- **When:** Each attempts to list categories
- **Then:** Both responses are `401` with `error_code` `NOT_AUTHENTICATED`; no `items` are returned
- **AC:** AC-03, FR-03
- **Type:** integration

### TC-22: Credentials are evaluated before any query parameter

- **US:** CM-US-02
- **Given:** A caller presenting no credentials
- **When:** The list is requested with an out-of-range `page` value (`page=0`)
- **Then:** The response is `401` `NOT_AUTHENTICATED`, not `422` — an unauthenticated caller learns nothing about the validity of their query parameters, mirroring WM-US-02 TC-27's ordering
- **AC:** AC-03, FR-03
- **Type:** integration

### TC-23: The default page is 1 of size 25, with an accurate total

- **US:** CM-US-02
- **Given:** An authenticated User and three existing categories they own
- **When:** The list is requested with no `page` or `page_size` supplied
- **Then:** The response is `200`; `page` is `1`, `page_size` is `25`, `items` contains all three categories, and `total` is `3`
- **AC:** AC-04, FR-04, FR-06, BR-02
- **Type:** integration

### TC-24: An explicit page and page size within range return that page and an accurate total

- **US:** CM-US-02
- **Given:** An authenticated User and five categories they own
- **When:** The list is requested with `page=2` and `page_size=2`
- **Then:** The response is `200`; `page` is `2`, `page_size` is `2`, `items` contains exactly two of the User's own categories, and `total` is `5`
- **AC:** AC-05, FR-04, FR-06
- **Type:** integration

### TC-25: A User only ever sees their own categories, never another User's

- **US:** CM-US-02
- **Given:** Two authenticated Users, `A` (two categories) and `B` (three categories)
- **When:** `A` requests the list of categories
- **Then:** The response is `200`; `items` contains exactly `A`'s two categories — none of `B`'s three — and `total` is `2`, not `5`
- **AC:** AC-07, FR-07, FR-10, BR-01, BR-04 *(assertion technique per QF-05)*
- **Type:** integration

### TC-26: The reported total counts only the caller's own categories, even when it is the smaller number

- **US:** CM-US-02
- **Given:** Two authenticated Users, `A` (no categories) and `B` (four categories)
- **When:** `A` requests the list of categories
- **Then:** The response is `200`; `items` is empty and `total` is `0` — not `4`, and not any count reflecting `B`'s categories
- **AC:** AC-02, AC-07, FR-07, FR-10, BR-04 *(assertion technique per QF-05)*
- **Type:** integration

### TC-27: The list is returned in a stable order matching the categories' ids sorted ascending

- **US:** CM-US-02
- **Given:** An authenticated User who creates five categories in an order that does not already match ascending id order (confirmed from the ids the creation calls actually returned)
- **When:** The User requests the list of categories twice, with nothing created, changed, or removed in between
- **Then:** Both responses return the same five categories in the same relative order, and that order equals the five ids sorted ascending as strings — not the order the categories were created in
- **AC:** AC-08, FR-08, BR-03 *(assertion technique per QF-06)*
- **Type:** integration

### TC-28: A `page` that is not a positive integer is rejected with 422

- **US:** CM-US-02
- **Given:** An authenticated User
- **When:** The list is requested with `page` set to each of `0`, `-1`, and `"abc"` in turn
- **Then:** Each response is `422` with `error_code` `VALIDATION_ERROR` and a `details.fields` entry locating `page`; no `items` are returned
- **AC:** AC-06, FR-05, BR-02
- **Type:** integration

### TC-29: A `page_size` that is not a positive integer is rejected with 422

- **US:** CM-US-02
- **Given:** An authenticated User
- **When:** The list is requested with `page_size` set to each of `0`, `-1`, and `"abc"` in turn
- **Then:** Each response is `422` with `error_code` `VALIDATION_ERROR` and a `details.fields` entry locating `page_size`; no `items` are returned
- **AC:** AC-06, FR-05, BR-02
- **Type:** integration

### TC-30: A `page_size` above the maximum is rejected with 422

- **US:** CM-US-02
- **Given:** An authenticated User
- **When:** The list is requested with `page_size=101`
- **Then:** The response is `422` `VALIDATION_ERROR` identifying `page_size`; the request is not silently capped at 100
- **AC:** AC-06, EC-02, FR-05, BR-02
- **Type:** integration

### TC-31: A page beyond the last available page returns an empty list with the accurate total

- **US:** CM-US-02
- **Given:** An authenticated User and three categories they own
- **When:** The list is requested with `page=5` and `page_size=25`
- **Then:** The response is `200`, not `404`; `items` is an empty list and `total` is still `3`
- **AC:** EC-01, FR-06
- **Type:** integration

### TC-32: A `page_size` of exactly 100 is accepted

- **US:** CM-US-02
- **Given:** An authenticated User
- **When:** The list is requested with `page_size=100`
- **Then:** The response is `200` — the cap is a ceiling, not a target: 100 is honoured, only 101 is rejected (TC-30)
- **AC:** EC-02, FR-05
- **Type:** integration

### TC-33: Paging through every page returns every category exactly once, in stable order

- **US:** CM-US-02
- **Given:** An authenticated User and five categories they own, created in an order that does not already match ascending id order
- **When:** Every page is fetched in turn with `page_size=2` (`page=1`, `page=2`, `page=3`)
- **Then:** The concatenation of all three pages' `items` contains every one of the five categories exactly once, with no duplicate and no gap, in the same ascending-id order TC-27 established, stable across the page boundaries
- **AC:** EC-03, FR-08, BR-03 *(assertion technique per QF-06)*
- **Type:** integration

### TC-34: An ADMIN-role caller who also owns a category sees only their own through this endpoint

- **US:** CM-US-02
- **Given:** An authenticated User whose role is `ADMIN` and owns one category, and a second User (any role) who owns two categories of their own
- **When:** The ADMIN requests the list of categories
- **Then:** The response is `200`; `items` contains exactly the ADMIN's own one category — never either of the other User's — and `total` is `1`
- **AC:** EC-04, FR-10, BR-01 *(assertion technique per QF-07)*
- **Type:** integration
