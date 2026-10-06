# Test Cases: Category Management (CM)

> **Feature:** SRS §6 Feature-04 · SDS §5.4 (CM)
> **Spec:** [spec.md](spec.md) · **Plan:** [plan.md](plan.md)
> **Stories in this file:** CM-US-01 *(TC-01…TC-17, all PASS)* · CM-US-02 *(TC-18…TC-34, all PASS)* · CM-US-04 *(TC-35…TC-63)*

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

---

## CM-US-04: Update a Category

> **IDs in this section are local to CM-US-04** — except `TC-NN`, which continues this epic file's own
> numbering. **Correction to this dispatch's own briefing:** the brief that started this work stated the
> epic's last entries were `TC-34`/`QF-12`; direct re-reading of this file before writing anything here
> shows the last **heading** in this file is `#### QF-08` (CM-US-02's own last finding) — the strings
> `QF-10` and `QF-12` that appear inside CM-US-02's own `QF-05`/`QF-08` prose are cross-references to
> **other epics'** own finding numbers (TM-US-02's `QF-10`/`QF-12`, for its join-based ownership check and
> its own un-constructable-case precedent respectively), not local headings in this file. Confirmed by
> `grep -n '^#### QF-' test_cases.md`, which returns only `QF-01`…`QF-08`. This story therefore continues
> from `TC-35` (correct as briefed) and `QF-09` (not `QF-13`).

### Quality Findings

#### QF-09

**Description.** AC-03/AC-04 require a category reference that does not exist at all and one that exists
but belongs to a different User to produce "the same not-found outcome" — mirrors BM-US-04 QF-16, now
applied to a category's own id. `plan.md` A3 makes this true by construction, since
`category_repo.get_owned_by_id()` filters by `user_id` in the query itself and returns `None` either way.
A test that merely checks both cases return *some* `404` would not distinguish "genuinely identical" from
"two different messages that both happen to carry status 404."

**Impact.** A weaker test could pass even if a future change accidentally made the two cases
distinguishable — for instance, a message that only names "belongs to another account" in the
ownership-mismatch case, itself a minor information leak about another User's data.

**Recommendation.** `TC-44` compares the full response body of the ownership-mismatch case against
`TC-43`'s not-found-at-all case and asserts they match exactly — `error_code`, `message`, and `details`
all identical, not merely the status code. Directly mirrors BM-US-04 QF-16/TC-68.

#### QF-10

**Description.** AC-11's claim that every unsubmitted field is left unchanged could be satisfied by a
test that only reads the `PATCH` response body — a service bug that mutated more than the submitted
fields on the stored row, while still constructing a response DTO from stale in-memory values, would pass
such a test undetected. This is the identical risk BM-US-04 QF-19 already named for Budget's own
`wallet_id`/`category_id`/`period`, now with the added twist that this story has *three* independently
optional fields instead of one always-untouched trio, so the risk is not just "did anything besides the
mutable field change" but "did submitting only *some* of the mutable fields still leave the others
genuinely untouched in storage, not merely reset to their current value by a careless 'update everything'
implementation."

**Impact.** A regression that let `update_category()` unconditionally overwrite all three columns
(ignoring which were actually submitted) would still produce a correct-looking response for the single
field the test checks, while silently corrupting or blanking the other two in storage, with every
response-body-only test still passing.

**Recommendation.** `TC-36`/`TC-37`/`TC-38` each submit exactly **one** of `name`/`type`/`icon`, and each
asserts both the response body **and** a direct read of the stored `categories` row through the test's
own `db` session for **all three** fields — the two not submitted must equal their pre-update values
exactly, not merely "some value."

#### QF-11

**Description.** AC-05 requires a submission naming none of `name`/`type`/`icon` to be refused. Because
this is the first cross-field (not per-field) validation rule in this story's own DTO, a weak test could
submit a body that is invalid for an unrelated reason (e.g. a field with the wrong JSON type) and observe
a `422`, without that `422` actually having been raised by *this* rule.

**Impact.** A future refactor that silently dropped the `model_validator` — for instance, during a change
that converts `CategoryUpdate` to use `exclude_unset` semantics — could pass a loosely-written test while
no longer rejecting a syntactically well-formed but semantically empty submission such as `{}`.

**Recommendation.** `TC-47` submits a body that is valid JSON and would deserialize cleanly into
`CategoryUpdate` but names none of the three fields (an empty object, `{}`), and asserts the `422`
response's `details`/`message` identifies the cross-field rule specifically (not a single field name),
distinguishing it from `TC-48`/`TC-51`/`TC-54`'s per-field `422`s.

