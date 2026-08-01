# CLAUDE.md — how work is done in this repo

Personal & Family Finance Management (PFM). This file is the operating contract for AI-assisted work here. Read it before touching anything.

The purpose of this project is to practise the **AIF-SDLC cycle**, where documents drive code. Producing implementation before its spec/design/test artifacts exist defeats the point, and has already been rejected once here — an implementation-first spike was built and then deleted rather than retrofitted with documentation.

---

## 1. Reference documents

| File | Owner | Rule |
| :-- | :-- | :-- |
| `SRS.md` v2.2.0 | the user; AI may **align**, not extend | Requirements baseline: FR, NFR, UXR, BF, Features 01–11 with Gherkin, §1.5 Conceptual Domain Model. See *They are references, not contracts* below. |
| `SDS.md` v1.3.0 | the user; AI may **align** | Technical baseline: domain model, ERD, architecture, API design, security design. See *They are references, not contracts* below. |
| `aif-review-checklist.md` | the user | Run before claiming any step gate. Edited once to remove Jira and record stack adaptations; otherwise treat as the user's. |
| `artifact-templates/*.md` | the user | **Read-only. Never edit. Never split.** The canonical shape of every artifact — see §1.1. |
| `constitution.md` | AI + user | Project rules with stable IDs (AR/API/NC/VL/LA/PF/SEC/TST/DOD/ENV), derived from the SDS. |
| `specs/**` | AI + user | The working artifacts, and the only ones. Design output goes here — **never** into `SDS.md`. |

`SDS.md` was aligned to `SRS.md` on 2026-07-30 (v1.1.0), to the built system on 2026-07-31 (v1.2.0), and to the `DG` diagram convention the same day (v1.3.0); `SRS.md` was aligned on 2026-07-31 (v2.1.0) and gained its conceptual domain model, §1.5, at the user's explicit request the same day (v2.2.0). **`SRS.md` wins any remaining disagreement** — the rulings are in *Resolved contradictions* below.

## 1.1 Artifact rules

0. **Three files per epic. Nothing else.** The complete deliverable for an epic is:

   ```
   specs/<NNN>-<epic-slug>/
   ├── spec.md         what and why      (step 1)
   ├── plan.md         how               (step 2)
   └── test_cases.md   proof             (steps 3 and 6)
   ```

   **Do not create any other document.** No ADRs, no traceability matrix, no `tasks.md`, no verification report, no defect record, no readiness analysis, no summary or index file. Each of those existed and was removed because it duplicated content one of the three files already carries:

   | Instead of a separate… | Write it in |
   | :-- | :-- |
   | ADR / deviation record | `plan.md` → *Gaps & Decisions (Resolved)* |
   | traceability matrix | `test_cases.md` → *Coverage Matrix* |
   | `tasks.md` | `plan.md` → *Open tasks* (`T-NN`) |
   | verification report / defect record | `test_cases.md` → result against each `TC-NN` |

   A fourth artifact — the **automation test file** — is a known gap. It is not designed yet, and step 4 currently writes tests into `backend/tests/`. Do not invent a location or format for it; raise it as its own decision.

   If a piece of information genuinely fits none of the three files, that is a finding to raise — not licence to add a fourth.

1. **One file per epic — never split.** Every story in an epic is appended to the **same** three files as a new `## <CODE>-US-NN` section. Never create a markdown file per story. This is how the checklist's "spec.md contains exactly one US" is satisfied: it means *specify one story per step*, not one file per story.
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

`SRS.md` and `SDS.md` were written before the code existed and they leave things open — and in places they contradict each other, and themselves.

**Both are alignable by the AI as of 2026-07-31.** They were read-only until then, and freezing them had the opposite of the intended effect: they drifted from the system, and each drift was filed as a permanent "documented deviation" in some `plan.md` instead of being fixed at the source. A reference nobody may correct stops being a reference. So:

- **Aligning** means correcting a contradiction, an outdated fact, a name that was never implemented, or an imprecision — making the document say what has already been agreed or already been built. Log every such edit in that document's own revision history (`SRS.md` §8, `SDS.md` §1.6). That table *is* the audit trail; there is no separate alignment file.
- **Extending is not aligning.** Adding, removing, or reinterpreting a *requirement* is the product owner's decision. **Stop and ask.** Adding Gherkin scenarios to `SRS.md` is on this side of the line even when the behaviour is settled everywhere else — which is exactly why UM-US-02's four unanchored ACs are recorded as a finding (`plan.md` F1) rather than back-filled.
- **Precedence is unchanged:** `SRS.md` → `SDS.md` → `constitution.md` → `specs/**`. Aligning the SDS *to the code* is routine. Aligning the SRS to the code is legitimate only where the SRS contradicts itself or a ruling the user has already made — when code and a requirement genuinely disagree, **the code is what changes.**
- **The artifacts still lead.** Design output goes in `specs/**`, never into `SDS.md` (§1.1). Aligning the SDS records what a story already settled; it is never where a story gets designed.

Where a deviation remains the right answer:

- **Deviate freely** where implementation reality demands it, then record it in the story's `plan.md` *Gaps & Decisions (Resolved)* table — one row, with the rationale. No separate ADR file (§1.1 rule 0). Prefer aligning the reference document when the deviation is really the document being wrong.
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
| Dev database | SQLite locally (Docker unreachable in this WSL2 setup); PostgreSQL is the target. One `DATABASE_URL` change. Record in `plan.md` *Gaps & Decisions*. | SDS §4.1 vs environment |
| Invitation token at rest | Stored **hashed** (SHA-256); the raw token exists only in the email. No longer a deviation — SDS §2.2/§2.3/§4.3.3 were aligned to `token_hash UK` at v1.2.0. | SDS §4.3.3 v1.2.0; SEC-03 |
| Refusal precedence on activation | Checks run in a **fixed order: invitation outstanding → user `PENDING` → expiry last.** So `expired` is reported only for a token that would otherwise have worked, and every other reason stays collapsed into one indistinguishable outcome permanently — not just for the first 24 hours. Reversing the order silently narrows the guarantee to the TTL window. | spec UM-US-02 BR-02, EC-11; plan A1 |
| Raw token in the state-check URL | **Accepted, documented exposure.** `GET /users/activate?token=…` puts the token in the access log. FR-17's guarantee is scoped to application logs and audit records; the residual leak is bounded by single use and the 24-hour TTL, and the same token already travels in the emailed link's URL. Alternatives (POST-body check, header-borne token) were weighed and rejected. | plan UM-US-02 A10; LA-01 |
| Audit scope on activation | Audit records cover every attempt **that reaches the service**. A `422` rejected by the Pydantic layer emits none, and is traceable through the request log instead — auditing it would mean emitting business events from `main.py`'s validation handler, against AR-01. | spec UM-US-02 FR-18; plan F2 |
| Aligning SRS/SDS | The AI **may align** both, and **may not extend** either. Logged in each document's revision history. | §1.1 *They are references, not contracts* |
| Sequence diagram shape | Four lanes only, `UI → API → <Name>Service → Store`. No `Repo`/`DB` lane, no SQL, no real parameter lists, every `UI→API` request answered with an HTTP status in every branch. The prior session's `plan.md` diagrams and the SDS §4.4.1 diagram violated this — an already-cited checklist rule that had been marked passed in error — and were redrawn. | constitution `DG-01`…`DG-07` |

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
| 2 | **Design** | SE | `plan.md` | Sequence diagram, layer assignment, DTOs, API contract, error codes. Every AC addressed. Constitution rules checked explicitly. Deviations recorded in *Gaps & Decisions*. No gaps left ambiguous — if there are, go back to Spec rather than patching forward. |
| 3 | **Quality** | QC | `test_cases.md` | ≥1 test case per AC, in Given/When/Then, with US + AC reference + type. Unhappy paths and edge cases covered. TC numbers sequential, appended never rewritten. **Written before test code.** |
| 4 | **Implement** | SE | code | Work the `T-NN` tasks already listed in `plan.md`, ordered migration → model → repository → service → router. Tests written from `test_cases.md` and seen failing first, then code until green. `pytest` green, `ruff` + `mypy` clean, coverage > 80%. |
| 5 | **Deploy** | SE | evidence in the message | App actually runs; `/health` 200; curl/Postman walkthrough executed with **real pasted output**, including a genuine Gmail delivery. Pasted into the gate message, not into a file. |
| 6 | **Verification** | QC | `test_cases.md` results | Every `TC-NN` given a result (PASS/FAIL/BLOCKED) **in `test_cases.md` itself**. Failures reproduced manually, root-caused, fixed, re-verified — the root cause recorded against its TC, not in a separate defect file. |

