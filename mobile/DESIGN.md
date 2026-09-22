---
name: PFM Mobile
description: Visual identity for the PFM mobile app — "Cash & Carry", a tactile paper-ledger /
  receipt-stamp aesthetic, approved after a 4-mockup review of the product owner.
status: draft — theme applied to a prototype; no screen here satisfies a TC (see CLAUDE.md §5)
created: 2026-09-22
supersedes: "Sky & Sedge" — this file's own previous version. Not deleted, only superseded, git
  keeps it in full (see "What this replaces, and why").
colors:
  kraft-board: '#E4D5B7'
  ledger-paper: '#FBF3E3'
  iron-gall-ink: '#2B2420'
  faded-ink: '#8A7A63'
  border: '#D8C79C'
  ledger-green: '#2E5339'
  stamp-red: '#8A3324'
  brass-coin: '#C08A2E'
  brass-deep: '#7A5518'
typography:
  hero:
    fontFamily: Courier Prime
    fontSize: 34px
    fontWeight: '700'
    lineHeight: '1.1'
  h1:
    fontFamily: Courier Prime
    fontSize: 28px
    fontWeight: '700'
    lineHeight: '1.15'
  h2:
    fontFamily: Courier Prime
    fontSize: 22px
    fontWeight: '700'
    lineHeight: '1.2'
  h3:
    fontFamily: Courier Prime
    fontSize: 18px
    fontWeight: '700'
    lineHeight: '1.3'
  body-lg:
    fontFamily: PT Serif
    fontSize: 17px
    fontWeight: '400'
    lineHeight: '1.5'
  body:
    fontFamily: PT Serif
    fontSize: 15px
    fontWeight: '400'
    lineHeight: '1.5'
  caption:
    fontFamily: PT Serif
    fontSize: 12px
    fontWeight: '700'
    lineHeight: '1.4'
    letterSpacing: 0.02em
rounded:
  none: '0'
  sm: 2px
  stamp: 4px
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
  overlay: '0 6px 24px -8px rgba(43, 36, 32, 0.18)'
---

## Why this document exists

CLAUDE.md §5 treats `mobile/` as a UI **prototype**, not implementation: fixture-driven, satisfying
no `TC`, with `[UI]` rows deferred until a screen is wired to a real endpoint. Replacing the visual
theme doesn't change any of that — this file is still the token contract the mobile code is checked
against, the same way it was under "Sky & Sedge," just with different values and a written rationale
for them. It is *not* a fourth `specs/` epic (CLAUDE.md §1.1 rule 0 still means three files, and this
isn't one of them).

## What this replaces, and why

The product owner reviewed four competing mockups and picked "Cash & Carry" decisively — a tactile
paper-ledger / receipt-stamp aesthetic — over "Sky & Sedge," the cream-and-slate identity ported from
a bird-photography shop theme. This is a full replacement, not a re-tokening: every colour, both type
families, and one shape rule change. Nothing about *what* the app is (a personal/family finance
prototype, English-only, mobile-only, still satisfying no `TC`) changed, so the sections below that
were never about the old palette — Layout & Spacing, most of Components — carry over close to
verbatim.

**"Sky & Sedge" is not deleted, only superseded.** Its full rationale — the cream/slate palette, the
Lora/Inter split, the bird-photography provenance — stays recoverable exactly the way that file itself
promised for *its* source: `git log -- mobile/DESIGN.md` finds the commit before this one, and
`git show <that sha>:mobile/DESIGN.md` (or the equivalent path for `tokens.ts`, `app/_layout.tsx`)
prints it in full. Nothing here silently erases the earlier reasoning; it's superseded, not
forgotten.

**Kept wholesale**, because it never depended on the palette: the 4px spacing scale and
`margin-mobile`, the flat/hairline depth system (still no shadow on anything resting on the page),
single-column mobile-only layout, English-only copy with the two type families still loading a
Vietnamese-capable subset (UM-US-02 EC-04 still needs `Đặng Ngọc Thịnh` to round-trip exactly), and
the same three components' worth of prototype-vs-real discipline (`PrototypeBanner`, `Placeholder`,
the `[UI]`-deferred test rows).

**Dropped:** the entire "Sky & Sedge" palette (cream/slate/sage), Lora and Inter as the app's type
faces, and the blanket "primary actions are pills" shape rule.

**Added:** the ink-press gradient stamp buttons, the torn/deckle-edge ticket motif (drawn in SVG, see
"Elevation & Depth" and "Components"), the postmark category-glyph treatment, and a genuine
income/expense contextual colour pair where the old system only ever had one interactive brand hue.

