# AIF-SDLC Review Checklist

> Use this after Claude produces an artifact at each step.
> Your job is to catch what Claude gets wrong (not follow `constitution.md`) — **not to redo the work**.

## Adaptations for the PFM project

This project has no Jira, and its stack differs from the one this checklist was written against. Two adaptations, recorded so nothing looks silently dropped:

**1. Ticket tracking removed.** Every `Jira & Git` block became a `Git` block: ticket-state checks are gone, gate-ordering and commit discipline stay. Bug tickets became defect records in `docs/06-defects/DEF-NNN-<slug>.md`, linked from the verification report. Progress lives in the session task list and git history.

**2. Stack-inapplicable items — mark `N/A (stack)`, do not silently skip.** The intent still maps:

| Written for | Applies here as |
| :-- | :-- |
| Java / Spring / Maven (`mvnw`, `@Transactional`, `@PreAuthorize`) | Python / FastAPI / `uv` (`uv run pytest`, explicit commit boundary, role dependency) |
| Flyway migrations (`V5__*.sql`) | Alembic revisions (`migrations/versions/`) |
| Playwright E2E + Testcontainers | `pytest` + `httpx`; E2E deferred until the mobile round |
| Next.js / shadcn/ui / Zod / Lucide | React Native + Expo — **deferred**, `mobile/` is a skeleton only |
| `/speckit.analyze`, `/model`, `/entity` prompts | not installed; the equivalent is a Gaps & Decisions pass in `plan.md` |
| Element IDs for frontend selectors | `N/A (mobile deferred)` until screens exist |
| Vietnamese UI labels, `Business Unit`/`Employee` domain terms | not applicable; PFM's domain is `User`/`Invitation`/`Wallet`/`Category`/`Budget`/`Transaction` |

Everything else applies as written.

---

