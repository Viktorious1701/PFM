/**
 * "Nullscapes" — high-detail tier, pure Skia (`@shopify/react-native-skia`).
 *
 * Rebuilt against the real level's own footage after two rounds of direct
 * correction (validated first as an HTML mockup — see the design canvas
 * this was ported from): the light source is a static circle (beam +
 * layered halo blurs, kept simple — no blur-sigma modulation, no ambient
 * whole-scene flash; that read as "flashy" and is gone for good, here and
 * in `NullscapesSceneLite`). What actually reads as "flickering lights
 * forming a circle" is two dense rings of small individually-flickering
 * blocks (not a flat stroke, not one shared pulse) — real objects
 * combined into a ring, per the reference. The spike field is three denser
 * rows, each with a rim-light stroke outline catching the light, and a
 * stream of small debris shards is continuously sucked into the light
 * (scaling down, fading, looping) rather than drifting ambiently — "the
 * explosion absorbs objects around it."
 *
 * The press-triggered glitch (ghost-echo pair + scanline flash) stays
 * exactly where it already lives — the Add-Transaction FAB
 * (`app/(tabs)/transactions/index.tsx`) — untouched by this file. This
 * component has no interactive glitch of its own; it's a passive backdrop.
 *
 * Flicker-group architecture: 104 individually-positioned blocks would
 * need 104 independent animation timelines to each flicker on its own
 * schedule — real but wasteful. Instead every block is assigned to one of
 * 8 phase groups (round-robin), each group driven by exactly one
 * `buildFlickerSequence`-timed shared value (the same proven pattern this
 * file already used for `jitter`). 8 independently-timed groups across 80
 * blocks reads as organic, uncoordinated flicker without 80 timelines.
 *
 * Only ever reached via the host component (`NullscapesScene.tsx`), and only
 * on native (iOS/Android), imported there with a deferred `require()`. Web
 * is forced onto `NullscapesSceneLite` unconditionally — see
 * `NullscapesScene.tsx`'s own doc comment for why: this file's cover-scale
 * transform (below) never redrew after its initial paint once loaded via
 * `WithSkiaWeb`'s `React.lazy()`+`Suspense` on web, a reproducible bug
 * tried four different ways with no fix found. Never import this file
 * directly from anything under `app/` — expo-router eagerly evaluates
 * every file there to build its route table, and this file pulls in
 * Skia's native bindings as a side effect of being imported at all.
 */
import { memo, useEffect, useState } from 'react';
import { StyleSheet, View, type ViewStyle, type LayoutChangeEvent } from 'react-native';
import { Canvas, Circle, Group, LinearGradient, Path, Rect } from '@shopify/react-native-skia';
import {
  Easing,
  useDerivedValue,
  useReducedMotion,
  useSharedValue,
  withRepeat,
  withSequence,
  withTiming,
  type SharedValue,
} from 'react-native-reanimated';

import { buildSpikeRow, mulberry32, VIEW_H, VIEW_W } from './NullscapesSceneLite';

const SKY_TOP = '#05070A';
const SKY_HORIZON = '#161B22';
const GLOW_CORE = '#FFFFFF';
const GLOW_HALO = 'rgba(174, 220, 255, 0.55)';
const GLOW_HALO_SOFT = 'rgba(174, 220, 255, 0.3)';
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

/** Same geometry `buildSpikeRow` already produces for the Lite version,
 * reformatted as an SVG path string — `Path` takes one directly. */
function toPath(points: string): string {
  const pairs = points.trim().split(' ');
  const [first, ...rest] = pairs;
  return `M ${first} L ${rest.join(' L ')} Z`;
}

// Denser than the original pass (smaller step, taller range) — "the spikes
// need a decoration revamp": each row now also carries a rim-light stroke
// (rendered as a second Path over the same geometry, style="stroke"),
// catching the light the way the reference's spike edges do.
const FARTHEST_PATH = toPath(buildSpikeRow(11, 128, 12, 28, 9));
const FAR_PATH = toPath(buildSpikeRow(29, 168, 24, 58, 10));
const NEAR_PATH = toPath(buildSpikeRow(47, 260, 55, 130, 11));

type RingBlock = { x: number; y: number; size: number; group: number };

/** One dense ring of small glow blocks around (CX, CY) — "various objects
 * combined to a circle," not a flat stroke. Each block's `group` picks
 * which of the 8 shared flicker timelines drives its opacity. */
