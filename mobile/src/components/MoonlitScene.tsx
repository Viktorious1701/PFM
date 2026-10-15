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
 *
 * Camera pan (screen transitions, validated in the "Moonlit Pan" study,
 * artifact GEGeQYdk1ZE7j9GgvetNT4): each grass layer is its own picture so
 * it can slide at its own speed and lean (shear about its own baseline)
 * against the motion. Layers are tiled three times side by side so they
 * can slide indefinitely with no empty edge. The sky and moon never move.
 *
 * Flash highlights are drawn as a second, highlighted copy of each layer
 * whose opacity follows the flash. Fading that copy over the plain one is
 * pixel-for-pixel the same as fading each line's own stroke opacity (the
 * blades underneath are identical), but costs three opacity writes per
 * frame instead of one per line — there are ~1,150 lines once tiled.
 */
import { Fragment, memo, useCallback, useMemo, useState } from 'react';
import { StyleSheet, View, type LayoutChangeEvent, type ViewStyle } from 'react-native';
import Animated, {
  Easing,
  useAnimatedStyle,
  useFrameCallback,
  useSharedValue,
  withSequence,
  withTiming,
  type SharedValue,
} from 'react-native-reanimated';
import Svg, { Circle, Defs, G, Line, Polygon, RadialGradient, Rect, Stop } from 'react-native-svg';

import { BurstBack, BurstFront, type MoonBurst } from './MoonBurst';
import { H, MOON_CX, MOON_CY, MOON_R, W } from './moonGeometry';


export const SKY = '#15273f';
const MOON_CORE = '#f7f0d8';
const MOON_MID = '#e9e6d2';

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
// drawGrassLayer, including the unconditional `side` draw. Only one
// period's blades (i = 0..count-1) are kept, then repeated at -W, 0, +W:
// the layer tiles seamlessly, so a pan can slide it any distance.
function buildLayer(o: LayerOpts): Blade[] {
  const rand = mulberry32(o.seed);
  const spacing = W / o.count;
  const one: { x: number; h: number; w: number; tipDX: number; tipY: number; side: number }[] = [];
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
      one.push({ x, h, w, tipDX: Math.sin(leanRad) * h, tipY: o.baseY - h * Math.cos(leanRad), side });
    }
  }
  const out: Blade[] = [];
  for (const k of [-1, 0, 1]) {
    for (const b of one) {
      const x = b.x + k * W;
      const tipX = x + b.tipDX;
      out.push({
        points: `${x - b.w / 2},${o.baseY} ${tipX},${b.tipY} ${x + b.w / 2},${o.baseY}`,
        hl: {
          x1: x + b.side * b.w * 0.18,
          y1: o.baseY - b.h * 0.06,
          x2: tipX + b.side * b.w * 0.06,
          y2: b.tipY + b.h * 0.08,
          width: Math.max(1, b.w * 0.1),
        },
      });
    }
  }
  return out;
}

type Layer = {
  blades: Blade[];
  fill: string;
  baseY: number;
  /** Fraction of the near layer's travel this layer covers in a pan. */
  speed: number;
  /** Fraction of the full lean this layer takes. */
  leanScale: number;
};

const LAYERS: Layer[] = [
  {
    blades: buildLayer({
      seed: 5, baseY: H * 0.88, count: 220, minH: H * 0.12, maxH: H * 0.3,
      minW: 7, maxW: 18, leanDeg: 16, fill: '#2c4463', centerBoost: false,
    }),
    fill: '#2c4463', baseY: H * 0.88, speed: 0.25, leanScale: 0.3,
  },
  {
    blades: buildLayer({
      seed: 11, baseY: H * 0.98, count: 110, minH: H * 0.32, maxH: H * 0.52,
      minW: 14, maxW: 34, leanDeg: 18, fill: '#1e3550', centerBoost: false,
    }),
    fill: '#1e3550', baseY: H * 0.98, speed: 0.5, leanScale: 0.6,
  },
  {
    blades: buildLayer({
      seed: 47, baseY: H * 1.05, count: 46, minH: H * 0.48, maxH: H * 0.72,
      minW: 26, maxW: 64, leanDeg: 20, fill: '#14263c', centerBoost: true,
    }),
    fill: '#14263c', baseY: H * 1.05, speed: 1, leanScale: 1,
  },
];
const NEAR = LAYERS.length - 1;
// Plain numbers for the per-frame worklets, so they never capture the
// blade arrays.
const LEAN_SCALES = LAYERS.map((L) => L.leanScale);

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
    for (const k of [-1, 0, 1]) {
      out.push({
        transform: `translate(${x + k * W} ${y}) rotate(${(rot * 180) / Math.PI})`,
        points: `0,${-len / 2} ${wid},0 0,${len / 2} ${-wid},0`,
        opacity: op,
      });
    }
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