## One rule carried over, unchanged

SRS UXR-02 and SDS §3.1 require budget health to be readable **by colour alone** — 🟢 healthy /
🟡 warning / 🔴 exceeded — and "Sky & Sedge" resolved the apparent tension between that and its own
"no third brand accent" rule by treating budget health as *status vocabulary*, not decoration, and by
requiring the fill to carry colour while the label and percentage stay in the neutral text colour
(never the status hue as text) plus the percentage figure itself, so a colour-blind reader still has
the number. That reasoning didn't depend on which hues were involved, and it doesn't change now:
`budgetHealth()`'s 80%/100% thresholds are untouched, and the budget-thermometer component still
renders **fill + label + percentage**, never fill alone. The hues just move — see Colors below.

## Colors

Same discipline as before: light, paper-toned surfaces; one dark ink for nearly all text; hairlines
instead of shadows for depth; saturated colour reserved for meaning (income, expense, budget health),
never for large-area brand decoration.

| Token | Value | Role |
| :-- | :-- | :-- |
| Kraft Board | `#E4D5B7` | `color.bg` — the desk/page background. Never behind text or a filled card. |
| Ledger Paper | `#FBF3E3` | `color.surface` — every card, the ticket body, the tab bar. |
| Iron-Gall Ink | `#2B2420` | `color.text` — primary text, headings, monetary figures. |
| Faded Ink | `#8A7A63` | `color.textMuted` — secondary text, and the interactive border colour (below). |
| Border | `#D8C79C` | `color.border` — the hairline. ~1.5:1 against Ledger Paper — decorative, deliberately faint. |
| Ledger Green | `#2E5339` | `color.income` — income accent, healthy budget. ~7.9:1 on Ledger Paper — safe as text. |
| Stamp Red | `#8A3324` | `color.expense` — expense accent, exceeded budget. ~7.4:1 on Ledger Paper — safe as text. |
| Brass Coin | `#C08A2E` | warning budget **fill**. ~2.75:1 on Ledger Paper — fails WCAG AA as small text; see below. |

**Brass Coin is a fill/large-numeral/icon-stroke colour, not a text colour.** Measured against Ledger
Paper it's ~2.75:1 — short of the 3:1 floor WCAG treats as usable even for large text, let alone the
4.5:1 normal-text floor. Everywhere the "warning" hue is needed as text or a small graphic — the
budget-meter's `fg` slot, the `PENDING` status dot, the prototype banner's own lettering — this system
uses **Brass Deep** (`#7A5518`) instead: the same family of colour, ~6.1:1 on Ledger Paper, safe as
text. `color.budget.warning.accent` (the actual fill bar, a large area) is the one place raw Brass
Coin is used, exactly per the brief.

**There is no longer one universal "primary" brand hue** the way `sky-deep` was in "Sky & Sedge" —
actions are contextually coloured: income green, expense red. Where a truly generic/neutral action
needs a colour — a plain "Cancel," a settings link, a form submit that is not itself income or
expense — it defaults to **Iron-Gall Ink text on Ledger Paper or a bordered background, never an
invented tint**; the one nuance is that the shared `Button` component's primary variant is a *filled*
pill, and an ink-filled pill with Ledger-Paper lettering still satisfies this (ink is the palette's own
neutral, not a brand tint) while reading as a rubber ink stamp, which is in-theme rather than an
exception to it.

Full remap, by role:

- **`bg` #E4D5B7 (Kraft Board)** — the page canvas. Same "never behind text or a filled card" rule as
  the old `bg-page`.
- **`surface` #FBF3E3 (Ledger Paper)** — cards, the ticket body, the tab bar, anything raised.
- **`surfaceSunken` #F0E4C8** — a duller, sunken paper tone: the status-pill field, the budget
  thermometer's field, a disabled button fill. Never a primary content area.
- **`border` #D8C79C (Border)** — the hairline. Frames cards, separates rows, is the depth mechanism.
  Never fill, never text.
- **`text` #2B2420 (Iron-Gall Ink)** — primary text, headings, and every monetary figure.
- **`textMuted` #8A7A63 (Faded Ink)** — secondary text: meta lines, helper copy, placeholders,
  inactive tab labels. Also `borderInteractive` — the decorative hairline is too faint (~1.5:1) to
  meet WCAG 1.4.11's ≥3:1 edge-contrast floor on a field a person types into; Faded Ink clears it at
  ~3.8:1.
- **`captionDeep` #6B5B45** — reserved, unused today, same status as before the port (a third text
  tier, in case a future screen needs one between `textMuted` and `text`).
