# Feature Specification: Category Management (CM)

> **Feature:** SRS §6 Feature-04 · SDS §5.4 (CM)
> **Spec:** [spec.md](spec.md)
> **Stories in this file:** CM-US-01 *(specified)*

---

## Source *(scope extraction — CLAUDE.md §1 scope rule)*

Only the sections below entered the working context for CM-US-01.

**SRS §6 Feature-04 · US-04-01 — Create a Category [MVP]**
> * **As an** Authenticated User
> * **I want to** create custom categories for income and expenses
> * **So that** I can organize my financial transactions.
>
> ```gherkin
> Feature: Create Category
>
>   Scenario: Create an expense category
>     Given the User is logged in
>     When the User enters category name "Groceries"
>     And the User selects category type "EXPENSE"
>     And the User clicks "Save Category"
>     Then the System saves the category under the user's account
> ```

**SRS §1.5 Conceptual Domain Model**
> **Category** — A label a User defines to classify money movement as one kind of income or expense, e.g. "Groceries" or "Salary" (FR-04).
>
> | Relationship | Cardinality | Meaning |
> | User defines Category | one User → many Categories | Categories belong to the User who created them, not to a shared list (FR-04) |

**SRS §2 FR-04 — Category Management**
> The System shall support user-defined Categories classified as either `INCOME` or `EXPENSE` (e.g., Groceries, Rent, Salary, Utilities).

**SDS §5.4.1 CM-US-01: Create a Category (USER)**
> * **Goal:** Define custom categories for classifying income and expense transactions.

**SDS §2.2 Domain Object** *(Category row, as aligned — see `plan.md` G1)*
> **Category:** Classification for monetary activities (`id`, `user_id`, `name`, `type`, `icon`).

**SDS §4.3.3 Data Design — `CATEGORIES` ERD** *(as aligned — `icon` added, see `plan.md` G1; SDS §1.6 v1.4.0)*
> ```
> CATEGORIES {
>     uuid id PK
>     uuid user_id FK
>     string name
>     string type
>     string icon
> }
> ```

**SDS §5.4.4 CM-US-04: Update a Category (USER)** *(read for context only — out of scope)*
> * **Goal:** Modify category name, type, or icon.

**constitution.md NC-05**
> Enum values are `UPPER_SNAKE_CASE` strings in the database and serialise as the same literal in JSON (`"PENDING"`, `"ACTIVE"`, `"SUPERSEDED"`). Human-friendly labels are a client concern.

**constitution.md SEC-08**
> Queries for user-owned data filter on the authenticated `user_id` at the repository layer (SDS §7.2, SRS NFR-06).

### Out of scope for this story

CM-US-02 (list categories) · CM-US-03 (view a category) · CM-US-04 (update a category, including icon assignment) · CM-US-05 (delete a category) · WM-US-02..05 · UM-US-04/05, DC-US-01/02 · Features 05–11 · SRS §6 Feature-10/11 placeholders.

Deliberately excluded from *this* story even though adjacent: reading a category back through any `GET` endpoint (CM-US-02/03 — this story is verifiable only through what `POST /api/v1/categories` itself returns and through direct inspection of the stored row), renaming or retyping a category (CM-US-04), assigning or changing a category's `icon` (CM-US-04 — see *Assumptions & Dependencies*, and `plan.md` G1/A4), archiving or removing a category (CM-US-05), the "system category" concept CM-US-02's own goal alludes to (see *Assumptions & Dependencies*), and any Transaction or Budget referencing a category (Feature-05, Feature-06).

---

## CM-US-01: Create a Category

### User Scenarios & Testing *(mandatory)*

As an **authenticated User**, I want to create a new category by giving it a name and a type — `INCOME` or `EXPENSE` — so that I can organize my financial transactions.

**Acceptance Criteria**:

**AC-01: Successfully create a category with all mandatory inputs**
**Given** an authenticated User,
**When** the User submits a category name and a category type of exactly `INCOME` or `EXPENSE`,
**Then** the system creates the category owned by the submitting User and returns a success result carrying the category's identifier, owner, name, and type.

**AC-02: Deny access to unauthenticated callers**
**Given** a caller presenting no credentials, or credentials that are invalid or expired,
**When** the caller attempts to create a category,
**Then** the system denies the request before evaluating the payload, creates nothing, and returns an unauthenticated error.

**AC-03: Reject a missing or blank category name**
**Given** an authenticated User,
**When** the submitted name is absent, empty, or only whitespace,
**Then** the system creates nothing and returns a validation error identifying the name field.

