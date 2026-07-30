# CLAUDE.md — how work is done in this repo

Personal & Family Finance Management (PFM). This file is the operating contract for AI-assisted work here. Read it before touching anything.

The purpose of this project is to practise the **AIF-SDLC cycle**, where documents drive code. Producing implementation before its spec/design/test artifacts exist defeats the point and has already been rejected once — see `docs/00-foundation/spike-notes.md`.

---

## 1. Reference documents

| File | Owner | Rule |
| :-- | :-- | :-- |
| `SRS.md` v2.0.0 | the user | **Read-only. Never edit.** Requirements baseline: FR, NFR, UXR, BF, Features 01–11 with Gherkin. |
| `SDS.md` v1.0.0 | the user | **Read-only. Never edit.** Technical baseline: domain model, ERD, architecture, API design, security design. |
| `aif-review-checklist.md` | the user | Run before claiming any step gate. Edited once to remove Jira and record stack adaptations; otherwise treat as the user's. |
| `artifact-templates/*.md` | the user | **Read-only. Never edit. Never split.** The canonical shape of every artifact — see §1.1. |
| `constitution.md` | AI + user | Project rules with stable IDs (AR/API/NC/VL/LA/PF/SEC/TST/DOD/ENV), derived from the SDS. |
| `specs/**`, `docs/**` | AI + user | Working artifacts. Design output goes here — **never** into `SDS.md`. |

`SDS.md` was aligned to `SRS.md` on 2026-07-30 and bumped to v1.1.0. The full audit trail is `docs/00-foundation/srs-sds-alignment.md`. **`SRS.md` now wins any remaining disagreement.**

## 1.1 Artifact rules

1. **One file per epic — never split.** Artifacts live at `specs/<NNN>-<epic-slug>/{spec.md, plan.md, test_cases.md}`. Every story in that epic is appended to the **same** file as a new `## <CODE>-US-NN` section. Never create a markdown file per story. This is how the checklist's "spec.md contains exactly one US" is satisfied: it means *specify one story per step*, not one file per story.
2. **Read `artifact-templates/` before writing or updating any artifact.** Match the template's section order, heading style, ID schemes, and status vocabulary. `spec-templates.md` → `spec.md`, `plan-templates.md` → `plan.md`, `test-case-templates.md` → `test_cases.md`.
3. **No Jira.** Never emit `> **Jira Story:**` or `> **Jira Epic:**` lines, and never check ticket state.
4. **Append, never renumber.** `TC-NN` runs continuously across an epic file; a new story continues from the last one. Existing AC/EC/FR/BR/TC entries are never renumbered or rewritten.

### ID schemes

| Prefix | Meaning | Artifact |
| :-- | :-- | :-- |
| `AC-NN` | Acceptance criterion (Given/When/Then) | spec.md |
| `EC-NN` | Edge case | spec.md |
| `FR-NN` / `BR-NN` | Functional requirement / business rule | spec.md |
| `SC-NN` | Success criterion | spec.md |
| `A1` / `R1` / `G1` | Gap or decision: assumption / refactor / open gap | plan.md |
| `T-NN` | Open implementation task | plan.md |
| `QF-NN` | Quality finding | test_cases.md |
| `TC-NN` | Test case | test_cases.md |

### Status vocabularies

- Gaps & Decisions → `✅ Resolved`
- Constitution notes → `Required` · `N/A` · `Required (exempt)` · `Required (spec-stricter)`
- Element IDs → `Missing` · `Present` · `N/A (mobile deferred)`
- AC classification → `[BOTH]` · `[API]` · `[UI]`
- Test type → `integration` · `e2e` · `unit`

### They are references, not contracts

`SRS.md` and `SDS.md` were written before the code existed and they leave things open — and in places they contradict each other.

- **Deviate freely** where implementation reality demands it, then record it as an ADR in `docs/02-design/adr/` and list it in the story's `spec.md` *Deviations* section.
- **Stop and ask the user** only when a change would genuinely *break* one of them:
  - contradicts the domain model (`SDS.md` §2) or ERD (§4.3.3),
  - changes a published endpoint contract (`SDS.md` §6),
  - violates an NFR (`SRS.md` §3, `SDS.md` §8),
  - the two documents disagree and the choice is material.