- **`sageSoft` #B7C9B8** — decorative-only pale wash of Ledger Green. Never text, never a small
  control.
- **`brassSoft` #E6D3A3** — decorative-only pale wash of Brass Coin. Replaces `skySoft` outright:
  "sky" has no referent left in this palette, and nothing in the app imported that key (checked by
  grep before renaming, so this is a clean rename, not a silent break).
- **`income` #2E5339 (Ledger Green)** / **`expense` #8A3324 (Stamp Red)** — the two contextual
  accents: the toggle, the stamp button gradients (via the deeper ink-press pair below), transaction
  amounts. Never used for a generic action — see the "no universal primary" note above.
- **`brassDeep` #7A5518** — the safe-contrast stand-in for the warning hue in text/small graphics; see
  above.
- **`budget.{healthy,warning,exceeded}`**, **`success`**, **`error`**, **`info`** — status vocabulary,
  never brand decoration, same as before. `info` still equals the neutral ink voice (`text`), the same
  relationship `info` had to `sky-deep` previously — an informational banner reads as part of the
  neutral voice, not a fourth accent.
- **`prototype`** — deliberately loud, and still built from `brassDeep` rather than raw Brass Coin,
  because its own label renders at caption size.

**Ink-press gradients** (two, used only on the two dashboard stamp buttons, nowhere else): expense
runs `#9C4530` → `#6B2A1C` top-to-bottom; income runs `#3C6B48` → `#1F3B27` top-to-bottom. These are
the one place a gradient exists in the system; a flat `income`/`expense` fill is correct everywhere
else a contextual colour is needed (the toggle segments, transaction-row amounts).

## Typography

**Courier Prime replaces Lora's role exactly** — headings and every monetary figure. A monospaced
typewriter face reads as a typed ledger column the moment a figure sits in it, which a proportional
serif never quite manages; that legibility-as-a-ledger read is the entire reason this face was chosen
over keeping a proportional heading face. **PT Serif replaces Inter's role exactly** — body copy,
labels, form text, captions. It's a warm, slightly literary book serif, deliberately distinct from the
money-figure face so the two never get confused at a glance, the same separation of concerns Lora/Inter
enforced before.

Both are Google Fonts packages (`@expo-google-fonts/courier-prime`, `@expo-google-fonts/pt-serif`);
neither ships a mid-weight. Confirmed from the installed packages' own generated `index.d.ts` (not
assumed): each exports only `_400Regular`, `_400Regular_Italic`, `_700Bold`, `_700Bold_Italic`. The
old ramp had a true semibold (Lora 600) and a true medium (Inter 500) for `headingSemibold` and
`bodyMedium`; neither exists here, so both **collapse onto the family's Bold cut** — `headingSemibold`
and `heading` are now the same asset (`CourierPrime_700Bold`), and `bodyMedium` maps to
`PTSerif_700Bold` rather than a medium weight. This is a real, visible step up in weight contrast
versus the old 500/600 mid-weights (most noticeable on button labels, chip text, and form labels,
which all render slightly bolder now than they used to), recorded here rather than left as an
unstated side effect of the font swap. PT Serif's italic (`PTSerif_400Regular_Italic`) is loaded too,
per the brief, and gets a real (if sparing) use: the small label above the net-balance tape.