#### QF-12

**Description.** EC-10/BR-04 — that changing a category's `type` has no retroactive effect on any
existing Transaction or Budget computation — is the single most consequential claim this story makes
beyond ordinary field-update mechanics (`plan.md` A13), and it is also the easiest one to get
"accidentally right" in a test that never actually creates the Transaction/Budget data that would reveal
a regression. A test that only PATCHes a category's `type` and checks the `200` response proves nothing
about history.

**Impact.** A future change that, for instance, added an eager "recompute dependent Transactions" step to
`update_category()` — plausible-looking defensive code a well-meaning future contributor might add,
believing it keeps data "consistent" — would silently violate FR-12/BR-04 while every test that does not
construct prior Transaction/Budget data first would keep passing.

**Recommendation.** `TC-60` creates a Transaction against a category **before** changing that category's
`type`, then re-reads the Transaction row directly and asserts its own stored `type` is exactly what it
was at creation — never the category's new `type`. `TC-61` does the equivalent for a Budget's computed
`amount_spent`/`status` on a subsequent list call. `TC-62` demonstrates the one real, forward-looking
consequence: a *new* Transaction of the category's *old* type, submitted after the type change, is
refused by TM-US-01's own existing `TRANSACTION_CATEGORY_TYPE_MISMATCH` check — proving the existing rule
correctly sees the new type, not that this story invented a new one.

#### QF-13

**Description.** `plan.md` A12 records that submitting `"icon": null` and omitting `icon` entirely are
indistinguishable by design — both leave the current value unchanged. A test that only checks "omitting
icon leaves it unchanged" would not also prove the (deliberately identical) behaviour for an explicit
`null`, leaving half of A12's own claim unverified.

**Impact.** A future change that accidentally implemented `exclude_unset`-style semantics only for the
omitted case — treating an explicit `"icon": null` as "clear the icon" while treating a missing key as
"leave unchanged" — would contradict A12 while a test that never submits an explicit `null` would not
catch it.

**Recommendation.** `TC-38` submits `icon` as an explicit value to set it; a companion assertion within
the same test submits a follow-up `PATCH` with `"icon": null` alongside a `name` change and confirms the
icon set by the previous call is still present afterward, unchanged — not cleared.

### Acceptance Criteria Classification

No category-update screen exists in `mobile/` this round, and no SRS UXR names one — the same basis
CM-US-01/CM-US-02 and BM-US-04 each used for their own all-`[API]` classification.

| AC/EC | Title | Label | Rationale |
|---|---|---|---|
| AC-01 | Successfully update one or more of name, type, and icon | **[API]** | No UI surface exists or is named by any UXR this round |
| AC-02 | Deny access to unauthenticated callers | **[API]** | Backend authorization contract |
| AC-03 | Reject an update to a category that does not exist | **[API]** | Persistence/ownership contract; bounded by QF-09 |
| AC-04 | Reject an update to a category owned by a different User | **[API]** | Persistence/ownership contract; bounded by QF-09 |
| AC-05 | Reject a submission naming none of name, type, or icon | **[API]** | Cross-field validation contract; bounded by QF-11 |
| AC-06 | Reject a blank name, when a name is submitted | **[API]** | Payload validation |
| AC-07 | Reject a name exceeding the maximum length, when submitted | **[API]** | Payload validation |
| AC-08 | Reject a type value that is not exactly INCOME/EXPENSE, when submitted | **[API]** | Payload validation |
| AC-09 | Reject a blank icon, when an icon is submitted | **[API]** | Payload validation |
| AC-10 | Reject an icon exceeding the maximum length, when submitted | **[API]** | Payload validation |
| AC-11 | A successful update changes only the submitted field(s) | **[API]** | Response/persistence contract; bounded by QF-10 |
| AC-12 | Return exactly the documented category fields | **[API]** | Response-payload contract |
| EC-01 | Type submitted in lowercase or mixed case | **[API]** | Payload validation |
| EC-02 | Name with surrounding whitespace | **[API]** | Persistence-shape (trimming) |
| EC-03 | Updated name matches another of the caller's own categories' names | **[API]** | Backend rule (absence of a uniqueness constraint) |
| EC-04 | More than one validation failure in a single submission | **[API]** | Backend validation-grouping contract |
| EC-05 | Unrecognised `user_id` field submitted alongside valid fields | **[API]** | Structural-ignore / ownership-immutability contract |
| EC-06 | Icon submitted for the first time, and changed a second time | **[API]** | Backend rule — not a special-cased no-op |
| EC-07 | Icon with surrounding whitespace | **[API]** | Persistence-shape (trimming) |
| EC-08 | A category reference that is not a well-formed identifier | **[API]** | Backend rule (no separate format validation) |
| EC-09 | Type submitted with surrounding whitespace | **[API]** | Payload validation |
| EC-10 | A category's type changed after a Transaction or Budget references it | **[API]** | Cross-story composition with TM-US-01/BM-US-02; bounded by QF-12 |
| EC-11 | A caller who owns a different category attempts to update another User's category | **[API]** | Persistence/ownership contract; bounded by QF-09 |
| EC-12 | Icon at the maximum supported length | **[API]** | Boundary value |