- Everything smaller: decide, document, keep moving.

### Resolved contradictions (do not re-litigate)

| Topic | Ruling | Source |
| :-- | :-- | :-- |
| User status values | **`PENDING`** / `ACTIVE` / `DEACTIVATED`. **SRS wins**; SDS was corrected. | SRS §6 US-01-01; SDS §2.4.1 v1.1.0 |
| Invitation status | Separate lifecycle on the invitation record: `PENDING` → `ACCEPTED` / `EXPIRED` / `SUPERSEDED`. `EXPIRED` is *derived* from `expires_at`, never written. An expired token leaves the **user** `PENDING`. | SRS §6 US-01-02; SDS §2.4.2 |
| Invitation storage | **Separate `invitations` table** per the SDS ERD — not columns on `users`. Inviting creates a `users` row (`PENDING`) *and* an `invitations` row, in one transaction. | SDS §2.1, §4.3.3 |
| Roles | `users.role` = `ADMIN` \| `USER`, enforced now. Invite and list-users are ADMIN-only. | SDS §5.2.1, §5.2.3 |
| Error shape | Flat: `{"error_code", "message", "details"}` — **not** nested under `"error"`. | SDS §6.6 |
| Dev database | SQLite locally (Docker unreachable in this WSL2 setup); PostgreSQL is the target. One `DATABASE_URL` change. ADR required. | SDS §4.1 vs environment |
| Invitation token at rest | Stored **hashed** (SHA-256); the raw token exists only in the email. Deviates from SDS §4.3.3's plain `token UK`. ADR required. | security deviation |

### Story ID map

The two documents number the same stories differently. Always cite both.

| SRS | SDS | Story | Epic file | Order |
| :-- | :-- | :-- | :-- | :-- |
| US-01-01 | UM-US-01 | Invite a user via email (ADMIN) | `specs/001-user-onboarding/` | **1st** |
| US-01-02 | UM-US-02 | Activate user account | `specs/001-user-onboarding/` | 2nd |
| US-01-03 | UM-US-03 | List users (ADMIN) | `specs/001-user-onboarding/` | 3rd |
| US-02-01 | SS-US-01 | Login | `specs/002-system-security/` | before implementing US-01-01 |
| US-02-02 | SS-US-02 | Logout | `specs/002-system-security/` | deferred |
| — | UM-US-04/05, DC-US-01/02 | SDS-only stories | — | out of MVP scope |

Note the split between *specification* order and *implementation* order: UM-US-01 is specified first because it is the first story of the first epic, but it **cannot be implemented** until login (US-02-01, a different epic) exists, since its ACs require an authenticated ADMIN. That dependency belongs in the spec's *Assumptions & Dependencies* section.

### The scope rule ("cut to the current story")

Before starting a story, extract **only** the `SRS.md` / `SDS.md` sections that story implements. Quote them at the top of its `spec.md`, then state what is deliberately excluded. Nothing else enters the working context — this is what stops Features 03–11 leaking into a Feature-01 story.

```markdown
## Source
### SRS §6 Feature-01 · US-01-01 (Gherkin)
> Scenario: Successfully send an email invitation …
### SDS §5.2.1 UM-US-01 (ADMIN)
> 1. Validates email format and checks for existing active accounts. …

## Out of scope for this story
US-01-02, US-01-03, US-02-01 · Features 03–11 · SRS §6 Feature-10/11 placeholders
```

If a story turns out to need something out of scope, that is a finding — write it down, do not silently expand.

---

## 2. The AIF-SDLC cycle

Six steps per story, in **strict order, none skipped or reordered**. Each produces reviewable artifacts and ends at a gate.

