/**
 * Design tokens — "Cash & Carry", a tactile paper-ledger/receipt-stamp system.
 * Replaces "Sky & Sedge" wholesale (approved after a 4-mockup review — see
 * ../../DESIGN.md "What this replaces, and why"; the old palette/rationale is
 * not deleted from history, only from this file — `git log -- DESIGN.md` and
 * `git show <sha>:mobile/src/theme/tokens.ts` recover it).
 *
 * The `budget` group is not decoration — SRS §4 UXR-02 and SDS §3.1 require
 * budget health to be conveyed by colour, without reading raw numbers:
 * 🟢 healthy · 🟡 warning · 🔴 exceeded. Anything rendering budget state must
 * source its colour from here so the three states stay visually distinct.
 * DESIGN.md's "One rule carried over" section explains why the label and
 * percentage text stay `ink` regardless of state — colour is never the only
 * channel, here or anywhere else in this file.
 */

export const color = {
  // Brand / interactive — DESIGN.md "Colors": there is no universal primary
  // hue any more (contrast the old sky-deep). `primary`/`secondary` are the
  // *generic/neutral* action colours — a plain "Cancel," a settings link, a
  // form submit that isn't itself income or expense — and both resolve to
  // Iron-Gall Ink, never an invented tint. `primary` is the one case where
  // ink is used as a *fill* rather than text-on-paper: the shared `Button`
  // component's primary variant is a solid pill, and an ink-filled pill with
  // Ledger Paper text reads as a rubber ink stamp, which is in-theme rather
  // than a contradiction of the "no tinted fill" rule (ink is the palette's
  // own neutral, not a brand tint). `secondary` keeps the literal text+border
  // treatment the rule describes.
  primary: '#2B2420', // Iron-Gall Ink
  primaryHover: '#463C33', // lighter ink, for a pressed/hover fill if ever wired
  primaryText: '#FBF3E3', // Ledger Paper — text on an ink fill
  secondary: '#2B2420', // Iron-Gall Ink — neutral outline/text action

  // Surfaces
  bg: '#E4D5B7', // Kraft Board — the desk/page background, never behind text or a filled card
  surface: '#FBF3E3', // Ledger Paper — every card
  surfaceSunken: '#F0E4C8', // a duller, sunken paper tone — status-pill field, disabled fill
  surfaceInverse: '#2B2420', // Iron-Gall Ink. Unused since the dashboard rebuild dropped the old
  // slate stat-tile for the ticket hero, but kept so the exported shape holds.

  // Text
  text: '#2B2420', // Iron-Gall Ink
  textMuted: '#8A7A63', // Faded Ink — also the interactive border colour, see below
  captionDeep: '#6B5B45', // reserved third text tier, unused today (same status as before the port)
  textInverse: '#FBF3E3', // Ledger Paper
  textOnInverse: 'rgba(251,243,227,0.78)',

  // Lines
  border: '#D8C79C', // hairline — decorative depth mechanism, never an interactive edge.
  // ~1.5:1 against `surface`, deliberately faint — see borderInteractive below.
  borderInteractive: '#8A7A63', // Faded Ink — ~3.8:1 against `surface`, clears WCAG 1.4.11's
  // >=3:1 non-text contrast floor on a field's edge (verified, not eyeballed).

  // Decorative-only accents — pale washes, barred from text/small controls.
  // `skySoft` is retired outright rather than re-tokened: "sky" has no referent
  // left in this palette, and nothing in the app imported that key (checked
  // before renaming). `brassSoft` takes its slot as a pale wash of Brass Coin.
  sageSoft: '#B7C9B8', // pale Ledger Green wash
  brassSoft: '#E6D3A3', // pale Brass Coin wash — replaces `skySoft`

  // Income / expense — the two contextual accents that replace the old single
  // "primary" brand hue for anything that IS income- or expense-specific
  // (the dashboard's stamp toggle/button, transaction amounts). Never used
  // for a generic/neutral action — see `primary`/`secondary` above.
  income: '#2E5339', // Ledger Green
  expense: '#8A3324', // Stamp Red

  // Brass Coin at full saturation is a fill/large-numeral/icon-stroke colour
  // only — at ~2.75:1 on Ledger Paper it fails WCAG AA for small text. This
  // deeper ink is the stand-in wherever the "warning/attention" hue is needed
  // as text or a small graphic (a status dot, the prototype strip) instead.
  brassDeep: '#7A5518',

  // Budget health — UXR-02 / SDS §3.1. Do not substitute ad-hoc hex values.
  // `accent` is the fill colour (large area — raw Brass Coin is fine here);
  // `fg` is reserved for text/small graphics, so `warning` uses `brassDeep`.
  budget: {
    healthy: { fg: '#2E5339', bg: '#F0E4C8', accent: '#2E5339' },
    warning: { fg: '#7A5518', bg: '#F0E4C8', accent: '#C08A2E' },
    exceeded: { fg: '#8A3324', bg: '#F0E4C8', accent: '#8A3324' },
  },

  // Feedback banners
  success: { fg: '#2E5339', bg: '#E6ECE1', accent: '#2E5339' },
  error: { fg: '#8A3324', bg: '#F2E1DA', accent: '#8A3324' },
  info: { fg: '#2B2420', bg: '#EDE6D6', accent: '#2B2420' }, // ink, so an informational
  // banner reads as part of the neutral voice, not a fourth accent — same
  // relationship the old palette kept between `info` and `sky-deep`.

  // Prototype chrome — deliberately loud so demo data is never mistaken for
  // real. Uses `brassDeep`, not raw Brass Coin, because the banner's own
  // label renders at `font.size.xs` — exactly the small-text case Brass Coin
  // fails contrast on.
  prototype: { fg: '#7A5518', bg: '#F5E7C4', border: '#7A5518' },

  // User / invitation status chips (SDS §2.4.1)
  status: {
    PENDING: { fg: '#2B2420', bg: '#F0E4C8', dot: '#7A5518' },
    ACTIVE: { fg: '#2B2420', bg: '#F0E4C8', dot: '#2E5339' },
    DEACTIVATED: { fg: '#2B2420', bg: '#F0E4C8', dot: '#8A7A63' },
  },
} as const;

