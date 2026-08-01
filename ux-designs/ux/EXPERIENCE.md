---
name: PFM
description: Experience contract for PFM — IA, behavior, states, flows, and accessibility.
status: final
created: 2026-07-18
updated: 2026-07-31
history: >
  Originally authored as the experience spine for "SamThuongShop," a bird-photography e-commerce
  shop design exercise unrelated to this repository's product. Retargeted on 2026-07-31 to describe
  PFM's actual information architecture, flows, and states — sourced from ../../SRS.md and
  ../../SDS.md rather than invented. The accessibility floor and interaction discipline (focus
  management, no color-alone states, reduced motion) carry over structurally; the shop-specific
  content (cart, checkout, bilingual copy, photography) does not.
sources:
  - ../../SRS.md   # requirements baseline — Features 01-09, BF-01..04, UXR-01..04
  - ../../SDS.md   # technical baseline — domain model, state diagrams, API design
design: ./DESIGN.md   # visual identity peer; tokens referenced via {path.to.token}
---

# PFM — Experience Spine

> This spine owns **how it works**: information architecture, behavior, states, flows, and the accessibility floor. The **look** — colors, type, shape, spacing — lives in `DESIGN.md`, referenced here by token name via `{path.to.token}` (e.g. `{colors.sky-deep}`, `{typography.h1}`, `{rounded.full}`). When this spine and any mockup disagree, the spine wins. Token and component names follow the Sky & Sedge set locked in `DESIGN.md` (neutrals `bg-page`/`surface`/`surface-sunken`/`border`; ink `ink`/`ink-muted`/`caption-deep`; accents `sky-soft`/`sky-deep`/`sage-soft`/`sage-deep`; status `success`/`pending`/`error`/`info`; components `stat-tile`/`wallet-card`/`budget-meter`/`transaction-row`/`status-pill`).

## Foundation

- **Form factor:** cross-platform — a React Native (Expo) mobile app is the primary build target for round 1 (`CLAUDE.md` scope), with a responsive web view also in SRS's stated scope (SRS §1.2: "PFM is a web and mobile software system") but not yet built. Mobile is first-class.
- **Theme:** **light mode only** for v1. Dark mode is out of scope — nothing in SRS §3–§4 asks for it.
- **Language:** **English only.** No requirement in SRS/SDS covers internationalisation, so no bilingual layer is designed for here (matching the identical ruling already made in `../../mobile/DESIGN.md`).
- **Visual direction:** "Sky & Sedge" — airy, modern, quiet; the numbers lead, the UI stays quiet. See `DESIGN.md` for the full look.
- **Navigation:** one unified nav (tab bar on mobile, top nav on future web) — **Dashboard · Wallets · Budgets · Transactions · Reports · Notifications**, plus **Family** for an ADMIN caller (invite and list members, SRS §6 Feature-01 US-01-01/US-01-03).
- **Scope:** **every signed-in account is a potential ADMIN or USER, not a separate customer/operator split.** An ADMIN additionally sees the Family surface (invite, list) — SDS §5.2.1/§5.2.3 — but there is no operator-only area hidden behind a second authentication system; role is a property of the one account model (SDS §2.4.1). **Round-1 build scope** (`CLAUDE.md` §5): onboarding (invite, activate, list) and login are implemented; Wallets/Categories/Budgets/Transactions/Reports/Notifications/Dashboard (Features 03–09) are specified below from the SRS but have no backend yet — this spine describes the full requirements baseline, not only what is currently built.

## Information Architecture

### Nav / sitemap

```
Global chrome (tab bar / top nav)
├── Login ──── Activate account (from an emailed invitation link)
├── Dashboard ── net balance, budget health bars, recent activity
├── Wallets ──── Wallet detail ── that wallet's transaction history
├── Categories ── Category detail
├── Budgets ──── Budget detail ── alerts when a threshold is crossed
├── Transactions ── Create / edit a transaction
├── Reports ──── Monthly summary, category breakdown
├── Notifications
└── Family (ADMIN only) ── Invite a member ── Member list with status
```

### Surfaces → SRS FRs

