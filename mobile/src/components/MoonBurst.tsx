/**
 * The song's climax, layered onto the moonlit scene — a port of the
 * validated "Moonburst" study (artifact WVrubjXpKr3dPZnApt6frC).
 *
 * Two kinds of event, both fired by the caller from the song's clock:
 *
 * - `strike()` / `release()`: a lightning bolt drops into the moon and
 *   flickers, then hangs as a glowing column (the "tornado") until
 *   `release()` fades it. Held for the whole climax. Its foot stays in the
 *   moon while the top whips left and right, snapping to a new lean and
 *   bend every 60-180 ms, like the references.
 * - `burst()`: one explosion — the moon blows out white and blooms, ~45
 *   small glowing orbs stream out of its centre like bullets and leave the
 *   screen, a few large soft glows drift out behind them, and dark shards
 *   are thrown up out of the grass.
 *
 * Orbs, glows and shards are fixed pools of views whose positions are
 * integrated each frame on the animation thread; firing a burst only
 * writes new start values into free slots, so nothing re-renders.
 *
 * `BurstBack` draws between the moon and the grass (everything glowing sits
 * behind the blades, which read as silhouettes against it); `BurstFront`
 * draws the shards in front of the grass.
 */
import { useCallback, useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, {
  Easing,
  useAnimatedProps,
  useAnimatedStyle,
  useFrameCallback,
  useSharedValue,
  withSequence,
  withTiming,
  type SharedValue,
} from 'react-native-reanimated';
import Svg, { Circle, Defs, Line, LinearGradient, Path, Polygon, RadialGradient, Stop } from 'react-native-svg';

const AnimatedPath = Animated.createAnimatedComponent(Path);

import { coverFit, H, MOON_CX, MOON_CY, MOON_R, W } from './moonGeometry';

// ---- pools ----
const ORB_SLOTS = 96;
const ORB_F = 8; // x, y, vx, vy, age, size, alpha, alive
const GLOW_SLOTS = 16;
const GLOW_F = 8; // x, y, vx, vy, age, radius, alpha, alive
const SHARD_SLOTS = 72;
const SHARD_F = 11; // x, y, vx, vy, age, rot, vr, len, wid, life, alive

// Values tuned in the study.
const ORBS_PER_BURST = 45;
const ORB_SPEED = 560; // scene units / s
const ORB_SIZE = 3;
const GLOWS_PER_BURST = 6;
const SHARDS_PER_BURST = 34;
const GLOW_LIFE_S = 3.2;

export type MoonBurst = {
  blow: SharedValue<number>;
  column: SharedValue<number>;
  drop: SharedValue<number>;
  bolt: SharedValue<number>;
  /** Column motion: [lean, leanTarget, bend, bendTarget, secondsToNextSnap]. */
  sway: SharedValue<number[]>;
  orbs: SharedValue<number[]>;
  glows: SharedValue<number[]>;
  shards: SharedValue<number[]>;
};

function freeSlot(arr: number[], slots: number, f: number, aliveAt: number, start: number): number {
  for (let k = 0; k < slots; k++) {
    const i = (start + k) % slots;
    if (arr[i * f + aliveAt] === 0) return i;
  }
  return start % slots; // pool full: reuse the oldest-ish slot
}

export function useMoonBurst(): {
  burst: MoonBurst;
  fireBurst: () => void;
  strike: () => void;
  release: () => void;
} {
  const blow = useSharedValue(0);
  const column = useSharedValue(0);
  const drop = useSharedValue(1);
  const bolt = useSharedValue(0);
  const sway = useSharedValue<number[]>([0, 0, 0.5, 0.5, 0]);
  const orbs = useSharedValue<number[]>(new Array(ORB_SLOTS * ORB_F).fill(0));
  const glows = useSharedValue<number[]>(new Array(GLOW_SLOTS * GLOW_F).fill(0));
  const shards = useSharedValue<number[]>(new Array(SHARD_SLOTS * SHARD_F).fill(0));

  // Integrates every live particle. Returns at once when nothing is alive.
  useFrameCallback((info) => {
    'worklet';
    const dt = Math.min(50, info.timeSincePreviousFrame ?? 16) / 1000;

    if (column.value > 0.001) {
      // Every 60-180 ms the top of the column picks a new lean (usually to
      // the other side) and a new bend, then snaps toward them in ~35 ms;
      // a little per-frame jitter keeps it alive between snaps.
      const w = sway.value.slice();
      w[4] -= dt;
      if (w[4] <= 0) {
        const side = w[1] > 0 ? -1 : 1;
        const flip = Math.random() < 0.75 ? side : -side;
        w[1] = flip * MOON_R * (0.35 + Math.random() * 0.95);
        w[3] = Math.random();
        w[4] = 0.06 + Math.random() * 0.12;
      }
      const k = 1 - Math.exp(-dt / 0.035);
      w[0] += (w[1] - w[0]) * k + (Math.random() - 0.5) * MOON_R * 0.04;
      w[2] += (w[3] - w[2]) * k;
      sway.value = w;
    }

    let o = orbs.value;
    let any = false;
    for (let i = 0; i < ORB_SLOTS; i++) if (o[i * ORB_F + 7] === 1) { any = true; break; }
    if (any) {
      o = o.slice();
      const drag = Math.exp(-0.12 * dt);
      for (let i = 0; i < ORB_SLOTS; i++) {
        const b = i * ORB_F;
        if (o[b + 7] === 0) continue;
        o[b + 4] += dt;
        if (o[b + 4] < 0) continue;
        o[b + 2] *= drag;
        o[b + 3] *= drag;
        o[b] += o[b + 2] * dt;
        o[b + 1] += o[b + 3] * dt;
        if (o[b] < -80 || o[b] > W + 80 || o[b + 1] < -80 || o[b + 1] > H + 80) o[b + 7] = 0;
      }
      orbs.value = o;
    }

    let g = glows.value;
    any = false;
    for (let i = 0; i < GLOW_SLOTS; i++) if (g[i * GLOW_F + 7] === 1) { any = true; break; }
    if (any) {
      g = g.slice();
      const drag = Math.exp(-0.4 * dt);
      for (let i = 0; i < GLOW_SLOTS; i++) {
        const b = i * GLOW_F;
        if (g[b + 7] === 0) continue;
        g[b + 4] += dt;
        if (g[b + 4] < 0) continue;
        g[b + 2] *= drag;
        g[b + 3] *= drag;
        g[b] += g[b + 2] * dt;
        g[b + 1] += g[b + 3] * dt;
        if (g[b + 4] > GLOW_LIFE_S) g[b + 7] = 0;
      }
      glows.value = g;
    }

    let s = shards.value;
    any = false;
    for (let i = 0; i < SHARD_SLOTS; i++) if (s[i * SHARD_F + 10] === 1) { any = true; break; }
    if (any) {
      s = s.slice();
      const drag = Math.exp(-0.9 * dt);
      for (let i = 0; i < SHARD_SLOTS; i++) {
        const b = i * SHARD_F;
        if (s[b + 10] === 0) continue;
        s[b + 4] += dt;
        s[b + 3] += 260 * dt;
        s[b + 2] *= drag;
        s[b + 3] *= drag;
        s[b] += s[b + 2] * dt;
        s[b + 1] += s[b + 3] * dt;
        s[b + 5] += s[b + 6] * dt;
        if (s[b + 4] > s[b + 9]) s[b + 10] = 0;
      }
      shards.value = s;
    }
  });

  const fireBurst = useCallback(() => {
    blow.value = withSequence(
      withTiming(1, { duration: 70, easing: Easing.out(Easing.quad) }),
      withTiming(1, { duration: 200 }),
      withTiming(0, { duration: 1700, easing: Easing.in(Easing.quad) }),
    );

    const o = orbs.value.slice();
    let at = 0;
    for (let n = 0; n < ORBS_PER_BURST; n++) {
      const i = freeSlot(o, ORB_SLOTS, ORB_F, 7, at);
      at = i + 1;
      // fanned upward and out — straight down they would only vanish into
      // the grass — and fired as a short stream (~0.45 s), not one pop
      const ang = -Math.PI / 2 + (Math.random() - 0.5) * Math.PI * 1.5;
      const sp = ORB_SPEED * (0.55 + Math.random() * 0.9);
      const b = i * ORB_F;
      o[b] = MOON_CX + Math.cos(ang) * MOON_R * 0.2;
      o[b + 1] = MOON_CY + Math.sin(ang) * MOON_R * 0.2;
      o[b + 2] = Math.cos(ang) * sp;
      o[b + 3] = Math.sin(ang) * sp;
      o[b + 4] = -Math.random() * 0.45;
      o[b + 5] = ORB_SIZE * (0.6 + Math.random() * 0.9);
      o[b + 6] = 0.7 + Math.random() * 0.3;
      o[b + 7] = 1;
    }
    orbs.value = o;

    const g = glows.value.slice();
    at = 0;
    for (let n = 0; n < GLOWS_PER_BURST; n++) {
      const i = freeSlot(g, GLOW_SLOTS, GLOW_F, 7, at);
      at = i + 1;
      const ang = -Math.PI / 2 + (Math.random() - 0.5) * Math.PI * 1.7;
      const sp = ORB_SPEED * (0.3 + Math.random() * 0.35);
      const b = i * GLOW_F;
      g[b] = MOON_CX;
      g[b + 1] = MOON_CY;
      g[b + 2] = Math.cos(ang) * sp;
      g[b + 3] = Math.sin(ang) * sp;
      g[b + 4] = -Math.random() * 0.3;
      g[b + 5] = 34 + Math.random() * 44;
      g[b + 6] = 0.24 + Math.random() * 0.16;
      g[b + 7] = 1;
    }
    glows.value = g;

    const s = shards.value.slice();
    at = 0;
    for (let n = 0; n < SHARDS_PER_BURST; n++) {
      const i = freeSlot(s, SHARD_SLOTS, SHARD_F, 10, at);
      at = i + 1;
      const ang = -Math.PI / 2 + (Math.random() - 0.5) * Math.PI * 1.1;
      const sp = 260 + Math.random() * 520;
      const b = i * SHARD_F;
      s[b] = MOON_CX + (Math.random() - 0.5) * MOON_R * 2.4;
      s[b + 1] = MOON_CY + MOON_R * (0.4 + Math.random() * 0.6);
      s[b + 2] = Math.cos(ang) * sp;
      s[b + 3] = Math.sin(ang) * sp;
      s[b + 4] = 0;
      s[b + 5] = Math.random() * Math.PI * 2;
      s[b + 6] = (Math.random() - 0.5) * 6;
      s[b + 7] = 10 + Math.random() * 34;
      s[b + 8] = 4 + Math.random() * 10;
      s[b + 9] = 1.6 + Math.random() * 1.2;
      s[b + 10] = 1;
    }
    shards.value = s;
  }, [blow, orbs, glows, shards]);

  const strike = useCallback(() => {
    // the bolt reaches down from the top in 90 ms and flickers for ~0.3 s
    drop.value = 0;
    drop.value = withTiming(1, { duration: 90, easing: Easing.out(Easing.quad) });
    column.value = withTiming(1, { duration: 60 });
    bolt.value = withSequence(
      ...[1, 0.45, 0.95, 0.35, 0.8, 0.25, 0.55, 0].map((v) => withTiming(v, { duration: 35 })),
    );
  }, [drop, column, bolt]);

  const release = useCallback(() => {
    column.value = withTiming(0, { duration: 1100, easing: Easing.in(Easing.quad) });
  }, [column]);

  const burst = useMemo(
    () => ({ blow, column, drop, bolt, sway, orbs, glows, shards }),
    [blow, column, drop, bolt, sway, orbs, glows, shards],
  );
  return { burst, fireBurst, strike, release };
}

// ---- static shapes (scene units) ----

// The column is a stack of strokes along one centre line, widest and
// faintest first, so its soft glow follows the line wherever it whips.
// The line runs from above the screen down into the moon: a quadratic
// whose top is offset by the lean and whose control point sits between
// "bowed" (bend 0, control under the moon) and "straight" (bend 1).
const COLUMN_TOP = -60;
const COLUMN_PAD = 40;
const COLUMN_BOTTOM = MOON_CY - MOON_R * 0.3;
// Many faint steps from a wide haze in to the cream core. Each step only
// adds a sliver of opacity, so their edges don't read as stripes — a
// blur would smooth them too, but re-blurring a full-screen layer that
// changes shape every frame ran the climax at ~10-20 fps.
const COLUMN_STEPS = 22;
const COLUMN_STROKES = Array.from({ length: COLUMN_STEPS }, (_, i) => {
  const t = i / (COLUMN_STEPS - 1); // 0 outermost .. 1 core
  return {
    width: MOON_R * (3.4 - 2.7 * Math.pow(t, 0.75)),
    color: t > 0.9 ? '#fffbef' : `rgb(${Math.round(200 + 50 * t)},${Math.round(214 + 36 * t)},${Math.round(240 + 8 * t)})`,
    opacity: 0.018 + 0.1 * Math.pow(t, 3) + (t > 0.9 ? 0.35 : 0),
  };
});

// Bolt: fixed jagged line down the column's resting centre.
function columnX(t: number) {
  return MOON_CX + MOON_R * 0.45 * (1 - t) * (1 - t);
}

const BOLT_PATH = (() => {
  let seed = 31;
  const rand = () => {
    seed = (seed * 16807) % 2147483647;
    return seed / 2147483647;
  };
  const pts: string[] = [];
  for (let i = 0; i <= 14; i++) {
    const t = i / 14;
    const jitter = i === 0 || i === 14 ? 0 : (rand() - 0.5) * 34;
    pts.push(`${columnX(t) + jitter},${COLUMN_TOP + (MOON_CY - MOON_R * 0.55 - COLUMN_TOP) * t}`);
  }
  return `M${pts.join(' L')}`;
})();

const BANDS = [1, 2, 3, 4, 5].map((i) => ({ r: MOON_R * (1.25 + i * 0.42), a: 0.09 * (1 - i * 0.13) }));

// Orb sprite: glow at the centre of a 180x30 box, streak trailing left.
// The view is rotated to the orb's heading and scaled to its size.
const ORB_VW = 180;
const ORB_VH = 30;

type Frame = { w: number; h: number };

function OrbView({ i, orbs, scale, offX, offY }: { i: number; orbs: SharedValue<number[]>; scale: number; offX: number; offY: number }) {
  const style = useAnimatedStyle(() => {
    const o = orbs.value;
    const b = i * ORB_F;
    const visible = o[b + 7] === 1 && o[b + 4] >= 0;
    return {
      opacity: visible ? o[b + 6] * Math.min(1, o[b + 4] * 12) : 0,
      transform: [
        { translateX: o[b] * scale + offX - (ORB_VW * scale) / 2 },
        { translateY: o[b + 1] * scale + offY - (ORB_VH * scale) / 2 },
        { rotate: `${Math.atan2(o[b + 3], o[b + 2])}rad` },
        { scale: o[b + 5] / ORB_SIZE },
      ],
    };
  });
  return (
    <Animated.View style={[styles.sprite, { width: ORB_VW * scale, height: ORB_VH * scale }, style]}>
      <Svg width="100%" height="100%" viewBox={`0 0 ${ORB_VW} ${ORB_VH}`}>
        <Defs>
          <LinearGradient id="orbTail" x1="0" y1="0" x2="1" y2="0">
            <Stop offset={0} stopColor="rgb(225,235,255)" stopOpacity={0} />
            <Stop offset={1} stopColor="rgb(235,242,255)" stopOpacity={0.7} />
          </LinearGradient>
          <RadialGradient id="orbGlow">
            <Stop offset={0} stopColor="#ffffff" stopOpacity={1} />
            <Stop offset={0.3} stopColor="rgb(240,246,255)" stopOpacity={0.8} />
            <Stop offset={1} stopColor="rgb(210,225,250)" stopOpacity={0} />
          </RadialGradient>
        </Defs>
        <Line x1={ORB_VW / 2 - 40} y1={ORB_VH / 2} x2={ORB_VW / 2} y2={ORB_VH / 2} stroke="url(#orbTail)" strokeWidth={ORB_SIZE * 1.1} strokeLinecap="round" />
        <Circle cx={ORB_VW / 2} cy={ORB_VH / 2} r={ORB_SIZE * 3.2} fill="url(#orbGlow)" />
      </Svg>
    </Animated.View>
  );
}

function GlowView({ i, glows, scale, offX, offY }: { i: number; glows: SharedValue<number[]>; scale: number; offX: number; offY: number }) {
  const style = useAnimatedStyle(() => {
    const g = glows.value;
    const b = i * GLOW_F;
    const age = g[b + 4];
    const visible = g[b + 7] === 1 && age >= 0;
    const r = g[b + 5];
    return {
      opacity: visible ? g[b + 6] * Math.max(0, 1 - age / GLOW_LIFE_S) * Math.min(1, age * 12) : 0,
      // drawn at radius 50 in a 100-unit box centred on the glow, then
      // scaled about that centre to radius r
      transform: [
        { translateX: (g[b] - 50) * scale + offX },
        { translateY: (g[b + 1] - 50) * scale + offY },
        { scale: r / 50 },
      ],
    };
  });
  return (
    <Animated.View style={[styles.sprite, { width: 100 * scale, height: 100 * scale }, style]}>
      <Svg width="100%" height="100%" viewBox="0 0 100 100">
        <Defs>
          <RadialGradient id="softGlow">
            <Stop offset={0} stopColor="rgb(210,222,245)" stopOpacity={1} />
            <Stop offset={0.55} stopColor="rgb(190,205,235)" stopOpacity={0.55} />
            <Stop offset={1} stopColor="rgb(190,205,235)" stopOpacity={0} />
          </RadialGradient>
        </Defs>
        <Circle cx={50} cy={50} r={50} fill="url(#softGlow)" />
      </Svg>
    </Animated.View>
  );
}

function ShardView({ i, shards, scale, offX, offY }: { i: number; shards: SharedValue<number[]>; scale: number; offX: number; offY: number }) {
  const style = useAnimatedStyle(() => {
    const s = shards.value;
    const b = i * SHARD_F;
    const alive = s[b + 10] === 1;
    return {
      opacity: alive ? 0.9 * Math.min(1, (s[b + 9] - s[b + 4]) / 0.5) : 0,
      transform: [
        { translateX: (s[b] - 22) * scale + offX },
        { translateY: (s[b + 1] - 22) * scale + offY },
        { rotate: `${s[b + 5]}rad` },
        { scaleX: s[b + 8] / 10 },
        { scaleY: s[b + 7] / 34 },
      ],
    };
  });
  return (
    <Animated.View style={[styles.sprite, { width: 44 * scale, height: 44 * scale }, style]}>
      <Svg width="100%" height="100%" viewBox="0 0 44 44">
        <Polygon points="22,5 27,39 17,39" fill="#16263b" />
      </Svg>
    </Animated.View>
  );
}

function ColumnStroke({ sway, width, color, opacity }: { sway: SharedValue<number[]>; width: number; color: string; opacity: number }) {
  const props = useAnimatedProps(() => {
    const [lean, , bend] = sway.value;
    const topX = MOON_CX + lean;
    const ctrlX = MOON_CX + lean * bend;
    const midY = (COLUMN_TOP + COLUMN_BOTTOM) / 2;
    return { d: `M${topX},${COLUMN_TOP} Q${ctrlX},${midY} ${MOON_CX},${COLUMN_BOTTOM}` };
  });
  return (
    <AnimatedPath
      animatedProps={props}
      d={`M${MOON_CX},${COLUMN_TOP} L${MOON_CX},${COLUMN_BOTTOM}`}
      stroke={color}
      strokeOpacity={opacity}
      strokeWidth={width}
      fill="none"
    />
  );
}

/** Everything glowing: behind the grass, in front of the moon. */
export function BurstBack({ burst, frame }: { burst: MoonBurst; frame: Frame }) {
  const { scale, offX, offY } = coverFit(frame.w, frame.h);
  const blowStyle = useAnimatedStyle(() => ({ opacity: burst.blow.value }));
  const bandStyle = useAnimatedStyle(() => ({ opacity: Math.max(burst.blow.value, burst.column.value * 0.6) }));
  const stripH = H * scale;
  const columnStyle = useAnimatedStyle(() => ({
    opacity: burst.column.value,
    transform: [{ translateY: (-(1 - burst.drop.value) * stripH) / 2 }, { scaleY: burst.drop.value }],
  }));
  const boltStyle = useAnimatedStyle(() => ({ opacity: burst.bolt.value }));
  const box = { position: 'absolute' as const, left: offX, top: offY, width: W * scale, height: H * scale };
  const colBox = { ...box, top: offY - COLUMN_PAD * scale, height: (H + COLUMN_PAD) * scale };
  const vb = `0 0 ${W} ${H}`;

  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      <Animated.View style={[box, bandStyle]}>
        <Svg width="100%" height="100%" viewBox={vb}>
          <Defs>
            {BANDS.map((band, i) => (
              <RadialGradient key={i} id={`band${i}`} gradientUnits="userSpaceOnUse" cx={MOON_CX} cy={MOON_CY} r={band.r + MOON_R * 0.04}>
                <Stop offset={(band.r - MOON_R * 0.2) / (band.r + MOON_R * 0.04)} stopColor="rgb(210,222,245)" stopOpacity={0} />
                <Stop offset={(band.r - MOON_R * 0.03) / (band.r + MOON_R * 0.04)} stopColor="rgb(225,234,252)" stopOpacity={band.a} />
                <Stop offset={1} stopColor="rgb(225,234,252)" stopOpacity={0} />
              </RadialGradient>
            ))}
          </Defs>
          {BANDS.map((band, i) => (
            <Circle key={i} cx={MOON_CX} cy={MOON_CY} r={band.r + MOON_R * 0.04} fill={`url(#band${i})`} />
          ))}
        </Svg>
      </Animated.View>

      <View style={StyleSheet.absoluteFill}>
        {Array.from({ length: GLOW_SLOTS }, (_, i) => (
          <GlowView key={i} i={i} glows={burst.glows} scale={scale} offX={offX} offY={offY} />
        ))}
        {Array.from({ length: ORB_SLOTS }, (_, i) => (
          <OrbView key={i} i={i} orbs={burst.orbs} scale={scale} offX={offX} offY={offY} />
        ))}
      </View>

      <Animated.View style={[box, blowStyle]}>
        <Svg width="100%" height="100%" viewBox={vb}>
          <Defs>
            <RadialGradient id="blowHalo" gradientUnits="userSpaceOnUse" cx={MOON_CX} cy={MOON_CY} r={MOON_R * 4.6}>
              <Stop offset={0.12} stopColor="rgb(215,225,240)" stopOpacity={0.55} />
              <Stop offset={0.4} stopColor="rgb(170,190,215)" stopOpacity={0.22} />
              <Stop offset={1} stopColor="rgb(120,150,190)" stopOpacity={0} />
            </RadialGradient>
            <RadialGradient id="bloom" gradientUnits="userSpaceOnUse" cx={MOON_CX} cy={MOON_CY} r={MOON_R * 1.8}>
              <Stop offset={0.5} stopColor="#ffffff" stopOpacity={0.75} />
              <Stop offset={1} stopColor="rgb(220,230,250)" stopOpacity={0} />
            </RadialGradient>
          </Defs>
          <Circle cx={MOON_CX} cy={MOON_CY} r={MOON_R * 4.6} fill="url(#blowHalo)" />
          <Circle cx={MOON_CX} cy={MOON_CY} r={MOON_R * 1.8} fill="url(#bloom)" />
          <Circle cx={MOON_CX} cy={MOON_CY} r={MOON_R * 1.06} fill="#ffffff" />
        </Svg>
      </Animated.View>

      <Animated.View style={[colBox, columnStyle]}>
        <Svg width="100%" height="100%" viewBox={`0 ${-COLUMN_PAD} ${W} ${H + COLUMN_PAD}`}>
          {COLUMN_STROKES.map((st, i) => (
            <ColumnStroke key={i} sway={burst.sway} {...st} />
          ))}
        </Svg>
      </Animated.View>

      <Animated.View style={[box, boltStyle]}>
        <Svg width="100%" height="100%" viewBox={vb}>
          <Path d={BOLT_PATH} stroke="#ffffff" strokeOpacity={0.25} strokeWidth={9} fill="none" strokeLinejoin="round" />
          <Path d={BOLT_PATH} stroke="#ffffff" strokeWidth={2.5} fill="none" strokeLinejoin="round" />
        </Svg>
      </Animated.View>
    </View>
  );
}

/** Shards thrown out of the grass: in front of it. */
export function BurstFront({ burst, frame }: { burst: MoonBurst; frame: Frame }) {
  const { scale, offX, offY } = coverFit(frame.w, frame.h);
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      {Array.from({ length: SHARD_SLOTS }, (_, i) => (
        <ShardView key={i} i={i} shards={burst.shards} scale={scale} offX={offX} offY={offY} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  sprite: { position: 'absolute', left: 0, top: 0 },
});
