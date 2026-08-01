---
name: PFM Mobile
description: Visual identity for the PFM mobile app — "Sky & Sedge", ported from a bird-photography
  shop theme and re-tokened for personal finance.
status: draft — theme applied to a prototype; no screen here satisfies a TC (see CLAUDE.md §5)
created: 2026-07-31
ported-from: ../ux-designs/ux/DESIGN.md
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
  h1:
    fontFamily: Lora
    fontSize: 28px
    fontWeight: '700'
    lineHeight: '1.15'
  h2:
    fontFamily: Lora
    fontSize: 22px
    fontWeight: '600'
    lineHeight: '1.2'
  h3:
    fontFamily: Lora
    fontSize: 18px
    fontWeight: '600'
    lineHeight: '1.3'
  hero:
    fontFamily: Lora
    fontSize: 34px
    fontWeight: '700'
    lineHeight: '1.1'
  body-lg:
    fontFamily: Inter
    fontSize: 17px
    fontWeight: '400'
    lineHeight: '1.5'
  body:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: '1.5'
  caption:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.4'
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
  base: 4px
  margin-mobile: 20px
shadows:
  overlay: '0 6px 24px -8px rgba(59, 65, 71, 0.18)'
---

## Why this document exists

CLAUDE.md §5 treats `mobile/` as a UI **prototype**, not implementation: fixture-driven, satisfying
no `TC`, with `[UI]` rows deferred until a screen is wired to a real endpoint. Porting a visual theme
doesn't change any of that — this file is the same kind of artifact `../ux-designs/ux/DESIGN.md` is
for its shop, scoped to the mobile app instead. It is *not* a fourth `specs/` epic (CLAUDE.md §1.1
rule 0 still means three files, and this isn't one of them); it's the token contract the mobile code
is checked against, the same way `src/theme/tokens.ts` already was before this pass — just with
different values and a written rationale for them.

## What was ported, and what was dropped

**Kept wholesale**, because it's a visual identity independent of what's being sold: the cream field
+ hairline-not-shadow depth system, the `ink`/`sky-deep`/`sage-deep` accent split with soft variants
barred from text, Lora-for-headings + Inter-for-everything-else, the 4px spacing scale, the radius
semantics (pill actions / 6px containers / sharp-and-framed media), and light-mode-only.

**Dropped:**
- **Every shop-specific component** — `product-card`, `variant-selector`, `watermark-badge`,
  `cart-line`, `gallery-item`. Nothing in PFM sells a photograph.
- **The bilingual layer** (`language-toggle`, the EN|VN rule, Vietnamese-first copy). No requirement
  in `SRS.md` covers internationalisation, and adding one now would be unspecified scope. English
  only. The two font families still load the Vietnamese subset, because UM-US-02 EC-04 requires a
  name like `Đặng Ngọc Thịnh` to render and persist exactly as typed — that's a correctness
  requirement about diacritics, not a bilingual UI.
- **Desktop breakpoints, the 12-column grid, the asymmetric hero rhythm.** Mobile-first here means
  mobile-*only* for now: this app is a single-column React Native surface, not a responsive web
  layout. If a tablet or web-desktop target is ever added, revisit.
- **The exact type ramp's sizes.** The source's `display`/`h1` (56px/40px) are print-magazine-hero
  sizes for a wide desktop viewport; halved-and-under here for a phone screen carrying financial
  figures, not a photograph. The *roles* (display → hero balance figure, h1 → screen title, h3 →
  card heading, caption → labels/pills) carry over unchanged.

**Added — finance components the source never needed**, in the same token language: `stat-tile`
(the dashboard's net-balance figure), `wallet-card`, `budget-meter`, `transaction-row`. `status-pill`
already existed in the source for order state and is reused as-is for user/invitation status.

## One real conflict, resolved

SRS UXR-02 and SDS §3.1 require budget health be readable **by colour alone** — 🟢 healthy /
🟡 warning / 🔴 exceeded — while the source `DESIGN.md` restricts `success`/`pending`/`error` to
"status affordances," not decoration, and bars a third brand accent. These don't actually conflict:
**budget health is status vocabulary, not a brand accent** — exactly the category the source already
carves out for order status. `success #4F7A52` / `pending #96681F` (repurposed as "warning" here,
since PFM has no literal "pending payment" state) / `error #A85248` are the correct hues under the
source's own rules, and `budgetHealth()`'s existing 80%/100% thresholds are untouched.

What *does* need stating: "colour alone" (UXR-02) and WCAG accessibility both matter, and a filled
bar with no label fails a colour-blind reader on both counts. So the `budget-meter` component carries
**fill + a text label + a percentage**, never fill alone — the same discipline the source's
`status-pill` already applied ("the label stays `ink`, the status hues fail AA as small text on the
sunken pill... color lives in the dot, meaning in the word"). This is the one place this port
reinterprets a source rule rather than just re-tokening it, and it's recorded here rather than
silently decided in a component file.

## Colors

Same palette, same discipline: **soft** hues are decoration/large-area only and fail AA as text;
**deep** hues carry text and interactive fill; both are validated against `bg-page`/`surface`.

- **`bg-page` #FBF9F4** — the cream canvas behind every screen. Never behind text or over a filled
  card.
- **`surface` #FFFFFF** — cards, inputs, the tab bar, anything raised.
- **`surface-sunken` #F1EDE4** — the status-pill field and any "lower layer" band. Never a primary
  content area.
- **`border` #E4DFD3` — the hairline. Frames cards, separates rows, replaces shadow as the depth
  mechanism. Never fill, never text.
- **`ink` #3B4147** — primary text, headings, and body copy. The default for anything a reader must
  read, including a wallet balance or a transaction amount.
- **`ink-muted` #6B7178** — secondary text: meta lines, helper copy, placeholders, inactive tab
  labels. Also the **interactive border** for text inputs — the decorative `border` hairline is too
  faint to meet WCAG 1.4.11's ≥3:1 edge-contrast requirement on a field a person types into.
- **`caption-deep` #71736B** — reserved, unused in this app currently (the source used it for photo
  captions; no direct PFM analogue yet). Kept in the palette rather than deleted, in case a future
  screen needs a third text tier between `ink-muted` and `ink`.
- **`sky-soft` #7E9AAB`** — decorative only: empty-state art, large calm washes. Never text, never a
  small control.
- **`sky-deep` #4C6577** — the **primary interactive** colour: primary-button fill, active tab,
  focus rings, links, the balance-tile background. The one hue that means "clickable" or "current."
- **`sage-soft` #8B9B7A`** — decorative only, reserved.
- **`sage-deep` #5E6F4B** — the **secondary interactive** colour: secondary-button outline/text.
  Used sparingly.
- **`success` #4F7A52`**, **`pending`→ warning #96681F`**, **`error` #A85248`** — status vocabulary
  for budget health and user/invitation state, never brand decoration. See *One real conflict* above.
- **`info` #4C6577`** — same value as `sky-deep`, so an informational banner reads as part of the
  primary voice, not a fourth accent.

## Typography

Lora (600/700) for headings and the balance hero figure; Inter (400/500) for everything else —
body copy, labels, form text, prices, captions. Headings never sit in Inter; monetary figures and UI
never sit in Lora. Both families load the Vietnamese subset (see *What was dropped*).

| Role | Family | Size | Weight | Used for |
|---|---|---|---|---|
| `hero` | Lora | 34 | 700 | The dashboard's net-balance figure |
| `h1` | Lora | 28 | 700 | Screen titles ("Invite Family Member", "Sign in to PFM") |
| `h2` | Lora | 22 | 600 | Section headings within a screen |
| `h3` | Lora | 18 | 600 | Card headings (a wallet name, a user's full name) |
| `body-lg` | Inter | 17 | 400 | Lead paragraph / screen description |
| `body` | Inter | 15 | 400 | Default body copy, list rows, form values |
| `caption` | Inter | 12 | 500 | Labels, meta text, pill contents, helper/error text |

## Layout & Spacing

4px base scale: `1`–`6` = 4/8/12/16/24/32. `margin-mobile` (20px) is the page edge on every screen —
`Screen.tsx`'s existing `space.lg` (16px) body padding moves to this. Single column, no horizontal
scroll, ever. Vertical rhythm between sections uses `spacing.5`–`spacing.6` so content breathes.

## Elevation & Depth

**Flat.** Depth comes from the `border` hairline and whitespace, never a shadow, on anything resting
on the page — cards, tiles, rows. Exactly one shadow token, `shadows.overlay`, exists and is reserved
for transient overlays (a modal, a dropdown) — this app doesn't have one yet, so it is unused but
kept for when it does.

## Shapes

- **Buttons → `rounded.full`** (pill). The one soft, obviously-tappable shape.
- **Cards, tiles, inputs → `rounded.md`** (6px). The default container radius.
- **Status pills → `rounded.full`.**

There is no photograph-framing rule here (the source's `rounded.sm` + hairline "print" treatment) —
PFM has no imagery to frame. The token is kept in the palette for a future avatar or receipt-image
feature, unused today.

## Components

### stat-tile
The dashboard's net-balance card. `sky-deep` fill, white `hero`-styled figure, a `caption`-styled
label above it in a translucent white. Replaces the old `surfaceInverse` slate tile 1:1 — same
position and role, new fill.

### wallet-card
`surface` card, `rounded.md`, 1px `border` hairline (no shadow). Wallet name in `body` `ink-muted`,
balance in `h3` `ink`.

### budget-meter
`surface-sunken` background at `rounded.md`. Category name + percentage in `caption`, both `ink`
(never the status hue as text — see *One real conflict*). A 6px track beneath, filled to the used
percentage in the status hue (`success`/`warning`/`error` from `budgetHealth()`), track background a
low-alpha `ink`. A `caption` `ink-muted` line below showing `$used of $limit`.

### transaction-row
`surface` row, `rounded.md`, 1px `border` hairline. Label in `body` `ink`; amount in `body` `ink` for
an expense, `success` for income — colour is a legitimate here because the sign is also shown
(`+`/`-`), so it isn't the sole channel of information (unlike the budget-meter case).

### status-pill *(existing `StatusChip`, re-tokened)*
`surface-sunken` background, `rounded.full`, `caption` label always `ink`, with a leading coloured
dot carrying the state hue: `PENDING` → `warning`, `ACTIVE` → `success`, `DEACTIVATED` → `ink-muted`.

### button-primary / button-secondary *(existing `Button`)*
Primary: `rounded.full` pill, `sky-deep` fill, white `caption`-weight label, `padding: spacing.3
spacing.4`. Pressed darkens toward `#3D5464`. Disabled: `surface-sunken` fill, `ink-muted` label.
Secondary: transparent fill, `sage-deep` text and 1px `sage-deep` border.

### text-input *(existing `TextField`)*
`surface` field, **1px `ink-muted` border** (not the decorative `border` hairline — see *Colors*),
`rounded.md`, `ink` text, `ink-muted` placeholder. Focus: 2px `sky-deep` border. Error: 1px `error`
border, helper text in `error`. Label above in `caption` `ink`.

### banner *(existing `Banner`)*
Left-border accent card, `rounded.md`, tone-coloured background + a 4px tone-coloured left edge,
message in the tone's foreground colour. Unchanged in shape from the current implementation — only
the tone palette (`color.success`/`.error`/`.info`) is re-tokened.

### screen chrome *(existing `Screen`, tab bar)*
`bg-page` cream page background (not `surface` — cream is the canvas, white is for raised content).
`margin-mobile` (20px) horizontal padding. Tab bar: `surface` background, 1px `border` top hairline,
`sky-deep` active / `ink-muted` inactive tint, `h3`-styled (Lora) header titles.

## Do's and Don'ts

**DO**
- Keep monetary figures in `ink` — they're information, not decoration.
- Frame every card with a `border` hairline instead of a shadow.
- Use `sky-deep` as the single "this is clickable / this is current" signal.
- Render budget/status hues as fill + dot, never as the only distinguishing text colour.

**DON'T**
- Put `sky-soft` or `sage-soft` on text or a small control.
- Add a drop-shadow to anything resting on the page.
- Introduce a third brand accent — status hues are vocabulary, not decoration.
- Set a heading in Inter or a monetary figure in Lora.
- Reach for the bilingual toggle, the shop components, or the desktop grid — they were deliberately
  dropped; see *What was ported, and what was dropped*.