| # | Step | Reviewer | Artifacts | Definition of done |
| :-- | :-- | :-- | :-- | :-- |
| 1 | **Spec** | BA | `spec.md` | Story statement (As a / I want / So that), ACs traced to SRS+SDS, every AC a testable observable outcome. No endpoint paths, DB fields, or tech names — those belong to `plan.md`. Exactly one US per file. Stable IDs (`AC-01`, `BR-01`, `EC-01`). |
| 2 | **Design** | SE | `plan.md` + ADRs | Sequence diagram, layer assignment, DTOs, API contract, error codes. Every AC addressed. Constitution rules checked explicitly. No gaps left ambiguous — if there are, go back to Spec rather than patching forward. |
| 3 | **Quality** | QC | `test_cases.md` | ≥1 test case per AC, in Given/When/Then, with US + AC reference + type. Unhappy paths and edge cases covered. TC numbers sequential, appended never rewritten. **Written before test code.** |
| 4 | **Implement** | SE | `tasks.md` + code | Tasks ordered migration → model → repository → service → router. Tests written from `test_cases.md` and seen failing first, then code until green. `pytest` green, `ruff` + `mypy` clean, coverage > 80%. |
| 5 | **Deploy** | SE | evidence | App actually runs; `/health` 200; curl/Postman walkthrough executed with **real pasted output**, including a genuine Gmail delivery. |
| 6 | **Verification** | QC | verification report | Every TC given a result (PASS/FAIL/BLOCKED). Failures reproduced manually, root-caused, logged in `docs/06-defects/`, fixed, re-verified. |

**If implementation diverges from `plan.md`, redefine the plan first** — never deviate silently and patch the document afterwards.

Diagrams, ERDs and sequence diagrams belong to the **Design** step. They are not introduced or altered during Implementation.

### Artifact layout

One folder per **epic**, three files, all stories of that epic inside them (§1.1 rule 1):

```
specs/
├── 001-user-onboarding/          Feature-01 / UM
│   ├── spec.md                   ## UM-US-01, then ## UM-US-02, ## UM-US-03 appended
│   ├── plan.md                   same story sections, design detail
│   ├── test_cases.md             TC-NN continuous across all three stories
│   └── tasks.md                  written at the Implement step
└── 002-system-security/          Feature-02 / SS
    ├── spec.md                   ## SS-US-01, ## SS-US-02
    └── …
```

Supporting documents live in `docs/`: `traceability.md` (master matrix), `00-foundation/`, `02-design/adr/`, `05-verification/`, `06-defects/`, `mobile-readiness.md`.

### Gate cadence

- **UM-US-01 (invite)** — the first story through the cycle: stop at **every** step gate.
- Later stories: stop after Spec+Design, after Quality, and after Verification.
- More gates on request; never fewer without being asked.

**A gate closes when the user reviews the artifact and commits it — not when the AI declares the step done.** The AI's job at a gate is to produce the artifact, run the checklist, paste the evidence, suggest a commit message, and stop.

### Traceability

`docs/traceability.md` is the master matrix: **SRS/SDS story → AC → TC → pytest node id → status**. Updated at step 3 (TC ids) and step 4 (pytest node ids). A story is done when every AC resolves through it to a passing test. Nothing else counts as done.

### Review checklist

Before claiming **any** gate, run the artifact through `aif-review-checklist.md` and record the result using its gate-record template. A gate claimed without the checklist is not a gate.

The checklist's own *Adaptations for the PFM project* section lists what was removed (ticket tracking) and how stack-specific items map here (Flyway → Alembic, Playwright/Testcontainers → `pytest` + `httpx`, Next.js/shadcn → React Native, deferred). Mark inapplicable items `N/A (stack)` explicitly — never skip them silently.

---

## 3. Commands

`uv` is the only entry point — this machine's system Python has no pip.

