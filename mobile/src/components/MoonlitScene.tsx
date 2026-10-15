/**
 * Moonlit-grass scene — a direct port of the validated HTML/canvas
 * prototype (artifact WMtDiZ4LoVvcuGm99dW5xf). Everything is drawn in the
 * prototype's own 1280x720 space with its exact numbers; the previous port
 * squeezed absolute pixel widths into a 400x260 viewBox, making every blade
 * ~3x too thick relative to the frame. `preserveAspectRatio="xMidYMid
 * slice"` covers any screen shape by cropping evenly, moon centered.
 *
 * Paint order matches the prototype exactly: sky, halo, moon, then each
 * blade's fill immediately followed by its own highlight line (so nearer
 * blades cover farther blades' highlights), then particles, then the flash
 * wash. Highlight lines use normal alpha rather than the canvas's additive
 * blend: `mixBlendMode` on an SVG shape crashes on web, and moving them to
 * a blended overlay would break that occlusion order.
 */
import { Fragment, memo } from 'react';
import { StyleSheet, View, type ViewStyle } from 'react-native';
import Animated, {
  Easing,
  useAnimatedProps,
  useAnimatedStyle,
  withSequence,
  withTiming,
  type SharedValue,
} from 'react-native-reanimated';
import Svg, { Circle, Defs, Line, Polygon, RadialGradient, Rect, Stop } from 'react-native-svg';

const AnimatedLine = Animated.createAnimatedComponent(Line);

const W = 1280;
const H = 720;

export const SKY = '#15273f';
const MOON_CORE = '#f7f0d8';
const MOON_MID = '#e9e6d2';
const MOON_CX = W * 0.49;
const MOON_CY = H * 0.5;
const MOON_R = H * 0.165;

// Canvas radial gradients have an inner radius (0.55R here); inside it the
// first stop's color holds. SVG has no inner radius, so that span is
// reproduced by repeating the first stop up to 0.55/3.4 and remapping the
// rest of the prototype's stops into the remaining range.
const HALO_R = MOON_R * 3.4;
const HALO_INNER = 0.55 / 3.4;
const HALO_STOPS: [number, string, number][] = [
  [0, 'rgb(210,220,235)', 0.55],
  [0.15, 'rgb(190,205,225)', 0.42],
  [0.3, 'rgb(165,185,210)', 0.3],
  [0.45, 'rgb(140,165,195)', 0.2],
  [0.6, 'rgb(115,145,180)', 0.12],
  [0.78, 'rgb(90,120,160)', 0.06],
  [1, 'rgb(90,120,160)', 0],
];

function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

type Blade = {
  points: string;
  fill: string;
  hl: { x1: number; y1: number; x2: number; y2: number; width: number };
};