**If implementation diverges from `plan.md`, redefine the plan first** — never deviate silently and patch the document afterwards.

Diagrams, ERDs and sequence diagrams belong to the **Design** step. They are not introduced or altered during Implementation.

### Artifact layout

One folder per **epic**, three files, all stories of that epic inside them (§1.1 rule 1):

```
specs/
├── 001-user-onboarding/          Feature-01 / UM
│   ├── spec.md                   ## UM-US-01, then ## UM-US-02, ## UM-US-03 appended
│   ├── plan.md                   same story sections, design detail
│   └── test_cases.md             TC-NN continuous across all three stories
└── 002-system-security/          Feature-02 / SS
    ├── spec.md                   ## SS-US-01, ## SS-US-02
    └── …
```

That is the whole artifact tree. `specs/` is the deliverable; there is no supporting-documents directory (§1.1 rule 0).

### Who does which step

**One agent does the work; the main session reviews it.** A general-purpose
subagent is dispatched **twice per story**, each time with a **self-contained
brief written by the main session** — there is no agent-definition file to read,
and none should be created. The brief carries the phase, the rules of §1.1, the
settled rulings, the ID/numbering state, and the design facts the phase needs:

| Dispatch | Phase | Produces | Then |
| :-- | :-- | :-- | :-- |
| 1 | `artifacts` (steps 1–3) | `spec.md` + `plan.md` + `test_cases.md` sections | review → gate |
| 2 | `implement` (steps 4–6) | code, tests, and a verdict against every `TC-NN` | review → gate |

The agent's only reading is the repo's real inputs — this file,
`constitution.md`, `artifact-templates/`, the epic's three artifacts, and
`backend/app/` for what already exists.

**Twice, not once.** A single context writing the spec *and* the code in one
sitting bends the spec to fit the code it already has in mind — the failure named
at the top of this file, which already cost a deleted spike. Splitting at the
artifact boundary keeps *documents drive code* literally true.

The main session's job is **the review gate, not the writing**: dispatch, read
what came back against the source documents, check the pasted evidence, and
either send it back or present it for the user's gate. Writing an artifact
directly in the main session skips the review — there is then nobody left to
catch the mistake.

Three rules keep this honest:

- **An agent that hits a genuine ambiguity stops and reports it.** It never invents a ruling. A `[NEEDS RULING]` marker in an artifact is a legitimate deliverable; a silently-invented answer is not. Contradictions between `SRS.md` and `SDS.md` where the choice is material belong to the user (§1).
- **An agent's report is evidence, not a gate.** Every claim gets checked — pasted output read, files opened, numbers re-derived. "The agent said it passed" is not verification.
- **A green test suite is necessary and not sufficient.** Two UM-US-01 defects survived a fully green run and were caught only by a live walkthrough: a response serialising timestamps with no timezone offset, and auth declared as a raw header so the documented usage failed with a misleading 401. Step 6 means real requests, real rows, real rendered docs — not just `pytest`.

### Gate cadence

- **UM-US-01 (invite)** — the first story through the cycle: stop at **every** step gate.
- Later stories: stop after Spec+Design, after Quality, and after Verification.
- More gates on request; never fewer without being asked.

**A gate closes when the user reviews the artifact and commits it — not when the AI declares the step done.** The AI's job at a gate is to produce the artifact, run the checklist, paste the evidence, suggest a commit message, and stop.