| # | Surface | Purpose | Reached from | FRs |
|---|---|---|---|---|
| 1 | **Login** | Email + password entry; redirects to Dashboard on success | Cold entry, sign-out | FR-02 |
| 2 | **Activate account** | One-page Name + Password form reached from an invitation email | Emailed activation link | FR-01, UXR-04 |
| 3 | **Dashboard** | Executive summary: net balance, wallet summary, budget health bars, recent transactions | Post-login landing | FR-09 |
| 4 | **Wallets list** | All wallets owned by the user, with current balance | Nav "Wallets" | FR-03 |
| 5 | **Wallet detail / create** | Name, type, currency, initial balance; that wallet's transaction history | Wallets list, dashboard wallet tile | FR-03 |
| 6 | **Categories** | User-defined income/expense categories | Nav "Categories" | FR-04 |
| 7 | **Budgets** | Monthly spending caps per category + wallet, with progress bars | Nav "Budgets" | FR-05 |
| 8 | **Transactions** | Log or list income/expense entries against a wallet + category | Nav "Transactions", dashboard CTA | FR-06 |
| 9 | **Reports** | Monthly income/expense summary, net savings trend, top categories | Nav "Reports" | FR-07 |
| 10 | **Notifications** | Alerts for budget thresholds, new invitations, low balances | Nav "Notifications" | FR-08 |
| 11 | **Family** *(ADMIN only)* | Invite a member by email; list all invited/active members and their status | Nav "Family" | FR-01, SRS US-01-01/US-01-03 |
| — | **Global chrome** | Persistent nav, session/account menu | Everywhere | — |

### Reference prototype

Unlike the shop, no HTML mockups exist for PFM's IA — `mockups/` and `.working/` still hold the
shop's mockups, out of scope here (see this file's `history` note). The one real reference is a
navigable, fixture-driven prototype for the invite flow at `../../mobile/app/(tabs)/users/invite.tsx`
(`CLAUDE.md` §5) — where it and this spine disagree, the spine wins, same rule the shop version
of this document already established.

### Surface closure

**Holds, for the requirements in scope.** Every Feature 01–09 need has a landing surface:
- FR-01 → (2, 11) · FR-02 → 1 · FR-03 → (4, 5) · FR-04 → 6 · FR-05 → 7 · FR-06 → 8 · FR-07 → 9 ·
  FR-08 → 10 · FR-09 → 3.
- **Features 10/11** (AI Assistant, Investment Portfolio — SRS §6 Phase 2/3 placeholders) map to
  no surface, intentionally: they are out of scope for this baseline the same way SRS's own
  release roadmap (§7) excludes them from MVP.
- No in-scope FR is orphaned; no in-scope surface lacks a reachable entry.

## Voice and Tone

Calm, plain, and precise — a person managing their own family's money, not a bank's marketing
copy. Confident about the numbers, never alarmist about an ordinary purchase. Brand voice proper
(adjectives, aesthetic posture) lives in `DESIGN.md` Brand & Style; this table governs functional
microcopy.