- [Adaptations for the PFM project](#adaptations-for-the-pfm-project)
- [Process Notes](#process-notes)
- [Step 1 — Spec Step · BA Reviews](#step-1--spec-step--ba-reviews)
- [Step 2 — Design Step · SE Reviews](#step-2--design-step--se-reviews)
- [Step 3 — Quality Step · QC Reviews](#step-3--quality-step--qc-reviews)
- [Step 4 — Implementation Step · SE Reviews](#step-4--implementation-step--se-reviews)
- [Step 5 — Deployment Step · SE Reviews](#step-5--deployment-step--se-reviews)
- [Step 6 — Verification Step · QC Reviews](#step-6--verification-step--qc-reviews)
- [Presentation to PO](#presentation-to-po)
- [Experience Sharing](#experience-sharing)
  - [Spec Step (BA)](#spec-step-ba)
  - [Design Step (SE)](#design-step-se)
  - [Quality Step (QC)](#quality-step-qc)
  - [Implementation Step (SE)](#implementation-step-se)
  - [Deployment Step (SE)](#deployment-step-se)
  - [Verification Step (QC)](#verification-step-qc)

---

## Process Notes

- [ ] SDLC flow is followed in strict order: **Spec → Design → Quality → Implement → Deploy → Verification** — no step skipped or reordered
- [ ] If implementation diverges from `plan.md`, the plan is redefined first — never deviate silently and patch the plan afterward
- [ ] Diagrams, ERDs, and sequence diagrams are produced in the **Design step** — not introduced or altered during Implementation
- [ ] `spec.md` / `plan.md` are the artifacts under review here and do **not** need to match `SDS.md` / `SRS.md` verbatim — if `SDS.md` / `SRS.md` violate RESTful API or sequence-diagram principles, that violation is not propagated into `spec.md` / `plan.md`
- [ ] Step 6 Verification is recorded against the US itself — no separate verification artifact is created

---

## Step 1 — Spec Step · BA Reviews

**Artifacts:** `spec.md` in `specs/[feature-id]-[slug]/` (ex: `specs/001-system-security/`)  + SRS §7 update     


### Git
- [ ] Working on the Spec step for exactly one US; the story is recorded in the session task list
- [ ] Commit lands at the gate with a `docs(spec):` message naming the US and its AC range

### SRS §7 Entry
- [ ] Story statement is under the correct Feature section (`§7.x`)
- [ ] Story format is correct: **As a/an** [actor], **I want to** [goal] **so that** [reason]
- [ ] Actor matches one of the defined roles: `ADMIN | HR | FA | PM | DM | SYSTEM`
- [ ] **No ACs in SRS** — only the story statement; AC block is detailed in `spec.md`
- [ ] Spec link (`> Spec: [...]`) appears **once** on the Feature header (`§7.x`), not under the US entry
- [ ] SRS Table of Contents is updated to include the new US entry

### `spec.md` Content
- [ ] All acceptance criteria provided in the prompt are present in `spec.md`
- [ ] Every AC describes a **testable, observable outcome** — not an implementation detail
- [ ] No technology names, endpoint paths, or DB field names leaked into ACs (those belong to `plan.md`)
- [ ] No Domain Objects, no ERD, no sequence diagrams, no pre-defined table fields present — `spec.md` stays conceptual; those belong to the Design step
- [ ] Business terminology matches the constitution (e.g. "Business Unit" not "Department", "Employee" not "Staff")
- [ ] `spec.md` contains exactly **one US** — no `User Story 1 / User Story 2` sub-sections, no `Priority: P1/P2/P3`, no `Why this priority`, no `Independent Test` fields

### Traceability
- [ ] This US can be traced to a CDM entity (SRS §2) or a business flow step (SRS §6)
- [ ] If a new Domain Entity is introduced, SRS §2 is updated and the sync date is current
- [ ] Business rules, functional requirements, ACs, Edge Cases..., each carry a stable ID (e.g. `BR-08`, `EM-FR-01`, `AC-03`, `EC-06`...) for traceability

---

## Step 2 — Design Step · SE Reviews

**Artifacts:** `plan.md` in `specs/[feature-id]-[slug]/` (ex: `specs/001-system-security/`) + SDS §5 update

### Git
- [ ] The Spec gate for this US is closed before Design starts
- [ ] Commit lands at the gate with a `docs(design):` message naming the US and any ADRs

### Pre-flight Gaps
- [ ] Claude flagged zero spec gaps — or flagged gaps were resolved before `plan.md` was reviewed
- [ ] If `plan.md` still has significant gaps or ambiguity after review, the work goes back to the Spec step rather than being patched forward
- [ ] Design scope matches the US being designed — no scope creep into unrelated stories

### SDS §5 Entry
- [ ] Plan link (`> Plan: [...]`) appears **once** on the Feature header (`§5.x`), not under a US sub-section
- [ ] US sub-section `§5.x.N` contains **only** the Purpose field — no Scope, Preconditions, Flows, or ACs
- [ ] SDS Table of Contents is updated to include the new US sub-section

### `plan.md` — Technical Design
- [ ] Business logic is assigned to the **service layer** (AR-01); controllers are thin (AR-02); repositories are data-access only (AR-03)
- [ ] DTO mapping is handled by mapper classes or service methods — not controllers or repositories (AR-04)
- [ ] Multi-entity write operations are wrapped in a single `@Transactional` method (AR-05)
- [ ] Sequence diagrams follow the correct call chain: Controller → Service → Repository (AR-01–AR-03)
- [ ] Service layer never touches Controller-related objects like HttpRequest, HttpResponse... — that belongs to the controller (AR-01/AR-02)

### `plan.md` — Data Modeling
- [ ] Domain Entities (in CDM, SRS §2) are kept distinct from Domain Objects (in memory, `plan.md`) — no premature technical binding
- [ ] A separate model/entity for a Many-to-Many relationship is introduced **only** when the join table carries extra attributes (e.g. `enrolled_at`, `quantity`); otherwise a plain join table is used
- [ ] `GenerationType` (`AUTO` / `UUID` / `IDENTITY`) is chosen deliberately per entity, not defaulted blindly
- [ ] Eager vs Lazy loading is chosen per relationship with the tradeoff stated (N+1 select problem risk vs over-fetching)
- [ ] Employee vs User relationship is respected: `User` is composite with `Employee` (`User` = auth/login info, `Employee` = business info) — not merged or reversed
- [ ] Business Unit is scoped correctly: created when a new internal unit is needed and may represent a unit in a foreign country

### `plan.md` — Sequence Diagrams
- [ ] Arrows follow correct logical order and are numbered for traceability
- [ ] Every action arrow has a matching return arrow
- [ ] Arrow labels describe the action/intent, not a method name or UI click target (e.g. "validate employee code", not "call `validateCode()`" or "click Submit button")
- [ ] Diagram favors earliest possible UI response — the user is not made to wait on DB operations before seeing feedback
- [ ] Feature access goes straight to the relevant page (e.g. "create record" → navigate directly to the creation page) instead of intermediate click-throughs
- [ ] Each workflow is cut off cleanly when it ends — separate flows are not blended into one diagram
- [ ] No direct SQL statements, backend method signatures, or frontend method parameters appear on the diagram — only actor-level actions

### `plan.md` — API Design
- [ ] All endpoints are versioned under `/api/v1/` with kebab-case plural resource names (API-01)
- [ ] Response envelope is present: `{ success, message, data, timestamp }` (API-02)
- [ ] HTTP status codes follow the mapping table (201 for creation, 400 for malformed input, 409 for conflicts, 422 for validation, etc.) (API-03)
- [ ] Error codes use `UPPER_SNAKE_CASE` with a resource prefix — e.g. `PROJECT_NOT_FOUND`, `CONFLICT_PENDING_REQUEST` — and are listed in the SDS error catalog (API-04)
- [ ] No generic `updateStatus` endpoint — each business action that triggers a state transition has its own explicit endpoint (API-05)
- [ ] List endpoints include `page`/`pageSize` parameters; max 1000 (API-06)

### `plan.md` — Naming & Security
- [ ] Package names follow `com.globee.grm.<feature>` (NC-01)
- [ ] Entity, Request/Response DTO, and DB table names follow NC-02–NC-04
- [ ] Method names are concise within their service context (e.g. within `BusinessUnitService`, `create` not `createBusinessUnit`) — qualified only when disambiguating a different operation
- [ ] Enum values match the SRS state machine definitions and serialize as human-readable string labels in API responses — e.g. `"status": "InProgress"` in JSON, "In Progress" in UI (NC-05)
- [ ] Each endpoint's permitted roles match the permission matrix in SRS/SDS (AC-01)
- [ ] Role authorization (`@PreAuthorize` or service-level check) is specified on every protected endpoint (AC-02)
- [ ] CSRF validation is specified for all POST/PUT/PATCH/DELETE endpoints (AC-05)
- [ ] Any new public API route (no auth required) is explicitly justified — not silently added to the SecurityConfig allowlist (Tech-IV)
- [ ] Spring Security Filter Chain order is correctly reflected in the design: Web Filter → Security Filter Chain → `authorizeHttpRequests` → Controller
- [ ] Passwords are designed to be hashed before storage — never stored or compared as plain text
- [ ] Bookmark/direct-URL access is validated at the filter layer in addition to route guarding (double validation)

### Cross-Document Sync
- [ ] If a new Domain Entity is introduced: SDS §2.1 traceability table is updated in the same edit (Cross-Doc)
- [ ] SRS §2 ↔ SDS §2.1 sync dates are current (Cross-Doc)
- [ ] Every entity name in `plan.md` matches the SRS §2 domain language exactly — no synonyms (Cross-Doc)

---

## Step 3 — Quality Step · QC Reviews

**Artifacts:** `test_cases.md` + `test_[feature-id].spec.ts` (ex: `test_001-system-security.spec.ts`) in `specs/[feature-id-slug]`

### Git
- [ ] The Design gate for this US is closed before Quality starts
- [ ] Commit lands at the gate with a `docs(test):` message naming the US and its TC range

### `test_cases.md` — Coverage
- [ ] At least **one test case per acceptance criterion** in `spec.md`
- [ ] Unhappy paths covered: validation errors, rejected states, guardrail violations
- [ ] Edge cases covered: boundary values, empty/null inputs, concurrent or duplicate actions

### `test_cases.md` — Structure
- [ ] Every TC-NN has all six fields: **US, Given, When, Then, AC reference, Type**
- [ ] TC numbers are sequential with **no gaps**, continuing from the last TC-NN in the file
- [ ] New TCs are appended — existing TCs from prior USs are not modified or removed

### Playwright Code — Integration Tests
- [ ] Entity ID extracted from **POST response directly** (`const { id } = await res.json()`) — never from a GET list
- [ ] Validation error assertions use `expect([400, 422]).toContain(res.status)`
- [ ] Business rule conflict assertions use `expect(res.status).toBe(409)`
- [ ] Each test creates all required data **fresh inside the test** — no reliance on seeded data

### Playwright Code — E2E Tests
- [ ] Selectors use **ID first** (`#btn-save-{id}`, `#message-success`), then text, then role
- [ ] Custom dropdowns handled as `ul > li > button` (no ARIA role assumed)
- [ ] Filter panel not toggled manually — selectors like `#search-name`, `#btn-search` used directly
- [ ] After API-creating an item: filter by name **before** clicking action buttons (pagination)
- [ ] Text locators scoped to table container (`#table-x`) to avoid matching hidden mobile cards
- [ ] Access-denied messages use `waitFor({ state: 'visible' })` (RoleGuard inline, no redirect)

### Playwright Code — General
- [ ] All test-created records are prefixed: `TestQC-[entity]-${Date.now()}`
- [ ] Existing helpers (session, apiRequest, navigateAs*) are **reused**, not duplicated
- [ ] New Playwright tests are **appended** to the existing `.spec.ts` — existing tests are untouched

---

## Step 4 — Implementation Step · SE Reviews

**Artifacts:** `tasks.md`, code diff, pre- and post-`/speckit.analyze` reports

### Git
- [ ] The Quality gate for this US is closed before Implementation starts
- [ ] Tests commit (`test:`) precedes the implementation commit (`feat:`), so the red-then-green order is visible in history

### Pre-implementation (`/speckit.analyze` report)
- [ ] **All Critical and High findings resolved** before `/speckit.implement` was run
- [ ] `tasks.md` covers every AC in `spec.md` and every component in `plan.md`
- [ ] Tasks are ordered: DB migration → DB entity → repository → service → controller → frontend

### Code Diff — Backend
- [ ] Backend code is not placed in `frontend/` and vice versa; shared config stays at repo root (Tech-I)
- [ ] Business logic lives in the service layer only — not in controllers or repositories (AR-01)
- [ ] Controllers contain only: HTTP binding, validation delegation, service call, response formatting (AR-02)
- [ ] Passwords are hashed (e.g. BCrypt) before persistence — plain text is never stored
- [ ] `@Transactional` is applied to write operations (Create/Update/Delete) only — never on read-only GET methods
- [ ] `@Transactional` parameters (e.g. `propagation`, `readOnly`) are written out explicitly rather than relying on silent defaults
- [ ] Validation errors are grouped and returned together in a single response — not one 400/422 per field
- [ ] Audit logging logic is extracted into a shared/common service — not duplicated per feature
- [ ] Method parameter names are pluralized when they hold arrays/multiple entities (e.g. `employeeIds`, `roles`) — not a singular name for a collection
- [ ] Numeric literals (e.g. clamped page size, max limits) are defined as named constants — not inline magic numbers
- [ ] Schema changes are in a **new numbered Flyway migration file** — no `ddl-auto: update` or `create` (Tech-II)
- [ ] All API responses use the standard envelope: `{ success, message, data, timestamp }` (API-02)
- [ ] HTTP status codes are correct: 201 for creation, 409 for conflict, 422 for validation, 404 for not found (API-03)
- [ ] Error codes use `UPPER_SNAKE_CASE` with a resource prefix — e.g. `EMPLOYEE_NOT_FOUND`, `CONFLICT_PENDING_REQUEST` (API-04)
- [ ] List endpoints enforce pagination with default page size 25 and maximum 1000; response includes total count (API-06 / PF-05)
- [ ] Code identifiers follow naming conventions: Java packages (NC-01), entity/DTO names (NC-02), API paths (NC-03), DB table/column names (NC-04), enum serialization (NC-05)
- [ ] Each endpoint's permitted roles match the permission matrix in SRS/SDS (AC-01)
- [ ] Every protected endpoint has `@PreAuthorize` or a service-level role check (AC-02)
- [ ] Ownership is validated where applicable — e.g. PM may only submit PURs or trigger status changes on their own projects (AC-03)
- [ ] Sensitive employee fields (salary, personal contact) are filtered from API responses based on the caller's role (AC-04)
- [ ] CSRF is validated for all POST/PUT/PATCH/DELETE endpoints (AC-05)
- [ ] Any new public route added to the SecurityConfig allowlist has a documented reason (Tech-IV)
- [ ] Required fields validated via DTO annotations (`@NotNull`, `@NotBlank`, etc.); backend is the source of truth — frontend Zod is UX only (VL-01 / DOD-04)
- [ ] Unique codes/names validated at three levels: frontend debounce, service layer check, and DB unique index — returns `CODE_ALREADY_EXISTS` / `NAME_ALREADY_EXISTS` on conflict (VL-02)
- [ ] Referenced entities are verified for existence and active status before use — returns 404 if not found, 409 if found but inactive (VL-03)
- [ ] Date range fields validate `startDate ≤ endDate` at form level and service level (VL-04)
- [ ] Numeric fields validate acceptable range, precision, and reject negatives where the domain forbids them (VL-05)
- [ ] All applicable Business Rules (BR-01–BR-10) for this US are enforced in the service layer — check `constitution.md` §Business Rules for the relevant BRs
- [ ] No PII, passwords, tokens, or credentials appear in log statements or source files (LA-01)
- [ ] Critical business events are logged at INFO with: timestamp, entity ID, actor user ID, action, result (LA-02)
- [ ] 403 and 401 responses are logged at WARN with: HTTP method, path, user ID (if known), and required role (LA-03)
- [ ] Permanent audit records are produced for: login/logout, project approval/rejection, PUR approval/rejection, and data configuration changes (LA-04)
- [ ] New DB columns used in `WHERE`, `JOIN`, or `ORDER BY` clauses have an index; no N+1 queries introduced (PF-01)
- [ ] API responses use DTO projections — no full entity graphs or unnecessary fields serialized (PF-02)
- [ ] `/health`, `/actuator/health`, and `/actuator/info` still return 200; Prometheus metrics endpoint not disabled (Tech-V)

### Code Diff — Frontend
- [ ] No `.js` or `.jsx` files in `frontend/src/` — TypeScript only; no `any` types without an explanatory comment (Tech-III)
- [ ] Zod schema matches backend DTO validation annotations — required fields, constraints, patterns (FE-01 / DOD-05)
- [ ] Navigation, form buttons, and action controls are hidden for roles that cannot perform the action (FE-02)
- [ ] Existing shadcn/ui primitives used before creating custom components; new shared components go in `components/features/` with a typed props interface (FE-03)
- [ ] All icons come from Lucide React — no mixed libraries or inline SVGs (FE-04)
- [ ] Every form shows: inline field-level errors on blur/submit, form-level error summary when multiple errors exist, loading state during submission, and success toast or redirect on completion (FE-05)
- [ ] Data tables for large datasets (employees, projects, costs) support column sorting, filtering, pagination (10/25/50 rows), and search (FE-06)
- [ ] All API calls go through the Next.js `/api/v1/[...path]` proxy — never directly to `localhost:9090` (FE-08)

### Test Coverage
- [ ] At least one **integration test** covers the happy path for every new endpoint (DOD-06)
- [ ] Integration tests for key error cases: invalid input, wrong role, conflict, not found (DOD-06)
- [ ] Authorization tests confirm `403` for disallowed roles and `401` for unauthenticated requests (DOD-03)
- [ ] Tests use **Testcontainers** (real DB) — no mocked repositories (Integration Testing)

### Post-implementation (`/speckit.analyze` report)
- [ ] No new Critical or High findings introduced by the implementation

### Document Sync (Definition of Done)
- [ ] SRS §7 ACs refined if the implementation revealed edge cases (DOD-01)
- [ ] SDS §5 design notes finalized — no "TBD" or "to be added" placeholders remaining (DOD-02)
- [ ] SDS §2.1 traceability table updated with actual class/table names (DOD-01)
- [ ] SDS §4.3.3 DB schema updated with final column definitions (DOD-02)
- [ ] SRS §2 / SDS §2 sync dates updated if any domain entity changed (Cross-Doc)

---

## Step 5 — Deployment Step · SE Reviews

**Artifact:** Deployed Test Environment

### Pre-deployment
- [ ] `./mvnw test` passed with **zero failures** before any deployment steps
- [ ] `docker compose down -v` was **not** used — it wipes all server data
- [ ] No existing Flyway migration file was edited — schema changes go in a new `V_next` file

### Deployment Health
- [ ] `GET [Test Env URL]:9090/health` returns 200
- [ ] `GET [Test Env URL]:9090/actuator/health` returns 200
- [ ] Frontend is reachable at `[Test Env URL]:3001`

### Handoff
- [ ] Deployment step marked complete in the session task list
- [ ] The running base URL is recorded in the evidence file so Step 6 can begin

---

## Step 6 — Verification Step · QC Reviews

**Artifact:** Verification report + Playwright report

### Pre-flight
- [ ] The Deploy step is complete, with pasted evidence, before Verification starts
- [ ] Every TC for this US has a recorded result before the story is called done

### Playwright Run
- [ ] Test run targets the correct spec file and filters to the correct US tag
- [ ] Every **e2e test case** in `test_cases.md` for this US has a recorded result (PASS / FAIL / BLOCKED)
- [ ] Every **integration test case** not covered by Playwright is manually verified and documented

### Verification Report
- [ ] Report table includes every TC-NN with: Test Name, AC reference, Type, Result, Notes
- [ ] Playwright report is saved to `automation-test/[feature-id-slug]/index.html` (ex: `automation-test/001-system-security/index.html`)

### On Failure
- [ ] A defect record is written to `docs/06-defects/DEF-NNN-<slug>.md` with: summary, reproduction, expected vs actual, the TC that caught it
- [ ] The defect is linked from the verification report
- [ ] The story stays open until the defect is fixed and re-verified

### On Full Pass
- [ ] All automated and manual checks are PASS
- [ ] `docs/traceability.md` shows every AC resolving to a passing test with a real pytest node id
- [ ] Story marked complete in the session task list

---

## Presentation to PO

- [ ] Recap the business flow from SRS before diving into details
- [ ] State clearly what has been completed and where the project currently stands
- [ ] Call out any open issues, risks, or blockers
- [ ] Structure the presentation with 5W1H — What it is, why it was done, who the audience is, when it's used, where it's used, how it was implemented

---

## Experience Sharing

### Spec Step (BA)

1. **ACs not derived from the FR table**
   - ACs in `spec.md` were written from memory or general understanding rather than traced from the Functional Requirements table in SRS §3.
   - This results in incomplete coverage — typically 8–10 ACs when the FR table would yield 15+.
   - Every AC must map to at least one FR row.

2. **Spec link placed at the wrong heading level**
   - The spec link (`> Spec: [...]`) is placed under a US entry (`§7.x.N`).
   - The correct position is at the feature header (`§7.x`), added once for the entire epic — never duplicated under individual stories.

3. **AC block left inside SRS**
   - Ensure ACs are documented only in `spec.md`, not in the SRS story entry — SRS should contain only the story statement.
   - SRS entries frequently contain AC blocks that belong exclusively in `spec.md`.
   - This violates the SRS/spec separation principle and causes duplication drift over time.

4. **Missing button and form behavior ACs**

   Create/edit form stories consistently lack ACs for:
   - Submit button loading state (disabled + label change during API call)
   - All interactive buttons disabled during the save operation
   - Form panel behavior (dismiss on success, stay open on error)

   These are always present in the implementation but are rarely specified upfront.

5. **SRS ToC not updated in the same edit**
   - After adding or renaming a story, the SRS ToC and SDS ToC entries are frequently left out of sync with the body.
   - Both ToCs must be updated in the same edit — this is a mandatory spec convention.

6. **Role mismatch between SRS and SDS**
   - Inconsistencies found across documents: a story marked `(ADMIN)` in SRS but `(Admin, HR)` in SDS, or `(All)` missing from dashboard and notification stories.
   - These mismatches are not caught when each document is reviewed in isolation.

7. **Full Scenario Coverage**
   - Make sure ACs cover full scenarios, including happy cases and edge cases like validation error, access denied, and similar boundary conditions.

8. **AC Clarity**
   - The ACs must be clear and detailed enough to ensure a shared understanding among all team members and prevent any confusion.

9. **Constitution Compliance**
    - Verify that ACs comply with and reference `constitution.md` as required.

### Design Step (SE)

1. **Constitution violations not flagged before handing off**

   Design artifacts are handed off to QC and Implementation without a constitution check. Violations are only discovered when the reviewer explicitly asks. Across all reviewed sessions, the following rules were missed every time without prompting:

   | Rule | Observation |
   |------|-------------|
   | API-06 / PF-05 | List endpoints designed without pagination — returns unbounded data |
   | LA-02 | Audit log design missing actor role field |
   | LA-04 | Audit storage designed as in-memory — not permanent |
   | API-02 | Response structure missing standard envelope (`success`, `message`, `data`, `timestamp`) |
   | DOD-06 | No test tasks included in the plan |

2. **`plan.md` uses non-standard sections**
   - Reviewed plans occasionally introduce sections that do not exist in the established template (e.g., `## Technical Context`, `## Constitution Check` invented inline).
   - These sections are inconsistent with other feature plans and mislead future readers.

3. **Pre-flight check uses the wrong working directory**
   - Pre-flight verification fails with a false `STOP` because the file lookup uses a relative path instead of the correct absolute path under `grm/`.
   - This blocks the step unnecessarily and wastes reviewer time.

4. **Spec Readiness Check**
   - Verify the targeted US exists in `spec.md` and that all requirements are clear, complete, and unambiguous before proceeding.

5. **Gap References to ACs**
   - Ensure that found gaps and open tasks reference the specific ACs in `spec.md`.

6. **Sequence Diagram Coverage**
   - Ensure that any available sequence diagrams cover the main flow as well as key error scenarios.

7. **SDS §5 Sub-section Structure**
   - Ensure that SDS §5 sub-section contains only the Purpose, removing Scope, Preconditions, Functional Design, and Flows if they are present.

8. **Plan Link Placement**
   - Make sure the Plan link is added only once on the SDS feature header and is not duplicated for second or subsequent USs.

9. **Use `/model` over `/entity`**
    - Prefer the `/model` prompt over `/entity` when generating technical design — it produces clearer separation between conceptual and technical domain objects.

### Quality Step (QC)

1. **Review AI-Generated Test Cases**
   - Carefully review all test cases generated by AI.
   - Ensure the test scenarios, test steps, and expected results are clear and understandable.

2. **Validate Against Requirements**
   - Compare the generated test cases with the `spec.md` document to verify accuracy and coverage.
   - If any scenario or requirement is unclear, ask the AI to explain its interpretation before proceeding.

3. **Identify Missing Test Coverage**
   - Review the requirement coverage and identify any missing test scenarios.
   - Provide feedback to the AI and request updates to both the test cases and the corresponding automation code.

4. **Remove Unnecessary Test Coverage**
   - Identify redundant, low-value, or out-of-scope test cases.
   - Instruct the AI to remove both the test cases and their associated automation code.

5. **Perform AI Self-Review**
   - Ask the AI to perform a second-pass review against the specification to verify whether any additional scenarios are still missing.
   - Confirm that the automation code remains fully aligned with the latest version of the test cases after any additions or removals.

6. **Analyze Coverage Gaps**
   - Ask the AI to summarize the reasons why any test cases were initially missing, duplicated, or unnecessary.
   - Refine the prompt if necessary to improve future test generation quality.

### Implementation Step (SE)

1. **Code not validated against spec AC**

   The most frequent implementation gap: business rules in the spec are not enforced in code. Common examples:
   - Employee code regex `^[A-Z0-9.]{3,20}$` instead of `^GB\.\d{4}$` (BR-08)
   - Uniqueness checked only at the database level, not at the service layer (BR-09 / VL-02)

2. **HTTP status codes inconsistent with the constitution**

   Reviewed PRs frequently use wrong status codes:

   | Scenario | Wrong | Correct |
   |----------|-------|---------|
   | Validation error | 400 | 422 |
   | Unauthenticated | 403 | 401 |
   | Business conflict / duplicate | 400 | 409 |

3. **Error codes mismatched between tests and implementation**
   - Integration tests assert error codes that do not match what the code actually returns (e.g., `CSRF_INVALID` vs `INVALID_CSRF_TOKEN`).
   - Tests pass code review but fail at runtime because no one cross-checked the actual response.

4. **Audit logging incomplete**
   - Reviewed code frequently logs only the action and entity — missing actor role, structured JSON format, and UTC timestamp.
   - LA-02 requires all five fields.

5. **UI element IDs missing or inconsistent**
   - Reviewed frontend code contains interactive elements without stable `id` attributes, or IDs that differ from the naming convention in `plan.md`.
   - Since QC and Implementation run in parallel, missing IDs discovered late cause rework in both the spec and the tests.
   - Recheck and update `test_cases.md` and `test_*.spec.ts` to ensure test functions use ID selectors for frontend component targeting and properly access the backend for automated testing.

6. **`/speckit.analyze` not run before starting**
   - Pre-implementation analysis is skipped, so gaps between `spec.md`, `plan.md`, and `tasks.md` are only discovered mid-implementation.
   - Running `/speckit.analyze` before writing any code surfaces these gaps early and prevents rework.

7. **Task Coverage Verification**
   - Ensure the work breakdown in `tasks.md` covers all ACs and that all tasks have been fully implemented, not just marked as Done.

8. **Integration Test Coverage**
   - Make sure integration tests have been created for every new endpoint, covering all happy-case scenarios.

9. **Flyway Migration Immutability**
    - Prevent making changes to existing Flyway migration files, especially after the application has been deployed to PROD.

10. **Code Quality Review**
    - Recheck code changes, run unit tests, and then provide clear instructions to AI to improve quality (algorithm, UI/UX, code structure, naming, etc.) or fix any identified issues.

11. **SDS §6.3 API Index Update**
    - Check and update SDS §6.3 API index if there are new endpoints.

### Deployment Step (SE)

1. **Flyway migration files edited after being applied**
   - V1 or V2 migration files are modified after already being applied to the database.
   - Flyway detects the checksum mismatch and refuses to boot.
   - The correct practice — creating a new migration file for any amendment — is consistently skipped under time pressure.

2. **Backend tests skipped before deployment**
   - Make sure all tests related to the US pass before deploying code to the remote host.
   - Deployment proceeds without running `mvnw test`.
   - Pre-existing failures in other modules are then reported as deployment failures, making the report unreliable.
   - Tests must pass before any deployment — not after.

3. **Deployment report mixes scopes**
   - Reports include test failures from unrelated modules alongside the US being deployed, without separating them.
   - Reviewers cannot determine whether the deployment itself succeeded.
   - The report must clearly distinguish failures within the US scope from pre-existing failures in other modules.

4. **Branch and Commit Verification**
   - Recheck and confirm that the app repo on the remote host is correctly set to the intended branch and commit.

5. **Application Rebuild Verification**
   - Verify that the application has been rebuilt and starts successfully on the remote host without any errors.

6. **Error Isolation**
   - If there is any error, do not execute any commands that may affect other apps on the remote host.

7. **Post-deployment Reachability**
   - Confirm both backend and frontend are reachable after deployment and fixes.

8. **Evidence File Update**
   - Record deployment status, any failed tests with reasons, and the confirmed base URL in the step's evidence file.

### Verification Step (QC)

1. **Execute the Initial Test Run**
   - Run the generated automation code for the first time and observe the execution results.
   - Do not allow the AI to automatically debug or modify the code during this initial run — the automation code is generated before implementation is fully validated; assumptions, workflows, or locators may be inaccurate.
   - Allowing unrestricted self-debugging at this stage may result in excessive token consumption and unnecessary code changes.

2. **Review Proposed Code Changes**

   Whenever the AI proposes code updates:
   - Review the specific changes and understand the reason for each modification.
   - If the change is valid, approve the update.
   - If the change appears incorrect, verify the behavior manually and provide guidance to the AI.
   - If the rationale is unclear, request a detailed explanation before proceeding.

3. **Validate Test Report**

   After all test cases have been executed, review the test report, including execution results and screenshots.

   For any failed test case:
   - Reproduce the scenario manually.
   - Determine whether the failure is caused by an application defect or an automation issue.
   - If the failure is not a product bug, ask the AI to investigate the root cause.
   - Update the automation code if necessary and rerun the affected test cases.

4. **Perform Final Regression Run**
   - Execute the full test suite again after all corrections have been completed.
   - Verify the final execution status and generate the final test report.
   - Log confirmed defects in `docs/06-defects/` with evidence.

5. **Analyze Automation Code Changes**
   - Ask the AI to summarize all code changes made during the execution and debugging process.
   - Identify the root causes that required modifications to the original generated automation code.
   - Refine the prompt if necessary to reduce similar issues in future automation generation.

---

## Gate Record

Claude must paste one of these when claiming a step gate. A gate claimed without it is not a gate.

```markdown
### Gate: <US id> — Step <n> <Step name>
Checklist run: <date>
Sections passed: <list the sections reviewed>
N/A (stack): <items marked inapplicable, with the mapping used>
Waived: <item> — <reason>
Blocking issues: none | <list>
Evidence: <pasted command output, or "documents only">
```

---

*Reference: [constitution.md](constitution.md) · [CLAUDE.md](CLAUDE.md) · [artifact-templates/](artifact-templates/)*