// ---- camera pan ----
// Values tuned in the Moonlit Pan study: 1100 ms pan, near grass travels
// 60% of the frame width, 2° lean at full speed, 10% spring-back wobble.
export const PAN_DELAY_MS = 120;
export const PAN_MS = 1100;
const NEAR_TRAVEL = 0.6 * W;
const LEAN_MAX = Math.tan((2 * Math.PI) / 180);
const SPRING_K = 160;
const SPRING_C = 2 * (1 - 0.75 * 0.1) * Math.sqrt(SPRING_K);
// A layer's strip spans [-W - EDGE, 2W + EDGE]; its offset is kept inside
// [-W + EDGE, W - EDGE] so the visible frame never reaches a strip end.
const EDGE = 160;

/** Shared state of the camera, owned by the caller (`useScenePan`) and read
 * by the scene. */
export type ScenePan = {
  /** Near-layer distance travelled, scene units. */
  camera: SharedValue<number>;
  /** Per layer: a whole number of W subtracted so the offset stays on its strip. */
  wrap: SharedValue<number[]>;
  /** Per layer lean spring: [x0, v0, x1, v1, x2, v2], x as tan(angle). */
  lean: SharedValue<number[]>;
  /** Running pan: elapsed ms, start camera, direction; elapsed < 0 = idle. */
  run: SharedValue<{ elapsed: number; from: number; dir: number }>;
};

function easeInOutCubic(t: number) {
  'worklet';
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}
function easeInOutCubicSlope(t: number) {
  'worklet';
  return t < 0.5 ? 12 * t * t : 3 * Math.pow(-2 * t + 2, 2); // peaks at 3
}
function mod(a: number, n: number) {
  'worklet';
  return ((a % n) + n) % n;
}

/** Owns the camera and drives it each frame. `startPan(1)` slides the field
 * forward (camera right, grass slides left), `startPan(-1)` back. */
export function useScenePan(): { pan: ScenePan; startPan: (dir: 1 | -1) => void } {
  const camera = useSharedValue(0);
  const wrap = useSharedValue<number[]>(LAYERS.map(() => 0));
  const lean = useSharedValue<number[]>(LAYERS.flatMap(() => [0, 0]));
  const run = useSharedValue({ elapsed: -1, from: 0, dir: 1 });

  // Always registered, but returns at once while the camera is at rest and
  // every lean has settled. (It can't switch itself off: on web the
  // callback captures its own handle before that handle exists.)
  useFrameCallback((info) => {
    'worklet';
    const r = run.value;
    if (r.elapsed < 0 && lean.value.every((n) => n === 0)) return;
    const dt = Math.min(50, info.timeSincePreviousFrame ?? 16);
    let speed = 0;
    if (r.elapsed >= 0) {
      const elapsed = r.elapsed + dt;
      const t = Math.min(1, Math.max(0, (elapsed - PAN_DELAY_MS) / PAN_MS));
      camera.value = r.from - r.dir * NEAR_TRAVEL * easeInOutCubic(t);
      if (elapsed > PAN_DELAY_MS && t < 1) speed = (-r.dir * easeInOutCubicSlope(t)) / 3;
      run.value = { ...r, elapsed: t >= 1 ? -1 : elapsed };
    }
    // Damped spring per layer toward a lean set by the camera's speed:
    // the field slides one way, the tips trail the other.
    const next = lean.value.slice();
    const steps = Math.max(1, Math.ceil(dt / 4));
    const h = dt / 1000 / steps;
    for (let i = 0; i < LEAN_SCALES.length; i++) {
      const target = -speed * LEAN_MAX * LEAN_SCALES[i];
      let x = next[i * 2];
      let v = next[i * 2 + 1];
      for (let n = 0; n < steps; n++) {
        v += (-SPRING_K * (x - target) - SPRING_C * v) * h;
        x += v * h;
      }
      if (Math.abs(x) < 1e-5 && Math.abs(v) < 1e-4 && target === 0) {
        x = 0;
        v = 0;
      }
      next[i * 2] = x;
      next[i * 2 + 1] = v;
    }
    lean.value = next;
  });

  const startPan = useCallback(
    (dir: 1 | -1) => {
      // Re-seat each layer on its strip so the whole move stays on it:
      // a forward move lowers the offset by up to `travel`, a back move
      // raises it. Shifting by whole multiples of W changes nothing visible.
      const from = camera.value;
      wrap.value = LAYERS.map((L) => {
        const travel = NEAR_TRAVEL * L.speed;
        const lo = dir === 1 ? -W + EDGE + travel : -W + EDGE;
        const t = from * L.speed;
        const seated = lo + mod(t - lo, W);
        return t - seated;
      });
      run.value = { elapsed: 0, from, dir };
    },
    [camera, wrap, run],
  );

  // Stable identity: the scene is memoised on its props, and a fresh
  // object here would re-render all ~3,500 grass shapes on every render of
  // the screen that owns the pan.
  const pan = useMemo(() => ({ camera, wrap, lean, run }), [camera, wrap, lean, run]);
  return { pan, startPan };
}

type Frame = { w: number; h: number };

