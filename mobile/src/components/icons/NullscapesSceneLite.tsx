/**
 * "Nullscapes" — low-detail tier, pure `react-native-svg` + Reanimated, no
 * Skia dependency. This IS the low-detail rendering path (see
 * `src/lib/renderTier.ts`) — not a separate stripped-down build, the same
 * visual language `NullscapesSceneRich.tsx` uses, at a lighter weight.
 *
 * Moonlit-grass scene, built and iterated as a standalone HTML/canvas
 * prototype against a set of reference images (not decoded from
 * `Nullscapes-level.gmd` — that data-driven approach was scrapped once it
 * became clear the actual target was a specific illustrated look, not a
 * precise recreation of the level's own placement data). Ported here after
 * the prototype was visually validated:
 * - a medium, fairly uniform royal-blue sky (not nearly-black) with one
 *   smooth halo around the moon — many close gradient stops, no visible
 *   ring banding;
 * - the moon sits low/centered, mostly buried in tall grass rather than
 *   floating clear above a thin band — looking down into dense grass, not
 *   up at open sky;
 * - three real depth bands of individually-placed triangular blades (far
 *   small/pale, mid, near big/dark), packed densely enough to overlap
 *   edge-to-edge, upright with natural per-blade jitter in both directions
 *   (no dominant wind lean);
 * - scattered static particle slivers, no motion of their own;
 * - a periodic grayish-white flash (ramp/hold/fade, long rest between
 *   cycles) during which every blade shows a thin highlight line along its
 *   own face — this is the only animated thing in the scene; the old
 *   continuous breathing pulse, flickering ring-of-blocks, and
 *   suction-particle stream are gone, replaced entirely by this.
 *
 * Also serves as the WEB fallback while Skia/CanvasKit's WASM loads (see
 * `NullscapesScene.tsx`'s host component) — so this file has to stand on
 * its own as a complete, correct illustration, not a placeholder.
 *
 * The `wrap` (boxed, fixed 400x260 aspect-ratio) style path still exists
 * below for a caller that passes no `style` override, but the only actual
 * mount point in this app right now is the full-bleed background — the
 * earlier empty-state boxed illustrations were removed in an earlier stage
 * of the Nullscapes rollout (confirmed via a repo-wide search before this
 * revision; the previous version of this comment was stale on that point).
 */
import { memo, useEffect } from 'react';
import { StyleSheet, View, type ViewStyle } from 'react-native';
import Animated, {
  Easing,
  useAnimatedProps,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withDelay,
  withRepeat,
  withSequence,
  withTiming,
  type SharedValue,
} from 'react-native-reanimated';
import Svg, { Circle, Defs, G, Line, Polygon, RadialGradient, Rect, Stop } from 'react-native-svg';

const AnimatedG = Animated.createAnimatedComponent(G);
const AnimatedLine = Animated.createAnimatedComponent(Line);

export const VIEW_W = 400;
export const VIEW_H = 260;

const SKY_TOP = '#15273F';
const MOON_CORE = '#F7F0D8';
const MOON_MID = '#E9E6D2';
const GRASS_FAR = '#2C4463';
const GRASS_MID = '#1E3550';
const GRASS_NEAR = '#14263C';
const HIGHLIGHT = 'rgba(225,233,247,'; // alpha appended at use site

export const MOON_CX = VIEW_W * 0.49;
export const MOON_CY = VIEW_H * 0.5;
export const MOON_R = VIEW_H * 0.165;

/** Deterministic PRNG (mulberry32) — same field shape every mount. */
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

export type GrassBlade = {
  poly: string;
  hlX1: number;
  hlY1: number;
  hlX2: number;
  hlY2: number;
  fill: string;
};

type GrassLayerOpts = {
  seed: number;
  baseY: number;
  count: number;
  minH: number;
  maxH: number;
  minW: number;
  maxW: number;
  leanDeg: number;
  fill: string;
  centerBoost?: boolean;
  boostAmount?: number;
};