**AC-04: Reject a category name exceeding the maximum supported length**
**Given** an authenticated User,
**When** the submitted name is longer than the system supports,
**Then** the system creates nothing and returns a validation error rather than truncating the name.

**AC-05: Reject a missing category type**
**Given** an authenticated User,
**When** the submitted type is absent from the submission,
**Then** the system creates nothing and returns a validation error identifying the type field.

**AC-06: Reject a category type value that is not exactly `INCOME` or `EXPENSE`**
**Given** an authenticated User,
**When** the submitted type is any value other than the literal `INCOME` or the literal `EXPENSE` — including a near-miss such as a different word, a case variant, or a value carrying extra whitespace,
**Then** the system creates nothing and returns a validation error identifying the type field.

**AC-07: A created category always belongs to the submitting User**
**Given** an authenticated User submits a valid category creation request,
**When** the category is created,
**Then** its owner is exactly the authenticated User who submitted the request, determined solely from the caller's own identity and never from any value in the request payload.

**AC-08: Return exactly the documented category fields**
**Given** an authenticated User submits a valid category creation request,
**When** the system returns the success result,
**Then** the result carries exactly the category's identifier, owner identifier, name, and type — no other field (in particular, no `icon` — see *Assumptions & Dependencies*), and no data belonging to any other User.

### Edge Cases

**EC-01**: **Category type submitted in lowercase or mixed case** — `"expense"` or `"Income"` is rejected under AC-06 rather than case-folded and accepted; the system performs no case normalisation on this field, matching this codebase's existing precedent for closed-vocabulary fields (`UserStatus`, `UserRole`) and for shape-validated fields (WM-US-01's `currency`).

**EC-02**: **Category name with surrounding whitespace** — `"  Groceries  "` is stored trimmed, as `"Groceries"`. Interior spacing is preserved as typed.

**EC-03**: **Two categories with the same name for the same User** — both are created successfully, each with its own identifier. No acceptance criterion or business rule requires category names to be unique, even for one User's own categories (see *Assumptions & Dependencies*).

**EC-04**: **More than one validation failure in a single submission** — when the name is blank and the type is malformed in the same request, both problems are reported together in one response, not just the first one encountered.

**EC-05**: **An unrecognised `icon` field submitted with the request** — the request additionally carries an `icon` key in its JSON body; the category is still created from its `name` and `type` alone, and the response carries no `icon` key. This story's contract has no `icon` field to populate (see *Assumptions & Dependencies*), so the extra key is silently ignored, never honoured.

**EC-06**: **Category type submitted with surrounding whitespace** — `" EXPENSE"` or `"INCOME "` is rejected under AC-06. Unlike `name` (EC-02), `type` receives no trimming: only the exact literal `"INCOME"` or `"EXPENSE"` is accepted.

### Requirements *(mandatory)*

#### Functional Requirements

- **FR-01**: The system must **allow** an authenticated User of any role to submit a category name and type in order to create a new category (SRS §6 US-04-01; SDS §5.4.1).
- **FR-02**: The system must **deny** the operation to unauthenticated callers, evaluating credentials before the payload (constitution API-08; mirrors WM-US-01 FR-02).
- **FR-03**: The system must **require** a non-empty category name after trimming surrounding whitespace, and **reject** — rather than truncate — a name longer than the system supports (AC-03, AC-04, EC-02).
- **FR-04**: The system must **require** the submitted type to match exactly one of the two literals `INCOME` or `EXPENSE` (SRS FR-04), and **reject** every other value, including a case variant or a value carrying extra whitespace, with no folding or trimming applied (AC-05, AC-06, EC-01, EC-06).
- **FR-05**: The system must **set** the category's owner to the authenticated caller's own identifier, never to any value supplied in the request payload (AC-07; constitution SEC-08).
- **FR-06**: The system must **return**, on success, exactly the category's identifier, owner identifier, name, and type — no `icon` and no other field (AC-08).
- **FR-07**: The system must **group** every validation failure from one submission into a single response rather than reporting only the first (EC-04; constitution VL-02).
- **FR-08**: The system must **impose no uniqueness constraint** on category name, including across two categories owned by the same User (EC-03).
- **FR-09**: The system must **silently ignore** any `icon` key (or any other field this story does not define) present in the request body — it is neither stored nor echoed back (EC-05; see *Assumptions & Dependencies*).

#### Business Rules