function buildRingBlocks(radius: number, count: number, seed: number, groupCount: number): RingBlock[] {
  const rand = mulberry32(seed);
  const out: RingBlock[] = [];
  for (let i = 0; i < count; i++) {
    const angle = (Math.PI * 2 * i) / count;
    out.push({
      x: CX + radius * Math.cos(angle),
      y: CY + radius * Math.sin(angle) * 0.82,
      size: 2.4 + rand() * 1.4,
      group: i % groupCount,
    });
  }
  return out;
}

const GROUP_COUNT = 8;
const RING_A = buildRingBlocks(72, 36, 11, GROUP_COUNT);
const RING_B = buildRingBlocks(98, 44, 23, GROUP_COUNT);

function buildFlickerSequence(seed: number, steps: number) {
  const rand = mulberry32(seed);
  const seq = [];
  for (let i = 0; i < steps; i++) {
    seq.push({ to: 0.35 + rand() * 0.55, duration: 180 + rand() * 420 });
  }
  return seq;
}
const GROUP_KEYFRAMES = Array.from({ length: GROUP_COUNT }, (_, i) => buildFlickerSequence(200 + i * 13, 10));

type Particle = { dx: number; dy: number; phase: number; size: number };

/** Debris sucked continuously into the light — scales down and fades as it
 * approaches, looping via one shared "phase" offset per particle against a
 * single clock, so the stream never visibly resets. */
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
const PARTICLES = buildParticles(10, 5);

