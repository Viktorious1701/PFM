# The AIF-SDLC cycle in this project

How work moves from a requirement to verified software here. Read `CLAUDE.md` for the rules; this file explains the shape.

## Why

Documents drive code. The alternative was tried first and rejected: ~1,750 lines of implementation with no spec, no design, no test plan, and no test run. Nothing explained *why* the code looked the way it did. See [`00-foundation/spike-notes.md`](00-foundation/spike-notes.md).

## The six steps

```
   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌───────────┐   ┌──────────┐   ┌──────────────┐
   │ 1 Spec   │──►│ 2 Design │──►│ 3 Quality│──►│4 Implement│──►│ 5 Deploy │──►│6 Verification│
   │   (BA)   │   │   (SE)   │   │   (QC)   │   │   (SE)    │   │   (SE)   │   │     (QC)     │
   └──────────┘   └──────────┘   └──────────┘   └───────────┘   └──────────┘   └──────────────┘
    spec.md        plan.md        test_cases     tasks.md        evidence       verification
                   + ADRs         .md            + code          (real output)  report
        │              │              │               │               │               │
        └──── gate ────┴──── gate ────┴───── gate ────┴──── gate ─────┴───── gate ────┘
                       reviewed against aif-review-checklist.md
```

Strict order. No step skipped or reordered. If implementation diverges from `plan.md`, the plan is redefined first — never patched afterwards to match code that already exists.

| Step | Question it answers | Artifact |
| :-- | :-- | :-- |
| **1 Spec** | What must be true for a user? | `spec.md` — story statement + ACs, conceptual only |
| **2 Design** | How will the system do it? | `plan.md` + ADRs — sequence diagram, layers, DTOs, API contract |
| **3 Quality** | How will we know it works? | `test_cases.md` — Given/When/Then, before any test code |
| **4 Implement** | Build it. | `tasks.md` + code, tests failing first then green |
| **5 Deploy** | Does it run for real? | evidence with pasted output, real Gmail delivery |
| **6 Verification** | Is it actually correct? | results per TC, defects logged and re-verified |

## Where things live

```
SRS.md                    requirements baseline    (user-owned, read-only)
SDS.md                    technical baseline       (user-owned, read-only)
aif-review-checklist.md   gate review checklist    (user-owned, read-only)
CLAUDE.md                 operating rules
constitution.md           project rules with stable IDs (AR/API/NC/VL/SEC/LA/PF/TST/DOD/ENV)

artifact-templates/       canonical artifact shapes  (user-owned, read-only)
specs/<NNN>-<epic>/       spec.md · plan.md · test_cases.md · tasks.md
                          ONE folder per epic; every story appended into the same files
docs/traceability.md      master matrix: story → AC → TC → pytest node id → status
docs/00-foundation/       environment record, spike post-mortem
docs/02-design/adr/       architecture decision records
docs/05-verification/     evidence and verification reports
docs/06-defects/          defect records
docs/mobile-readiness.md  React Native round: what blocks it, how it will ship
backend/                  the application
spike/                    discarded first attempt — reference only, never edit
```

## Round 1 order

Specification order follows the epics. Implementation order differs, because invite requires an authenticated ADMIN and invite-only registration cannot bootstrap itself.

| Story | SRS | SDS | Epic file | Specified | Implemented |
| :-- | :-- | :-- | :-- | :-- | :-- |
| Invite a user via email (ADMIN) | US-01-01 | UM-US-01 | `001-user-onboarding` | 1st | after login |
| Activate user account | US-01-02 | UM-US-02 | `001-user-onboarding` | 2nd | 3rd |
| List users (ADMIN) | US-01-03 | UM-US-03 | `001-user-onboarding` | 3rd | 4th |
| Login | US-02-01 | SS-US-01 | `002-system-security` | with invite's design | 1st |

Backend only. Mobile is a skeleton this round — folders and config, no screens and no network — and becomes real work only after Feature-01 is verified.

## Reading a traceability row

```
US-01-01 / UM-US-01 · AC-03 (24h TTL)
  → TC-0101-07 happy: token valid at T+23h
  → TC-0101-08 boundary: expired at T+24h+1s
  → tests/integration/test_us_01_01_invite.py::test_tc_0101_08_expired_token  PASS
```

Every AC must reach a passing test with a real node id. That is the only definition of done.