function LayerView({ layer, index, flash, pan, frame }: {
  layer: Layer;
  index: number;
  flash: SharedValue<number>;
  pan: ScenePan;
  frame: Frame;
}) {
  const scale = Math.max(frame.w / W, frame.h / H);
  const stripW = (3 * W + 2 * EDGE) * scale;
  const stripH = H * scale;
  const left = (frame.w - W * scale) / 2 - (W + EDGE) * scale;
  const top = (frame.h - H * scale) / 2;
  const { speed, baseY } = layer;

  const slide = useAnimatedStyle(() => ({
    transform: [{ translateX: (pan.camera.value * speed - pan.wrap.value[index]) * scale }],
  }));
  // Shear about this layer's own baseline: skewX pivots on the view's
  // center, so a translate moves the pivot down to the baseline.
  const shear = useAnimatedStyle(() => {
    const s = pan.lean.value[index * 2];
    return {
      transform: [
        { translateX: s * (baseY * scale - stripH / 2) },
        { skewX: `${-Math.atan(s)}rad` },
      ],
    };
  });
  const highlight = useAnimatedStyle(() => ({ opacity: flash.value }));

  const viewBox = `${-W - EDGE} 0 ${3 * W + 2 * EDGE} ${H}`;
  const box = { position: 'absolute' as const, left, top, width: stripW, height: stripH };

  return (
    <Animated.View style={[box, slide]} pointerEvents="none">
      <Animated.View style={[StyleSheet.absoluteFill, shear]}>
        <Svg width={stripW} height={stripH} viewBox={viewBox}>
          <G fill={layer.fill}>
            {layer.blades.map((b, i) => (
              <Polygon key={i} points={b.points} />
            ))}
          </G>
        </Svg>
        <Animated.View style={[StyleSheet.absoluteFill, highlight]}>
          <Svg width={stripW} height={stripH} viewBox={viewBox}>
            {layer.blades.map((b, i) => (
              <Fragment key={i}>
                <Polygon points={b.points} fill={layer.fill} />
                <Line
                  x1={b.hl.x1}
                  y1={b.hl.y1}
                  x2={b.hl.x2}
                  y2={b.hl.y2}
                  stroke="rgb(225,233,247)"
                  strokeWidth={b.hl.width}
                  strokeOpacity={0.5}
                />
              </Fragment>
            ))}
          </Svg>
        </Animated.View>
      </Animated.View>
    </Animated.View>
  );
}

function ParticlesView({ pan, frame }: { pan: ScenePan; frame: Frame }) {
  const scale = Math.max(frame.w / W, frame.h / H);
  const stripW = (3 * W + 2 * EDGE) * scale;
  const stripH = H * scale;
  const slide = useAnimatedStyle(() => ({
    transform: [{ translateX: (pan.camera.value - pan.wrap.value[NEAR]) * scale }],
  }));
  return (
    <Animated.View
      style={[
        {
          position: 'absolute',
          left: (frame.w - W * scale) / 2 - (W + EDGE) * scale,
          top: (frame.h - H * scale) / 2,
          width: stripW,
          height: stripH,
        },
        slide,
      ]}
      pointerEvents="none"
    >
      <Svg width={stripW} height={stripH} viewBox={`${-W - EDGE} 0 ${3 * W + 2 * EDGE} ${H}`}>
        {PARTICLES.map((p, i) => (
          <Polygon key={i} points={p.points} transform={p.transform} fill="#dfe8fb" opacity={p.opacity} />
        ))}
      </Svg>
    </Animated.View>
  );
}

/** `flash`, `pan` and `burst` are owned by the caller (see `app/index.tsx`)
 * — the scene never flashes, moves or explodes on its own. */
function MoonlitSceneImpl({
  style,
  flash,
  pan,
  burst,
}: {
  style?: ViewStyle;
  flash: SharedValue<number>;
  pan: ScenePan;
  burst: MoonBurst;
}) {
  const [frame, setFrame] = useState<Frame | null>(null);
  const onLayout = useCallback((e: LayoutChangeEvent) => {
    const { width, height } = e.nativeEvent.layout;
    setFrame((f) => (f && f.w === width && f.h === height ? f : { w: width, h: height }));
  }, []);
  const washStyle = useAnimatedStyle(() => ({ opacity: flash.value * 0.38 }));

  return (
    <View
      style={[styles.fill, style]}
      pointerEvents="none"
      importantForAccessibility="no-hide-descendants"
      onLayout={onLayout}
    >
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
      </Svg>

      {frame ? <BurstBack burst={burst} frame={frame} /> : null}
      {frame
        ? LAYERS.map((layer, i) => (
            <LayerView key={i} layer={layer} index={i} flash={flash} pan={pan} frame={frame} />
          ))
        : null}
      {frame ? <ParticlesView pan={pan} frame={frame} /> : null}
      {frame ? <BurstFront burst={burst} frame={frame} /> : null}
      <Animated.View style={[styles.wash, washStyle]} />
    </View>
  );
}

export const MoonlitScene = memo(MoonlitSceneImpl);

const styles = StyleSheet.create({
  fill: { flex: 1, overflow: 'hidden' },
  wash: { ...StyleSheet.absoluteFill, backgroundColor: 'rgb(205,212,222)', mixBlendMode: 'screen' },
});
