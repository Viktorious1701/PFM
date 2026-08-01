---
name: PFM
description: Visual identity for PFM — a calm, editorial personal & family finance app that tracks
  wallets, budgets, and everyday transactions.
status: final
created: 2026-07-18
updated: 2026-07-31
history: >
  Originally authored for "SamThuongShop," a bird-photography e-commerce shop design exercise
  unrelated to this repository's product. Retargeted on 2026-07-31 to describe PFM instead — the
  underlying visual system (colors, type ramp, spacing scale) is unchanged; only what it describes
  changed. See ../../mobile/DESIGN.md for the adapted, mobile-only version of this same system that
  the shipped app actually uses — this file is the source design spec, at full responsive-web scale.
colors:
  bg-page: '#FBF9F4'
  surface: '#FFFFFF'
  surface-sunken: '#F1EDE4'
  border: '#E4DFD3'
  ink: '#3B4147'
  ink-muted: '#6B7178'
  caption-deep: '#71736B'
  sky-soft: '#7E9AAB'
  sky-deep: '#4C6577'
  sage-soft: '#8B9B7A'
  sage-deep: '#5E6F4B'
  success: '#4F7A52'
  pending: '#96681F'
  error: '#A85248'
  info: '#4C6577'
typography:
  display:
    fontFamily: Lora
    fontSize: 56px
    fontWeight: '700'
    lineHeight: '1.08'
    letterSpacing: -0.01em
  h1:
    fontFamily: Lora
    fontSize: 40px
    fontWeight: '700'
    lineHeight: '1.15'
    letterSpacing: -0.005em
  h2:
    fontFamily: Lora
    fontSize: 30px
    fontWeight: '600'
    lineHeight: '1.2'
  h3:
    fontFamily: Lora
    fontSize: 22px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.65'
  body:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  caption:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: '1.45'
    letterSpacing: 0.02em
rounded:
  none: '0'
  sm: 2px
  DEFAULT: 6px
  md: 6px
  lg: 12px
  full: 9999px
spacing:
  '1': 4px
  '2': 8px
  '3': 12px
  '4': 16px
  '5': 24px
  '6': 32px
  '7': 48px
  '8': 64px
  '9': 96px
  base: 4px
  gutter: 24px
  margin-mobile: 20px
  margin-desktop: 32px
  max-content: 1200px
shadows:
  overlay: '0 6px 24px -8px rgba(59, 65, 71, 0.18)'
