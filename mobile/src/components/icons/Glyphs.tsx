/**
 * Postmark glyph set — the line-art drawn inside a `PostmarkIcon` ring.
 *
 * Same technique throughout, ported faithfully from the approved mockup's
 * line-art: viewBox `0 0 24 24`, `strokeWidth={1.7}` (dropping to `1.3` for
 * fine interior detail lines — ledger rules, receipt lines), round caps and
 * joins, `fill="none"` unless noted (a clasp/center dot is filled solid).
 *
 * Every glyph takes the `color` it should draw itself in, rather than
 * hardcoding `color.text` the way the original three (Groceries/Transport/
 * Salary) used to — the same glyph now has to render in either the muted
 * inactive tone or `color.surface` once stamped active inside a
 * `PostmarkIcon` (see that component), so the color has to come from the
 * caller.
 */
import { Circle, Path } from 'react-native-svg';

type GlyphProps = { color: string };

// ---- Dashboard category glyphs (hero ticket, DEMO categories) ----------

export function GroceriesGlyph({ color }: GlyphProps) {
  return (
    <>
      <Path
        d="M5 9h14l-1.5 10a2 2 0 01-2 1.8H8.5a2 2 0 01-2-1.8Z"
        fill="none"
        stroke={color}
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <Path
        d="M8 9V7a4 4 0 018 0v2"
        fill="none"
        stroke={color}
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </>
  );
}

export function TransportGlyph({ color }: GlyphProps) {
  return (
    <>
      <Circle cx={12} cy={12} r={6} fill="none" stroke={color} strokeWidth={1.7} />
      <Path d="M12 6v12M6 12h12" fill="none" stroke={color} strokeWidth={1.7} strokeLinecap="round" />
    </>
  );
}

export function SalaryGlyph({ color }: GlyphProps) {
  return (
    <Path
      d="M8 4v16M8 4h11l4 4M8 12h15"
      fill="none"
      stroke={color}
      strokeWidth={1.7}
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  );
}

/** Rent — a roofline over a doorway, ported from the approved summary.html
 * mockup's `#glyphRent` (the one mockup file with all four of these). */
export function RentGlyph({ color }: GlyphProps) {
  return (
    <>
      <Path
        d="M4 12L12 5L20 12"
        fill="none"
        stroke={color}
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <Path
        d="M6 11V19H18V11"
        fill="none"
        stroke={color}
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <Path
        d="M10 19V14H14V19"
        fill="none"
        stroke={color}
        strokeWidth={1.3}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </>
  );
}

/** Utilities — a lightning bolt, ported from `#glyphUtilities`. */
export function UtilitiesGlyph({ color }: GlyphProps) {
  return (
    <Path
      d="M13 3L6 14H11L10 21L18 9H13L14 3Z"
      fill="none"
      stroke={color}
      strokeWidth={1.7}
      strokeLinejoin="round"
    />
  );
}

/** Entertainment — a film strip, ported from `#glyphEntertainment`. */
export function EntertainmentGlyph({ color }: GlyphProps) {
  return (
    <>
      <Path
        d="M4,7 L20,7 L20,9.6 A2.9,2.9 0 0 0 20,15.4 L20,18 L4,18 L4,15.4 A2.9,2.9 0 0 0 4,9.6 Z"
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinejoin="round"
      />
      <Path
        d="M12 7.5V17.5"
        fill="none"
        stroke={color}
        strokeWidth={1.2}
        strokeDasharray="1.6 2"
        strokeLinecap="round"
      />
    </>
  );
}

/** Dining — a fork and spoon, ported from `#glyphDining` (matches "Dining
 * Out", the category name used elsewhere in this app's demo data). */
export function DiningGlyph({ color }: GlyphProps) {
  return (
    <>
      <Path
        d="M6,3 V9 M9,3 V9 M12,3 V9 M9,9 V21"
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <Path
        d="M17,3 C19.2,3 19.4,7.6 17,9.8 V21"
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </>
  );
}

// ---- Tab-bar nav glyphs --------------------------------------------------

/** Dashboard — an open ledger book. */
export function DashboardGlyph({ color }: GlyphProps) {
  return (
    <>
      <Path
        d="M12 7L4 5.2V16.8L12 18.5L20 16.8V5.2L12 7Z"
        fill="none"
        stroke={color}
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <Path
        d="M12 7V18.5"
        fill="none"
        stroke={color}
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <Path
        d="M6.3 8.6L10.3 9.4M6.3 11.3L10.3 12.1M6.3 14L10 14.7"
        fill="none"
        stroke={color}
        strokeWidth={1.3}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </>
  );
}

/** Transactions — a torn receipt. */
export function TransactionsGlyph({ color }: GlyphProps) {
  return (
    <>
      <Path
        d="M8 4H16V16.5L14.6 18.3L13.2 16.6L11.8 18.3L10.4 16.6L9 18.3L8 16.8V4Z"
        fill="none"
        stroke={color}
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <Path
        d="M10 7.5H14M10 10.2H14M10 12.9H13"
        fill="none"
        stroke={color}
        strokeWidth={1.3}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </>
  );
}

/** Wallets — a folded billfold. The clasp dot is filled, not stroked. */
export function WalletsGlyph({ color }: GlyphProps) {
  return (
    <>
      <Path
        d="M4 8a2 2 0 012-2h12a2 2 0 012 2v9a2 2 0 01-2 2H6a2 2 0 01-2-2Z"
        fill="none"
        stroke={color}
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <Path
        d="M4 8.3L12 11.8L20 8.3"
        fill="none"
        stroke={color}
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <Circle cx={16.5} cy={13} r={1.1} fill={color} stroke="none" />
    </>
  );
}

/** Budgets — a hand-drawn ink-ring target. The center dot is filled, not stroked. */
export function BudgetsGlyph({ color }: GlyphProps) {
  return (
    <>
      <Circle cx={12} cy={12} r={8} fill="none" stroke={color} strokeWidth={1.7} strokeDasharray="2.5 2.5" />
      <Circle cx={12} cy={12} r={4.8} fill="none" stroke={color} strokeWidth={1.7} />
      <Circle cx={12} cy={12} r={1.4} fill={color} stroke="none" />
    </>
  );
}

/** Family — two linked rings. */
export function FamilyGlyph({ color }: GlyphProps) {
  return (
    <>
      <Circle cx={9.3} cy={12} r={5.8} fill="none" stroke={color} strokeWidth={1.7} />
      <Circle cx={14.7} cy={12} r={5.8} fill="none" stroke={color} strokeWidth={1.7} />
    </>
  );
}
