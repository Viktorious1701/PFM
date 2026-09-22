# Test Cases: Category Management (CM)

> **Feature:** SRS §6 Feature-04 · SDS §5.4 (CM)
> **Spec:** [spec.md](spec.md) · **Plan:** [plan.md](plan.md)
> **Stories in this file:** CM-US-01 *(TC-01…TC-17)*

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

Not yet populated — CM-US-01 is at the Quality step (steps 1–3 of the AIF-SDLC cycle). This table is extended with real pytest node ids and PASS/FAIL/BLOCKED results once the Implement step (step 4) writes `backend/tests/integration/test_cm_us_01_create_category.py` from the test cases below, per `constitution.md` DOD-07.

| TC | pytest node id | Result |
|---|---|---|
| TC-01 | *(pending Step 4)* | PENDING |
| TC-02 | *(pending Step 4)* | PENDING |
| TC-03 | *(pending Step 4)* | PENDING |
| TC-04 | *(pending Step 4)* | PENDING |
| TC-05 | *(pending Step 4)* | PENDING |
| TC-06 | *(pending Step 4)* | PENDING |
| TC-07 | *(pending Step 4)* | PENDING |
| TC-08 | *(pending Step 4)* | PENDING |
| TC-09 | *(pending Step 4)* | PENDING |
| TC-10 | *(pending Step 4)* | PENDING |
| TC-11 | *(pending Step 4)* | PENDING |
| TC-12 | *(pending Step 4)* | PENDING |
| TC-13 | *(pending Step 4)* | PENDING |
| TC-14 | *(pending Step 4)* | PENDING |
| TC-15 | *(pending Step 4)* | PENDING |
| TC-16 | *(pending Step 4)* | PENDING |
| TC-17 | *(pending Step 4)* | PENDING |

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