type LayerOpts = {
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

// Same math and the same rand() call order as the prototype's
// drawGrassLayer, including the unconditional `side` draw.
function buildLayer(o: LayerOpts): Blade[] {
  const rand = mulberry32(o.seed);
  const spacing = W / o.count;
  const out: Blade[] = [];
  for (let i = -1; i <= o.count + 1; i++) {
    const x = i * spacing + (rand() - 0.5) * spacing * 0.9;
    const distFromMoon = Math.abs(x - MOON_CX) / (W * 0.5);
    const boost = o.centerBoost ? Math.max(0, 1 - distFromMoon * 1.8) : 0;
    const h = o.minH + rand() * (o.maxH - o.minH) + boost * (o.maxH * 0.9) * rand();
    const w = o.minW + rand() * (o.maxW - o.minW);
    const lean = (rand() - 0.5) * 2 * o.leanDeg;
    const leanRad = (lean * Math.PI) / 180;
    const tipX = x + Math.sin(leanRad) * h;
    const tipY = o.baseY - h * Math.cos(leanRad);
    const side = rand() < 0.5 ? -1 : 1;
    out.push({
      points: `${x - w / 2},${o.baseY} ${tipX},${tipY} ${x + w / 2},${o.baseY}`,
      fill: o.fill,
      hl: {
        x1: x + side * w * 0.18,
        y1: o.baseY - h * 0.06,
        x2: tipX + side * w * 0.06,
        y2: tipY + h * 0.08,
        width: Math.max(1, w * 0.1),
      },
    });
  }
  return out;
}

const BLADES: Blade[] = [
  ...buildLayer({
    seed: 5, baseY: H * 0.88, count: 220, minH: H * 0.12, maxH: H * 0.3,
    minW: 7, maxW: 18, leanDeg: 16, fill: '#2c4463', centerBoost: false,
  }),
  ...buildLayer({
    seed: 11, baseY: H * 0.98, count: 110, minH: H * 0.32, maxH: H * 0.52,
    minW: 14, maxW: 34, leanDeg: 18, fill: '#1e3550', centerBoost: false,
  }),
  ...buildLayer({
    seed: 47, baseY: H * 1.05, count: 46, minH: H * 0.48, maxH: H * 0.72,
    minW: 26, maxW: 64, leanDeg: 20, fill: '#14263c', centerBoost: true,
  }),
];

type Particle = { transform: string; points: string; opacity: number };

const PARTICLES: Particle[] = (() => {
  const rand = mulberry32(777);
  const out: Particle[] = [];
  for (let i = 0; i < 70; i++) {
    const x = rand() * W;
    const y = rand() * H;
    const len = 4 + rand() * 10;
    const wid = 0.8 + rand() * 1.4;
    const rot = rand() * Math.PI * 2;
    const op = 0.15 + rand() * 0.55;
    out.push({
      transform: `translate(${x} ${y}) rotate(${(rot * 180) / Math.PI})`,
      points: `0,${-len / 2} ${wid},0 0,${len / 2} ${-wid},0`,
      opacity: op,
    });
  }
  return out;
})();

// Short attack so the peak lands on the beat that triggered it (the
// caller fires FLASH_LEAD_MS early); snares here are ~1.88s apart, so the
// whole envelope finishes well before the next one. Reduced motion is
// handled by the caller (it simply never fires).
export const FLASH_LEAD_MS = 60;
const RAMP_MS = FLASH_LEAD_MS;
const HOLD_MS = 70;
const FADE_MS = 600;

/** Starts one flash on `flash`. Called straight from the song's playback
 * loop rather than through a React prop/state change: a state change
 * re-rendered this whole ~800-element tree before the animation could
 * start, measured at ~80-370ms late. */
export function fireFlash(flash: SharedValue<number>): void {
  flash.value = withSequence(
    withTiming(1, { duration: RAMP_MS, easing: Easing.out(Easing.quad) }),
    withTiming(1, { duration: HOLD_MS }),
    withTiming(0, { duration: FADE_MS, easing: Easing.in(Easing.quad) }),
  );
}

/** `flash` is owned by the caller (see `app/index.tsx`) — the scene never
 * flashes on its own. */
function MoonlitSceneImpl({ style, flash }: { style?: ViewStyle; flash: SharedValue<number> }) {

  const highlightProps = useAnimatedProps(() => ({ strokeOpacity: flash.value * 0.5 }));
  const washStyle = useAnimatedStyle(() => ({ opacity: flash.value * 0.38 }));

  return (
    <View style={[styles.fill, style]} pointerEvents="none" importantForAccessibility="no-hide-descendants">
      <Svg width="100%" height="100%" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid slice">
        <Defs>
          <RadialGradient id="halo" gradientUnits="userSpaceOnUse" cx={MOON_CX} cy={MOON_CY} r={HALO_R}>
            {[[-1, HALO_STOPS[0][1], HALO_STOPS[0][2]] as const, ...HALO_STOPS].map(([t, color, a]) => (
              <Stop
                key={t}
                offset={t < 0 ? 0 : HALO_INNER + t * (1 - HALO_INNER)}
                stopColor={color}
                stopOpacity={a}
              />
            ))}
          </RadialGradient>
          <RadialGradient id="moon" gradientUnits="userSpaceOnUse" cx={MOON_CX} cy={MOON_CY} r={MOON_R}>
            <Stop offset={0} stopColor={MOON_CORE} />
            <Stop offset={0.75} stopColor={MOON_CORE} />
            <Stop offset={1} stopColor={MOON_MID} />
          </RadialGradient>
        </Defs>

        <Rect x={0} y={0} width={W} height={H} fill={SKY} />
        <Rect x={0} y={0} width={W} height={H} fill="url(#halo)" />
        <Circle cx={MOON_CX} cy={MOON_CY} r={MOON_R} fill="url(#moon)" />

        {BLADES.map((b, i) => (
          <Fragment key={i}>
            <Polygon points={b.points} fill={b.fill} />
            <AnimatedLine
              x1={b.hl.x1}
              y1={b.hl.y1}
              x2={b.hl.x2}
              y2={b.hl.y2}
              stroke="rgb(225,233,247)"
              strokeWidth={b.hl.width}
              strokeOpacity={0}
              animatedProps={highlightProps}
            />
          </Fragment>
        ))}

        {PARTICLES.map((p, i) => (
          <Polygon key={`p${i}`} points={p.points} transform={p.transform} fill="#dfe8fb" opacity={p.opacity} />
        ))}
      </Svg>
      <Animated.View style={[styles.wash, washStyle]} />
    </View>
  );
}

export const MoonlitScene = memo(MoonlitSceneImpl);

const styles = StyleSheet.create({
  fill: { flex: 1, overflow: 'hidden' },
  wash: { ...StyleSheet.absoluteFill, backgroundColor: 'rgb(205,212,222)', mixBlendMode: 'screen' },
});
