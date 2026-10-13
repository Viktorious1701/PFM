/**
 * "Nullscapes" — low-detail tier, pure `react-native-svg` + Reanimated, no
 * Skia dependency. This IS the low-detail rendering path (see
 * `src/lib/renderTier.ts`) — not a separate stripped-down build, the same
 * visual language `NullscapesSceneRich.tsx` uses, at a lighter weight:
 * - the light source is a single clean circle (beam + layered halo blurs),
 *   static but for a slow breathing pulse — no blur-sigma modulation, no
 *   ambient whole-scene flash (removed for good, see Rich's own doc
 *   comment for why);
 * - one ring of flickering blocks (Rich has two) — still individually
 *   flickering (4 phase groups, not a shared pulse), just half the count;
 * - the same denser, rim-lit spike rows as Rich (SVG lets a single
 *   `Polygon` carry both fill and stroke, so the rim costs nothing extra
 *   here, unlike Skia's `Path`, which needed a second element);
 * - 6 suction debris shards (Rich has 10), same inward-pull math.
 *
 * Also serves as the WEB fallback while Skia/CanvasKit's WASM loads (see
 * `NullscapesScene.tsx`'s host component) — so this file has to stand on
 * its own as a complete, correct illustration, not a placeholder.
 *
 * Used both as a small boxed illustration (the two existing empty-state
 * call sites, which pass no `style` override and get the fixed 400x260
 * aspect-ratio box) and, via the host component, as a full-bleed
 * background (passing `style={StyleSheet.absoluteFillObject}`).
 */
import { memo, useEffect } from 'react';
import { StyleSheet, View, type ViewStyle } from 'react-native';
import Animated, {
  Easing,
  useAnimatedProps,
  useReducedMotion,
  useSharedValue,
  withRepeat,
  withSequence,
  withTiming,
  type SharedValue,
} from 'react-native-reanimated';
import Svg, { Circle, Defs, G, Polygon, RadialGradient, Rect, Stop } from 'react-native-svg';

const AnimatedCircle = Animated.createAnimatedComponent(Circle);
const AnimatedRect = Animated.createAnimatedComponent(Rect);
const AnimatedG = Animated.createAnimatedComponent(G);

export const VIEW_W = 400;
export const VIEW_H = 260;

const SKY_TOP = '#05070A';
const SKY_HORIZON = '#161B22';
const GLOW_CORE = '#FFFFFF';
const GLOW_MID = '#AEDCFF';
const BLOCK_GLOW = '#DFF5FF';
const SPIKE_FARTHEST_FILL = '#3A4350';
const SPIKE_FAR_FILL = '#232B36';
const SPIKE_NEAR_FILL = '#12151A';
const SPIKE_FARTHEST_RIM = 'rgba(150, 170, 195, 0.3)';
const SPIKE_FAR_RIM = 'rgba(170, 200, 230, 0.35)';
const SPIKE_NEAR_RIM = 'rgba(200, 230, 255, 0.4)';
const DEBRIS_FILL = '#1C222B';
const DEBRIS_RIM = 'rgba(207, 243, 255, 0.5)';

const CX = 192;
const CY = 96;

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

/** Denser than the original pass (smaller step, taller range) — matches
 * `NullscapesSceneRich.tsx`'s own density exactly; path complexity is
 * free here (one `Polygon` either way), so there's no reason for the two
 * tiers to look like different scenes. */
export function buildSpikeRow(seed: number, baseY: number, minH: number, maxH: number, step: number): string {
  const rand = mulberry32(seed);
  const pts: string[] = [`${-step},${baseY}`];
  let x = -step;
  while (x <= VIEW_W + step) {
    const h = minH + rand() * (maxH - minH);
    pts.push(`${x.toFixed(1)},${(baseY - h).toFixed(1)}`);
    x += step * (0.55 + rand() * 0.5);
  }
  pts.push(`${VIEW_W + step},${baseY}`);
  return pts.join(' ');
}

const FARTHEST = buildSpikeRow(11, 128, 12, 28, 9);
const FAR = buildSpikeRow(29, 168, 24, 58, 10);
const NEAR = buildSpikeRow(47, 260, 55, 130, 11);