components:
  top-nav:
    height: 64px
    background: '{colors.surface}'
    border-bottom: 1px solid {colors.border}
    link-color: '{colors.ink}'
    link-hover-color: '{colors.sky-deep}'
    font: '{typography.caption}'
  button-primary:
    background: '{colors.sky-deep}'
    color: '#FFFFFF'
    radius: '{rounded.full}'
    padding: '{spacing.3} {spacing.5}'
    font: '{typography.caption}'
    hover-background: '#3D5464'
    disabled-background: '{colors.surface-sunken}'
    disabled-color: '{colors.ink-muted}'
    focus-ring: '2px solid {colors.ink}'
    focus-ring-offset: 2px
  button-secondary:
    background: transparent
    color: '{colors.sage-deep}'
    border: 1px solid {colors.sage-deep}
    radius: '{rounded.full}'
    padding: '{spacing.3} {spacing.5}'
    hover-background: '{colors.surface-sunken}'
  stat-tile:
    background: '{colors.sky-deep}'
    radius: '{rounded.md}'
    label-font: '{typography.caption}'
    label-color: 'rgba(255, 255, 255, 0.78)'
    value-font: '{typography.display}'
    value-color: '#FFFFFF'
    padding: '{spacing.6}'
  wallet-card:
    background: '{colors.surface}'
    radius: '{rounded.md}'
    border: 1px solid {colors.border}
    name-font: '{typography.body}'
    name-color: '{colors.ink-muted}'
    balance-font: '{typography.h3}'
    balance-color: '{colors.ink}'
    gap: '{spacing.3}'
  budget-meter:
    background: '{colors.surface-sunken}'
    radius: '{rounded.md}'
    label-font: '{typography.caption}'
    label-color: '{colors.ink}'   # label always ink — the fill carries the status hue, not the text
    track-background: 'rgba(59, 65, 71, 0.12)'
    track-height: 6px
    fill-healthy: '{colors.success}'
    fill-warning: '{colors.pending}'
    fill-exceeded: '{colors.error}'
    padding: '{spacing.4}'
  transaction-row:
    border-bottom: 1px solid {colors.border}
    title-color: '{colors.ink}'
    meta-color: '{colors.ink-muted}'
    amount-color-expense: '{colors.ink}'
    amount-color-income: '{colors.success}'
    gap: '{spacing.4}'
  status-pill:
    radius: '{rounded.full}'
    background: '{colors.surface-sunken}'
    font: '{typography.caption}'
    label-color: '{colors.ink}'   # label always ink for AA on the sunken pill; the DOT carries the status hue
    active-dot: '{colors.success}'
    pending-dot: '{colors.pending}'
    deactivated-dot: '{colors.ink-muted}'
    padding: '{spacing.1} {spacing.3}'
  text-input:
    background: '{colors.surface}'
    border: 1px solid {colors.ink-muted}   # interactive fields need a >=3:1 edge (WCAG 1.4.11); border token is decorative-only
    radius: '{rounded.md}'
    text-color: '{colors.ink}'
    placeholder-color: '{colors.ink-muted}'
    focus-border: 1px solid {colors.sky-deep}
    error-border: 1px solid {colors.error}
    padding: '{spacing.3} {spacing.4}'
    font: '{typography.body}'
  footer:
    background: '{colors.surface-sunken}'
    border-top: 1px solid {colors.border}
    text-color: '{colors.ink}'   # ink not ink-muted: ink-muted fails AA on surface-sunken (4.22:1)
    link-color: '{colors.ink}'
    heading-font: '{typography.h3}'
    font: '{typography.body}'
---

## Brand & Style

PFM is a **calm, editorial personal & family finance app** — quiet enough that checking the
week's grocery spend never feels like wrestling a spreadsheet. The direction is **"Sky &
Sedge"**: airy, modern, and quiet, built so that a family's own numbers — a wallet balance, a
budget bar, a logged expense — are always the clearest thing on the screen. Every layout decision
starts from one rule: **the numbers lead, the chrome supports.** Cream and hairline recede into
the background; the figures carry the weight.

The posture is calm and confident, never "fintech-loud" — no flashing arrows, no gamified badges,
no red alarm bells for an ordinary purchase. Generous whitespace, restrained type, and a two-hue
accent palette that reads as trustworthy rather than urgent — the pale blue of open sky, the muted
green of sedge and reed. Nothing on the screen competes with the one number a person actually
opened the app to check.

This is a **light-mode-only** system in v1 — no dark theme; nothing in PFM's requirements baseline
(SRS §3–§4) asks for one. The interface is **English-only** — no requirement in this project
covers internationalisation, so no bilingual layer is designed for.

## Colors

The palette is a warm cream field with two nature accents. There is a hard split between **soft**
and **deep** variants: soft hues are for decoration and large calm areas; deep hues carry any text
or interactive fill. Every deep pairing below has been chosen to pass **WCAG AA (≥4.5:1) on the
`{colors.bg-page}` cream** — the soft variants deliberately do not, which is why they are barred
from text.

- **`bg-page` #FBF9F4** — the warm-cream canvas behind everything. The default page background.
  Never used for text or on top of a filled card.
- **`surface` #FFFFFF** — pure white for cards, inputs, nav, and any raised content. Not used as a
  page background (that stays cream).
- **`surface-sunken` #F1EDE4** — a recessed tone for the footer, status-pill fields, budget-meter
  tracks, and quiet section bands. Signals "lower layer," never used for primary content areas.
- **`border` #E4DFD3** — the hairline. This is the workhorse of the whole system: it frames cards,
  separates transaction rows, and outlines wallet tiles. It replaces shadow as our depth
  mechanism. Never used as fill or text.