/** Many individually-placed triangular blades (not one zigzag silhouette
 * line) — packed densely enough to overlap, upright with natural per-blade
 * jitter in both directions. Each blade also carries a highlight-line
 * endpoint pair, computed unconditionally for every blade regardless of
 * whether the flash is active: computing it conditionally (only when
 * needed) was tried first and silently shifted every later blade's
 * position whenever the flash's random draw started/stopped firing, since
 * both drew from the same seeded sequence — this is why the geometry below
 * never depends on anything time-varying. */
export function buildGrassLayer(opts: GrassLayerOpts): GrassBlade[] {
  const rand = mulberry32(opts.seed);
  const spacing = VIEW_W / opts.count;
  const boostAmount = opts.boostAmount ?? 0.9;
  const blades: GrassBlade[] = [];
  for (let i = -1; i <= opts.count + 1; i++) {
    const x = i * spacing + (rand() - 0.5) * spacing * 0.9;
    // a few blades near the moon's own x reach a bit taller, so some
    // silhouettes graze the moon's bottom edge
    const distFromMoon = Math.abs(x - MOON_CX) / (VIEW_W * 0.5);
    const boost = opts.centerBoost ? Math.max(0, 1 - distFromMoon * 1.8) : 0;
    const h = opts.minH + rand() * (opts.maxH - opts.minH) + boost * (opts.maxH * boostAmount) * rand();
    const w = opts.minW + rand() * (opts.maxW - opts.minW);
    const lean = (rand() - 0.5) * 2 * opts.leanDeg;
    const leanRad = (lean * Math.PI) / 180;
    const tipX = x + Math.sin(leanRad) * h;
    const tipY = opts.baseY - h * Math.cos(leanRad);
    const side = rand() < 0.5 ? -1 : 1;
    blades.push({
      poly: `${(x - w / 2).toFixed(1)},${opts.baseY.toFixed(1)} ${tipX.toFixed(1)},${tipY.toFixed(1)} ${(x + w / 2).toFixed(1)},${opts.baseY.toFixed(1)}`,
      hlX1: x + side * w * 0.18,
      hlY1: opts.baseY - h * 0.06,
      hlX2: tipX + side * w * 0.06,
      hlY2: tipY + h * 0.08,
      fill: opts.fill,
    });
  }
  return blades;
}

const FAR_BLADES = buildGrassLayer({
  seed: 5, baseY: VIEW_H * 0.88, count: 220,
  minH: VIEW_H * 0.12, maxH: VIEW_H * 0.3, minW: 7, maxW: 18,
  leanDeg: 16, fill: GRASS_FAR,
});
const MID_BLADES = buildGrassLayer({
  seed: 11, baseY: VIEW_H * 0.98, count: 110,
  minH: VIEW_H * 0.32, maxH: VIEW_H * 0.52, minW: 14, maxW: 34,
  leanDeg: 18, fill: GRASS_MID,
});
const NEAR_BLADES = buildGrassLayer({
  seed: 47, baseY: VIEW_H * 1.05, count: 46,
  minH: VIEW_H * 0.48, maxH: VIEW_H * 0.72, minW: 26, maxW: 64,
  leanDeg: 20, fill: GRASS_NEAR, centerBoost: true, boostAmount: 0.35,
});
// Draw order is back-to-front: far first, near last.
const ALL_BLADES: GrassBlade[] = [...FAR_BLADES, ...MID_BLADES, ...NEAR_BLADES];

type Particle = { x: number; y: number; len: number; wid: number; rotDeg: number; opacity: number };

/** Static scattered slivers — no motion of their own, unlike the old
 * suction-particle stream. */
function buildParticles(count: number, seed: number): Particle[] {
  const rand = mulberry32(seed);
  const out: Particle[] = [];
  for (let i = 0; i < count; i++) {
    out.push({
      x: rand() * VIEW_W,
      y: rand() * VIEW_H,
      len: 2.5 + rand() * 6,
      wid: 0.5 + rand() * 0.9,
      rotDeg: rand() * 360,
      opacity: 0.15 + rand() * 0.55,
    });
  }
  return out;
}
const PARTICLES = buildParticles(70, 777);

