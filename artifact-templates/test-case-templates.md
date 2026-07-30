
## PM-US-02: List Projects

> **Jira Story:** [GBX03-20](https://globee-software-ecommerce.atlassian.net/browse/GBX03-20)
> **Quality Step ticket:** [GBX03-228](https://globee-software-ecommerce.atlassian.net/browse/GBX03-228)

### Quality Findings

#### QF-08
**Description.** Scope filtering ("Projects a PM manages" / "assigned to a DM", AC-13/FR-27) requires resolving the authenticated User to its own Employee record, but `plan.md` G1/T14 flags that the `users`↔`employees` link is an **open task** — it does not exist in code yet. There is also no "current user's Employee" (`whoami`) endpoint, and no public way to know which seeded Employee maps to `pm.user@globee.local` / `dm.user@globee.local`.

**Impact.** A strictly deterministic PM/DM *own-scope* assertion ("PM sees exactly the Projects they manage, and no others") cannot be constructed through the public API or the UI: creating a Project as `pm.user` with an arbitrary `pmEmployeeId` does not guarantee that Project falls into `pm.user`'s own scope, because the list filters on the acting user's *resolved* Employee, not on the id supplied at create time.

**Recommendation.** Cover AC-13/FR-27 with the deterministic surface that *is* available: (a) **FA scope** (sees all Projects) is fully deterministic and is the primary happy-path proxy — TC-54; (b) the **scope-narrowing invariant** `PM total <= FA total` and `DM total <= FA total` is deterministic and real — TC-62; (c) a **strict own-scope** test is environment-gated (`test.skip` unless `GRM_PM_SELF_PROJECT_ID` names a Project known to be managed by `pm.user`) and otherwise asserted in the backend Testcontainers suite — TC-63. This mirrors PM-US-01's handling of un-constructable preconditions (QF-06; gated TC-10).

#### QF-09
**Description.** AC-16 / FR-26 require "an explicit empty indicator" when Forecast Income or Customer Name is absent, but neither `spec.md` nor `plan.md` names the glyph/text to render.

**Impact.** The E2E assertion for AC-16 must assume a concrete indicator string.

**Recommendation.** Tests assume the em dash as a non-blank, non-zero indicator. If the Implementation Step renders a different indicator, update TC-74 and the frontend together in that PR (FE-06/Cross-Document Consistency). The **integration** assertion is glyph-independent — it checks the API serializes the absent value as `null` (not `0`, not empty string).

#### QF-10
**Description.** AC-14 requires "every status ... from `New` through `Cancelled`" to appear within scope, but PM-US-01 creates Projects only in `New` status and all lifecycle transitions are explicitly out of scope for this feature slice. The only status this suite can *construct* is `New`.

**Impact.** Full every-status coverage depends on the `plan.md` T20 dev seed (Projects spanning every status), which this suite cannot create for itself.

**Recommendation.** The integration test (TC-56) asserts (a) every returned `status` is a valid `ProjectStatus` display label, and (b) the constructable `New` status appears. Strict "all nine statuses present" is gated on the T20 seed and left to the backend Testcontainers suite.

#### QF-11
**Description.** `plan.md` T16 names the `ProjectSummaryResponse` DTO and its six fields conceptually but not the concrete JSON field names.

**Impact.** Tests must assume the response shape before the DTO exists.

**Recommendation.** Tests assume camelCase, consistent with `EmployeeSummaryResponse`: `code`, `name`, `businessUnitName`, `forecastIncome`, `customerName`, `status` — exactly six keys, no more (PF-02). Reconcile with the real DTO in the Implementation Step if it differs.

#### QF-12
**Description.** AC-17 (retrieval audit) records a `PROJECT_LIST` event, but no audit-log retrieval endpoint exists (constitution AC-06 restricts audit reads to ADMIN and there is no such endpoint in this feature).

**Impact.** The audit entry cannot be asserted through any public API or UI path.

**Recommendation.** TC-72 is `test.skip`'d here and asserted only in the backend Testcontainers suite by inspecting `activity_logs` — identical to PM-US-01 TC-22.

#### QF-13
**Description.** `spec.md` AC-13/FR-26 name "owning Business Unit" as a displayed and sortable field but do not say whether it displays/sorts by the Business Unit's `code` or `name`; `plan.md` A2 resolves this to **`name`** (matching the `EmployeeSummaryResponse.businessUnitName` convention).

**Impact.** The list-row field and the `sortBy` value must pick one.

**Recommendation.** Tests use the field `businessUnitName` and the sort header id `sort-business-unit` with `sortBy=businessUnitName`, per `plan.md` A2.

#### QF-14
**Description.** EC-08 (no Projects / empty scope) cannot be produced deterministically for an FA against ambient data (other tests and the T20 seed create Projects), and PM/DM empty scope is blocked by QF-08.

**Impact.** A live empty-list E2E is not constructable.

**Recommendation.** The E2E empty-state (TC-81) uses a Playwright route mock returning an empty page (EM-US-03 TC-100 precedent). The **API** empty-page path is exercised deterministically via page-beyond-range (TC-69, EC-09), which returns `content: []` regardless of scope.

### Acceptance Criteria Classification

| AC/EC | Title | Label | Rationale |
|---|---|---|---|
| AC-13 | View the Project list (scope, six fields, total count) | **[BOTH]** | API: envelope, exact six fields, total, scope invariant; UI: table renders the fields |
| AC-14 | All statuses visible within scope | **[BOTH]** | API: `status` label serialization; UI: status column renders label — bounded by QF-10 |
| AC-15 | Paginated results (bounded page, further-pages indication, total) | **[BOTH]** | API: page/pageSize/totalElements/totalPages; UI: pagination + page-size controls |
| AC-16 | Absent optional values shown explicitly | **[BOTH]** | API: `null` serialization; UI: explicit empty indicator (QF-09) |
| AC-17 | Retrieval audit | **[API]** | Backend persistence only — no audit-read endpoint (QF-12) |
| AC-18 | Disallowed roles (ADMIN, HR) denied | **[BOTH]** | API 403 `ACCESS_DENIED`; UI inline access-denied, table absent |
| AC-19 | Unauthenticated access denied | **[BOTH]** | API 401 `UNAUTHORIZED`; UI redirect to login |
| AC-20 | Ordered results (six fields, asc/desc, default) | **[BOTH]** | API: sorted content + invalid→default; UI: sort header reorders rows |
| EC-08 | No Projects / empty scope | **[UI]** | Empty-state message (route mock, QF-14); API empty path via EC-09 |
| EC-09 | Requested page beyond available data | **[API]** | Empty page, 200 — no distinct UI surface |
| EC-10 | Invalid pagination values | **[API]** | Clamped to defaults/max, 200 — backend concern |
| EC-11 | Invalid ordering values | **[API]** | Default order applied, 200 — backend concern |

### Coverage Matrix

| AC/EC | Label | Integration TC(s) | E2E TC(s) |
|---|---|---|---|
| AC-13 | [BOTH] | TC-54, TC-59, TC-62, TC-63 | TC-73 |
| AC-14 | [BOTH] | TC-56 | TC-75 |
| AC-15 | [BOTH] | TC-57, TC-58 | TC-76, TC-77 |
| AC-16 | [BOTH] | TC-55 | TC-74 |
| AC-17 | [API] | TC-72 | — |
| AC-18 | [BOTH] | TC-60 | TC-79 |
| AC-19 | [BOTH] | TC-61 | TC-80 |
| AC-20 | [BOTH] | TC-64, TC-65, TC-66, TC-67, TC-68 | TC-78 |
| EC-08 | [UI] | TC-69 | TC-81 |
| EC-09 | [API] | TC-69 | — |
| EC-10 | [API] | TC-70, TC-71 | — |
| EC-11 | [API] | TC-67, TC-68 | — |

> All `[BOTH]` and `[UI]`-classified rows have at least one E2E TC. `[API]`-only rows (AC-17, EC-09, EC-10, EC-11) are justified above (no audit-read endpoint per QF-12; page/pagination/ordering are backend contract concerns with no distinct UI surface). TC-63 (strict PM own-scope) is environment-gated per QF-08; TC-72 (retrieval audit) is backend-Testcontainers-only per QF-12.

### TC-54: FA lists all Projects — 200, envelope, exactly the six summary fields

- **US:** PM-US-02
- **Given:** An authenticated FA user, and a Project created via PM-US-01 (mandatory-only, so Forecast Income and Customer Name are absent)
- **When:** `GET /api/v1/projects` is sent (FA scope = all Projects)
- **Then:** The response is `200`; `body.success = true`; `body.data.content` includes the created Project (found by Code); that item exposes **exactly** the keys `code`, `name`, `businessUnitName`, `forecastIncome`, `customerName`, `status` (no other field, PF-02/QF-11); `body.data.totalElements` is present
- **AC:** AC-13, FR-26
- **Type:** integration

### TC-55: Absent Forecast Income / Customer Name serialize as null

- **US:** PM-US-02
- **Given:** An authenticated FA user and a Project created with no Forecast Income and no Customer Name
- **When:** `GET /api/v1/projects` is retrieved and the Project located by Code
- **Then:** The item's `forecastIncome` is `null` and `customerName` is `null` — not `0`, not empty string (glyph-independent, QF-09)
- **AC:** AC-16, FR-26
- **Type:** integration

...