- **`ink` #3B4147** — the primary text color for both headings and body, and the color of
  **monetary figures** — wallet balances, transaction amounts, budget totals. Passes AA
  comfortably on cream and white. The default for anything a reader must read.
- **`ink-muted` #6B7178** — secondary text: meta lines, helper copy, inactive states, placeholder
  text. AA on cream. Not for long body passages.
- **`caption-deep` #71736B** — a slightly warm neutral reserved for a tertiary text tier, one step
  quieter than `ink-muted` — e.g. a timestamp under a transaction row. Not currently assigned to a
  component; kept in the palette rather than deleted.
- **`sky-soft` #7E9AAB** — decorative sky-blue for large calm areas only: hero wash panels,
  illustrative dividers, empty-state art (e.g. "No transactions yet"). **Never text, never a small
  control.**
- **`sky-deep` #4C6577** — the **primary interactive** color: links, primary-button fill, focus
  rings, selected states, the stat-tile fill. AA on cream and white. This is the one hue users
  learn to mean "clickable" or "current."
- **`sage-soft` #8B9B7A** — decorative sage-green for category tags rendered as filled chips
  backed by their own deep text — e.g. an "Income" flag or a custom category accent. Large/
  decorative use only, never small text on cream.
- **`sage-deep` #5E6F4B** — the **secondary interactive** color: secondary-button outline/text,
  secondary links. Used sparingly so it never rivals `sky-deep`. AA on cream and white.
- **`success` #4F7A52** — the *budget healthy* / account **ACTIVE** state. Used for the status
  **dot** or **fill** (and for short status text on cream/white, where it passes AA); on the
  `{colors.surface-sunken}` status pill or budget-meter the label stays `{colors.ink}` and this
  hue rides the dot/fill. AA on cream, not on sunken.
- **`pending` #96681F** — the *budget warning* (75–99% spent) / account **PENDING** (invited, not
  yet activated) state (a muted amber-brown, not a yellow). Same rule as `success`: dot/fill hue
  and cream/white status text only; the pill label stays `{colors.ink}`. AA on cream, not on
  sunken.
- **`error` #A85248** — the *budget exceeded* state and input validation errors. AA on cream.
  Never decorative.
- **`info` #4C6577** — informational notices; intentionally the same value as `sky-deep` so system
  messaging reads as part of the primary voice.

**Accent discipline:** only two accent hues live on any screen — sky and sage. No third accent is
introduced. Semantic colors (success/pending/error) are status vocabulary, not brand accents, and
appear only inside status affordances (status pills, budget meters) and validation.

## Typography

Two families:

- **Lora** (serif, weights 600 / 700) — the editorial voice. All headings, and the dashboard's
  hero net-balance figure. Its literary warmth gives the app a calm, magazine feel rather than a
  spreadsheet one.
- **Inter** (sans, weights 400 / 500) — the quiet functional voice. All body copy, UI labels,
  monetary figures, form text, and captions. Neutral, highly legible.

**The ramp** (`{typography.*}`):

| Role | Family | Size | Weight | Line height |
|---|---|---|---|---|
| `display` | Lora | 56px | 700 | 1.08 |
| `h1` | Lora | 40px | 700 | 1.15 |
| `h2` | Lora | 30px | 600 | 1.2 |
| `h3` | Lora | 22px | 600 | 1.3 |
| `body-lg` | Inter | 18px | 400 | 1.65 |
| `body` | Inter | 16px | 400 | 1.6 |
| `caption` | Inter | 13px | 500 | 1.45 |

`display` is reserved for the dashboard's hero net-balance figure. `h3` is a card heading — a
wallet name, a transaction's category. `caption` (with slight tracking) is the label used for nav
items, meta hints, and status pills. **Rules:** headings never use Inter; monetary figures and UI
never use Lora.

## Layout & Spacing

A **4px base scale** drives all spacing: `{spacing.1}`–`{spacing.9}` = 4, 8, 12, 16, 24, 32, 48,
64, 96px. Named tokens: `{spacing.gutter}` (24px column gutter), `{spacing.margin-desktop}` (32px)
and `{spacing.margin-mobile}` (20px) for page edges. Content is capped at
`{spacing.max-content}` (~1200px) and centered.

