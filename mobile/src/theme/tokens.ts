/**
 * Design tokens.
 *
 * The `budget` group is not decoration — SRS §4 UXR-02 and SDS §3.1 require
 * budget health to be conveyed by colour alone, without reading raw numbers:
 * 🟢 healthy · 🟡 warning · 🔴 exceeded. Anything rendering budget state must
 * source its colour from here so the three states stay visually distinct.
 */

export const color = {
  // Brand / interactive
  primary: '#2563eb',
  primaryText: '#ffffff',

  // Surfaces
  bg: '#f8fafc',
  surface: '#ffffff',
  surfaceInverse: '#1e293b',

  // Text
  text: '#0f172a',
  textMuted: '#64748b',
  textInverse: '#ffffff',
  textOnInverse: '#94a3b8',

  // Lines
  border: '#cbd5e1',

  // Budget health — UXR-02 / SDS §3.1. Do not substitute ad-hoc hex values.
  budget: {
    healthy: { fg: '#166534', bg: '#dcfce7', accent: '#16a34a' },
    warning: { fg: '#92400e', bg: '#fef3c7', accent: '#d97706' },
    exceeded: { fg: '#991b1b', bg: '#fee2e2', accent: '#dc2626' },
  },

  // Feedback banners
  success: { fg: '#166534', bg: '#dcfce7', accent: '#16a34a' },
  error: { fg: '#991b1b', bg: '#fee2e2', accent: '#dc2626' },
  info: { fg: '#1e40af', bg: '#dbeafe', accent: '#2563eb' },

  // Prototype chrome — deliberately loud so demo data is never mistaken for real
  prototype: { fg: '#92400e', bg: '#fef3c7', border: '#d97706' },

  // User / invitation status chips (SDS §2.4.1)
  status: {
    PENDING: { fg: '#92400e', bg: '#fef3c7' },
    ACTIVE: { fg: '#166534', bg: '#dcfce7' },
    DEACTIVATED: { fg: '#475569', bg: '#e2e8f0' },
  },
} as const;

export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 20, xxl: 24 } as const;

export const radius = { sm: 4, md: 8, lg: 12 } as const;

export const font = {
  size: { xs: 11, sm: 12, body: 14, md: 15, lg: 16, xl: 18, title: 22, hero: 32 },
  weight: { regular: '400', medium: '500', semibold: '600', bold: '700' },
} as const;

/** Budget health from a percentage used. Thresholds per SDS §3.2 (80% warning). */
export function budgetHealth(percentUsed: number): 'healthy' | 'warning' | 'exceeded' {
  if (percentUsed >= 100) return 'exceeded';
  if (percentUsed >= 80) return 'warning';
  return 'healthy';
}