| Do | Don't |
|---|---|
| "Your account is not activated. Please check your email invitation." (the SRS's own message) | "Access denied!!" |
| "This budget is at 80% of its limit." | "You're about to go broke!" |
| "Invitation sent successfully." | "SUCCESS! 🎉🎉🎉" |
| Short, complete sentences; one idea per line. | Exclamation stacking, urgency countdowns, faux scarcity. |

## Component Patterns

Behavioral only — every visual spec (fill, radius, type ramp) lives in `DESIGN.md.Components`.
Colors named here are semantic references.

| Component | Behavioral rules |
|---|---|
| **Nav / tab bar** | Persistent — Dashboard / Wallets / Budgets / Transactions / Reports / Notifications, plus Family for an ADMIN caller. Active item in `{colors.sky-deep}`, inactive `{colors.ink-muted}`. On mobile this is a bottom tab bar, so no hamburger collapse is needed (see Responsive). |
| **stat-tile** | The dashboard's net-balance hero card (`DESIGN.md` `stat-tile`). Updates immediately after any transaction is logged — no manual refresh (UXR-03). |
| **wallet-card** | Shows wallet name and current balance; the whole card is one tap target → wallet detail. No hover-only affordance on touch. |
| **budget-meter** | Shows category name and percentage used, both `{colors.ink}` — never the status hue as text (see `DESIGN.md`'s "One real conflict" note, reconciling SRS UXR-02's colour-alone requirement with WCAG). The fill carries the health hue (`success` / `pending` / `error`). Crossing 75% or 100% of the limit raises a Notification (FR-05, SRS §5 BF-04). |
| **transaction-row** | Shows category, wallet, date, and a signed amount — `{colors.ink}` for an expense, `{colors.success}` for income. Tapping opens the transaction for edit. |
| **status-pill** | Maps to account/invitation status: **ACTIVE** / **PENDING** (invited, awaiting activation) / **DEACTIVATED** (`DESIGN.md` `status-pill`). Used in the Family list, ADMIN-only. |
| **Forms** | (login, activation, invite, wallet/category/budget/transaction create) Every field has a visible label (never placeholder-only). Inline validation on blur and on submit; errors sit beneath the field in `{colors.error}` with text, not color alone. Primary submit uses `{colors.sky-deep}`; disabled while a required field is invalid or a request is in flight. |

## State Patterns

Status colors are used semantically: `{colors.success}` (healthy / active), `{colors.pending}`
(warning / awaiting), `{colors.error}` (exceeded / invalid). In every case a text label
accompanies the color (never color alone).

| State | Surface | Treatment |
|---|---|---|
| **Account not yet activated** | Login | Attempting to log in with a `PENDING` account shows "Your account is not activated. Please check your email invitation." — the SRS's own message (SS-US-01 AC-02) — not a generic access-denied message. |
| **Invalid credentials** | Login | An unknown email, a wrong password, or a `DEACTIVATED` account all show one generic "The email or password is incorrect." — never distinguishing which, so a login attempt cannot be used to learn whether an account exists (SS-US-01 AC-03/AC-04). |
| **Invitation link expired** | Activate account | "Invitation link has expired. Please request a new invitation." (UM-US-02 AC-02), shown **before** the person fills in the form via a pre-check (UXR-04, UM-US-02 AC-11). |
| **Invitation link invalid or already used** | Activate account | One generic "This link is invalid or has already been used." — the same message whether the token was never valid, already used, superseded, or its account is no longer eligible (UM-US-02's AC-03/04/05, deliberately indistinguishable so a stale link cannot be used to probe account state). |
| **Budget healthy** | Budgets, Dashboard | Green fill, percentage shown, comfortably under the limit. |
| **Budget warning** | Budgets, Dashboard | Amber fill once spending crosses 75% of the limit (FR-05); a Notification is raised (BF-04). |
| **Budget exceeded** | Budgets, Dashboard | Red fill at or past 100% of the limit; the overspend amount is shown plainly, not hidden. |
| **Empty list** (wallets, categories, budgets, transactions) | Respective list surfaces | A calm empty state with a single "+" action to create the first one. Never a blank page or dead end. |
| **Loading** | Any list or dashboard surface | Skeleton blocks sized to the eventual content; no layout jump when data arrives. |
| **Invitation sent** | Family (ADMIN) | "Invitation sent successfully" confirmation (UM-US-01 AC-01); the new invitee appears in the Family list as `PENDING` immediately. |
| **Form validation errors** | All forms | Inline, beneath the field, `{colors.error}` + text + `aria-describedby`; the first invalid field receives focus on failed submit. |

## Interaction Primitives

- **Tap to act.** Whole wallet cards, budget meters, and transaction rows are single targets; no
  reliance on hover to reveal a primary action.
- **Logging a transaction** confirms with a brief non-blocking banner and returns to where the
  person was — it does not force a redirect to a different surface.
- **Focus management** for any modal (e.g. a confirm-delete on a wallet or budget): traps focus
  while open, restores focus to its trigger on close, closes on `Esc`.
- **Banned:** urgency countdowns, faux scarcity, auto-playing motion on load, hover-only
  affordances on touch, modal stacks more than one level deep.

## Accessibility Floor

Behavioral floor; visual contrast is proven in `DESIGN.md`. **All text/CTA tokens (`sky-deep`,
`sage-deep`, `pending`, `caption-deep`, `success`, `error`) pass WCAG AA** for their text/CTA use
per the Sky & Sedge contrast board — the `soft` variants are decorative/large-area only.

- **Keyboard nav + visible focus:** every interactive element reachable and operable by keyboard;
  **the focus ring must contrast with the control it sits on** (primary buttons use an
  `{colors.ink}` ring offset from the `{colors.sky-deep}` fill — a same-color ring is invisible and
  is banned); `Tab` order follows reading order on every surface.
- **Overlay focus management:** any modal (confirm-delete, a detail sheet) **traps focus while
  open, restores focus to its trigger on close**, closes on `Esc`, and uses `role="dialog"` /
  `aria-modal="true"`. No overlay is keyboard-escapable only by mouse.
- **Page structure:** a "Skip to content" link is the first focusable element on every web surface;
  landmark regions (`header`/`nav`/`main`/`footer`) wrap the nav and content; exactly one `<h1>`
  per surface with no skipped heading levels.
- **Chart / icon accessibility:** any chart or icon conveying budget or account state also carries
  a text equivalent (`aria-label` or an adjacent label) — never color or shape alone (SRS UXR-02).
- **Form labels/errors:** visible `<label>` per field; **required fields carry a visible
  non-color marker ("Required") plus `aria-required`** — asterisk-only or color-only is not
  enough; errors associated via `aria-describedby`; error state conveyed by text + icon, not
  color alone.
- **Target sizes:** interactive targets ≥ 44×44px (mobile-first), with adequate spacing between
  adjacent controls.
- **Reduced motion:** honor `prefers-reduced-motion` — drop the transaction-logged toast fade and
  any budget-meter fill animation, show the end state immediately.

## Key Flows

Sourced from SRS §5 Business Flows, not invented.

### Flow 1 — An ADMIN invites a family member, who activates and logs their first expense (BF-01, BF-02)

**Entry state:** an ADMIN, signed in, on the Family screen.

1. The ADMIN taps "Invite a family member," enters the invitee's email, submits (UM-US-01 AC-01).
2. The system creates a `PENDING` account, generates a 24-hour token, and sends an activation
   email; the ADMIN sees "Invitation sent successfully" and the new row appears in the Family list
   as `PENDING`.
3. The invitee opens the email on their phone and taps the activation link, landing on the
   one-page Activate Account form (UXR-04).
4. They enter their full name and choose a password meeting the policy, then submit.
5. **CLIMAX:** the account becomes `ACTIVE`; they are directed to the Login screen with "Account
   activated successfully" — deliberately no auto-login (UM-US-02 AC-01, AC-09).
6. They log in and land on the Dashboard, which is empty of activity — a calm empty state, not a
   wall of demo numbers.
7. **Resolution:** they create their first Wallet, log their first Transaction, and watch the
   Dashboard's stat-tile update immediately (UXR-03) — the moment the app becomes theirs.
- **Edge case:** if the activation link has expired, step 3 instead shows "Invitation link has
  expired. Please request a new invitation." before the form is ever shown (UM-US-02 AC-02,
  AC-11); they ask the ADMIN to re-invite, which supersedes the old link and issues a fresh one
  (UM-US-01 EC-02).

*Surfaces:* 11 → 2 → 1 → 3 → (5, 8). *Components:* status-pill, forms, stat-tile.

### Flow 2 — A family member sets a budget and is warned before overspending (FR-05, BF-04)

**Entry state:** an `ACTIVE` user, signed in, with at least one wallet and category already set up.

1. They open Budgets and set a monthly cap on "Dining Out" against their Checking wallet.
2. Over the following weeks they log several dining transactions; each one updates the wallet
   balance and the budget-meter's fill immediately.
3. **CLIMAX:** a transaction pushes spending past 75% of the cap — the meter turns amber and a
   Notification appears, without the person having to go check.
4. They see the meter and decide to ease off; the color communicates the state at a glance, even
   without reading the percentage (UXR-02).
5. **Resolution:** if spending reaches 100%, the meter turns red and the overspend is shown
   plainly, not hidden — the app's job is to inform, not to shame.

*Surfaces:* 7 → 8 → 10 → 3. *Components:* budget-meter, transaction-row.

### Flow 3 — A user reviews their monthly report (FR-07, lighter)

**Entry state:** an `ACTIVE` user, signed in, at month's end.

1. They open Reports and see a monthly income vs. expense summary.
2. They browse the net savings trend and top spending categories.
3. **CLIMAX:** a category they didn't expect — dining out again — stands out as the top expense,
   prompting them to reconsider next month's plan.
4. **Resolution:** they navigate straight to Budgets to adjust the cap, closing the loop from
   insight to action.

*Surfaces:* 9 → 7. *Components:* transaction-row (aggregated), budget-meter.

## Responsive & Platform

**Mobile-first.** Per `CLAUDE.md`'s round-1 scope, mobile (React Native/Expo) is the current build
target; a responsive web view is in SRS's stated scope but not yet built.

| Breakpoint | Behavior |
|---|---|
| `≥ lg` (desktop, future web) | Full nav inline; Dashboard uses the asymmetric panel + column grid (`DESIGN.md`); wallet/budget lists in a multi-column grid. |
| `md` (tablet) | Grids reflow to 2 columns. |
| `< md` (mobile, current build) | Bottom tab bar; all grids reflow to 1 column, no horizontal scroll; forms are a single scrollable column. |

**Data loading strategy:** skeleton blocks sized to the eventual content; no layout jump when
transaction, wallet, or report data arrives.