| Role | Family | Size | Weight | Used for |
| :-- | :-- | :-- | :-- | :-- |
| `hero` | Courier Prime | 34 | 700 | A giant money figure (the dashboard hero ticket) |
| `h1` | Courier Prime | 28 | 700 | Screen titles ("Invite Family Member", "Sign in to PFM") |
| `h2` | Courier Prime | 22 | 700 | Section headings within a screen |
| `h3` | Courier Prime | 18 | 700 | Card headings (a wallet name, a user's full name) |
| `body-lg` | PT Serif | 17 | 400 | Lead paragraph / screen description |
| `body` | PT Serif | 15 | 400 | Default body copy, list rows, form values |
| `caption` | PT Serif | 12 | 700 (was 500) | Labels, meta text, pill contents, helper/error text |

Headings never sit in PT Serif; monetary figures and UI chrome never sit outside Courier Prime.
`@expo-google-fonts/lora` is fully removed (package and every `Lora_*` import) — checked by grepping
the whole `mobile/` tree before removal, per CLAUDE.md's honesty rules, rather than assumed clean.
`@expo-google-fonts/inter` remains installed for now (only Lora's removal was in scope for this pass);
nothing in the app renders with it any more after this change.

## Layout & Spacing

Unchanged from "Sky & Sedge": 4px base scale, `1`–`6` = 4/8/12/16/24/32, `margin-mobile` (20px) as the
page edge on every screen. Single column, no horizontal scroll, ever. Vertical rhythm between sections
uses `spacing.5`–`spacing.6`. None of this was ever about the old palette, so none of it moved.

## Elevation & Depth

Still **flat.** Depth still comes from the `border` hairline and whitespace, never a shadow, on
anything resting on the page. `shadows.overlay` is still reserved for a transient overlay (a modal, a
dropdown) this app doesn't have yet — recoloured to Iron-Gall Ink, otherwise untouched.

The one new physical cue is the hero ticket's torn top edge, and it is deliberately **not** a shadow
or a blur — it's geometry. React Native has no CSS `clip-path`, so the jagged silhouette is drawn as a
thin `react-native-svg` strip: a zigzag path filled with the same Ledger Paper colour as the card body
beneath it, sitting on the Kraft Board page colour, so the boundary between the two reads as torn
paper without a single pixel of drop-shadow. This keeps the flat-depth rule intact rather than
quietly breaking it for one component.

## Shapes

**Primary actions move away from the old blanket "pills" rule — but only the two new stamp actions,
not every button.** The dashboard's IN/OUT stamp button is a small-radius rectangle (`radius.stamp`,
4px) — a "stamped ticket," not a pill — because a pill reads as a soft app button and this needed to
read as a rubber stamp hitting paper. This is a deliberate, scoped change, not an oversight: the
shared `Button` component (Sign In, Send Invite, Activate) is untouched by this pass and keeps its
existing pill (`radius.full`); it wasn't part of the dashboard rebuild, and re-shaping a component
used across screens that weren't part of this review is a separate decision, not one made silently
here.

- **The two stamp actions → `radius.stamp`** (4px). The one place the old pill rule no longer
  applies.
- **Cards, tiles, the ticket body → `radius.md`** (6px), unchanged from before.
- **The shared `Button`, `StatusChip` → `radius.full`** (pill), unchanged — out of scope for this
  pass.

There is still no photograph-framing rule (`radius.sm` stays reserved, unused, for a future avatar or
receipt-image feature).

## Components

### hero ticket *(replaces stat-tile)*
Ledger Paper card with a torn SVG top edge (see "Elevation & Depth"), framed on the remaining three
sides with a `border` hairline. Contains, top to bottom: the IN/OUT toggle, a giant Courier Prime
amount on a rule line (static/placeholder — there is no real amount-entry keypad behind this screen
yet, so it renders in `textMuted` rather than `text` to read as an empty field, with a one-line note
saying so), the three postmark category glyphs, and the gradient stamp button. This is the dashboard's
new focal point, replacing the old slate stat-tile in both position and role.

### IN/OUT toggle
Two segments in a hairline-framed strip. The inactive segment is Ledger Paper with ink text; the
active segment fills with its own contextual colour (`income` green or `expense` red) with Ledger
Paper text. OUT is the default-active segment — expense is the more frequent action, per the approved
concept.

### stamp button
A `radius.stamp` rectangle filled with the ink-press gradient matching whichever side of the toggle is
active, Ledger Paper lettering. Links to `/(tabs)/transactions/create` regardless of toggle state —
that screen has no real form yet to receive a direction, so both sides of the toggle lead to the same
placeholder. Built with `expo-linear-gradient`'s `<LinearGradient>` wrapped by `Link`'s `asChild` (a
single `Pressable` child, confirmed from `expo-router`'s own source rather than assumed, matching
AGENTS.md's rule about this SDK's docs being stale).

### postmark category glyph
Each category icon (groceries, transport, salary) is a `react-native-svg` `<Path>`/`<Circle>` glyph,
~24×24, single ~1.7 stroke width, Iron-Gall Ink, ported faithfully from the approved mockup's line-art
placeholders. It sits inside a thin dashed-stroke ring (`r=10.5`, `strokeDasharray="3 4"`) — the
"postmark" treatment — at the same stroke width as the glyph itself, since the brief calls for "a
single" stroke weight across the whole icon, ring included. The ring and glyph set now live in
`src/components/icons/` (`PostmarkIcon.tsx`, `Glyphs.tsx`) as a shared definition, not copied per
screen: the tab bar (five new nav glyphs — ledger book, torn receipt, billfold, ink-ring target, linked
rings) uses the exact same component, with its active tab rendered as the ring turning into a solid
ink-filled badge rather than a colour tint, since a colour swap alone would break the paper/stamp
metaphor — it reuses the ink-press logic already established for the dashboard's stamp buttons.

### balance tape *(replaces the old balance figure's standalone position)*
A small strip styled like a piece of tape tacked onto the ledger below the hero ticket: sunken-paper
fill, dashed top/bottom borders standing in for perforation, a slight rotation. Holds the net balance
figure people used to find in the stat-tile.

### Ledger Book *(new)*
A tap-to-expand row (`▸`/`▾` plus a hint line, plain `useState`, no gesture library) that reveals the
wallet cards, budget thermometers, and recent transactions beneath it when open. The three sections'
own data and structure are unchanged from before this pass; only their being tucked behind a fold, and
their colours, are new.

### wallet-card
Ledger Paper card, `radius.md`, 1px `border` hairline (no shadow). Wallet name in `body` `textMuted`,
balance in `headingSemibold` `text`.

### budget-thermometer *(replaces budget-meter)*
`surfaceSunken` background at `radius.md`. Category name + percentage in `bodyMedium`, both `text`
(never the status hue as text — see "One rule carried over"). An 8px track beneath, filled to the used
percentage in the status hue (`healthy`/`warning`/`exceeded` from `budgetHealth()`), track background
a low-alpha ink. A `body` `textMuted` line below showing `$used of $limit`.

### transaction-row
Ledger Paper row, `radius.md`, 1px `border` hairline. Label in `body` `text`; amount in `bodyMedium`,
coloured `expense` (Stamp Red) or `income` (Ledger Green) — legitimate here because the `+`/`-` sign
is also shown, so colour is a supplement, never the sole channel (same discipline as the old
transaction-row, now symmetric: both directions have a real accent, where only income did before).

### status-pill *(existing `StatusChip`, re-tokened)*
`surfaceSunken` background, `radius.full`, label always `text`, with a leading coloured dot carrying
the state hue: `PENDING` → `brassDeep`, `ACTIVE` → `income` green, `DEACTIVATED` → `textMuted`.

### button-primary / button-secondary *(existing `Button`, re-tokened, shape untouched)*
Primary: `radius.full` pill, Iron-Gall Ink fill, Ledger Paper lettering — see the "no universal
primary" note in Colors for why a neutral fill is ink rather than an invented tint. Secondary:
transparent fill, ink text and 1px ink border. Out of scope for the shape change (see "Shapes").

### text-input *(existing `TextField`, re-tokened)*
Ledger Paper field, **1px Faded Ink border** (not the decorative `border` hairline — see Colors),
`radius.md`, ink text, Faded Ink placeholder. Focus: 2px ink border. Error: 1px `expense`-toned border,
helper text in the same tone.

### banner *(existing `Banner`, re-tokened)*
Left-border accent card, `radius.md`, tone-coloured background + a 4px tone-coloured left edge,
message in the tone's foreground colour. Unchanged in shape — only the tone palette
(`success`/`error`/`info`) moved.

### screen chrome *(existing `Screen`, tab bar)*
Kraft Board page background (not Ledger Paper — Kraft Board is the desk, Ledger Paper is what sits on
it). `margin-mobile` (20px) horizontal padding. Tab bar: Ledger Paper background, 1px `border` top
hairline, ink active / Faded Ink inactive tint, Courier Prime header titles.

## Do's and Don'ts

**DO**
- Keep monetary figures in `text` (Iron-Gall Ink) — they're information, not decoration, except the
  dashboard's own placeholder amount, which is deliberately `textMuted` to read as empty.
- Frame every card with a `border` hairline instead of a shadow; draw the one exception (the ticket's
  torn edge) as SVG geometry, not a shadow.
- Use `income`/`expense` as the only two contextual "this is clickable and it means something
  directional" signals; fall back to ink for anything generic.
- Render budget/status hues as fill + dot/label, never as the only distinguishing text colour.
- Reserve raw Brass Coin for fills, large numerals, and icon strokes; use `brassDeep` anywhere it
  would be small text.

**DON'T**
- Put `sageSoft` or `brassSoft` on text or a small control.
- Add a drop-shadow to anything resting on the page.
- Invent a tinted fill for a generic/neutral action — default to ink text on paper or a bordered
  background instead.
- Set a heading in PT Serif or a monetary figure outside Courier Prime.
- Assume the shared `Button` component follows the new stamp-rectangle shape — it doesn't yet; that's
  a separate decision.
- Reach for the bilingual toggle, the shop components, or the desktop grid — dropped before this pass
  and still out of scope.
