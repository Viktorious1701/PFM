/**
 * Tokens for the UI that sits on top of the moonlit scene. Panels are
 * translucent night-blue so the grass and moon stay visible behind them;
 * type is Rajdhani — thin, geometric, uppercase labels with wide tracking.
 */
export const moon = {
  panel: 'rgba(12,23,39,0.78)',
  panelBorder: 'rgba(223,232,251,0.14)',
  hairline: 'rgba(223,232,251,0.1)',
  ink: '#eef3ff',
  inkSoft: 'rgba(238,243,255,0.78)',
  muted: 'rgba(223,232,251,0.55)',
  track: 'rgba(223,232,251,0.08)',
  income: '#6FE3C9',
  expense: '#FF9B9B',
  danger: '#FF9B9B',
  field: 'rgba(6,13,24,0.6)',
  fieldBorder: 'rgba(223,232,251,0.22)',
  focus: '#a9c8ff',
} as const;

/** Expense-category hues, in fixed order (validated against #0e1a2b,
 * worst adjacent CVD ΔE 8.4). A category beyond the top five folds into
 * "Other", which is neutral gray — never a sixth generated hue. */
export const CATEGORY_HUES = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181'] as const;
export const OTHER_HUE = '#7c8799';

export const font = {
  light: 'Rajdhani_300Light',
  regular: 'Rajdhani_400Regular',
  medium: 'Rajdhani_500Medium',
  semibold: 'Rajdhani_600SemiBold',
  bold: 'Rajdhani_700Bold',
} as const;
