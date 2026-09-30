# Feature Specification: Category Management (CM)

> **Feature:** SRS §6 Feature-04 · SDS §5.4 (CM)
> **Spec:** [spec.md](spec.md)
> **Stories in this file:** CM-US-01 *(implemented, verified — 219 passed, 99% coverage)* · CM-US-02 *(specified)*

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
