# Feature Specification: Category Management (CM)

> **Feature:** SRS §6 Feature-04 · SDS §5.4 (CM)
> **Spec:** [spec.md](spec.md)
> **Stories in this file:** CM-US-01 *(implemented, verified — 219 passed, 99% coverage)* · CM-US-02 *(implemented, verified — 391 passed)* · CM-US-04 *(implemented, verified — 526 total passing)* · CM-US-03 *(spec + design + test cases written — not yet implemented)*

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

---

## CM-US-02: List Categories

> **IDs in this section are local to CM-US-02.** `AC-01` below is not CM-US-01's `AC-01`; each
> story section numbers its own criteria, per `artifact-templates/spec-templates.md`. Only
> `TC-NN` in `test_cases.md` runs continuously across the epic (`CLAUDE.md` §1.1 rule 4).

### Source *(scope extraction — CLAUDE.md §1 scope rule)*

**SRS §6 Feature-04 — searched in full; no entry for this story exists**
> `### Feature-04: Category Management` contains exactly one story, `#### US-04-01: Create a Category [MVP]` (already quoted in full in this file's CM-US-01 section above), immediately followed by `### Feature-05: Budget Management`. There is no `US-04-02` header, bare or otherwise — unlike WM-US-02, which at least inherited a bare `#### US-03-02: View List of Wallets [MVP]` header from its own feature section. This story has **less** SRS textual anchor than WM-US-02 had, not the same amount.

**SRS §1.5 Conceptual Domain Model**
> **Category** — A label a User defines to classify money movement as one kind of income or expense, e.g. "Groceries" or "Salary" (FR-04).
>
> | Relationship | Cardinality | Meaning |
> | User defines Category | one User → many Categories | Categories belong to the User who created them, not to a shared list (FR-04) |

**SRS §2 FR-04 — Category Management**
> The System shall support user-defined Categories classified as either `INCOME` or `EXPENSE` (e.g., Groceries, Rent, Salary, Utilities).

**SDS §5.4.2 CM-US-02: List Categories (USER)**
> * **Goal:** Retrieve all system and user-defined transaction categories.

One sentence — the entire technical baseline for this story, the same thinness WM-US-02's own SDS goal had.

**SDS §2.1 Domain Layer Traceability**
> | **Category** | `categories` | `CategoryModel` | `CategoryRead`, `CategoryCreate` |

**SDS §2.2 Domain Object**
> **Category:** Classification for monetary activities (`id`, `user_id`, `name`, `type`, `icon`).

**SDS §2.3 Domain Object Relationships** *(class diagram)*
> `User "1" -- "*" Category : defines`

**SDS §6.3 API Index / §6.5 API → User Story Traceability** *(observation, not acted on)*
> Neither table names any `/categories` endpoint at all — not CM-US-01's own, already-implemented `POST /api/v1/categories`, and not a `GET`. This is a larger version of the gap WM-US-02's own spec.md already found for `WM-API-02` (present in §6.3, absent from §6.5) — here §6.3 has no row for Category at all to begin with. Left as-is: this dispatch's scope is limited to the three files in `specs/004-category-management/` and does not extend to editing `SDS.md`.

**constitution.md API-06, PF-04, SEC-08, PF-02**
> **API-06** List endpoints accept `page` and `page_size`; default 25, maximum 100. Responses carry a total count.
> **PF-04** List endpoints are always bounded (see API-06). No unbounded result set reaches a client.
> **SEC-08** Queries for user-owned data filter on the authenticated `user_id` at the repository layer (SDS §7.2, SRS NFR-06).
> **PF-02** Columns used in `WHERE`, `JOIN`, or `ORDER BY` carry an index. No N+1 query patterns.

**`specs/004-category-management/plan.md` CM-US-01 A5** *(this story's own inherited open question)*
> No `is_system` flag or nullable owner — the "system vs. user-defined category" concept is deferred entirely, not decided here … If CM-US-02 (List Categories) needs to surface shared or ownerless categories, raising and designing that is CM-US-02's own decision — not something CM-US-01 may pre-empt by guessing at a flag or a nullable column no AC here justifies.

### Out of scope for this story

CM-US-01 (create a category, already implemented) · CM-US-03 (view a single category) · CM-US-04 (update a category) · CM-US-05 (delete a category) · WM-US-*, UM-US-04/05, DC-US-01/02 · Features 05–11 · SRS §6 Feature-10/11 placeholders.

Deliberately excluded even though adjacent: filtering, searching, or sorting the list by anything other than the fixed, stable order this story defines, **including a filter on `type`** (neither SRS nor SDS names one for this story — see *Assumptions & Dependencies*); a "system category" concept with no owning User (no domain-model support exists for one — see *Assumptions & Dependencies*); viewing a single category's full detail (CM-US-03); renaming or retyping a category (CM-US-04); archiving or removing a category (CM-US-05); and any Transaction or Budget referencing a category (Feature-05, Feature-06).

### User Scenarios & Testing *(mandatory)*

As an **authenticated User**, I want to view the list of categories I own, so that I can see every
income and expense label I've defined without having to create a new one just to check.

**Acceptance Criteria**:

**AC-01: Successfully list every category the caller owns**
**Given** an authenticated User who owns one or more categories, of both types,
**When** the User requests the list of categories,
**Then** the system returns every category owned by that User, each carrying its identifier, owner,
name, and type, together with the total number of categories that User owns.

**AC-02: Return an empty list for a User with no categories yet**
**Given** an authenticated User who owns no categories,
**When** the User requests the list,
**Then** the system returns an empty list of categories together with a total of zero, not an error.

**AC-03: Deny access to unauthenticated callers**
**Given** a caller presenting no credentials, or credentials that are invalid or expired,
**When** the caller attempts to list categories,
**Then** the system denies the request before evaluating any query parameter, returns nothing, and
returns an unauthenticated error.

**AC-04: Bound and paginate the result by default**
**Given** an authenticated User,
**When** the User requests the list without specifying a page or page size,
**Then** the system returns at most 25 of that User's categories on the first page, together with the
total number of categories that User owns.

**AC-05: Accept an explicit page and page size within range**
**Given** an authenticated User,
**When** the User requests a specific page together with a page size up to the maximum of 100,
**Then** the system returns that page of the User's own categories and the same accurate total.

**AC-06: Reject a page or page size outside the allowed range**
**Given** an authenticated User,
**When** the requested page or page size is zero, negative, otherwise not a positive integer, or a
page size greater than 100,
**Then** the system rejects the request with a validation error identifying the offending parameter,
and returns no categories.

**AC-07: A User only ever sees their own categories**
**Given** at least two Users, each owning one or more categories,
**When** one of them requests the list,
**Then** the response's categories are exactly the ones owned by the requesting User — none belonging
to any other User appears — and the reported total counts only the requesting User's own categories,
never every category in the system.

**AC-08: Return the list in a stable, deterministic order**
**Given** an authenticated User who owns two or more categories, with nothing created, changed, or
removed in between,
**When** the User requests the same page more than once, or requests adjacent pages of one paging
sequence,
**Then** the system returns the same categories in the same relative order every time, consistently
across those adjacent pages.

**AC-09: Reuse the documented per-category fields, wrapped in a paginated envelope**
**Given** an authenticated User requests the list,
**When** the system returns the result,
**Then** each entry carries exactly the fields a created category already carries — identifier, owner
identifier, name, and type — no more, no other User's data, no `icon` (CM-US-01 A4/AC-08), and no
field this story invents — and the overall response additionally carries the total count, the page
number, and the page size.

### Edge Cases

**EC-01**: **A page number beyond the last available page** — returns an empty list of categories
together with the accurate, caller-scoped total, not a not-found error.

**EC-02**: **Page size at the exact maximum** — a page size of exactly 100 is accepted; 101 is
rejected under AC-06. The cap is a ceiling, not a target.

**EC-03**: **More categories than fit on one page** — paging through every page with a fixed page size
returns every one of the caller's own categories exactly once, with no duplicate and no gap, in the
same stable order AC-08 establishes.

**EC-04**: **A caller whose role is ADMIN, who also owns categories** — sees, through this endpoint,
only the categories that caller owns. Nothing about this endpoint grants an ADMIN visibility into
another User's categories; unlike UM-US-03, which is deliberately ADMIN-wide, this route has no
ADMIN-wide sense at all — it is scoped to the caller regardless of role.

### Requirements *(mandatory)*

#### Functional Requirements

- **FR-01**: The system must **allow** an authenticated User of any role to retrieve the list of
  categories they own (SDS §5.4.2; mirrors CM-US-01 FR-01's "any role" treatment).
- **FR-02**: The system must **include**, for every listed category, its identifier, owner identifier,
  name, and type — the same fields CM-US-01 already defined for a single created category (SDS §2.1,
  §2.2; CM-US-01 AC-08; constitution PF-03).
- **FR-03**: The system must **deny** the operation to unauthenticated callers, evaluating credentials
  before any query parameter (constitution API-08; mirrors CM-US-01 FR-02).
- **FR-04**: The system must **accept** `page` and `page_size` query parameters, defaulting to page 1
  and page size 25 when omitted (constitution API-06).
- **FR-05**: The system must **reject** a `page` or `page_size` value that is not a positive integer,
  or a `page_size` greater than 100, with a validation error (constitution API-06, PF-04).
- **FR-06**: The system must **return**, alongside every page, the total number of categories the
  caller owns (constitution API-06).
- **FR-07**: The system must **filter** every category query this endpoint issues — both the bounded
  page of items and the total count — to only the categories owned by the authenticated caller
  (constitution SEC-08; plan.md A3).
- **FR-08**: The system must **order** the returned categories by a stable, deterministic key,
  consistently across pages of the same request pattern (plan.md A1).
- **FR-09**: The system must **apply no filter** based on a category's `type` — every category the
  caller owns, `INCOME` or `EXPENSE` alike, appears somewhere in the paginated result (plan.md A8;
  mirrors WM-US-02 FR-09's "no type-based filter," applied here to Category's own `type` field rather
  than Wallet's).
- **FR-10**: The system must **never include**, in either the returned categories or the reported
  total, any category owned by a User other than the caller, regardless of the caller's role — and
  must **never surface a category with no owner**, since this story's domain model has none to surface
  (constitution SEC-08; AC-07, EC-04; plan.md A7).

#### Business Rules

- **BR-01**: Only the categories owned by the authenticated caller are ever returned by this endpoint;
  no role — including ADMIN — grants visibility into another User's categories through this route (SDS
  §5.4.2 "(USER)"; constitution SEC-08; EC-04).
- **BR-02**: A page never carries more than 100 categories; the default when unspecified is 25 (FR-04,
  FR-05; mirrors WM-US-02 BR-02).
- **BR-03**: Categories are ordered by a stable key, consistently across pages of the same request
  pattern; this story establishes no chronological ordering guarantee, because no creation timestamp
  exists on `Category` (FR-08; plan.md A1; see Assumptions & Dependencies).
- **BR-04**: The reported total always equals the count of categories owned by the caller, never the
  system-wide category count (FR-06, FR-07, FR-10).
- **BR-05**: The endpoint applies no content-based filter — every category the caller owns is subject
  only to pagination, never to a filter on `type` (FR-09).
- **BR-06**: This story's category set is exactly the set CM-US-01 can create — every row has exactly
  one owning User. No "system category" with no owner exists to list (FR-10; plan.md A7).

#### Key Entities

- **Category**: A label a User defines to classify money movement as one kind of income or expense
  (SRS §1.5). Carries `id`, `user_id`, `name`, and `type` (SDS §2.1, §2.2; CM-US-01). This story only
  reads categories CM-US-01 already created — it creates, renames, and deletes none.
- **User**: Reused from Feature-01/Feature-02 with no new column. The authenticated caller's own
  identifier is the only scope this story ever queries by (constitution SEC-08).

### Success Criteria *(mandatory)*

- **SC-01**: An authenticated User can retrieve every category they own, carrying the same
  per-category fields CM-US-01 already established, in one call.
- **SC-02**: No request to this endpoint can return an unbounded number of rows.
- **SC-03**: No User can see another User's category, or another User's category count, through this
  endpoint, regardless of role.
- **SC-04**: A User can page through their entire category set with an accurate total and no
  duplicated or skipped category.
- **SC-05**: A User with no categories yet receives an empty list and a zero total, never an error.

### Assumptions & Dependencies

- **Login (SS-US-01) and CM-US-01 (Create a Category) are already implemented** — there is nothing to
  list otherwise, mirroring WM-US-02's own dependency on WM-US-01.

- **`SRS.md` names this story even more thinly than WM-US-02.** WM-US-02 at least inherited a bare
  header; `SRS §6 Feature-04` has no `US-04-02` entry of any kind. `SDS.md` §5.4.2 supplies the only
  sentence. Every AC above beyond "list the caller's own categories" (pagination, ordering, the empty
  case, the envelope shape) is derived from constitution API-06/PF-04/SEC-08 and from the WM-US-02
  precedent, not from either reference document directly — the same situation WM-US-02's own
  Assumptions recorded, now one document thinner. Recorded once, here, rather than against each AC.

- **The "system categories" question CM-US-01 `plan.md` A5 deferred is resolved: this story does not
  build one.** SDS §5.4.2's goal text — "system **and** user-defined transaction categories" — is the
  only place in either reference document that implies a category can exist with no owning User.
  CM-US-01 A5 explicitly deferred this exact question to this story rather than guessing. It is
  resolved here, not deferred again: SRS §1.5 states plainly that categories "belong to the User who
  created them, **not to a shared list**"; SDS §2.1/§2.2/§2.3's own domain model draws exactly one
  relationship for Category (`User "1" -- "*" Category : defines`, no second, ownerless class); and the
  schema CM-US-01 built has `categories.user_id NOT NULL`, no `is_system` column, and no seed migration
  anywhere under `backend/migrations/versions/` creating an ownerless row. `CLAUDE.md`'s precedence
  rule gives SRS the win over SDS on a disagreement, and here SRS is explicit while SDS is one
  under-supported phrase contradicted by its own document's domain model — the same class of internal
  SDS gap CM-US-01 G1 found and fixed for `icon`, except here by phrase rather than by a missing ERD
  column, and reaching into SRS too. Inventing nullable ownership or an `is_system` flag now, on the
  strength of one phrase with no seed data or ERD support anywhere, would be exactly the domain-model
  extension `CLAUDE.md` §1 reserves for a stop-and-ask decision. **Recommended, not performed in this
  dispatch:** a future SDS alignment pass should reword §5.4.2's goal to drop "system and" — the same
  kind of correction v1.2.0 already made for the never-implemented `UserActivate`/`ActivateUser` name —
  left undone here because this dispatch's file scope is limited to `specs/004-category-management/`
  (`plan.md` A7).

- **No `type` filter exists in this story.** SDS §5.4.2's goal sentence names no filter dimension at
  all — contrast TM-US-02, whose own SDS §5.6.2 goal explicitly reads "Query and filter logged
  transactions by wallet, category, or date range," which is exactly why TM-US-02 built three filters
  unprompted by SRS. No equivalent sentence exists here. Declining to add one mirrors WM-US-02's own
  declination to filter by wallet `type`/`currency`/`balance` when nothing asked for it (`plan.md` A8).

- **The ordering decision.** `CategoryModel` has no `created_at` column — confirmed directly from
  `backend/app/models/category.py` — and SDS §4.3.3's `CATEGORIES` ERD (as aligned by CM-US-01 G1 to
  add `icon`) still lists only `id`, `user_id` (FK), `name`, `type`, `icon` — no timestamp, the
  identical gap WM-US-01 A5 found for `wallets` and WM-US-02 A1 then designed around. The same
  reasoning applies verbatim: adding a column the ERD does not list is a domain-model change reserved
  for the user's own decision, and no AC in either reference document asks for chronological order —
  only *a* list. This story therefore orders by the one key every category already has, unconditionally,
  without any schema change: the primary key `id` (`ORDER BY id ASC`). This satisfies everything
  pagination correctness requires (a total, stable, gap-free, duplicate-free order across pages) at the
  same acknowledged cost WM-US-02 accepted: no chronological or otherwise human-meaningful signal
  (`plan.md` A1; `test_cases.md` QF-06).

- **Pagination combined with ownership filtering.** Mirrors WM-US-02 A3 exactly, one table, one
  predicate: both the bounded page query and the total-count query in `category_repo.list_owned()`
  must carry the identical `user_id` predicate, or the reported total would silently mean something
  different from what the items show (`plan.md` A3; `test_cases.md` QF-05).

- **The response envelope.** `SDS.md` §2.1's traceability row names only `CategoryRead`/
  `CategoryCreate`; this story reuses `CategoryRead` **unchanged** as the per-item shape (four
  fields, no `icon`) and wraps it in a new envelope, `CategoryListRead { items, total, page, page_size
  }`, mirroring `WalletListRead` (WM-US-02 `plan.md` A2) and `TransactionListRead` (TM-US-02 `plan.md`
  A8) exactly. Neither envelope is in SDS's registry; all three exist to satisfy constitution API-06.

- **No category `type` vocabulary question to re-litigate.** CM-US-01 already settled that `type` is a
  closed `CategoryType` enum (its own `plan.md` A2). This story only reads existing rows through that
  same field; it introduces no new validation surface.

- **Reading a single category's full detail is out of scope.** This story is verified through the list
  endpoint's own envelope; there is no `GET /categories/{id}` yet (CM-US-03).

---

## CM-US-04: Update a Category

> **IDs in this section are local to CM-US-04.** `AC-01` below is not CM-US-01's or CM-US-02's own
> `AC-01`; each story section numbers its own criteria, per `artifact-templates/spec-templates.md` and
> this codebase's own CM-US-02/WM-US-02/TM-US-02/BM-US-02/BM-US-03/BM-US-04 precedent. Only `TC-NN` (and
> `QF-NN`) in `test_cases.md` run continuously across the epic (`CLAUDE.md` §1.1 rule 4) — this story
> continues from `TC-35`/`QF-09`, confirmed by direct re-count of `test_cases.md`'s own current end
> before writing anything here (that file's own header note records a correction to a wrong number this
> dispatch was originally briefed with for the `QF` series).

### Source *(scope extraction — CLAUDE.md §1 scope rule)*

**SRS §6 Feature-04 — searched in full; confirmed, no entry for this story exists**
> The same situation CM-US-02 was already in (its own Source section above documents this precedent):
> `### Feature-04: Category Management` contains exactly one story, `#### US-04-01: Create a Category
> [MVP]` (quoted in full in this file's CM-US-01 section), immediately followed by `### Feature-05:
> Budget Management`. There is no `US-04-02`, `US-04-03`, or `US-04-04` header of any kind. This story is
> grounded the same way CM-US-02 was: in SRS §1.5's conceptual domain model and SRS §2 FR-04's text
> directly, and in SDS §5.4.4 — not in a bare story header that does not exist.

**SRS §1.5 Conceptual Domain Model**
> **Category** — A label a User defines to classify money movement as one kind of income or expense,
> e.g. "Groceries" or "Salary" (FR-04).

**SRS §2 FR-04 — Category Management**
> The System shall support user-defined Categories classified as either `INCOME` or `EXPENSE` (e.g.,
> Groceries, Rent, Salary, Utilities).

**SDS §5.4.4 CM-US-04: Update a Category (USER)**
> * **Goal:** Modify category name, type, or icon.

Confirmed directly from `SDS.md` itself, not assumed from any briefing summary: unlike a vaguer
"rename or update configuration"-style goal line (a different epic's own Update story, not read into
this one under the scope rule), this goal names three concrete fields directly — `name`, `type`, `icon`.
The disjunctive phrasing ("name, type, **or** icon") is read literally in *Assumptions & Dependencies*
below: it is the textual basis for treating all three fields as independently optional on this
operation, not a requirement that every update touch all three.

**SDS §2.2 Domain Object** *(Category row, as aligned by CM-US-01 G1 — SDS §1.6 v1.4.0)*
> **Category:** Classification for monetary activities (`id`, `user_id`, `name`, `type`, `icon`).

**SDS §4.3.3 Data Design — `CATEGORIES` ERD** *(as aligned by CM-US-01 G1)*
> ```
> CATEGORIES {
>     uuid id PK
>     uuid user_id FK
>     string name
>     string type
>     string icon
> }
> ```

**`specs/004-category-management/plan.md` CM-US-01 A4** *(this story's own inherited open decision)*
> `icon` is not created or populated by this story [CM-US-01] ... Adding it is CM-US-04's own decision to
> make, since CM-US-04 (`SDS §5.4.4`) is the story whose goal actually names icon-editing.

**`backend/app/models/category.py` docstring** *(read directly, not assumed)*
> No `icon` column (plan.md A4) — SDS §4.3.3's ERD was aligned to add a nullable `icon` at the document
> level (plan.md G1), but no AC in this story's own set asks for it, so the column is deferred to
> CM-US-04.

**`backend/app/repositories/category_repo.py`** *(read directly)*
> `get_owned_by_id(db, *, category_id, user_id)` already exists — built for BM-US-01's own creation-time
> reference check (`budget_service.create_budget`'s category-ownership validation) — and is reused
> unchanged by this story for its own lookup; see *Assumptions & Dependencies*.

**constitution.md API-03, API-05, SEC-08, VL-02, VL-06**
> API-03: HTTP status codes: `200` read/update · ... — an update response is `200`, not `201`.
> API-05: No generic `updateStatus` endpoint. Each business state transition gets its own explicit
> endpoint.
> SEC-08: Queries for user-owned data filter on the authenticated `user_id` at the repository layer.
> VL-02: Validation errors are returned together in one `422`, not one error per field.
> VL-06: Referenced entities are verified to exist and be active before use — `404` if absent, `409` if
> present but in the wrong state.

**`specs/005-budget-management/spec.md` BM-US-04 "Acceptance Criteria"** *(this story's own update-
mechanics precedent, mirrored — not a different epic's requirement leaking in)*
> AC-04: "the system creates nothing and returns the same not-found outcome [as AC-03] in either case —
> the response gives no indication of which of the two happened."

### Out of scope for this story

CM-US-01 (create, implemented) · CM-US-02 (list, implemented) · CM-US-03 (view a single category — not
yet implemented; see *Assumptions & Dependencies* for why this story does not depend on it) · CM-US-05
(delete a category) · WM-US-*, BM-US-*, TM-US-*, UM-US-04/05, DC-US-01/02 · Features 06–11 · SRS §6
Feature-10/11 placeholders.

Deliberately excluded even though adjacent: changing a category's owner (this story's contract has no
field capable of naming one — ownership is immutable, exactly as it was at creation, CM-US-01 BR-01);
re-validating, re-deriving, or otherwise touching any existing Transaction or Budget as a side effect of
a name/type/icon change (reasoned through explicitly below, not merely declined — see the `type`-
editability discussion in *Assumptions & Dependencies*); introducing an operation to clear an `icon`
value back to absent once set (reasoned through below — see *Assumptions & Dependencies*); archiving or
removing a category (CM-US-05); and any mobile/UI screen — no SRS UXR names one this round, and
`mobile/` stays a fixture-driven prototype scoped to UM-US-01 only (`CLAUDE.md` §5).

### User Scenarios & Testing *(mandatory)*

As an **authenticated User**, I want to change one or more of a category's name, type, and icon, so that
I can correct a mistake or reorganize my categories without deleting and recreating them.

**Acceptance Criteria**:

**AC-01: Successfully update one or more of a category's name, type, and icon**
**Given** an authenticated User who owns a category,
**When** the User submits a new value for at least one of `name`, `type`, or `icon`,
**Then** the system updates exactly the submitted field(s), leaves every field the User did not submit
unchanged, and returns a success result carrying the category's identifier, owner, name, type, and icon.

**AC-02: Deny access to unauthenticated callers**
**Given** a caller presenting no credentials, or credentials that are invalid or expired,
**When** the caller attempts to update a category,
**Then** the system denies the request before evaluating anything else, changes nothing, and returns an
unauthenticated error.

**AC-03: Reject an update to a category that does not exist**
**Given** an authenticated User,
**When** the submitted category reference matches no category at all,
**Then** the system changes nothing and returns a not-found error.

**AC-04: Reject an update to a category owned by a different User**
**Given** an authenticated User,
**When** the submitted category reference matches a category owned by a different User,
**Then** the system changes nothing and returns the same not-found outcome AC-03 describes — the
response gives no indication of which of the two happened.

**AC-05: Reject a submission naming none of name, type, or icon**
**Given** an authenticated User who owns a category,
**When** the submission names none of `name`, `type`, or `icon` at all,
**Then** the system changes nothing and returns a validation error rather than treating the request as a
no-op success.

**AC-06: Reject a blank name, when a name is submitted**
**Given** an authenticated User who owns a category,
**When** a `name` is submitted that is empty or only whitespace,
**Then** the system changes nothing and returns a validation error identifying the name field.

**AC-07: Reject a name exceeding the maximum supported length, when a name is submitted**
**Given** an authenticated User who owns a category,
**When** the submitted `name` is longer than the system supports,
**Then** the system changes nothing and returns a validation error rather than truncating the name.

**AC-08: Reject a type value that is not exactly INCOME or EXPENSE, when a type is submitted**
**Given** an authenticated User who owns a category,
**When** the submitted `type` is any value other than the literal `INCOME` or the literal `EXPENSE` —
including a near-miss such as a different word, a case variant, or a value carrying extra whitespace,
**Then** the system changes nothing and returns a validation error identifying the type field.

**AC-09: Reject a blank icon, when an icon is submitted**
**Given** an authenticated User who owns a category,
**When** an `icon` is submitted that is empty or only whitespace,
**Then** the system changes nothing and returns a validation error identifying the icon field.

**AC-10: Reject an icon exceeding the maximum supported length, when an icon is submitted**
**Given** an authenticated User who owns a category,
**When** the submitted `icon` is longer than the system supports,
**Then** the system changes nothing and returns a validation error rather than truncating the icon.

**AC-11: A successful update changes only the submitted field(s)**
**Given** an authenticated User who successfully updates one or more fields of one of their own
categories,
**When** the update completes,
**Then** the category's owner is unchanged, and every one of `name`, `type`, and `icon` that was not
named in the request holds exactly the value it held immediately before the request.

**AC-12: Return exactly the documented category fields**
**Given** an authenticated User successfully updates a category,
**When** the system returns the success result,
**Then** the result carries exactly the category's identifier, owner identifier, name, type, and icon —
no other field, and no data belonging to any other User's category.

### Edge Cases

**EC-01**: **Type submitted in lowercase or mixed case** — `"expense"` or `"Income"` is rejected under
AC-08 rather than case-folded and accepted, exactly as CM-US-01 EC-01 already established for creation —
this story introduces no new normalisation behaviour for `type`.

**EC-02**: **Name with surrounding whitespace** — `"  Utilities  "` is stored trimmed, as `"Utilities"`,
exactly as CM-US-01 EC-02 already established. Interior spacing is preserved as typed.

**EC-03**: **An updated name matches another of the caller's own categories' names** — the update still
succeeds; no acceptance criterion or business rule requires category names to be unique, even for one
User's own categories, exactly as CM-US-01 EC-03 already established for creation.

**EC-04**: **More than one validation failure in a single submission** — when the submitted `name` is
blank and the submitted `type` is malformed in the same request, both problems are reported together in
one response, not just the first one encountered, exactly as CM-US-01 EC-04 already established.

**EC-05**: **An unrecognised `user_id` field submitted alongside otherwise valid fields** — the request
additionally carries a `user_id` key naming a different, real User; the category's owner remains exactly
the caller, never the named User — the extra key is silently ignored, never honoured, exactly as CM-US-01
EC-05/`plan.md` A6 already established for creation (there, the ignored field was `icon`, which this
story now makes real; here it is `user_id`, which remains structurally absent from this story's own DTO
too).

**EC-06**: **An icon submitted for the first time, and an icon changed a second time** — a category
created by CM-US-01 has no `icon` value; submitting one for the first time is accepted as an ordinary
successful update, as is later submitting a different value in place of one already set. Neither case is
a no-op or a conflict.

**EC-07**: **An icon with surrounding whitespace** — `"  shopping-cart  "` is stored trimmed, as
`"shopping-cart"`, the same treatment EC-02 already establishes for `name`.

**EC-08**: **A category reference that is not even a well-formed identifier** — a value such as
`"not-a-real-id"` is refused with the same not-found outcome as a well-formed but non-existent reference
(AC-03). No separate malformed-identifier error exists; a reference either resolves to a category the
caller owns, or it does not, regardless of its shape — mirrors BM-US-04 EC-03.

**EC-09**: **Type submitted with surrounding whitespace** — `" EXPENSE"` or `"INCOME "` is rejected under
AC-08; unlike `name`/`icon` (EC-02, EC-07), `type` receives no trimming, exactly as CM-US-01 EC-06
already established.

**EC-10**: **A category's type is changed after a Transaction or a Budget already references it** —
accepted; this story performs no check of, and has no effect on, any existing Transaction's own stored
`type`, or on the result of any Budget's spend computation for activity already recorded. Reasoned
through in full in *Assumptions & Dependencies*, because it is the one consequence of this story that is
not obvious from the CRUD mechanics alone.

**EC-11**: **A caller who owns one or more categories of their own, attempting to update a different
User's category** — refused with the identical outcome AC-04 describes; owning some category never
entitles a caller to act on another User's category — mirrors BM-US-04 EC-07.

**EC-12**: **Icon at the maximum supported length** — a value at exactly that bound is accepted; one
character more is rejected under AC-10. The cap is a ceiling, not a target, mirroring CM-US-02 EC-02's
own treatment of `page_size`.

### Requirements *(mandatory)*

#### Functional Requirements

- **FR-01**: The system must **allow** an authenticated User of any role to submit a new value for at
  least one of `name`, `type`, or `icon`, identifying the category to update by its own identifier, in
  order to update that category (SDS §5.4.4).
- **FR-02**: The system must **deny** the operation to unauthenticated callers, evaluating credentials
  before anything else (constitution API-08; mirrors CM-US-01 FR-02, BM-US-04 FR-02).
- **FR-03**: The system must **require** the submitted category reference to resolve to a category owned
  by the authenticated caller, and **refuse** the request with an identical outcome whether no such
  category exists at all or it exists and is owned by a different User (AC-03, AC-04, EC-08, EC-11;
  constitution SEC-08, VL-06).
- **FR-04**: The system must **require** at least one of `name`, `type`, or `icon` to be present in the
  submission, and **reject** — rather than silently accept as a no-op — a submission naming none of the
  three (AC-05).
- **FR-05**: The system must, **when `name` is submitted**, require it non-empty after trimming
  surrounding whitespace and no longer than the system-supported maximum, **rejecting** — rather than
  truncating — a value that fails either bound; the trimmed value is what gets stored (AC-06, AC-07,
  EC-02).
- **FR-06**: The system must, **when `type` is submitted**, require it to match exactly one of the two
  literals `INCOME` or `EXPENSE`, with no case-folding or trimming applied to any other value (AC-08,
  EC-01, EC-09).
- **FR-07**: The system must, **when `icon` is submitted**, require it non-empty after trimming
  surrounding whitespace and no longer than the system-supported maximum, **rejecting** — rather than
  truncating — a value that fails either bound; the trimmed value is what gets stored (AC-09, AC-10,
  EC-07, EC-12).
- **FR-08**: The system must **leave** every one of `name`, `type`, and `icon` not named in the request
  unchanged, and must **leave** the category's owner unchanged regardless of anything submitted,
  including an unrecognised `user_id` key (AC-11, EC-05).
- **FR-09**: The system must **return**, on success, exactly the category's identifier, owner identifier,
  name, type, and icon — no other field (AC-12).
- **FR-10**: The system must **group** every validation failure from one submission into a single
  response rather than reporting only the first (EC-04; constitution VL-02).
- **FR-11**: The system must **impose no uniqueness constraint** on an updated category name, including
  across two categories owned by the same User (EC-03; mirrors CM-US-01 FR-08).
- **FR-12**: The system must **apply no restriction and no retroactive effect** tied to a category's
  `type` changing: an existing Transaction's own stored `type` must never change as a result, and the
  result of any Budget's spend computation over activity already recorded must never change as a result
  (EC-10; see *Assumptions & Dependencies* for the full reasoning).

#### Business Rules

- **BR-01**: A category's ownership for this operation is established directly from its own `user_id`
  column — unlike Budget (BM-US-04 BR-02), a category carries its own owner, so no second table is
  consulted to decide ownership (SRS §1.5 "User defines Category"; constitution SEC-08; FR-03).
- **BR-02**: `name`, `type`, and `icon` are each independently optional on this operation; at least one
  must be present, or the request is refused (FR-04).
- **BR-03**: Category names carry no uniqueness constraint, per-User or system-wide, on update any more
  than at creation (FR-11; mirrors CM-US-01 BR-03).
- **BR-04**: A category's `type` carries no standing consistency invariant against any Transaction or
  Budget that references it. The only place `type` consistency is ever checked is at the moment a new
  Transaction is created (a different story's own rule, not restated or re-triggered by this one); it is
  never re-checked against a category's current `type` afterward, and changing a category's `type` does
  not retroactively revisit that decision for any Transaction already recorded (FR-12).
- **BR-05**: A category's owner is immutable through this story's contract; no field exists by which a
  caller could even attempt to change it (FR-08).

#### Key Entities

- **Category**: A label a User defines to classify money movement as one kind of income or expense (SRS
  §1.5). This is the first story to **write** to an existing Category row rather than only creating or
  reading one (mirrors BM-US-04's own framing for Budget). Carries `id`, `user_id`, `name`, `type` (SDS
  §2.2, §4.3.3; CM-US-01), and now, for the first time, a real `icon` value (SDS §2.2, §4.3.3 as aligned
  by CM-US-01 G1; this story's own build-out, per CM-US-01 A4). `name`, `type`, and `icon` are each
  independently mutable; the owner is not.
- **Transaction**: Reused unchanged, read by neither this story's request nor response — referenced only
  in reasoning about `type`-editability (see *Assumptions & Dependencies*). Carries its own independent
  `type`, set once at creation and never re-derived from its category afterward (TM-US-01).
- **Budget**: Reused unchanged, read by neither this story's request nor response — referenced only in
  reasoning about `type`-editability. Its spend computation keys on `(wallet_id, category_id)` and each
  Transaction's own stored `type`, never on a category's current `type` (BM-US-02).
- **User**: Reused from Feature-01/Feature-02 with no new column. The authenticated caller's own
  ownership of the category being updated is the only scope this story ever checks or changes.

### Success Criteria *(mandatory)*

- **SC-01**: An authenticated User can update at least one of a category's name, type, and icon in one
  call, and the response reflects exactly the resulting state of all five fields.
- **SC-02**: No category can be updated without an authenticated caller.
- **SC-03**: A category can never be updated by a User who does not own it — whether because the
  reference does not exist at all, or because it belongs to someone else, the request is refused
  identically either way.
- **SC-04**: A submission naming none of name, type, or icon is always refused, never silently accepted
  as a no-op success.
- **SC-05**: An updated name, type, or icon is always stored at the validated, trimmed value the User
  specified — never silently rounded, case-folded, truncated, or defaulted — and every field the User did
  not name keeps exactly its prior value, including the category's owner.
- **SC-06**: Changing a category's type never alters any already-recorded Transaction's own type, nor the
  result of any Budget computation over activity already recorded; it governs only how a new Transaction
  created from this point forward is validated against the category.

### Assumptions & Dependencies

- **Login (SS-US-01), Create a Category (CM-US-01), and List Categories (CM-US-02) are already
  implemented.** Every acceptance criterion here presupposes at least one category already on record,
  owned by the authenticated caller.

- **CM-US-03 (View a Category) is not yet implemented, and this story does not depend on it.**
  `backend/app/repositories/category_repo.py` already defines `get_owned_by_id(db, *, category_id,
  user_id)` — confirmed directly by reading the file — built for BM-US-01's own creation-time
  category-ownership check (`budget_service.create_budget` validates a *referenced* category this way).
  That function is a repository-level, single-table lookup with no dependency on any public
  single-resource `GET` endpoint existing; this story reuses it unchanged for its own ownership-scoped
  fetch (mirrors BM-US-04 A3's own generalisation of `budget_repo.get_owned_by_id()` from a
  referenced-row check to the row being acted on directly — the identical move, one epic later). The
  category identifier a caller submits to this endpoint is already available to them from CM-US-01's own
  create response or CM-US-02's own list response; no "view one category" screen or endpoint is a
  precondition for "edit one category."

- **All three fields — `name`, `type`, `icon` — are independently optional; at least one must be
  present.** SDS §5.4.4's own goal text reads "Modify category name, type, **or** icon" — confirmed
  directly, not assumed — the disjunctive phrasing of three concrete field names, unlike BM-US-04's own
  single-field contract (BM-US-04 A1/A6), where "required" and "optional" were the same question because
  `amount_limit` was the DTO's only field. A caller changing just one thing — fixing a typo in the name,
  reclassifying the type, or picking an icon for the first time — should not be forced to resend the
  other two unchanged values, and nothing in SRS or SDS suggests an all-or-nothing replacement is
  intended. A submission naming none of the three is still refused (AC-05) rather than treated as a
  meaningless no-op success, the same "don't silently accept a request that does nothing" discipline
  VL-02/EC-04 already apply to grouped validation. This is the first multi-field optional update contract
  in this codebase — CM-US-01/CM-US-02 only ever read or wrote a category wholesale, and BM-US-04's own
  Update story had exactly one mutable field, so there is no precedent in this codebase for *which* of
  several fields a partial update should require. Recorded as `plan.md` A1.

- **Submitting `icon` as `null`, or omitting it, are treated identically — both mean "leave the current
  icon exactly as it is."** There is consequently no operation in this story's own contract to clear an
  `icon` back to absent once one has been set; the only observable way to change `icon` is to submit a
  new, non-blank string in its place. Nothing in SRS or SDS asks for a "remove my icon" capability, and
  inventing the sentinel-vs-omitted distinction such an operation would need (a caller would have to be
  able to say "I am deliberately sending null," distinguishable from "I didn't mention icon at all") is
  exactly the kind of unrequested complexity BM-US-04 A1 already declined for Budget's own re-targeting
  question, under the identical "fewest invented rules" discipline. If a future story needs to let a User
  remove an icon entirely, that is a gap to raise then — not a capability silently built into this one
  now. Recorded as `plan.md` A12.

- **`icon` is bounded at a short length, trimmed, and required non-blank when submitted.** No SRS or SDS
  source states a length rule for `icon`, the same situation CM-US-01 A1 already found for `name`. Rather
  than inventing an unrelated number, this follows the same codebase discipline CM-US-01 A1 established —
  reuse a precedent for the nearest comparable kind of field — but `icon` is not a label like `name`: the
  test data already used in this epic (`test_cases.md` TC-13: `"icon": "shopping-cart"`) and the ordinary
  shape of an icon-library key or a short slug are both well under half of `name`'s own bound, so a
  materially smaller bound is used instead of reusing `name`'s verbatim — generous for a short identifier,
  still clearly distinct from a label-length field. The exact number carries the same epistemic status
  CM-US-01 A1 already flagged for its own: reasoned, not dictated by any source. Recorded as `plan.md`
  A5/A11 (which states the exact figure — a technical bound, not repeated here per the spec/plan split).

- **`icon` carries no format constraint beyond length and non-blankness — it is treated as an opaque
  string, not a URL, not an enum of known icon names, and not a glyph/emoji-specific rule.** No SRS or SDS
  source, and no mobile fixture (the prototype scope is limited to UM-US-01's invite screen, `CLAUDE.md`
  §5), describes what an icon value is supposed to look like or how a client renders it. Inventing a
  format rule — a URL pattern, a closed vocabulary of recognised icon keys, a MIME-type check for an
  embedded image — would be answering a question nobody has asked yet, the same restraint CM-US-02 A8
  already showed in declining an unrequested `type` filter. Recorded as `plan.md` A11.

- **A category's `type` is freely editable after Transactions or Budgets already reference it, with no
  retroactive consequence anywhere in this codebase — reasoned through directly against the real code,
  not assumed.** Three facts, confirmed by reading the actual implementation rather than inferring from
  the spec alone:
  1. `backend/app/schemas/transaction.py`'s `TransactionRead`/`TransactionModel` carry their **own**
     independent `type` field (`EXPENSE`/`INCOME`) — it is set once, from the request, at creation
     (`backend/app/services/transaction_service.py::create_transaction`), and nothing in this codebase
     ever re-reads it from the transaction's own category afterward.
  2. `transaction_service.create_transaction`'s category-type-consistency rule (TM-US-01 BR-03,
     `TransactionCategoryTypeMismatchError`) runs exactly once, at the moment a Transaction is created —
     comparing the category's `type` *at that moment* to the submitted Transaction `type`. It is not a
     standing invariant re-checked on any later read, and nothing in this codebase re-validates an
     existing Transaction against its category's *current* `type`.
  3. `backend/app/repositories/transaction_repo.py::get_expense_totals_by_wallet_category` — the function
     BM-US-02's own budget spend-aggregation calls — sums Transactions filtered on `TransactionModel.type
     == TransactionType.EXPENSE` (the **transaction's own stored type**) and grouped by `(wallet_id,
     category_id)`; it never joins to `CategoryModel` and never reads `CategoryModel.type` at all. A
     category's `type` changing therefore cannot change which past Transactions are summed into a
     Budget's `amount_spent`, because that computation was never keyed on the category's `type` to begin
     with — only on the pairing and each Transaction's own already-fixed `type`.
  Together these mean a category's `type` is pure metadata for *future* Transaction creation (TM-US-01
  BR-03 will compare against whatever `type` the category holds **at that later moment**), never a value
  anything reaches back through history to re-check. Restricting `type` edits — for instance, refusing to
  change the `type` of a category already referenced by a Transaction or a Budget — would be inventing a
  constraint to protect an invariant that, on direct inspection, this codebase does not actually maintain
  anywhere past creation time. The one real, observable consequence — demonstrated by `test_cases.md`
  TC-62 — is forward-looking and unsurprising: after a category's `type` changes, a *new* Transaction of
  the category's *old* `type` submitted against it is refused by TM-US-01's own existing check, exactly as
  it would be refused against any other category whose `type` disagrees with the submission; this is
  TM-US-01's own rule correctly reacting to new data, not a new rule this story introduces. Recorded as
  `plan.md` A13; EC-10; BR-04; FR-12.

- **No new uniqueness constraint on `name`, matching CM-US-01's own creation-time decision (A3).** No AC,
  EC, or BR requires one for update any more than CM-US-01 required one for creation.

- **No audit event.** Constitution LA-04 names exactly three audited event families (invitations sent,
  activations completed, logins); category creation and listing were already excluded (CM-US-01 A8,
  CM-US-02 A5), and updating a category's fields is no closer to any of the three than those were. No AC
  or FR here asks for one.

- **`PATCH /api/v1/categories/{category_id}`, not a generic `PATCH` with a status field and not a
  dedicated action endpoint.** Constitution API-05 reserves its concern for a **named business state
  transition** (its own example: `/users/activate`); `name`/`type`/`icon` are ordinary business fields,
  and — unlike Budget, which already has a real computed status field this update must not be able to set
  (BM-US-04 A2) — Category has no status or lifecycle field of any kind at all, so the "is this secretly a
  state machine" question BM-US-04 had to reason through explicitly does not even arise here. A verb-free
  `PATCH` on the resource's own id is the default shape constitution NC-03 reserves such endpoints *from*.
  Mirrors BM-US-04 A2.

- **This story introduces the first multi-field optional update contract in this codebase.** CM-US-01's
  own `CategoryCreate` and BM-US-04's own `BudgetUpdate` are each single-shape DTOs where every field is
  simply required; this story's `CategoryUpdate` is the first DTO in this codebase whose fields are each
  independently optional, with a cross-field "at least one must be present" rule Pydantic cannot express
  as a single field constraint (the same class of cross-field rule TM-US-02 A7 already needed for its own
  `date_from`/`date_to` ordering, reused here as precedent for *how* to express a cross-field check, not
  *what* the check says).

---

## CM-US-03: View a Category

> **IDs in this section are local to CM-US-03.** `AC-01` below is not CM-US-01's, CM-US-02's, or
> CM-US-04's own `AC-01`; each story section numbers its own criteria, per
> `artifact-templates/spec-templates.md` and this codebase's own precedent (mirrors WM-US-03's own
> opening note in `specs/003-wallet-management/spec.md`). Only `TC-NN` (and `QF-NN`) in
> `test_cases.md` run continuously across the epic (`CLAUDE.md` §1.1 rule 4) — confirmed by direct
> count against that file's own current end (`TC-63`, `QF-13`, both CM-US-04's own last entries,
> confirmed with `grep -oE '^### TC-[0-9]+' test_cases.md | sort -t- -k2 -n | tail` and the equivalent
> for `QF-`) before writing anything here: this story continues from `TC-64` and `QF-14`.

### Source *(scope extraction — CLAUDE.md §1 scope rule)*

**SRS §6 Feature-04 — searched in full; confirmed, no entry for this story exists**
> The same situation CM-US-02 and CM-US-04 were already in (each documents this precedent in its own
> Source section above): `### Feature-04: Category Management` contains exactly one story, `#### US-04-01:
> Create a Category [MVP]` (quoted in full in this file's CM-US-01 section), immediately followed by
> `### Feature-05: Budget Management`. There is no `US-04-02`, `US-04-03`, `US-04-04`, or `US-04-05`
> header of any kind — confirmed directly by re-reading `SRS.md` §6 Feature-04 in full for this
> dispatch, not assumed from the prior stories' own findings. This story is grounded the same way
> CM-US-02/CM-US-04 were: in SRS §1.5's conceptual domain model and SRS §2 FR-04's text directly, and
> in SDS §5.4.3 — not in a bare story header that does not exist.

**SRS §1.5 Conceptual Domain Model**
> **Category** — A label a User defines to classify money movement as one kind of income or expense,
> e.g. "Groceries" or "Salary" (FR-04).

**SRS §2 FR-04 — Category Management**
> The System shall support user-defined Categories classified as either `INCOME` or `EXPENSE` (e.g.,
> Groceries, Rent, Salary, Utilities).

**SDS §5.4.3 CM-US-03: View a Category (USER)**
> * **Goal:** View details and category metadata.

Confirmed directly from `SDS.md` itself, not assumed from any briefing summary — the entire SDS entry
for this story is this one sentence, the same thinness CM-US-02 (§5.4.2) and CM-US-04 (§5.4.4) each
already found for their own goals. Unlike WM-US-03's own SDS §5.3.3 goal ("View detailed balance and
**history** for a specific wallet"), which named a second, genuinely open concept ("history") its own
epic had to reason through at length (`specs/003-wallet-management/plan.md` WM-US-03 A2), this story's
own goal — "details and category metadata" — names nothing beyond the category's own already-
established fields. "Metadata" here is read as a synonym for the category's own attributes (`id`,
`user_id`, `name`, `type`, `icon` — all five already established and already returned by CM-US-01/
CM-US-02/CM-US-04), not as an invitation to embed a second entity's data the way "history" was for
Wallet. Category has no related entity this endpoint could even embed data from in the first place:
unlike Wallet (which owns a Transaction history), nothing in SDS §2.2/§2.3's domain model names
anything "beneath" a Category for a detail view to surface. See *Assumptions & Dependencies* for the
full reasoning, not merely asserted here.

**SDS §2.2 Domain Object** *(Category row, as aligned — CM-US-01 G1, CM-US-04 A5)*
> **Category:** Classification for monetary activities (`id`, `user_id`, `name`, `type`, `icon`).

**SDS §4.3.3 Data Design — `CATEGORIES` ERD** *(as aligned)*
> ```
> CATEGORIES {
>     uuid id PK
>     uuid user_id FK
>     string name
>     string type
>     string icon
> }
> ```

**SDS §6.3 API Index** *(checked directly, not assumed)*
> Lists no `/categories` endpoint at all, of any kind — confirmed directly, the same gap CM-US-02's own
> Source section already found for this same table ("Neither table names any `/categories` endpoint at
> all"). No stale `WM-API-03`/`WM-API-04`-shaped row exists here to be either confirmed-stale or
> matched; there is simply nothing in this table for this story to reconcile against.

**`backend/app/schemas/category.py` `CategoryRead`** *(read directly, not assumed)*
> Five fields already: `id`, `user_id`, `name`, `type`, `icon` — extended to five by CM-US-04 (plan.md
> A6). Unlike WM-US-03 (which reused a six-field `WalletRead` already complete at WM-US-01) or TM-US-03
> (which reused `TransactionRead`), this story's own reused DTO was only completed to its final shape
> one story ago, in this same epic — there is no "fewer fields than CM-US-04 returns" question to
> resolve, because `icon` already exists in the DTO this story reuses unchanged.

**`backend/app/repositories/category_repo.py` `get_owned_by_id(db, *, category_id, user_id)`** *(read
directly, not assumed)*
> Already exists (CM-US-01, for BM-US-01's own creation-time reference check; reused unchanged by
> CM-US-04 for its own ownership-scoped lookup). Already collapses "no such category" and "exists,
> owned by someone else" to the identical `None` by construction (constitution SEC-08) — exactly the
> lookup this story's own "fetch the category being viewed" need requires.

**`backend/app/core/errors.py` `CategoryNotFoundError`** *(read directly, not assumed)*
> Already exists (CM-US-04, `404`, `CATEGORY_NOT_FOUND`) — built for exactly "the category being acted
> on directly was not found or not owned by the caller," the identical situation this story's own
> single collapsed outcome needs. No new error class required.

**`specs/003-wallet-management/{spec.md,plan.md,test_cases.md}` WM-US-03, and
`specs/006-transaction-management/{spec.md,plan.md,test_cases.md}` TM-US-03** *(this story's own
primary design precedent — two prior "view a single X" stories, both already built this exact shape)*
> WM-US-03 A2: "The response reuses `WalletRead` unchanged — no new DTO, no embedded transaction
> data." · TM-US-03 A3: "The response reuses `TransactionRead` unchanged — no new DTO." · Both stories'
> own AC-03/AC-04 pairs collapse "does not exist" and "exists, owned by someone else" to an identical
> `404` body, proved in each epic's own `test_cases.md` (WM-US-03 QF-12/TC-63, extended to an
> own-a-different-row caller by TC-69) by a full-response-body comparison, not merely a matching status
> code.

**constitution.md API-01, API-03, API-07, VL-06, SEC-08, SEC-10, PF-02, PF-03**
> API-03: HTTP status codes: `200` read/update … `404` not found.
> VL-06: Referenced entities are verified to exist and be active before use — `404` if absent.
> SEC-08: Queries for user-owned data filter on the authenticated `user_id` at the repository layer.
> SEC-10: Error messages must not reveal whether an account exists, except where a story deliberately
> does so.
> PF-03: Responses are built from DTO projections — never a full ORM entity graph.

### Out of scope for this story

CM-US-01 (create, implemented) · CM-US-02 (list, implemented) · CM-US-04 (update, implemented) ·
CM-US-05 (delete a category — not yet designed; see *Assumptions & Dependencies* for why this story
does not depend on it) · WM-US-*, BM-US-*, TM-US-*, UM-US-04/05, DC-US-01/02 · Features 05–11 · SRS §6
Feature-10/11 placeholders.

Deliberately excluded even though adjacent: embedding any Transaction or Budget data that references
this category (no AC asks for it, and no sibling entity's data is named by SDS §5.4.3's own goal —
unlike WM-US-03's own "history" question, there is no equivalent open word here to reason through, see
*Assumptions & Dependencies*); renaming, retyping, or changing any field of a category (CM-US-04,
already delivered); archiving or removing a category (CM-US-05); listing every category a caller owns
(CM-US-02, already delivered — this story is the single-resource counterpart); and any mobile/UI
screen — no SRS UXR names one this round, and `mobile/` stays a fixture-driven prototype scoped to
UM-US-01 only (`CLAUDE.md` §5).

### User Scenarios & Testing *(mandatory)*

As an **authenticated User**, I want to view the full detail of one of my own categories, so that I
can confirm its name, type, and icon without paging through my entire category list to find it.

**Acceptance Criteria**:

**AC-01: Successfully view the detail of a category the caller owns**
**Given** an authenticated User who owns a category,
**When** the User requests that category by its own identifier,
**Then** the system returns a success result carrying the category's identifier, owner identifier,
name, type, and icon.

**AC-02: Deny access to unauthenticated callers**
**Given** a caller presenting no credentials, or credentials that are invalid or expired,
**When** the caller attempts to view a category,
**Then** the system denies the request before evaluating the category reference at all, and returns
an unauthenticated error.

**AC-03: Reject a category reference that does not exist at all**
**Given** an authenticated User,
**When** the submitted category reference matches no category in the system,
**Then** the system returns a not-found error.

**AC-04: Reject a category reference belonging to a different User**
**Given** an authenticated User,
**When** the submitted category reference matches a category owned by a different User,
**Then** the system returns the same not-found outcome AC-03 describes — the response gives no
indication of which of the two happened.

**AC-05: Return exactly the documented category fields — no other User's data**
**Given** an authenticated User successfully views one of their own categories,
**When** the system returns the success result,
**Then** the result carries exactly the category's identifier, owner identifier, name, type, and
icon — no other field, and no data belonging to any other User.

### Edge Cases

**EC-01**: **A category reference that is not even a well-formed identifier** — a value such as
`"not-a-real-id"` is refused with the same not-found outcome as a well-formed but non-existent
reference (AC-03), the identical treatment CM-US-04 EC-08 already established for this same kind of
reference.

**EC-02**: **A caller who owns a different category of their own, attempting to view another User's
category** — refused with the identical outcome AC-04 describes; owning some category never entitles
a caller to view another User's category, the identical scoping CM-US-04 EC-11 already established
for updating.

**EC-03**: **An ADMIN-role caller attempting to view a category they do not own** — refused exactly as
any other caller would be; no role elevates visibility through this endpoint, mirroring WM-US-03 EC-03/
TM-US-03 EC-03 for their own single-resource reads, and CM-US-02 EC-04's own "no role elevation" ruling
for the list endpoint.

**EC-04**: **A category with no `icon` ever set** — the request still succeeds, returning `icon` as
`null`; an absent icon is not an error condition for this endpoint, the ordinary state of every
category CM-US-01 creates and that CM-US-04 does not require to be set.

### Requirements *(mandatory)*

#### Functional Requirements

- **FR-01**: The system must **allow** an authenticated User of any role to view the full detail of a
  category they own, identifying it by its own identifier (SDS §5.4.3).
- **FR-02**: The system must **deny** the operation to unauthenticated callers, evaluating credentials
  before the category reference is examined at all (constitution API-08; mirrors CM-US-01 FR-02,
  CM-US-04 FR-02).
- **FR-03**: The system must **require** the submitted category reference to resolve to a category
  owned by the authenticated caller, and **refuse** the request with an identical outcome whether no
  such category exists at all or it exists and is owned by a different User (AC-03, AC-04, EC-01,
  EC-02; constitution SEC-08, VL-06).
- **FR-04**: The system must **apply no role elevation** — an ADMIN caller viewing a category they do
  not own is refused by the identical rule FR-03 states for any other caller (EC-03).
- **FR-05**: The system must **return**, on success, exactly the category's identifier, owner
  identifier, name, type, and icon — no other field, and no data belonging to any other User (AC-05).

#### Business Rules

- **BR-01**: A category's ownership for this operation is established directly from its own `user_id`
  column, the identical basis CM-US-04 BR-01 already established for update — no second table is
  consulted to decide ownership. A category reference that does not resolve to a row the caller owns
  is refused identically whether no such row exists at all or it exists and belongs to a different
  User (FR-03).
- **BR-02**: Viewing a category is a pure read; it changes no stored data.

#### Key Entities

- **Category**: A label a User defines to classify money movement as one kind of income or expense
  (SRS §1.5). Carries `id`, `user_id`, `name`, `type`, and `icon` (SDS §2.2, §4.3.3; CM-US-01,
  CM-US-04). This story only **reads** an existing Category row — the second Category Management
  story to do so without writing (after CM-US-02's list), and the first to do so for exactly one
  category at a time.
- **User**: Reused from Feature-01/Feature-02 with no new column. The authenticated caller's own
  ownership of the category being viewed is the only scope this story ever checks (constitution
  SEC-08).

### Success Criteria *(mandatory)*

- **SC-01**: An authenticated User can view the full detail of one of their own categories in one
  call, and the result carries all five of its documented fields.
- **SC-02**: No category can be viewed without an authenticated caller.
- **SC-03**: A category can never be viewed by a User who does not own it — whether because the
  reference does not exist at all, or because it belongs to someone else, the request is refused
  identically either way, regardless of the caller's role.
- **SC-04**: The response never exposes another category's or another User's data, and never carries
  any field beyond the five this story documents.

### Assumptions & Dependencies

- **Login (SS-US-01), Create a Category (CM-US-01), List Categories (CM-US-02), and Update a Category
  (CM-US-04) are already implemented.** Every acceptance criterion here presupposes at least one
  category already on record, owned by the authenticated caller — the identical dependency shape
  WM-US-03/TM-US-03 each declared on their own predecessors.

- **CM-US-05 (Delete a Category) is not yet designed, and this story does not depend on it.** The
  category identifier a caller submits to this endpoint is already available to them from CM-US-01's
  own create response or CM-US-02's own list response; no "delete" capability is a precondition for
  "view one."

- **SDS §5.4.3's "category metadata" wording raises no open design question the way WM-US-03's own
  "history" wording did, and this is reasoned through directly, not merely asserted.** WM-US-03's own
  `plan.md` A2 had to weigh three live readings of a goal sentence that named a second, genuinely open
  concept ("history") belonging to a different entity (Transaction) this codebase already models
  richly and separately. This story's own SDS goal — "View details and category metadata" — names
  nothing a Category does not already carry as one of its own five fields. Checked directly against
  SDS §2.2/§2.3's own domain model: Category's only relationship is `User "1" -- "*" Category :
  defines` (confirmed in CM-US-02's own Source section) — there is no second entity a Category "owns"
  the way Wallet owns its Transactions, so there is no sibling-entity data this endpoint could even be
  tempted to embed. "Metadata" is therefore read as the ordinary sense of "the category's own
  descriptive attributes" — `name`, `type`, `icon` — not as an invitation to surface Transaction or
  Budget rows that merely *reference* this category. This story's own response is `CategoryRead`
  reused unchanged, with no enrichment, matching WM-US-03 A2/TM-US-03 A3's own conclusion but arrived
  at here with a materially thinner source tension to resolve. No `[NEEDS RULING]` follows, the same
  outcome CM-US-02/CM-US-04 each recorded for their own thin-SDS situations.

- **The ownership-collapse behaviour (AC-03/AC-04 return the identical outcome) is reused, not
  redesigned.** This is the third Category Management story to need "does this reference resolve to a
  row the caller owns" (after CM-US-04's own update lookup, which itself reused the pattern BM-US-04
  established for Budget). `category_repo.get_owned_by_id()` already performs this collapse at the
  query level (confirmed directly by reading the file) — reused completely unchanged, following
  WM-US-03 A3/TM-US-03's own generalisation of the identical move one epic each before this one.

- **`CategoryRead` is reused completely unchanged — no new DTO, no enrichment.** Mirrors WM-US-03 A2/
  TM-US-03 A3 exactly. Unlike those two stories, there is no competing reading of the SDS goal to
  reject first (see above) — the "reuse, don't enrich" conclusion here has no real alternative to
  argue down.

- **`CategoryNotFoundError` is reused completely unchanged — no new error class.** It already exists
  (CM-US-04, built for exactly "the category being acted on directly was not found or not owned"), the
  identical situation WM-US-03 A7 found for `WalletNotFoundError` (already built by WM-US-04, one
  story earlier in that epic) — this is the second Category Management story in a row needing no new
  error class, after CM-US-04 itself needed one new class (`CategoryNotFoundError`) that this story
  now gets to reuse rather than build.

- **No audit event.** Constitution LA-04 names exactly three audited event families; viewing one
  category is no closer to any of them than creating one (CM-US-01 A8), listing them (CM-US-02 A5), or
  updating one (CM-US-04 A9) already were. No AC or FR here asks for one.
