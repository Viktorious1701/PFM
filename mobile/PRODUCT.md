# Product

<!-- impeccable:product-schema 1 -->

## Platform

ios, android

Ships to both as one unified native mobile app (Expo/React Native) with a single, deliberately bespoke
visual identity — not per-OS adapted (so not "adaptive" in the genuinely-diverging sense), and not
"web": `DESIGN.md` itself calls the layout "mobile-only, single-column." The web build (`expo start
--web`) is a developer-convenience preview only — there is no Android emulator in this dev environment,
so web is how the layout gets checked without hardware — not a real responsive web surface aimed at
browser users. Confirmed with the user directly (not inferred).

## Users

Individuals and families managing personal finances together. One member holds the `ADMIN` role and
invites other household members (`USER` role) by email — there is no open self-registration, so every
account is a verified real person before they can touch shared financial data. Primary job: log income
and expense transactions as they happen, organize money across multiple wallets (cash, bank accounts,
credit lines), and keep category-level spending under a monthly budget without manually tallying
numbers. (SRS §1.1–1.3, §1.5 Conceptual Domain Model.)

## Product Purpose

Helps individuals and families record, track, and control their daily finances — specifically to
prevent overspending through visible, color-coded budget health, and to keep onboarding trustworthy
through invitation-only account creation (SRS §1.1). Success means: logging a transaction is fast
enough to do in the moment (not a deferred end-of-day chore), and a user can tell whether they're
within budget at a glance, without reading raw numbers.

## Positioning

The combination SRS §1.1 names as the product's mechanism: **verified-only onboarding** (invitation +
email token, no open signup) + **low-friction expense logging** + **proactive overspending prevention**
(budget thresholds surfaced visually, not just recorded). A generic expense tracker logs transactions;
PFM's differentiation is pairing that with real account trust (every user was invited by someone who
vouches for them) and budget health that's legible without doing mental math.

## Operating Context

- Daily/frequent use: logging transactions as money moves, not a periodic reconciliation task.
- Multi-wallet: a household typically holds several wallets (cash, one or more bank accounts, a credit
  line) and categorizes every transaction against one of them.
- Monthly budget cycle: budgets are set per category per wallet, over a calendar month, and reset each
  period (SDS §5.5).
- Household admin workflow: one ADMIN invites and manages the other members who share visibility into
  the same financial picture (SRS Feature-01).
- Backend is feature-complete and ahead of the UI: the REST API already has full CRUD for Wallets,
  Categories, Budgets, and Transactions, plus a summary report endpoint and soft-delete (archive) on
  Wallets and Categories. The mobile app is being wired onto this API screen-by-screen — Wallets,
  Transactions, and the Reports summary are real today; Budgets is still a placeholder screen awaiting
  its UI build.

## Capabilities and Constraints

- **Invite-only accounts.** No open self-registration (SRS §1.3 Constraints) — prevents non-existent
  or unverified emails from ever reaching financial data.
- **Manual entry only, this round.** No live bank-feed or exchange-rate integration; asset values and
  transactions are entered by hand (SRS §1.3, MVP Focus). Asset/investment holdings tracking (SRS
  Feature-11) and the AI assistant (Feature-10) are explicit future-phase placeholders, out of scope now.
- **Money precision.** All amounts are `DECIMAL(15,2)`, never floating point, end to end.
- **Name round-tripping.** Full names must preserve non-Latin diacritics exactly (confirmed test case:
  `Đặng Ngọc Thịnh` must round-trip unchanged) — the UI is English-copy only, but user-entered names are
  not assumed to be ASCII.
- **Stack:** Expo (React Native) + TypeScript + `expo-router`, backend is FastAPI/SQLAlchemy/Alembic
  (Python) over SQLite in dev, Postgres in deployment. Existing codebase — not a greenfield choice.
- **Budget health must be readable by color alone** (🟢 healthy / 🟡 warning / 🔴 exceeded — SRS UXR-02,
  SDS §3.1), and color is never the *only* channel for that same information elsewhere (see
  Accessibility below).

## Brand Commitments

- **Name:** PFM (Personal & Family Finance Management).
- **Committed visual identity: "Cash & Carry"** — a tactile paper-ledger / receipt-stamp aesthetic,
  decisively chosen by the product owner after a 4-mockup review, documented in full in
  `mobile/DESIGN.md`. Palette: Kraft Board, Ledger Paper, Iron-Gall Ink, Faded Ink, Ledger Green,
  Stamp Red, Brass Coin. Type: Courier Prime (headings) + PT Serif (body). Signature motifs: torn/
  deckle-edge ticket edges (SVG), postmark-style category glyphs, ink-press gradient stamp buttons.
  Supersedes an earlier "Sky & Sedge" cream/slate identity (not deleted — recoverable via
  `git log -- mobile/DESIGN.md`).
- **This identity deliberately overrides native OS chrome on both iOS and Android** — no SF Symbols, no
  Material 3 components, no per-OS navigation idiom. This is a brand-first decision the product owner
  already made, not an unaddressed native-conformance gap; a future audit/critique pass should not
  flag the absence of native components as a defect without re-litigating this approval.
- **One rule carried over from "Sky & Sedge," still binding:** budget-health text/percentage labels
  stay Iron-Gall Ink regardless of state — color conveys the health state, but the label itself is
  never rendered in a color-only-legible way, so colorblind users aren't reading color as the sole
  signal for the same fact twice.

## Evidence on Hand

No real user screenshots, testimonials, press, or benchmark data were provided. `mobile/src/api/
mock.ts` holds fixture data used only in the app's mock/prototype mode (`EXPO_PUBLIC_API_MOCK=1`) —
illustrative, not real user data, and must not be presented as such in any design artifact. Future
design work should not fabricate customer quotes, usage numbers, or screenshots beyond what the real
app genuinely renders.

## Product Principles

1. **Invitation-only trust boundary.** Every account that can touch financial data was vouched for by
   an existing ADMIN — never relax this for onboarding convenience.
2. **Logging should take seconds, not forms.** The product's core daily action is recording a
   transaction; friction there undermines the whole value proposition.
3. **Budget health is legible without arithmetic.** Color-coded state (🟢/🟡/🔴) is a requirement, not
   decoration — and it's never the *only* way the same fact is conveyed.
4. **One brand world, not per-OS chrome.** Cash & Carry is the visual identity on iOS and Android alike,
   by deliberate choice — bespoke components over native conformance is the committed direction here,
   not a gap to close.
5. **The backend leads; the UI catches up screen by screen.** Design work should assume the API
   contract is already settled and stable — new screens are wired to real, already-shipped endpoints,
   not built against a guessed future contract.

## Accessibility & Inclusion

- Budget health must never rely on color as the sole channel for the same fact in the same place — the
  numeric/text label stays neutral ink regardless of health state (SRS UXR-02, SDS §3.1; see Brand
  Commitments).
- User-entered full names must preserve non-Latin diacritics exactly through every storage/display
  round-trip (confirmed test case uses Vietnamese: `Đặng Ngọc Thịnh`).
- No other accessibility standard (WCAG level, screen-reader conformance target) has been explicitly
  set by any source document — treated as undecided rather than assumed.