/**
 * Ink-press gradients for the dashboard's two stamp buttons ONLY — see
 * DESIGN.md "Components → hero ticket." Not used anywhere else; a flat
 * `color.income` / `color.expense` fill is correct everywhere else a
 * contextual colour is needed.
 */
export const gradient = {
  /** OUT / expense — top → bottom. */
  expenseStamp: ['#9C4530', '#6B2A1C'],
  /** IN / income — top → bottom. */
  incomeStamp: ['#3C6B48', '#1F3B27'],
} as const;

export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 20, xxl: 24, xxxl: 32 } as const;

/**
 * `stamp` is new: the two dashboard stamp buttons use a small-radius rectangle
 * — a "stamped ticket," not a pill — per DESIGN.md "Shapes." Everything else
 * keeps its old meaning; `full` still means a true pill where one is wanted
 * (the shared `Button`, `StatusChip`).
 */
export const radius = { none: 0, sm: 2, md: 6, lg: 12, full: 9999, stamp: 4 } as const;

/**
 * Two families, distinct roles that never swap (DESIGN.md "Typography"):
 * Courier Prime for headings and every money figure — replacing Lora's role
 * exactly; PT Serif for body copy and labels — replacing Inter's role
 * exactly. Neither ships a mid-weight: Courier Prime is 400/700 only, PT
 * Serif is 400/700 only (confirmed from the installed packages' own
 * `index.d.ts`, not assumed), so `headingSemibold` and `bodyMedium` collapse
 * onto the Bold cut of their family rather than a true semibold/medium.
 */
export const font = {
  family: {
    heading: 'CourierPrime_700Bold',
    headingSemibold: 'CourierPrime_700Bold', // no 600 cut exists — collapsed onto Bold
    body: 'PTSerif_400Regular',
    bodyMedium: 'PTSerif_700Bold', // no 500 cut exists — collapsed onto Bold
    bodyItalic: 'PTSerif_400Regular_Italic', // PT Serif's italic — used sparingly for flavour text
  },
  size: { xs: 12, sm: 13, body: 15, md: 15, lg: 17, xl: 18, title: 28, hero: 34 },
  weight: { regular: '400', medium: '500', semibold: '600', bold: '700' },
} as const;

/**
 * Named text styles so a screen picks a role, not a family — DESIGN.md forbids
 * a heading in PT Serif or a monetary figure outside Courier Prime.
 */
export const textStyle = {
  hero: { fontFamily: font.family.heading, fontSize: font.size.hero, color: color.text },
  h1: { fontFamily: font.family.heading, fontSize: font.size.title, color: color.text },
  h2: { fontFamily: font.family.headingSemibold, fontSize: 22, color: color.text },
  h3: { fontFamily: font.family.headingSemibold, fontSize: font.size.xl, color: color.text },
  bodyLg: { fontFamily: font.family.body, fontSize: font.size.lg, color: color.text },
  body: { fontFamily: font.family.body, fontSize: font.size.body, color: color.text },
  caption: { fontFamily: font.family.bodyMedium, fontSize: font.size.sm, color: color.textMuted },
} as const;

export const shadow = {
  // Reserved for transient overlays only (a modal, a dropdown) — DESIGN.md
  // "Elevation & Depth" keeps the flat, hairline-and-whitespace depth model.
  // The hero ticket's torn edge is drawn as SVG geometry, not a shadow.
  overlay: {
    shadowColor: '#2B2420',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.18,
    shadowRadius: 24,
    elevation: 8,
  },
} as const;

/** Budget health from a percentage used. Thresholds per SDS §3.2 (80% warning). */
export function budgetHealth(percentUsed: number): 'healthy' | 'warning' | 'exceeded' {
  if (percentUsed >= 100) return 'exceeded';
  if (percentUsed >= 80) return 'warning';
  return 'healthy';
}