type RingBlock = { x: number; y: number; size: number; group: number };

function buildRingBlocks(radius: number, count: number, seed: number, groupCount: number): RingBlock[] {
  const rand = mulberry32(seed);
  const out: RingBlock[] = [];
  for (let i = 0; i < count; i++) {
    const angle = (Math.PI * 2 * i) / count;
    out.push({
      x: CX + radius * Math.cos(angle),
      y: CY + radius * Math.sin(angle) * 0.82,
      size: 2.2 + rand() * 1.2,
      group: i % groupCount,
    });
  }
  return out;
}

const GROUP_COUNT = 4;
const RING = buildRingBlocks(85, 28, 17, GROUP_COUNT);

function buildFlickerSequence(seed: number, steps: number) {
  const rand = mulberry32(seed);
  const seq = [];
  for (let i = 0; i < steps; i++) {
    seq.push({ to: 0.35 + rand() * 0.55, duration: 180 + rand() * 420 });
  }
  return seq;
}
const GROUP_KEYFRAMES = Array.from({ length: GROUP_COUNT }, (_, i) => buildFlickerSequence(300 + i * 13, 10));

type Particle = { dx: number; dy: number; phase: number; size: number };

function buildParticles(count: number, seed: number): Particle[] {
  const rand = mulberry32(seed);
  const out: Particle[] = [];
  for (let i = 0; i < count; i++) {
    const angle = rand() * Math.PI * 2;
    const dist = 45 + rand() * 75;
    out.push({
      dx: dist * Math.cos(angle),
      dy: dist * Math.sin(angle) * 0.75 - 20,
      phase: i / count,
      size: 4 + rand() * 4,
    });
  }
  return out;
}
const PARTICLES = buildParticles(6, 41);

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
  const breathe = useSharedValue(0.85);
  const ringRotate = useSharedValue(0);
  const suckT = useSharedValue(0);
  const groupOpacities = GROUP_KEYFRAMES.map(() => useSharedValue(0.6));
  const ownTabScale = useSharedValue(1);
  const scale = tabScale ?? ownTabScale;

  useEffect(() => {
    if (reduceMotion) {
      breathe.value = 0.85;
      ringRotate.value = 0;
      suckT.value = 0;
      groupOpacities.forEach((g) => {
        g.value = 0.6;
      });
      return;
    }

    breathe.value = withRepeat(
      withSequence(
        withTiming(0.95, { duration: 2400, easing: Easing.inOut(Easing.sin) }),
        withTiming(0.78, { duration: 2400, easing: Easing.inOut(Easing.sin) }),
      ),
      -1,
      true,
    );

    ringRotate.value = withRepeat(withTiming(360, { duration: 55000, easing: Easing.linear }), -1, false);
    suckT.value = withRepeat(withTiming(1, { duration: 6000, easing: Easing.linear }), -1, false);

    groupOpacities.forEach((g, i) => {
      g.value = withRepeat(
        withSequence(...GROUP_KEYFRAMES[i].map((k) => withTiming(k.to, { duration: k.duration, easing: Easing.linear }))),
        -1,
        true,
      );
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reduceMotion, breathe, ringRotate, suckT]);

  const glowProps = useAnimatedProps(() => ({ opacity: breathe.value }));
  // `rotation`/`origin`/`translateX`/`translateY` as separate props only get
  // converted into a real `transform` attribute inside react-native-svg's
  // own WebShape `prepare()` step — `Animated.createAnimatedComponent`
  // writes props straight to the DOM on web and skips that step entirely,
  // so those prop names leaked through as literal (invalid) DOM attributes.
  // A hand-built `transform` STRING is itself a real, valid SVG attribute
  // the browser parses natively — no react-native-svg-side processing
  // needed — so it survives the animated path correctly on both platforms.
  const ringProps = useAnimatedProps(() => ({
    transform: `rotate(${ringRotate.value} ${CX} ${CY})`,
  }));

  const particleProps = PARTICLES.map((p) =>
    useAnimatedProps(() => {
      const t = (suckT.value + p.phase) % 1;
      const k = 1 - t;
      const opacity = t > 0.8 ? Math.max(0, 0.8 * (1 - (t - 0.8) / 0.2)) : 0.8;
      const scale = 0.06 + k * 0.94;
      return {
        opacity,
        transform: `translate(${CX + p.dx * k} ${CY + p.dy * k}) scale(${scale})`,
      };
    }),
  );

  const groupProps = groupOpacities.map((g) => useAnimatedProps(() => ({ opacity: g.value })));

  // The cross-tab "camera zoom" (`src/lib/tabCameraScale.ts`). SVG's
  // `transform` attribute has no separate origin concept the way Skia's
  // `Group` does, so "scale about a point" is hand-rolled as the standard
  // translate/scale/translate trick — same hand-built-STRING pattern as
  // `ringProps`/`particleProps` above, for the same reason: Reanimated's
  // convenience `scale`/`origin` props on `Animated.createAnimatedComponent`
  // leak through as invalid literal DOM attributes on web.
  const tabZoomProps = useAnimatedProps(() => ({
    transform: `translate(${CX} ${CY}) scale(${scale.value}) translate(${-CX} ${-CY})`,
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
          <RadialGradient id="nsGlowLite" cx="50%" cy="50%" r="50%">
            <Stop offset="0%" stopColor={GLOW_CORE} stopOpacity={1} />
            <Stop offset="45%" stopColor={GLOW_MID} stopOpacity={0.65} />
            <Stop offset="100%" stopColor={GLOW_MID} stopOpacity={0} />
          </RadialGradient>
        </Defs>

        <AnimatedG animatedProps={tabZoomProps}>
        <Rect x={0} y={0} width={VIEW_W} height={VIEW_H} fill={SKY_TOP} />
        <Rect x={0} y={60} width={VIEW_W} height={120} fill={SKY_HORIZON} opacity={0.35} />

        {/* debris sucked into the light — each particle is its own SVG `G`
            (never an RN `View`: `Svg`'s children must stay SVG elements),
            with its local polygon centered on 0,0 and the G's own
            translate/scale carrying it from its starting offset in toward
            (CX, CY) as it shrinks and fades. */}
        {PARTICLES.map((p, i) => (
          <AnimatedG key={`p${i}`} animatedProps={particleProps[i]}>
            <Polygon
              points={`0,${-p.size} ${p.size},${p.size} ${-p.size},${p.size}`}
              fill={DEBRIS_FILL}
              stroke={DEBRIS_RIM}
              strokeWidth={0.6}
            />
          </AnimatedG>
        ))}

        {/* one dense, individually-flickering ring */}
        <AnimatedG animatedProps={ringProps}>
          {RING.map((b, i) => (
            <AnimatedRect
              key={`r${i}`}
              x={b.x - b.size / 2}
              y={b.y - b.size / 2}
              width={b.size}
              height={b.size}
              fill={BLOCK_GLOW}
              animatedProps={groupProps[b.group]}
            />
          ))}
        </AnimatedG>

        {/* the light source, static but for the slow breathing pulse */}
        <AnimatedCircle cx={CX} cy={CY} r={72} fill="url(#nsGlowLite)" animatedProps={glowProps} />

        <Polygon
          points={FARTHEST}
          fill={SPIKE_FARTHEST_FILL}
          stroke={SPIKE_FARTHEST_RIM}
          strokeWidth={1}
          opacity={0.9}
        />
        <Polygon points={FAR} fill={SPIKE_FAR_FILL} stroke={SPIKE_FAR_RIM} strokeWidth={1} />
        <Polygon points={NEAR} fill={SPIKE_NEAR_FILL} stroke={SPIKE_NEAR_RIM} strokeWidth={1} />
        </AnimatedG>
      </Svg>
    </View>
  );
}

export const NullscapesSceneLite = memo(NullscapesSceneLiteImpl);

const styles = StyleSheet.create({
  wrap: { width: '100%', aspectRatio: VIEW_W / VIEW_H, borderRadius: 4, overflow: 'hidden' },
  fill: { flex: 1 },
});