// Memoized: mounted once as a sibling of `<Tabs>` now (`app/(tabs)/_layout.tsx`),
// so `TabsLayout` re-rendering for unrelated reasons must not force a full
// reconciliation of this scene's 80-100+ element tree — its `style`/`tabScale`
// props are both stable references (`StyleSheet.absoluteFillObject`, the
// `tabNearScale` singleton), so memo is a real, cheap bail-out here.
function NullscapesSceneRichImpl({
  style,
  tabScale,
}: {
  style?: ViewStyle;
  tabScale?: SharedValue<number>;
}): React.JSX.Element {
  const reduceMotion = useReducedMotion();
  const breathe = useSharedValue(0.85);
  const ringRotateA = useSharedValue(0);
  const ringRotateB = useSharedValue(0);
  const suckT = useSharedValue(0);
  const ownTabScale = useSharedValue(1);
  const scale = tabScale ?? ownTabScale;
  // One shared opacity value per flicker group (8 total) — not per block.
  const groupOpacities = GROUP_KEYFRAMES.map(() => useSharedValue(0.6));

  useEffect(() => {
    if (reduceMotion) {
      breathe.value = 0.85;
      ringRotateA.value = 0;
      ringRotateB.value = 0;
      suckT.value = 0;
      groupOpacities.forEach((g) => {
        g.value = 0.6;
      });
      return;
    }

    breathe.value = withRepeat(
      withSequence(
        withTiming(0.95, { duration: 2200, easing: Easing.inOut(Easing.sin) }),
        withTiming(0.78, { duration: 2200, easing: Easing.inOut(Easing.sin) }),
      ),
      -1,
      true,
    );

    ringRotateA.value = withRepeat(withTiming(360, { duration: 50000, easing: Easing.linear }), -1, false);
    ringRotateB.value = withRepeat(withTiming(-360, { duration: 70000, easing: Easing.linear }), -1, false);
    suckT.value = withRepeat(withTiming(1, { duration: 6000, easing: Easing.linear }), -1, false);

    groupOpacities.forEach((g, i) => {
      g.value = withRepeat(
        withSequence(...GROUP_KEYFRAMES[i].map((k) => withTiming(k.to, { duration: k.duration, easing: Easing.linear }))),
        -1,
        true,
      );
    });
    // groupOpacities' own identity is stable (created once via .map above,
    // same length every render) — only the primitives that drive it belong
    // in the dependency array.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reduceMotion, breathe, ringRotateA, ringRotateB, suckT]);

  const ringATransform = useDerivedValue(() => [{ rotate: (ringRotateA.value * Math.PI) / 180 }]);
  const ringBTransform = useDerivedValue(() => [{ rotate: (ringRotateB.value * Math.PI) / 180 }]);

  // Each particle's current transform/opacity, derived from the one shared
  // clock plus its own baked-in phase — fixed-length array, same hook count
  // every render, so .map-ing useDerivedValue over it is safe.
  const particleTransforms = PARTICLES.map((p) =>
    useDerivedValue(() => {
      const t = (suckT.value + p.phase) % 1;
      const k = 1 - t;
      return [{ translateX: p.dx * k }, { translateY: p.dy * k }, { scale: 0.06 + k * 0.94 }];
    }),
  );
  const particleOpacities = PARTICLES.map((p) =>
    useDerivedValue(() => {
      const t = (suckT.value + p.phase) % 1;
      if (t > 0.8) return Math.max(0, 0.8 * (1 - (t - 0.8) / 0.2));
      return 0.8;
    }),
  );

  // The boxed empty-state call sites pass no `style` and get the fixed
  // aspect-ratio box below. The Dashboard's full-bleed call site passes
  // `StyleSheet.absoluteFillObject` (position:'absolute' + 0 insets, no
  // width/height) to stretch across the screen — but `styles.wrap`'s own
  // `width:'100%'` + `aspectRatio` would still win on web even then (CSS
  // computes height from width via the ratio instead of stretching to fill
  // the insets), collapsing a full-bleed background down to a small boxed
  // illustration. Detect that case from the same `position:'absolute'` the
  // caller already sets, and skip the aspect-ratio box entirely for it.
  // `StyleSheet.flatten` (not a raw `style?.position` read) because
  // react-native-web's own `StyleSheet.create` returns an opaque, atomic-CSS
  // style reference on web, not a plain object — direct property access on
  // it silently reads `undefined`.
  const fullBleed = StyleSheet.flatten(style)?.position === 'absolute';

  // Unlike `NullscapesSceneLite`'s `<Svg viewBox=... preserveAspectRatio="xMidYMid
  // slice">`, Skia's `<Canvas>` has no built-in content-to-box scaling — every
  // path/shape below is drawn in the fixed `VIEW_W`x`VIEW_H` (400x260) design
  // space regardless of the Canvas's actual rendered size. Without a matching
  // scale transform, a full-bleed box (e.g. the Dashboard's ~420x787) only ever
  // gets the scene's original small top-left region painted, leaving the rest
  // blank — the boxed empty-state call sites hid this because their box's CSS
  // size (from `width:'100%'` + `aspectRatio`) happens to stay close to 400x260.
  // Measure the actual box and reproduce "cover" (xMidYMid slice) by hand:
  // scale by the larger of the two ratios, then center the overflow.
  //
  // This cover-scale is computed ONCE, from `useState`/`onLayout`, and the
  // `<Canvas>` below is given `key={size.width}x${size.height}` so React
  // fully REMOUNTS it — a brand new Skia root/commit, not a prop update —
  // the moment the real size is known, rather than updating the existing
  // instance's transform in place.
  //
  // This is a deliberate workaround, not the "proper" fix: three different
  // update-in-place mechanisms were tried and each traced all the way
  // through (a wrapping `View`'s `onLayout` feeding `useState`; the same
  // feeding a Reanimated shared value instead; `<Canvas>`'s own purpose-built
  // `onSize` shared-value prop) — all three produced correctly-recomputed
  // scale values (confirmed via diagnostic logging reaching this component's
  // render output, and confirmed via a render-count log that the component
  // does re-render multiple times, ruling out a "renders once" theory too)
  // yet the Canvas never visually redrew afterward, still only ever painting
  // the original unscaled 400x260 region — a reproducible but unexplained
  // Skia/Suspense interaction (no matching upstream issue found). A full
  // remount sidesteps it: Skia only ever has to get the FIRST paint of a
  // given instance right, which it reliably does, instead of relying on an
  // in-place update after the fact.
  const [size, setSize] = useState({ width: VIEW_W, height: VIEW_H });
  const onLayout = (e: LayoutChangeEvent) => {
    const { width, height } = e.nativeEvent.layout;
    if (width > 0 && height > 0 && (width !== size.width || height !== size.height)) {
      setSize({ width, height });
    }
  };
  const canvasKey = `${size.width}x${size.height}`;
  const coverScale = Math.max(size.width / VIEW_W, size.height / VIEW_H);
  const coverOffsetX = (size.width - VIEW_W * coverScale) / 2;
  const coverOffsetY = (size.height - VIEW_H * coverScale) / 2;

  // The cross-tab "camera zoom" (`src/lib/tabCameraScale.ts`) stays
  // shared-value-driven — it changes continuously after mount without ever
  // needing a remount, the same way the already-working ring rotation and
  // particle motion in this same file do.
  const tabZoomTransform = useDerivedValue(() => [
    { translateX: CX },
    { translateY: CY },
    { scale: scale.value },
    { translateX: -CX },
    { translateY: -CY },
  ]);

  return (
    <View
      style={[fullBleed ? styles.fill : styles.wrap, style]}
      pointerEvents="none"
      importantForAccessibility="no-hide-descendants"
      onLayout={onLayout}
    >
      <Canvas key={canvasKey} style={styles.canvas}>
        <Group transform={[{ translateX: coverOffsetX }, { translateY: coverOffsetY }, { scale: coverScale }]}>
        <Group transform={tabZoomTransform}>
        <Path path={`M 0,0 L ${VIEW_W},0 L ${VIEW_W},${VIEW_H} L 0,${VIEW_H} Z`} color={SKY_TOP} />
        <Path path={`M 0,60 L ${VIEW_W},60 L ${VIEW_W},180 L 0,180 Z`} color={SKY_HORIZON} opacity={0.35} />

        {/* debris sucked into the light */}
        {PARTICLES.map((p, i) => (
          <Group key={`p${i}`} transform={particleTransforms[i]} opacity={particleOpacities[i]}>
            <Path
              path={`M ${p.dx},${p.dy - p.size} L ${p.dx + p.size},${p.dy + p.size} L ${p.dx - p.size},${p.dy + p.size} Z`}
              color={DEBRIS_FILL}
            />
            <Path
              path={`M ${p.dx},${p.dy - p.size} L ${p.dx + p.size},${p.dy + p.size} L ${p.dx - p.size},${p.dy + p.size} Z`}
              color={DEBRIS_RIM}
              style="stroke"
              strokeWidth={0.6}
            />
          </Group>
        ))}

        {/* two dense, individually-flickering rings */}
        <Group transform={ringATransform} origin={{ x: CX, y: CY }}>
          {RING_A.map((b, i) => (
            <Rect
              key={`a${i}`}
              x={b.x - b.size / 2}
              y={b.y - b.size / 2}
              width={b.size}
              height={b.size}
              color={BLOCK_GLOW}
              opacity={groupOpacities[b.group]}
            />
          ))}
        </Group>
        <Group transform={ringBTransform} origin={{ x: CX, y: CY }}>
          {RING_B.map((b, i) => (
            <Rect
              key={`b${i}`}
              x={b.x - b.size / 2}
              y={b.y - b.size / 2}
              width={b.size}
              height={b.size}
              color={BLOCK_GLOW}
              opacity={groupOpacities[b.group]}
            />
          ))}
        </Group>

        {/* the light source, static but for the slow breathing pulse */}
        <Group opacity={breathe}>
          <Rect x={CX - 40} y={CY - 300} width={80} height={300}>
            <LinearGradient
              start={{ x: 0, y: 0 }}
              end={{ x: 0, y: 1 }}
              colors={['rgba(255,255,255,0)', 'rgba(207,243,255,0.5)', 'rgba(255,255,255,0.92)']}
              positions={[0, 0.65, 1]}
            />
          </Rect>
          <Circle cx={CX} cy={CY} r={85} color={GLOW_HALO_SOFT} />
          <Circle cx={CX} cy={CY} r={60} color={GLOW_HALO} />
          <Circle cx={CX} cy={CY} r={26} color={GLOW_CORE} />
        </Group>

        {/* dense, decorated spike field — fill + rim-light stroke per row */}
        <Path path={FARTHEST_PATH} color={SPIKE_FARTHEST_FILL} opacity={0.9} />
        <Path path={FARTHEST_PATH} color={SPIKE_FARTHEST_RIM} style="stroke" strokeWidth={1} />

        <Path path={FAR_PATH} color={SPIKE_FAR_FILL} />
        <Path path={FAR_PATH} color={SPIKE_FAR_RIM} style="stroke" strokeWidth={1} />

        <Path path={NEAR_PATH} color={SPIKE_NEAR_FILL} />
        <Path path={NEAR_PATH} color={SPIKE_NEAR_RIM} style="stroke" strokeWidth={1} />
        </Group>
        </Group>
      </Canvas>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { width: '100%', aspectRatio: VIEW_W / VIEW_H, borderRadius: 4, overflow: 'hidden' },
  fill: { flex: 1 },
  canvas: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0 },
});

export const NullscapesSceneRich = memo(NullscapesSceneRichImpl);

export default NullscapesSceneRich;
