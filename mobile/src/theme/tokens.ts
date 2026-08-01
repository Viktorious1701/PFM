/**
 * Design tokens — "Sky & Sedge", ported and re-tokened for personal finance.
 * See ../../DESIGN.md for the full rationale, including the one place this
 * port reinterprets the source (budget-health colour + label, not fill alone).
 *
 * The `budget` group is not decoration — SRS §4 UXR-02 and SDS §3.1 require
 * budget health to be conveyed by colour, without reading raw numbers:
 * 🟢 healthy · 🟡 warning · 🔴 exceeded. Anything rendering budget state must
 * source its colour from here so the three states stay visually distinct.
 */

export const color = {
  // Brand / interactive — DESIGN.md "Colors": sky-deep is primary, sage-deep secondary.
  primary: '#4C6577', // sky-deep
  primaryHover: '#3D5464',
  primaryText: '#FFFFFF',
  secondary: '#5E6F4B', // sage-deep

  // Surfaces
  bg: '#FBF9F4', // bg-page — cream canvas, never behind text or a filled card
  surface: '#FFFFFF',
  surfaceSunken: '#F1EDE4',
  surfaceInverse: '#4C6577', // sky-deep, used for the stat-tile fill

  // Text
  text: '#3B4147', // ink
  textMuted: '#6B7178', // ink-muted — also the interactive border colour, see below
  captionDeep: '#71736B',
  textInverse: '#FFFFFF',
  textOnInverse: 'rgba(255,255,255,0.78)',

  // Lines
  border: '#E4DFD3', // hairline — decorative depth mechanism, never an interactive edge
  borderInteractive: '#6B7178', // ink-muted — WCAG 1.4.11 needs >=3:1 on a field's edge

  // Decorative-only accents — DESIGN.md bars these from text/small controls
  skySoft: '#7E9AAB',
  sageSoft: '#8B9B7A',

  // Budget health — UXR-02 / SDS §3.1. Do not substitute ad-hoc hex values.
  budget: {
    healthy: { fg: '#4F7A52', bg: '#F1EDE4', accent: '#4F7A52' },
    warning: { fg: '#96681F', bg: '#F1EDE4', accent: '#96681F' },
    exceeded: { fg: '#A85248', bg: '#F1EDE4', accent: '#A85248' },
  },

  // Feedback banners
  success: { fg: '#4F7A52', bg: '#EEF3EC', accent: '#4F7A52' },
  error: { fg: '#A85248', bg: '#F7ECEA', accent: '#A85248' },
  info: { fg: '#4C6577', bg: '#EAF0F3', accent: '#4C6577' },

  // Prototype chrome — deliberately loud so demo data is never mistaken for real
  prototype: { fg: '#96681F', bg: '#FBF0DC', border: '#96681F' },

  // User / invitation status chips (SDS §2.4.1)
  status: {
    PENDING: { fg: '#3B4147', bg: '#F1EDE4', dot: '#96681F' },
    ACTIVE: { fg: '#3B4147', bg: '#F1EDE4', dot: '#4F7A52' },
    DEACTIVATED: { fg: '#3B4147', bg: '#F1EDE4', dot: '#6B7178' },
  },
} as const;

export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 20, xxl: 24, xxxl: 32 } as const;

export const radius = { none: 0, sm: 2, md: 6, lg: 12, full: 9999 } as const;

/**
 * Two families, distinct roles that never swap (DESIGN.md "Typography"):
 * Lora for headings and the balance hero figure, Inter for everything else.
 */
export const font = {
  family: {
    heading: 'Lora_700Bold',
    headingSemibold: 'Lora_600SemiBold',
    body: 'Inter_400Regular',
    bodyMedium: 'Inter_500Medium',
  },
  size: { xs: 12, sm: 13, body: 15, md: 15, lg: 17, xl: 18, title: 28, hero: 34 },
  weight: { regular: '400', medium: '500', semibold: '600', bold: '700' },
} as const;

/**
 * Named text styles so a screen picks a role, not a family — DESIGN.md forbids
 * a heading in Inter or a monetary figure in Lora.
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
  // "Elevation & Depth". Nothing resting on the page uses this.
  overlay: {
    shadowColor: '#3B4147',
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