// ---- the periodic flash: ramp -> hold -> fade -> long rest, looping ----
const CYCLE_MS = 7000;
const RAMP_MS = 180;
const HOLD_MS = 90;
const FADE_MS = 650;
const REST_MS = CYCLE_MS - (RAMP_MS + HOLD_MS + FADE_MS);

// Memoized for the same reason as `NullscapesSceneRich` — see its own
// doc-comment. This is also the Skia web fallback AND the whole app's `low`
// detail tier, so it's mounted exactly as persistently as Rich is.
function NullscapesSceneLiteImpl({
  style,
  tabScale,
}: {
  style?: ViewStyle;
  tabScale?: SharedValue<number>;
}): React.JSX.Element {
  const reduceMotion = useReducedMotion();
  const flash = useSharedValue(0);
  const ownTabScale = useSharedValue(1);
  const scale = tabScale ?? ownTabScale;

  useEffect(() => {
    if (reduceMotion) {
      flash.value = 0;
      return;
    }
    flash.value = withRepeat(
      withSequence(
        withTiming(1, { duration: RAMP_MS, easing: Easing.out(Easing.quad) }),
        withTiming(1, { duration: HOLD_MS }),
        withTiming(0, { duration: FADE_MS, easing: Easing.in(Easing.quad) }),
        withDelay(REST_MS, withTiming(0, { duration: 1 })),
      ),
      -1,
      false,
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reduceMotion]);

  // One shared animated prop reused across every blade's highlight line —
  // the opacity is identical for all of them at any given moment, driven by
  // the same `flash` value, so there's no need for a per-blade hook.
  const highlightProps = useAnimatedProps(() => ({
    opacity: flash.value * 0.5,
  }));

  const flashOverlayStyle = useAnimatedStyle(() => ({ opacity: flash.value * 0.38 }));

  // The cross-tab "camera zoom" (`src/lib/tabCameraScale.ts`). SVG's
  // `transform` attribute has no separate origin concept the way Skia's
  // `Group` does, so "scale about a point" is hand-rolled as the standard
  // translate/scale/translate trick, written as a plain string (never
  // Reanimated's convenience `scale`/`origin` props on
  // `Animated.createAnimatedComponent` — those leak through as invalid
  // literal DOM attributes on web).
  const tabZoomProps = useAnimatedProps(() => ({
    transform: `translate(${MOON_CX} ${MOON_CY}) scale(${scale.value}) translate(${-MOON_CX} ${-MOON_CY})`,
  }));

  // Same full-bleed-vs-boxed split as `NullscapesSceneRich.tsx` — see its
  // doc comment: `styles.wrap`'s own `width:'100%'` + `aspectRatio` would
  // otherwise win over the Dashboard's absolute-fill `style` override on
  // web, collapsing the full-bleed background down to the small boxed size.
  // `StyleSheet.flatten` because react-native-web's `StyleSheet.create`
  // returns an opaque atomic-CSS reference, not a plain object — a raw
  // `style?.position` read silently comes back `undefined`.
  const fullBleed = StyleSheet.flatten(style)?.position === 'absolute';

  return (
    <View
      style={[fullBleed ? styles.fill : styles.wrap, style]}
      pointerEvents="none"
      importantForAccessibility="no-hide-descendants"
    >
      <Svg width="100%" height="100%" viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} preserveAspectRatio="xMidYMid slice">
        <Defs>
          {/* one smooth glow, many closely-spaced stops so it blends
              continuously into the sky with no visible ring edges.
              Deliberately kept small/tight (see the Rect size below) and
              falling off hard past 50% -- this app applies its own
              per-tab camera zoom (`tabZoomProps`, up to ~1.9x) ON TOP OF
              the viewBox-to-viewport "slice" scaling every full-bleed
              instance of this 400x260 design already needs just to cover
              a real (very differently-shaped) screen. Those compound
              multiplicatively into a much higher effective zoom than the
              1x this was validated at in the standalone HTML prototype --
              a halo sized to look right at 1x ends up ballooning to cover
              nearly the whole visible frame at 5x+, washing out the
              lighter far/mid grass layers' contrast against the
              now-much-brighter sky until only the darkest near blades
              still read. Confirmed directly: inspected the live DOM,
              read the actual applied `transform="translate(196 130)
              scale(1.22) translate(-196 -130)"` on the Transactions tab,
              and reproduced the washed-out look in a fresh screenshot
              before changing anything here. */}
          <RadialGradient id="nsHaloLite" cx="50%" cy="50%" r="50%">
            <Stop offset="0%" stopColor="rgb(210,220,235)" stopOpacity={0.55} />
            <Stop offset="20%" stopColor="rgb(185,202,222)" stopOpacity={0.38} />
            <Stop offset="40%" stopColor="rgb(150,172,200)" stopOpacity={0.2} />
            <Stop offset="60%" stopColor="rgb(115,145,180)" stopOpacity={0.08} />
            <Stop offset="80%" stopColor="rgb(90,120,160)" stopOpacity={0.02} />
            <Stop offset="100%" stopColor="rgb(90,120,160)" stopOpacity={0} />
          </RadialGradient>
          <RadialGradient id="nsMoonLite" cx="50%" cy="50%" r="50%">
            <Stop offset="0%" stopColor={MOON_CORE} stopOpacity={1} />
            <Stop offset="75%" stopColor={MOON_CORE} stopOpacity={1} />
            <Stop offset="100%" stopColor={MOON_MID} stopOpacity={1} />
          </RadialGradient>
        </Defs>

        <AnimatedG animatedProps={tabZoomProps}>
          <Rect x={0} y={0} width={VIEW_W} height={VIEW_H} fill={SKY_TOP} />
          <Rect
            x={MOON_CX - MOON_R * 1.8}
            y={MOON_CY - MOON_R * 1.8}
            width={MOON_R * 3.6}
            height={MOON_R * 3.6}
            fill="url(#nsHaloLite)"
          />
          <Circle cx={MOON_CX} cy={MOON_CY} r={MOON_R} fill="url(#nsMoonLite)" />

          {PARTICLES.map((p, i) => (
            <Polygon
              key={`p${i}`}
              points={`0,${-p.len / 2} ${p.wid},0 0,${p.len / 2} ${-p.wid},0`}
              fill="#DFE8FB"
              opacity={p.opacity}
              transform={`translate(${p.x} ${p.y}) rotate(${p.rotDeg})`}
            />
          ))}

          {ALL_BLADES.map((b, i) => (
            <Polygon key={`g${i}`} points={b.poly} fill={b.fill} />
          ))}
          {/* highlight lines drawn as a separate pass, all after the blade
              fills, so every highlight sits on top of every blade
              regardless of depth layer */}
          {ALL_BLADES.map((b, i) => (
            <AnimatedLine
              key={`h${i}`}
              x1={b.hlX1}
              y1={b.hlY1}
              x2={b.hlX2}
              y2={b.hlY2}
              stroke={`${HIGHLIGHT}1)`}
              strokeWidth={1}
              animatedProps={highlightProps}
            />
          ))}
        </AnimatedG>
      </Svg>

      {/* additive wash over the whole scene — a real `mixBlendMode:'screen'`
          View, not an SVG shape: `mixBlendMode` on a raw react-native-svg
          shape crashes at runtime on web ("Indexed property setter is not
          supported" on CSSStyleDeclaration — confirmed this session; SVG
          shapes don't forward `style` the way a plain View does). */}
      <Animated.View style={[styles.flashOverlay, flashOverlayStyle]} pointerEvents="none" />
    </View>
  );
}

export const NullscapesSceneLite = memo(NullscapesSceneLiteImpl);

const styles = StyleSheet.create({
  wrap: { width: '100%', aspectRatio: VIEW_W / VIEW_H, borderRadius: 4, overflow: 'hidden' },
  fill: { flex: 1 },
  flashOverlay: { ...StyleSheet.absoluteFill, backgroundColor: '#CDD4DE', mixBlendMode: 'screen' },
});