### Coverage Matrix

| AC/EC | Label | Integration TC(s) | E2E TC(s) |
|---|---|---|---|
| AC-01 | [API] | TC-35, TC-36, TC-37, TC-38, TC-39 | — |
| AC-02 | [API] | TC-41, TC-42 | — |
| AC-03 | [API] | TC-43 | — |
| AC-04 | [API] | TC-44 | — |
| AC-05 | [API] | TC-47 | — |
| AC-06 | [API] | TC-48 | — |
| AC-07 | [API] | TC-49 | — |
| AC-08 | [API] | TC-51 | — |
| AC-09 | [API] | TC-54 | — |
| AC-10 | [API] | TC-55 | — |
| AC-11 | [API] | TC-36, TC-37, TC-38, TC-58 | — |
| AC-12 | [API] | TC-59 | — |
| EC-01 | [API] | TC-52 | — |
| EC-02 | [API] | TC-50 | — |
| EC-03 | [API] | TC-40 | — |
| EC-04 | [API] | TC-57 | — |
| EC-05 | [API] | TC-58 | — |
| EC-06 | [API] | TC-38, TC-39 | — |
| EC-07 | [API] | TC-56 | — |
| EC-08 | [API] | TC-45 | — |
| EC-09 | [API] | TC-53 | — |
| EC-10 | [API] | TC-60, TC-61, TC-62 | — |
| EC-11 | [API] | TC-46 | — |
| EC-12 | [API] | TC-63 | — |

