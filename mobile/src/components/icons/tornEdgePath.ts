/**
 * Builds an SVG path string for a zigzag "torn paper" edge.
 *
 * Renamed from `tornEdge.ts` (this file's original name) when `TornEdge.tsx`
 * was added beside it — the two names differed only in casing, which this
 * project's actual filesystem (an NTFS drive mounted into WSL2 at
 * `/mnt/d`) treats as one path, breaking TypeScript module resolution
 * (`tsc` matched the component import to this file instead, case-
 * insensitively). This file keeps owning the path-string math; the
 * `TornEdge` component that renders it now lives in `./TornEdge.tsx`.
 *
 * Tuned for a wide, thin strip; not a fit for a small square icon (see
 * `Glyphs.tsx`'s `TransactionsGlyph`, which hand-draws its own small
 * torn-receipt edge rather than forcing this helper into a 24×24 viewBox).
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