The grid is a **12-column** desktop grid with 24px gutters. Whitespace is a feature, not leftover
space: sections breathe with `{spacing.8}`–`{spacing.9}` vertical rhythm so the eye rests between
figures.

**Asymmetric dashboard rhythm** is the signature move: a **wide balance/chart panel (8 columns)
paired with a narrow quick-actions column (4 columns)** — the numbers dominant, the actions
deferential. A wallet or transaction detail view follows the same split: the figure and its
history on the left, the edit/action column on the right.

**Breakpoints (responsive web, mobile-first):**
- **Mobile (< 640px):** single column, 20px margins, no horizontal scroll ever. The net-balance
  stat-tile goes full-width above a stacked wallet/transaction list. List density = 1 column.
- **Tablet (640–1024px):** 6–8 column feel; wallet cards = 2–3 columns; margins ease toward 32px.
- **Desktop (> 1024px):** full 12-column grid, 32px margins, asymmetric dashboard split active;
  wallet cards = 3–4 columns.

## Elevation & Depth

**Flat editorial.** Depth comes from **whitespace and the `{colors.border}` hairline**, not from
shadows. Cards, wallet tiles, budget meters, and inputs sit on the page with a 1px
`{colors.border}` outline and generous surrounding space — they are *framed*, like entries in a
ledger, never *floated*.

Exactly **one** shadow token exists, `{shadows.overlay}` (`0 6px 24px -8px rgba(59,65,71,0.18)`),
and it is reserved for **transient overlays only**: the nav dropdown, a notification panel, and
modals. If an element is part of the page, it gets a hairline; if it floats above the page
temporarily, it gets the overlay shadow. Nothing else casts a shadow — resting cards never do.

## Shapes

Radius encodes what a thing *is*:

- **Buttons → `{rounded.full}` (9999px, pill).** The one soft, friendly, obviously-tappable shape.
  Pills read as "action" and give the quiet UI a single warm gesture.
- **Cards & inputs → `{rounded.md}` (6px).** A gentle rounding that feels modern and calm without
  turning tech-y. The default container radius.
- **`{rounded.sm}` (2px), reserved.** No photographic content exists in v1 to frame with it; kept
  in the token set for a future receipt-image or avatar feature, unused today.

The logic: soft where the user acts (pills), calm where the UI holds content (6px).

## Components

Token references resolve against the frontmatter above.

### top-nav
Full-width bar, `{components.top-nav.height}` tall, `{colors.surface}` background with a
`{colors.border}` bottom hairline (no shadow at rest). Left: wordmark in Lora. Center/right: nav
links — Dashboard · Wallets · Budgets · Transactions · Reports · Family — in `{typography.caption}`,
color `{colors.ink}`, hover `{colors.sky-deep}`. On mobile it collapses to a hamburger opening a
menu that uses `{shadows.overlay}` (it is transient).

### button-primary
Pill (`{rounded.full}`), solid `{colors.sky-deep}` fill, white label in `{typography.caption}`,
padding `{spacing.3} {spacing.5}`. Hover darkens to `#3D5464`; focus shows a **2px `{colors.ink}`
ring offset 2px from the fill** — a same-color `{colors.sky-deep}` ring on a `{colors.sky-deep}`
button is invisible and is forbidden. Disabled = `{colors.surface-sunken}` fill with
`{colors.ink-muted}` text. Example labels: "Send invitation," "Save budget," "Log transaction."

### button-secondary
Pill, transparent fill, `{colors.sage-deep}` text and 1px `{colors.sage-deep}` border. Hover fills
`{colors.surface-sunken}`. Used for lower-priority actions ("Cancel," "Skip"). Never competes
visually with primary.

### stat-tile
The dashboard's net-balance card. `{colors.sky-deep}` fill at `{rounded.md}`, a `{typography.caption}`
label in translucent white ("Total Net Balance") above the figure itself in `{typography.display}`
white (e.g. **$12,450.00**). The single largest, highest-contrast element on the dashboard — this
is the number a person opened the app to see.