```bash
cd backend

uv sync                                   # install/refresh dependencies
uv run pytest -v                          # full suite, SMTP mocked
uv run pytest --cov=app --cov-report=term-missing   # coverage (DOD: >80%)
uv run pytest -m smtp                     # opt-in: real Gmail send (needs .env)
uv run ruff check . && uv run ruff format .
uv run mypy app
uv run alembic revision --autogenerate -m "…"
uv run alembic upgrade head
uv run python -m app.cli create-admin --email you@example.com --password '…'
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger at `/docs`, ReDoc at `/redoc`. FastAPI ≥0.141 makes `include_router` lazy — to list routes read `app.openapi()["paths"]`, not `app.routes`.

---

## 4. Conventions

Full rules with stable IDs live in [`constitution.md`](constitution.md). The essentials:

- **Layering** `router → service → repository → model` (AR-01…03). No queries in routers, no `Request`/`Response` objects in services.
- **Transactions** services never commit; the router owns the commit, so one request is one transaction (NFR-05).
- **Time** all reads go through `app.core.clock.utcnow()`. Never `datetime.now()`. SQLite returns naive datetimes — pass them through `clock.ensure_aware()` before comparing or serialising.
- **Money** `DECIMAL(15,2)` / Python `Decimal`. Never float.
- **Errors** one flat envelope, validation included: `{"error_code": "INVITATION_TOKEN_EXPIRED", "message": "…", "details": {}}`. Codes are `UPPER_SNAKE_CASE` with a resource prefix, catalogued in the story's `plan.md`.
- **Config** `pydantic-settings` in `app/core/config.py`, grown per story — a story adds only the settings its spec justifies. Secrets from `.env` (gitignored); `.env.example` documents every key.
- **Secrets** never log or return a raw token, password, or hash. Invitation tokens are stored hashed.
- **Tests** named for what they prove, each carrying its `TC-xx` id in a docstring. A test that cannot fail is not a test.
### Git — never write history

**The AI never runs `git commit`, `git push`, `git add`, `git reset`, `git rebase`, or `git tag`.** Git history belongs to the user.

At each gate, instead:
1. Leave the work in the working tree, **unstaged**.
2. Print a **suggested** commit message in a fenced block, ready to copy.
3. Notify the user the step is done, with its gate record and pasted verification output.

Read-only git is fine and encouraged for reporting state: `git status`, `git log`, `git diff`, `git show`.

The only exception is an explicit instruction in the user's current message ("commit this", "push it"). Approval to commit once never carries to the next step.

Suggested message format — one per step gate, so the history reads as the cycle:

```
docs(spec):   US-02-01 login — AC-01..05
docs(design): US-02-01 plan + ADR-0002 JWT session
docs(test):   US-02-01 test_cases TC-0201-01..12
test:         US-02-01 failing tests from TC plan
feat:         US-02-01 login endpoint — TC-0201-* green
docs(verify): US-02-01 verification report
```

---

## 5. Current state and boundaries

- **Round 1 scope:** UM-US-01 invite (specified first), UM-US-02 activate, UM-US-03 list users, plus SS-US-01 login — which must be *implemented* first, since the others need an authenticated ADMIN. **Out of scope:** everything else, including Features 03–11 and SRS §6 Feature-10/11 placeholders.
- **Backend first.** `mobile/` is a skeleton only — folders, config and placeholder files, no screens and no network — until Feature-01 is verified. Analysis in `docs/mobile-readiness.md`; SDS §4.3.1 is the target design.
- **The discarded implementation-first attempt has been deleted.** Its lessons — 6 verified environment findings and the full list of ways it contradicted the SDS — are in `docs/00-foundation/spike-notes.md`. The code itself remains recoverable with `git show 56768c8` if a detail is ever needed; do not restore it, and never import from it.
- **Artifacts are tracked in git.** `specs/` and `docs/` are the deliverable, not scratch space. `.gitignore` excludes only `.venv`, `__pycache__`, `*.db`, `.env` and tool caches.
- Dev DB is SQLite; PostgreSQL is the deployment target (SDS §4.5).

## 6. Honesty rules

- Never report a step complete without its artifact on disk.
- Never write "tests pass" without having run them and pasted the output.
- State skipped, blocked, or deviating work in the same message, not later.
- Do not write documentation that retroactively justifies code already written.
- **Never imply work is saved to git history when it only exists in the working tree.** Say "written, uncommitted" and name the files.
