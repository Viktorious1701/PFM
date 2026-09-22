/**
 * "Postmark" icon badge — a dashed-ring stamp drawn around a glyph.
 *
 * Extracted from the Dashboard hero ticket's original inline `Postmark`
 * (DESIGN.md "postmark category glyph") so the tab bar can reuse the exact
 * same ring/badge definition instead of a second copy. The glyph itself is
 * always the caller's `children` — this component only ever draws the ring.
 *
 * Two rendering states, driven by `active`:
 *  - **inactive** (default) — the Dashboard's original, unchanged look: a
 *    thin dashed ring, `fill="none"`. The ring's stroke color is
 *    `inactiveColor`, which defaults to `color.text` (Iron-Gall Ink) because
 *    that is what the Dashboard's always-shown category row has always used
 *    — it has no active/inactive concept of its own, so the default has to
 *    reproduce its exact prior appearance with zero call-site changes beyond
 *    the glyph now taking an explicit `color` prop (see `Glyphs.tsx`). The
 *    tab bar, which *does* have an inactive state, passes `color.textMuted`
 *    explicitly to match `tabBarInactiveTintColor`.
 *  - **active** — the ring becomes a solid Iron-Gall Ink fill, no dash, no
 *    stroke: a rubber stamp freshly pressed into the paper. The glyph is
 *    expected to be drawn in a light color (`color.surface`) by the caller
 *    so it reads as a light mark stamped into dark ink.
 */
import type { ReactNode } from 'react';
import Svg, { Circle } from 'react-native-svg';

import { color } from '../../theme/tokens';

const VIEWBOX = '0 0 24 24';
const RING_CX = 12;
const RING_CY = 12;
const RING_RADIUS = 10.5;
const RING_STROKE_WIDTH = 1.2;
const RING_DASH = '3 4';

type PostmarkIconProps = {
  /** Renders the ring as a solid stamped fill instead of a dashed outline. Defaults to `false`. */
  active?: boolean;
  /** On-screen box size in px. Defaults to 44 (the Dashboard's original size). The tab bar passes a smaller `size`. The internal viewBox is always `0 0 24 24`, so this only scales the rendered box. */
  size?: number;
  /**
   * Ring stroke color when `active` is `false`. Defaults to `color.text`,
   * reproducing the Dashboard's original always-on look. Ignored when
   * `active` — the stamped ring is always solid `color.text` regardless of
   * what is passed here.
   */
  inactiveColor?: string;
  children: ReactNode;
};

export function PostmarkIcon({
  active = false,
  size = 44,
  inactiveColor = color.text,
  children,
}: PostmarkIconProps) {
  return (
    <Svg width={size} height={size} viewBox={VIEWBOX}>
      {active ? (
        <Circle cx={RING_CX} cy={RING_CY} r={RING_RADIUS} fill={color.text} stroke="none" />
      ) : (
        <Circle
          cx={RING_CX}
          cy={RING_CY}
          r={RING_RADIUS}
          fill="none"
          stroke={inactiveColor}
          strokeWidth={RING_STROKE_WIDTH}
          strokeDasharray={RING_DASH}
        />
      )}
      {children}
    </Svg>
  );
}
