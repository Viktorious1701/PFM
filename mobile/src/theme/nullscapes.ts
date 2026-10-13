/**
 * "Nullscapes" design tokens — the dark, icy-blue, Space Grotesk component
 * language validated in the design canvas's `Components.dc.html` swatch
 * sheet (buttons, wallet cards, transaction rows, budget bars). Promoted
 * out of the Dashboard screen (where it first shipped) once a second, third,
 * and fourth screen needed the same colors/type — one stable, module-level
 * object instead of one copy per screen.
 *
 * This is the app's committed visual identity, replacing "Cash & Carry"
 * (`./tokens.ts`) wholesale. `tokens.ts`'s `budgetHealth()` tier-derivation
 * logic is still reused (pure function, no color baked in) — only the hues
 * it's rendered with move here.
 */

export const ns = {
  card: '#10141B',
  cardBorder: 'rgba(111,227,201,0.18)',
  hairline: 'rgba(234,246,255,0.12)',
  ink: '#F4FBFF',
  inkSoft: '#EAF6FF',
  muted: 'rgba(234,246,255,0.5)',
  mutedFaint: 'rgba(234,246,255,0.35)',
  mint: '#6FE3C9',
  mintBorder: 'rgba(111,227,201,0.4)',
  danger: '#FF9B9B',
  dangerStrong: '#FF8080',
  dangerBorder: 'rgba(255,120,120,0.4)',
  warning: '#FFC46E',
  track: 'rgba(255,255,255,0.08)',
  buttonTop: '#2E3542',
  buttonBottom: '#14171C',
  buttonRing: 'rgba(207,243,255,0.25)',
  buttonGlow: 'rgba(174,220,255,0.25)',

  // Chrome — header/tab-bar, matching the validated zoom-traversal mockups
  // exactly ("Glitch-only theme, no Cash & Carry chrome").
  chromeBg: 'rgba(11,14,19,0.9)',
  chromeBorder: 'rgba(111,227,201,0.15)',
  tabActive: '#EAF6FF',
  tabInactive: '#4C5666',
} as const;

export const nsFont = {
  regular: 'SpaceGrotesk_400Regular',
  medium: 'SpaceGrotesk_500Medium',
  semibold: 'SpaceGrotesk_600SemiBold',
  bold: 'SpaceGrotesk_700Bold',
} as const;

/** Budget-health accent mapping — paired with `tokens.ts`'s `budgetHealth()`. */
export const nsBudgetAccent = {
  healthy: ns.mint,
  warning: ns.warning,
  exceeded: ns.dangerStrong,
} as const;