### wallet-card
`{colors.surface}` card at `{rounded.md}` with a `{colors.border}` hairline (no shadow). Wallet
name in `{typography.body}` `{colors.ink-muted}` (e.g. "Checking"), balance in `{typography.h3}`
`{colors.ink}` beneath it.

### budget-meter
`{colors.surface-sunken}` field at `{rounded.md}`. Category name and percentage used, both in
`{typography.caption}` `{colors.ink}` — **never** the status hue as text (see *One real conflict*
in `../../mobile/DESIGN.md`, which reconciles this against SRS UXR-02's colour-alone requirement).
A 6px track beneath, filled to the used percentage in the status hue
(`{colors.success}`/`{colors.pending}`/`{colors.error}` per the 75%/100% thresholds), track
background a low-alpha `{colors.ink}`. A `{typography.caption}` `{colors.ink-muted}` line below
showing the amount spent against the limit.

### transaction-row
A row separated from the next by a `{colors.border}` bottom hairline, `{spacing.4}` gap. Left:
category label in `{colors.ink}` and a meta line (wallet, date) in `{colors.ink-muted}`. Right:
the amount — `{colors.ink}` for an expense, `{colors.success}` for income, since the `+`/`-` sign
is also shown, so colour is never the sole channel of meaning here.

### status-pill
Pill (`{rounded.full}`) on `{colors.surface-sunken}`, `{typography.caption}` label in
`{colors.ink}` with a leading colored **dot**. The dot carries the status hue: **ACTIVE** →
`{colors.success}` ("Active"); **PENDING** → `{colors.pending}` ("Invited — awaiting activation");
**DEACTIVATED** → `{colors.ink-muted}` ("Deactivated"). The label stays `{colors.ink}` — the
status hues fail AA as small text on the sunken pill — so color lives in the dot, meaning in the
word. Never a loud fill.

### text-input
`{colors.surface}` field, 1px `{colors.ink-muted}` border (interactive fields need a ≥ 3:1 edge
per WCAG 1.4.11 — the decorative `{colors.border}` hairline is too faint here), `{rounded.md}`,
`{colors.ink}` text, `{colors.ink-muted}` placeholder, padding `{spacing.3} {spacing.4}`. Focus =
2px `{colors.sky-deep}` border. Error = 1px `{colors.error}` border with helper text in
`{colors.error}` plus a non-color error icon. Labels sit above in `{typography.caption}`
`{colors.ink}`, required fields marked "Required" (e.g. "Wallet name," "Monthly budget amount").

### footer
`{colors.surface-sunken}` band with a `{colors.border}` top hairline. Body text `{colors.ink}`
(not `{colors.ink-muted}` — it fails AA at 4.22:1 on the sunken band), links `{colors.ink}`,
section headings in `{typography.h3}`. Holds account settings, help, and sign-out links.

## Do's and Don'ts

**DO**
- **DO keep monetary figures in `{colors.ink}`** — they're information, not decoration.
- **DO frame every card with a `{colors.border}` hairline** instead of a shadow.
- **DO use `{colors.sky-deep}` as the single "clickable / current" signal** for links and primary
  actions.
- **DO render budget and account-status hues as fill or dot, never as the only distinguishing text
  color** — a colour-blind reader must be able to tell the states apart from the word alone.
- **DO keep depth flat** — rely on whitespace + hairline; reserve `{shadows.overlay}` strictly for
  transient overlays.

**DON'T**
- **DON'T put `{colors.sky-soft}` or `{colors.sage-soft}` on text or small controls** — soft
  variants are decorative/large-area only and fail AA.
- **DON'T add drop-shadows to cards, wallet tiles, or budget meters at rest** — a resting element
  gets a hairline, never a shadow.
- **DON'T introduce a third accent hue** — only sky and sage; semantic colors are for status, not
  decoration.
- **DON'T set headings in Inter or monetary figures/UI in Lora** — the two families do not swap
  roles.
- **DON'T let UI chrome compete with a figure** — no heavy buttons or loud fills layered over a
  balance or a chart.
- **DON'T introduce a dark theme in v1** — this is a light-mode-only system.