> Every AC and EC has at least one integration TC. There is no `[BOTH]` or `[UI]` row — no
> category-update screen exists this round, and none is named by any SRS UXR. **Known coverage limits,
> accepted:** none — unlike CM-US-02 (QF-08, the "system category" question) and CM-US-01 (QF-04,
> `icon`'s own absence), this story's own contract has no construction the public API cannot reach; every
> AC/EC here is directly testable through `PATCH /api/v1/categories/{category_id}` and direct row reads.

### Test Implementation Map *(filled at step 4)*

All under `backend/tests/integration/test_cm_us_04_update_category.py`, plus the one-line amendments to
`test_cm_us_01_create_category.py` (`TC-14`) and `test_cm_us_02_list_categories.py` (`TC-19`) `plan.md`
A6/T-07 records. Run one with `uv run pytest -k <fragment>`.

| TC | pytest node id | Result |
|---|---|---|
| TC-35 … TC-63 | *(assigned at the Implement step)* | Not yet run |

---

### TC-35: An authenticated User updates all three fields in one request — 200 with all three updated

- **US:** CM-US-04
- **Given:** An authenticated User who owns a category with `name` `"Utilities"`, `type` `"EXPENSE"`, no icon
- **When:** `PATCH /api/v1/categories/{id}` is sent with `name` `"Bills"`, `type` `"INCOME"`, `icon` `"receipt"`
- **Then:** The response is `200`; the body carries `id` unchanged, `user_id` equal to the caller's id, `name` `"Bills"`, `type` `"INCOME"`, `icon` `"receipt"`
- **AC:** AC-01, FR-01, FR-09
- **Type:** integration

### TC-36: Updating only `name` leaves `type` and `icon` unchanged, verified in storage

- **US:** CM-US-04
- **Given:** An authenticated User who owns a category with `name` `"Utilities"`, `type` `"EXPENSE"`, `icon` `"bolt"` (set via a prior update)
- **When:** A `PATCH` is submitted with only `name` `"Bills"`
- **Then:** The response is `200` with `name` `"Bills"`, `type` `"EXPENSE"`, `icon` `"bolt"`; a direct read of the `categories` row confirms `type` and `icon` columns are unchanged
- **AC:** AC-01, AC-11, FR-08 *(assertion technique per QF-10)*
- **Type:** integration

### TC-37: Updating only `type` leaves `name` and `icon` unchanged, verified in storage

- **US:** CM-US-04
- **Given:** An authenticated User who owns a category with `name` `"Utilities"`, `type` `"EXPENSE"`, `icon` `"bolt"`
- **When:** A `PATCH` is submitted with only `type` `"INCOME"`
- **Then:** The response is `200` with `name` `"Utilities"`, `type` `"INCOME"`, `icon` `"bolt"`; a direct read of the `categories` row confirms `name` and `icon` columns are unchanged
- **AC:** AC-01, AC-11, FR-08 *(assertion technique per QF-10)*
- **Type:** integration

### TC-38: Updating only `icon` for the first time leaves `name`/`type` unchanged; a later explicit null does not clear it

- **US:** CM-US-04
- **Given:** An authenticated User who owns a category with `name` `"Utilities"`, `type` `"EXPENSE"`, and no `icon` set
- **When:** A `PATCH` is submitted with only `icon` `"bolt"`; then a second `PATCH` is submitted with `name` `"Bills"` and `icon` explicitly `null`
- **Then:** After the first call, the response and the stored row both show `icon` `"bolt"`, `name`/`type` unchanged; after the second call, `name` is `"Bills"` and `icon` is still `"bolt"` — the explicit `null` did not clear it
- **AC:** AC-01, AC-11, EC-06, FR-08 *(assertion technique per QF-10, QF-13)*
- **Type:** integration

### TC-39: Changing an already-set icon to a different value succeeds as an ordinary update

- **US:** CM-US-04
- **Given:** An authenticated User who owns a category with `icon` already set to `"bolt"`
- **When:** A `PATCH` is submitted with `icon` `"flash"`
- **Then:** The response is `200` with `icon` `"flash"`; the stored row confirms it, not a conflict or no-op
- **AC:** AC-01, EC-06
- **Type:** integration

### TC-40: An updated name matching another of the caller's own categories' names still succeeds

- **US:** CM-US-04
- **Given:** An authenticated User who owns two categories, `"Utilities"` and `"Groceries"`
- **When:** A `PATCH` renames `"Groceries"` to `"Utilities"`
- **Then:** The response is `200` with `name` `"Utilities"`; both categories now share the name, each with its own distinct id
- **AC:** EC-03, FR-11, BR-03
- **Type:** integration

### TC-41: An unauthenticated caller is denied with 401

- **US:** CM-US-04
- **Given:** A caller presenting no `Authorization` header
- **When:** A category update is submitted with an otherwise valid payload against a real category
- **Then:** The response is `401` with `error_code` `NOT_AUTHENTICATED`; the target category's stored fields are unchanged
- **AC:** AC-02, FR-02
- **Type:** integration

### TC-42: Credentials are evaluated before the payload

- **US:** CM-US-04
- **Given:** A caller presenting no credentials
- **When:** A `PATCH` is submitted against a real category id with an empty body (`{}`, otherwise a 422-triggering payload)
- **Then:** The response is `401` `NOT_AUTHENTICATED`, not `422` — an unauthenticated caller learns nothing about the validity of their payload, mirroring CM-US-02 TC-22's ordering
- **AC:** AC-02, FR-02
- **Type:** integration

### TC-43: A category_id matching no category at all is rejected with 404 CATEGORY_NOT_FOUND

- **US:** CM-US-04
- **Given:** An authenticated User
- **When:** `PATCH /api/v1/categories/{id}` is sent with a `category_id` that matches no category in the system
- **Then:** The response is `404` with `error_code` `CATEGORY_NOT_FOUND`; nothing is changed
- **AC:** AC-03, FR-03
- **Type:** integration

### TC-44: A category_id belonging to a different User is rejected with the identical outcome as TC-43

- **US:** CM-US-04
- **Given:** Two authenticated Users `A` and `B`, where `B` owns a category
- **When:** `A` submits a `PATCH` against `B`'s `category_id`
- **Then:** The response is `404`; its `error_code`, `message`, and `details` are identical to TC-43's response; `B`'s category is unchanged
- **AC:** AC-04, FR-03 *(assertion technique per QF-09)*
- **Type:** integration

### TC-45: A category reference that is not a well-formed identifier gets the same outcome as a well-formed but non-existent one

- **US:** CM-US-04
- **Given:** An authenticated User
- **When:** `PATCH /api/v1/categories/not-a-real-id` is sent with a valid payload
- **Then:** The response is `404` `CATEGORY_NOT_FOUND`, identical to TC-43's response
- **AC:** EC-08, FR-03
- **Type:** integration

### TC-46: A caller who owns a different category of their own cannot update another User's category

- **US:** CM-US-04
- **Given:** Two authenticated Users, `A` (owns category `CA`) and `B` (owns category `CB`)
- **When:** `A` submits a `PATCH` against `CB`'s `category_id`
- **Then:** The response is `404` `CATEGORY_NOT_FOUND`, identical to TC-43/TC-44's responses; `CB` is unchanged, and `A`'s own `CA` is also unaffected
- **AC:** EC-11, FR-03
- **Type:** integration

### TC-47: A submission naming none of name, type, or icon is rejected with 422, identifying the cross-field rule

- **US:** CM-US-04
- **Given:** An authenticated User who owns a category
- **When:** A `PATCH` is submitted with an empty JSON body, `{}`
- **Then:** The response is `422` `VALIDATION_ERROR` whose `details`/`message` names the "at least one field" rule, not a single field; nothing is changed
- **AC:** AC-05, FR-04, BR-02 *(assertion technique per QF-11)*
- **Type:** integration

### TC-48: A blank or whitespace-only name, when submitted, is rejected with 422

- **US:** CM-US-04
- **Given:** An authenticated User who owns a category
- **When:** A `PATCH` is submitted with `name` `""` and, separately, `"   "`
- **Then:** Each response is `422` `VALIDATION_ERROR` identifying the `name` field; nothing is persisted
- **AC:** AC-06, FR-05
- **Type:** integration

### TC-49: A name exceeding 100 characters, when submitted, is rejected, not truncated

- **US:** CM-US-04
- **Given:** An authenticated User who owns a category
- **When:** A `PATCH` is submitted with a `name` of 101 characters
- **Then:** The response is `422` `VALIDATION_ERROR`; the stored name is unchanged, not truncated
- **AC:** AC-07, FR-05
- **Type:** integration

### TC-50: A name with surrounding whitespace is stored trimmed

- **US:** CM-US-04
- **Given:** An authenticated User who owns a category
- **When:** A `PATCH` is submitted with `name` `"  Bills  "`
- **Then:** The response is `200`; the persisted `name` is `"Bills"` — interior spacing preserved, surrounding whitespace removed
- **AC:** EC-02, FR-05
- **Type:** integration

### TC-51: A type value that is neither INCOME nor EXPENSE, when submitted, is rejected with 422

- **US:** CM-US-04
- **Given:** An authenticated User who owns a category
- **When:** A `PATCH` is submitted with `type` in turn `"SAVINGS"`, `"TRANSFER"`, and `""`
- **Then:** Each response is `422` `VALIDATION_ERROR` whose `details` names the `type` field; nothing is persisted
- **AC:** AC-08, FR-06
- **Type:** integration

### TC-52: A lowercase or mixed-case type value, when submitted, is rejected, not case-folded

- **US:** CM-US-04
- **Given:** An authenticated User who owns a category
- **When:** A `PATCH` is submitted with `type` `"expense"` and, separately, `"Income"`
- **Then:** Each response is `422` `VALIDATION_ERROR` whose `details` names the `type` field; the stored `type` is unchanged — not case-folded and accepted
- **AC:** EC-01, FR-06
- **Type:** integration

### TC-53: A type value with surrounding whitespace, when submitted, is rejected, not trimmed

- **US:** CM-US-04
- **Given:** An authenticated User who owns a category
- **When:** A `PATCH` is submitted with `type` `" EXPENSE"` and, separately, `"INCOME "`
- **Then:** Each response is `422` `VALIDATION_ERROR` whose `details` names the `type` field; the stored `type` is unchanged — unlike `name`/`icon`, `type` receives no trimming
- **AC:** EC-09, FR-06
- **Type:** integration

### TC-54: A blank or whitespace-only icon, when submitted, is rejected with 422

- **US:** CM-US-04
- **Given:** An authenticated User who owns a category
- **When:** A `PATCH` is submitted with `icon` `""` and, separately, `"   "`
- **Then:** Each response is `422` `VALIDATION_ERROR` identifying the `icon` field; nothing is persisted
- **AC:** AC-09, FR-07
- **Type:** integration

### TC-55: An icon exceeding 50 characters, when submitted, is rejected, not truncated

- **US:** CM-US-04
- **Given:** An authenticated User who owns a category
- **When:** A `PATCH` is submitted with an `icon` of 51 characters
- **Then:** The response is `422` `VALIDATION_ERROR`; the stored icon is unchanged, not truncated
- **AC:** AC-10, FR-07
- **Type:** integration

### TC-56: An icon with surrounding whitespace is stored trimmed

- **US:** CM-US-04
- **Given:** An authenticated User who owns a category
- **When:** A `PATCH` is submitted with `icon` `"  shopping-cart  "`
- **Then:** The response is `200`; the persisted `icon` is `"shopping-cart"` — interior spacing preserved, surrounding whitespace removed
- **AC:** EC-07, FR-07
- **Type:** integration

### TC-57: Multiple validation failures in one submission are reported together

- **US:** CM-US-04
- **Given:** An authenticated User who owns a category
- **When:** A `PATCH` is submitted with `name` `""` and `type` `"SAVINGS"` in the same request
- **Then:** The response is a single `422` whose `details` identifies both the `name` and the `type` fields — not just the first one encountered
- **AC:** EC-04, FR-10
- **Type:** integration

### TC-58: A successful update never changes the category's owner, even when an unrecognised user_id is submitted

- **US:** CM-US-04
- **Given:** Two authenticated Users, `A` (owns a category) and `B`
- **When:** `A` submits a `PATCH` against their own category with an otherwise valid `name` change that additionally includes an unrecognised `"user_id": "<B's id>"` key in the JSON body
- **Then:** The response is `200`; the updated category's `user_id` is still `A`'s id, never `B`'s — verified both in the response and by a direct read of the stored row
- **AC:** AC-11, EC-05, FR-08, BR-05 *(assertion technique per CM-US-01 QF-01/TC-12)*
- **Type:** integration

### TC-59: The response exposes exactly the five documented fields

- **US:** CM-US-04
- **Given:** An authenticated User who owns a category
- **When:** An update is submitted successfully
- **Then:** The response body's keys are exactly `id`, `user_id`, `name`, `type`, `icon` — no more
- **AC:** AC-12, FR-09
- **Type:** integration

### TC-60: Changing a category's type does not alter an existing Transaction's own stored type

- **US:** CM-US-04
- **Given:** An authenticated User with a wallet, a category of type `EXPENSE`, and a Transaction of type `EXPENSE` already recorded against that wallet and category
- **When:** The category's `type` is updated to `INCOME`
- **Then:** The response is `200`; a direct read of the `transactions` row for that Transaction shows its own `type` is still `EXPENSE`, unchanged
- **AC:** EC-10, FR-12, BR-04 *(per QF-12)*
- **Type:** integration

### TC-61: Changing a category's type does not alter a Budget's already-recorded spend computation

- **US:** CM-US-04
- **Given:** An authenticated User with a wallet, a category of type `EXPENSE`, a Budget for that wallet and category, and an `EXPENSE` Transaction of `150.00` already recorded against them, contributing to the Budget's `amount_spent`
- **When:** The category's `type` is updated to `INCOME`, and the User then requests `GET /api/v1/budgets`
- **Then:** The listed Budget's `amount_spent` is still `150.00`, reflecting the pre-existing Transaction exactly as before the type change — the sum is not recomputed away because the category's type no longer matches
- **AC:** EC-10, FR-12, BR-04 *(per QF-12; cross-story composition with BM-US-02)*
- **Type:** integration

### TC-62: After a type change, a new Transaction of the category's old type is refused by TM-US-01's own existing check

- **US:** CM-US-04
- **Given:** An authenticated User with a category whose `type` was `EXPENSE` and has just been updated to `INCOME`
- **When:** The User attempts to create a new Transaction of type `EXPENSE` against that category
- **Then:** The response is `409` `TRANSACTION_CATEGORY_TYPE_MISMATCH` — TM-US-01's own existing rule, now correctly evaluated against the category's new type; this story introduces no new rule to produce this outcome
- **AC:** EC-10, FR-12 *(per QF-12; cross-story composition with TM-US-01)*
- **Type:** integration

### TC-63: An icon of exactly 50 characters is accepted

- **US:** CM-US-04
- **Given:** An authenticated User who owns a category
- **When:** A `PATCH` is submitted with an `icon` of exactly 50 characters
- **Then:** The response is `200`; the stored `icon` is the full 50-character value — the cap is a ceiling, not a target: 50 is honoured, only 51 is rejected (TC-55)
- **AC:** EC-12, FR-07
- **Type:** integration