- **BR-01**: A category belongs to exactly one User, assigned at creation time from the authenticated caller's own identity (SRS §1.5 "User defines Category"; constitution SEC-08; FR-05).
- **BR-02**: A category's type is exactly one of the two literals `INCOME` or `EXPENSE` — no other value, and no case or whitespace variant of either, is permitted (SRS FR-04; FR-04).
- **BR-03**: Category names carry no uniqueness constraint, per-User or system-wide (FR-08).
- **BR-04**: A category created by this story carries no `icon` value — the field is neither accepted nor returned by this story's contract, regardless of what the ERD's target design (SDS §4.3.3, as aligned) eventually carries (FR-06, FR-09).

#### Key Entities

- **Category**: A label a User defines to classify money movement as one kind of income or expense (SRS §1.5). Carries `id`, `user_id`, `name`, and `type` in this story (SDS §2.2, §4.3.3 as aligned). `type` is a closed two-value vocabulary — `INCOME` | `EXPENSE` (SRS FR-04) — unlike WM-US-01's free-text `type`. The domain model's `icon` attribute (SDS §2.2, §5.4.4) is not created or populated by this story; see *Assumptions & Dependencies*. Every category this story creates is user-owned — whether a distinct "system category" concept (no owning User) exists is explicitly not decided here; see *Assumptions & Dependencies*.
- **User**: Reused from Feature-01/Feature-02 with no new column. The authenticated caller becomes the category's owner; no role restriction applies (any authenticated, `ACTIVE` User may create a category).

### Success Criteria *(mandatory)*

- **SC-01**: An authenticated User can create a category with a name and a type in one call, and the response reflects exactly what was created.
- **SC-02**: No category can be created without an authenticated caller.
- **SC-03**: Every category's owner is exactly the User who created it — never a value supplied in the request, and never another User's identifier.
- **SC-04**: A category's type is always exactly `INCOME` or `EXPENSE` — never any other value, never case-folded, never trimmed from a padded input.
- **SC-05**: Malformed category-creation input — a missing or blank name, an over-long name, a missing or invalid type — is rejected before anything is persisted, with every problem in one submission reported together.

### Assumptions & Dependencies

- **Login (SS-US-01) is already implemented.** Like WM-US-01 and unlike UM-US-01, this story is specified after `CurrentUserDep` (`backend/app/core/deps.py`) and the login endpoint are both real. AC-02 is fully implementable and testable against the live dependency chain.
- **The SDS §2.2 / §4.3.3 `icon` contradiction has been aligned, not extended.** SDS §2.2's Category domain object and SDS §5.4.4's CM-US-04 goal ("Modify category name, type, or icon") both already treated `icon` as a real Category attribute; SDS §4.3.3's `CATEGORIES` ERD omitted it — the same class of gap WM-US-01 found in `wallets.created_at`. The ERD was corrected to add a nullable `icon` column, recorded in `SDS.md` §1.6 as v1.4.0. That said, **this story's own AC set never mentions `icon`** — neither the SRS Gherkin, nor FR-04, nor SDS §5.4.1's goal statement asks for it at creation time. CM-US-01 therefore neither creates the column in its migration nor accepts/returns the field; the column is CM-US-04's own decision to add, since CM-US-04 is the story whose goal actually names icon-editing. Recorded as `plan.md` G1/A4, not silently patched.
- **No category name length rule exists in either reference document.** This story follows WM-US-01's own precedent — a 100-character bound — for a short free-text label field, rather than inventing an unrelated number with no textual support. Recorded as `plan.md` A1.
- **No uniqueness constraint on category name exists in either reference document.** This story follows WM-US-01's own precedent (its `plan.md` A6): no unique index and no service-layer duplicate check. Recorded as `plan.md` A3.
- **The "system and user-defined categories" concept named by CM-US-02's own goal (SDS §5.4.2, out of scope) is not decided here.** Nothing in CM-US-01's own AC set requires distinguishing a User-owned category from a category with no owner. This story's `categories.user_id` is `NOT NULL`: every category CM-US-01 creates is user-owned. Whether a nullable owner, an `is_system` flag, or a seed of shared categories is needed is CM-US-02's own decision to raise — not inherited silently from here. Recorded as `plan.md` A5.
- **No audit event is required for category creation.** Constitution LA-04 names invitations, activations, and logins as the events this codebase audits; it does not name category creation, and no AC or FR here asks for one — the same reasoning WM-US-01's `plan.md` A9 already recorded for wallet creation.
- **Reading a created category back is out of scope.** This story is verified through what `POST /api/v1/categories` itself returns and through direct inspection of the stored row — there is no `GET` endpoint yet (CM-US-02/03).
