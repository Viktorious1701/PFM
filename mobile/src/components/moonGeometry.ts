/** The moonlit scene's own coordinate space (the prototype's 1280x720
 * canvas) and where the moon sits in it — shared by the scene and the
 * climax burst so both draw against the same moon. */
export const W = 1280;
export const H = 720;
export const MOON_CX = W * 0.49;
export const MOON_CY = H * 0.5;
export const MOON_R = H * 0.165;

/** Screen placement of the scene for a frame of `w` x `h` px: cover-scaled
 * ("slice"), centered, edges cropped evenly. */
export function coverFit(w: number, h: number) {
  const scale = Math.max(w / W, h / H);
  return { scale, offX: (w - W * scale) / 2, offY: (h - H * scale) / 2 };
}

/** Seeded PRNG (mulberry32) — the prototype's, so blades land in the same
 * places every run. */
export function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export type GrassSpec = {
  seed: number;
  baseY: number;
  count: number;
  minH: number;
  maxH: number;
  minW: number;
  maxW: number;
  leanDeg: number;
  fill: string;
  centerBoost: boolean;
};

/** The three grass layers, far to near — the approved prototype's numbers. */
export const GRASS: readonly GrassSpec[] = [
  { seed: 5, baseY: H * 0.88, count: 220, minH: H * 0.12, maxH: H * 0.3, minW: 7, maxW: 18, leanDeg: 16, fill: '#2c4463', centerBoost: false },
  { seed: 11, baseY: H * 0.98, count: 110, minH: H * 0.32, maxH: H * 0.52, minW: 14, maxW: 34, leanDeg: 18, fill: '#1e3550', centerBoost: false },
  { seed: 47, baseY: H * 1.05, count: 46, minH: H * 0.48, maxH: H * 0.72, minW: 26, maxW: 64, leanDeg: 20, fill: '#14263c', centerBoost: true },
];

export type RawBlade = { x: number; h: number; w: number; tipDX: number; tipY: number; side: number };

/** One period of a layer's blades (i = 0..count-1), which tiles every W.
 * Same math and rand() call order as the prototype's drawGrassLayer,
 * including the unconditional `side` draw. */
export function grassBlades(o: GrassSpec): RawBlade[] {
  const rand = mulberry32(o.seed);
  const spacing = W / o.count;
  const out: RawBlade[] = [];
  for (let i = -1; i <= o.count + 1; i++) {
    const x = i * spacing + (rand() - 0.5) * spacing * 0.9;
    const distFromMoon = Math.abs(x - MOON_CX) / (W * 0.5);
    const boost = o.centerBoost ? Math.max(0, 1 - distFromMoon * 1.8) : 0;
    const h = o.minH + rand() * (o.maxH - o.minH) + boost * (o.maxH * 0.9) * rand();
    const w = o.minW + rand() * (o.maxW - o.minW);
    const lean = (rand() - 0.5) * 2 * o.leanDeg;
    const leanRad = (lean * Math.PI) / 180;
    const side = rand() < 0.5 ? -1 : 1;
    if (i >= 0 && i < o.count) {
      out.push({ x, h, w, tipDX: Math.sin(leanRad) * h, tipY: o.baseY - h * Math.cos(leanRad), side });
    }
  }
  return out;
}