### Traceability

The **Coverage Matrix inside `test_cases.md`** is the traceability record: **story → AC/EC → TC → pytest node id → status**. Filled at step 3 (TC ids) and extended at step 4 (pytest node ids). There is no separate matrix file.

A story is done when every AC resolves through that matrix to a passing test. Nothing else counts as done.

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

### Checking the mermaid diagrams

Run this at the **Design** gate, before claiming step 2. Both `plan.md` diagrams once shipped
broken and rendered as an error box in every viewer, and nothing in the cycle caught it:

```bash
npm install --no-save mermaid@11 jsdom      # once, in a scratch directory
node check.mjs specs/001-user-onboarding/plan.md SDS.md
```

`check.mjs` extracts every ` ```mermaid ` block and runs `mermaid.parse()` over it, reporting the
starting line of any block that fails. **The trap to know about:** mermaid's message and note text
token is `[^#\n;]+`, so a **semicolon or `#` inside a label silently ends the statement** and the
parse fails several lines later with a misleading error. Use an em dash or a comma. Em dashes, `|`,
`->` inside labels, multi-word participant aliases and `autonumber` are all fine.

Parsing clean is necessary, not sufficient — it says the diagram renders, not that it follows
`constitution.md`'s `DG` group. Also check by eye (or grep) that no fenced block contains `SELECT`,
`INSERT`, `UPDATE … WHERE`, `rowcount`, a `Repo`/`DB` participant, or a real method signature (DG-01,
DG-04), and that every `UI→API` arrow has a matching `-->>UI` return carrying an HTTP status, in
every `alt`/`opt` branch (DG-05). A diagram that parses but shows SQL is not a passing diagram — see
the *Sequence diagram shape* row in *Resolved contradictions* above for why this matters enough to be
a rule and not just a preference.

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
docs(design): US-02-01 plan — JWT session, error catalog
docs(test):   US-02-01 test_cases TC-0201-01..12
test:         US-02-01 failing tests from TC plan
feat:         US-02-01 login endpoint — TC-0201-* green
docs(test):   US-02-01 TC results — 12 PASS
```

Note the last line: verification closes by recording results **in `test_cases.md`**, so it is another `docs(test)` commit rather than a new document.

---

## 5. Current state and boundaries

- **Round 1 scope:** UM-US-01 invite (specified first), UM-US-02 activate, UM-US-03 list users, plus SS-US-01 login — which must be *implemented* first, since the others need an authenticated ADMIN. **Out of scope:** everything else, including Features 03–11 and SRS §6 Feature-10/11 placeholders.
- **Backend first.** `mobile/` holds a **UI prototype**, not implementation: a navigable Expo web app whose data comes entirely from fixtures (`EXPO_PUBLIC_API_MOCK=1`), because the backend has no routes yet. Its invite screen implements UM-US-01's ACs against those fixtures. It satisfies **no** TC, and the `[UI]` rows in `test_cases.md` stay deferred. SDS §4.3.1 is the target design. Findings that cost real debugging time live in `mobile/AGENTS.md`.
- **The discarded implementation-first attempt has been deleted.** Its code remains recoverable with `git show 56768c8` if a detail is ever needed; do not restore it, and never import from it. Its lesson is the one at the top of this file.
- **`specs/` is the tracked deliverable, not scratch space.** `.gitignore` excludes `.venv`, `__pycache__`, `*.db`, `.env`, `node_modules/`, tool caches — and `docs/`, which is kept on disk but deliberately untracked (§1.1 rule 0). Earlier commits still contain `docs/`; `git show <sha>:docs/<path>` retrieves a file if one is ever needed.
- Dev DB is SQLite; PostgreSQL is the deployment target (SDS §4.5).

## 6. Honesty rules

- Never report a step complete without its artifact on disk.
- Never write "tests pass" without having run them and pasted the output.
- State skipped, blocked, or deviating work in the same message, not later.
- Do not write documentation that retroactively justifies code already written.
- **Never imply work is saved to git history when it only exists in the working tree.** Say "written, uncommitted" and name the files.
