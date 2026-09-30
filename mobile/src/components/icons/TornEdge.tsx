/**
 * Torn/deckle top edge — extracted from the Dashboard hero ticket's original
 * private `TornEdge` (`app/(tabs)/index.tsx`), so other torn-edge call sites
 * share one component instead of a second copy. `./tornEdgePath.ts`'s
 * `buildTornEdgePath` still owns the zigzag math; this component only wraps
 * it in the `react-native-svg` strip that renders it. (That helper was
 * renamed from `tornEdge.ts` when this file was added beside it — the two
 * names differed only in casing, which broke module resolution on this
 * project's case-insensitive filesystem; see `tornEdgePath.ts`'s own
 * doc-comment.)
 *
 * Defaults (`height=14`, `teeth=16`) and the `320` reference width used to
 * build the path are exactly the Dashboard's original hard-coded constants
 * (`TORN_EDGE_WIDTH`/`TORN_EDGE_HEIGHT`/`TORN_EDGE_TEETH`) — a bare
 * `<TornEdge />` renders byte-identical output to the pre-extraction
 * private component. `width` is deliberately not a prop: like the original,
 * this always renders at `width="100%"` with `preserveAspectRatio="none"`,
 * so the SVG stretches to fill its parent regardless of the coordinate
 * space the teeth are computed in.
 */
import Svg, { Path } from 'react-native-svg';

import { color } from '../../theme/tokens';
import { buildTornEdgePath } from './tornEdgePath';

/** Reference width the zigzag path is computed in before being stretched to
 * 100% — matches the Dashboard's original `TORN_EDGE_WIDTH`. Not a prop: no
 * call site has ever needed to vary it. */
const REFERENCE_WIDTH = 320;

type TornEdgeProps = {
  fill?: string;
  height?: number;
  teeth?: number;
};

export function TornEdge({ fill = color.surface, height = 14, teeth = 16 }: TornEdgeProps) {
  const d = buildTornEdgePath(REFERENCE_WIDTH, height, teeth);

  return (
    <Svg
      width="100%"
      height={height}
      viewBox={`0 0 ${REFERENCE_WIDTH} ${height}`}
      preserveAspectRatio="none"
    >
      <Path d={d} fill={fill} />
    </Svg>
  );
}
