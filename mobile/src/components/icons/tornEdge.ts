/**
 * Builds an SVG path string for a zigzag "torn paper" edge.
 *
 * Extracted from the Dashboard hero ticket (`app/(tabs)/index.tsx`'s
 * `TornEdge`), which still owns the one place this is actually drawn. Shared
 * here so other torn/deckle-edge motifs can reuse the exact same math instead
 * of a second copy — though note this generator is tuned for a wide, thin
 * strip; it is not a fit for a small square icon (see `Glyphs.tsx`'s
 * `TransactionsGlyph`, which hand-draws its own small torn-receipt edge
 * rather than forcing this helper into a 24×24 viewBox).
 */
export function buildTornEdgePath(width: number, height: number, teeth: number): string {
  const step = width / teeth;
  const points = [`M0,${height}`, 'L0,0'];
  for (let i = 1; i <= teeth; i++) {
    const x = i * step;
    const y = i % 2 === 0 ? 0 : height - 2;
    points.push(`L${x},${y}`);
  }
  points.push(`L${width},${height}`, 'Z');
  return points.join(' ');
}
