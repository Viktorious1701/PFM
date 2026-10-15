/**
 * "Nullscapes" — high-detail tier, pure Skia (`@shopify/react-native-skia`).
 *
 * Mirrors `NullscapesSceneLite.tsx`'s moonlit-grass scene exactly, same
 * geometry (`buildGrassLayer`, same seeds/counts), reimplemented with Skia
 * primitives. UNVERIFIED on an actual device — this file only ever runs on
 * native (iOS/Android) and this project has no device/emulator available in
 * this environment (constitution ENV-04); Lite is what's actually tested in
 * a real browser. Flagged here rather than silently assumed correct.
 *
 * The press-triggered glitch (ghost-echo pair + scanline flash) stays
 * exactly where it already lives — the Add-Transaction FAB
 * (`app/(tabs)/transactions/index.tsx`) — untouched by this file. This
 * component has no interactive glitch of its own; it's a passive backdrop.
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
import { Canvas, Circle, Group, Path, RadialGradient as SkiaRadialGradient, vec } from '@shopify/react-native-skia';
import Animated, {
  Easing,
  useAnimatedStyle,
  useDerivedValue,
  useReducedMotion,
  useSharedValue,
  withDelay,
  withRepeat,
  withSequence,
  withTiming,
  type SharedValue,
} from 'react-native-reanimated';

import {
  buildGrassLayer,
  MOON_CX,
  MOON_CY,
  MOON_R,
  VIEW_H,
  VIEW_W,
  type GrassBlade,
} from './NullscapesSceneLite';

const SKY_TOP = '#15273F';
const MOON_CORE = '#F7F0D8';
const MOON_MID = '#E9E6D2';
const GRASS_FAR = '#2C4463';
const GRASS_MID = '#1E3550';
const GRASS_NEAR = '#14263C';

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
const ALL_BLADES: GrassBlade[] = [...FAR_BLADES, ...MID_BLADES, ...NEAR_BLADES];

/** `GrassBlade.poly` is an SVG `points="x,y x,y x,y"` string (shared with
 * Lite); Skia's `Path` wants `M x,y L x,y L x,y Z` instead. */
function bladeToPath(poly: string): string {
  const pairs = poly.trim().split(' ');
  const [first, ...rest] = pairs;
  return `M ${first} L ${rest.join(' L ')} Z`;
}
const BLADE_PATHS = ALL_BLADES.map((b) => bladeToPath(b.poly));

type Particle = { x: number; y: number; len: number; wid: number; rotRad: number; opacity: number };

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

function buildParticles(count: number, seed: number): Particle[] {
  const rand = mulberry32(seed);
  const out: Particle[] = [];
  for (let i = 0; i < count; i++) {
    out.push({
      x: rand() * VIEW_W,
      y: rand() * VIEW_H,
      len: 2.5 + rand() * 6,
      wid: 0.5 + rand() * 0.9,
      rotRad: rand() * Math.PI * 2,
      opacity: 0.15 + rand() * 0.55,
    });
  }
  return out;
}
const PARTICLES = buildParticles(70, 777);
const PARTICLE_PATHS = PARTICLES.map(
  (p) => `M 0,${-p.len / 2} L ${p.wid},0 L 0,${p.len / 2} L ${-p.wid},0 Z`,
);

const CYCLE_MS = 7000;
const RAMP_MS = 180;
const HOLD_MS = 90;
const FADE_MS = 650;
const REST_MS = CYCLE_MS - (RAMP_MS + HOLD_MS + FADE_MS);

// Memoized: mounted once as a sibling of `<Tabs>` (`app/(tabs)/_layout.tsx`),
// so `TabsLayout` re-rendering for unrelated reasons must not force a full
// reconciliation of this scene's element tree.
function NullscapesSceneRichImpl({
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

  const highlightOpacity = useDerivedValue(() => flash.value * 0.5);
  const flashOverlayStyle = useAnimatedStyle(() => ({ opacity: flash.value * 0.38 }));

  // `styles.wrap` (boxed, fixed aspect ratio) is still here for a caller
  // that passes no `style`, but the only real mount point in this app is
  // the full-bleed background (`app/(tabs)/_layout.tsx`) — the earlier
  // empty-state boxed illustrations were removed in an earlier rollout
  // stage. The full-bleed caller passes `StyleSheet.absoluteFill`, but
  // `styles.wrap`'s own `width:'100%'` + `aspectRatio` would still win on
  // web even then, collapsing it down to a small boxed illustration.
  // Detect that case from the same `position:'absolute'` the caller
  // already sets, and skip the aspect-ratio box entirely for it.
  const fullBleed = StyleSheet.flatten(style)?.position === 'absolute';

  // Unlike `NullscapesSceneLite`'s `<Svg viewBox=... preserveAspectRatio="xMidYMid
  // slice">`, Skia's `<Canvas>` has no built-in content-to-box scaling — every
  // path/shape below is drawn in the fixed `VIEW_W`x`VIEW_H` (400x260) design
  // space regardless of the Canvas's actual rendered size. Measure the actual
  // box and reproduce "cover" (xMidYMid slice) by hand: scale by the larger of
  // the two ratios, then center the overflow. Computed once via `useState`/
  // `onLayout`, with the `<Canvas>` keyed on size so React remounts it rather
  // than updating in place — see `NullscapesSceneRich`'s prior revision for
  // why an in-place update never visually redrew here (a reproducible Skia/
  // Suspense interaction, no matching upstream issue found).
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

  const tabZoomTransform = useDerivedValue(() => [
    { translateX: MOON_CX },
    { translateY: MOON_CY },
    { scale: scale.value },
    { translateX: -MOON_CX },
    { translateY: -MOON_CY },
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

            {/* one smooth halo, many stops baked into the gradient's own
                color list so it blends continuously with no ring banding.
                Kept small/tight (see `NullscapesSceneLite.tsx`'s matching
                doc comment) -- this app's per-tab camera zoom stacks
                multiplicatively with the Canvas's own cover-scale, and a
                halo sized to look right unzoomed balloons to wash out the
                lighter grass layers once both zooms compound. */}
            <Circle cx={MOON_CX} cy={MOON_CY} r={MOON_R * 1.8}>
              <SkiaRadialGradient
                c={vec(MOON_CX, MOON_CY)}
                r={MOON_R * 1.8}
                colors={[
                  'rgba(210,220,235,0.55)',
                  'rgba(185,202,222,0.38)',
                  'rgba(150,172,200,0.20)',
                  'rgba(115,145,180,0.08)',
                  'rgba(90,120,160,0.02)',
                  'rgba(90,120,160,0)',
                ]}
                positions={[0, 0.2, 0.4, 0.6, 0.8, 1]}
              />
            </Circle>
            <Circle cx={MOON_CX} cy={MOON_CY} r={MOON_R}>
              <SkiaRadialGradient
                c={vec(MOON_CX, MOON_CY)}
                r={MOON_R}
                colors={[MOON_CORE, MOON_CORE, MOON_MID]}
                positions={[0, 0.75, 1]}
              />
            </Circle>

            {PARTICLES.map((p, i) => (
              <Group key={`p${i}`} transform={[{ translateX: p.x }, { translateY: p.y }, { rotate: p.rotRad }]}>
                <Path path={PARTICLE_PATHS[i]} color="#DFE8FB" opacity={p.opacity} />
              </Group>
            ))}

            {ALL_BLADES.map((b, i) => (
              <Path key={`g${i}`} path={BLADE_PATHS[i]} color={b.fill} />
            ))}
            {/* highlight lines, all after every blade fill so each one sits
                on top regardless of depth layer */}
            {ALL_BLADES.map((b, i) => (
              <Path
                key={`h${i}`}
                path={`M ${b.hlX1},${b.hlY1} L ${b.hlX2},${b.hlY2}`}
                color="rgba(225,233,247,1)"
                style="stroke"
                strokeWidth={1}
                opacity={highlightOpacity}
              />
            ))}
          </Group>
        </Group>
      </Canvas>

      {/* additive wash over the whole scene -- a plain RN View with
          `mixBlendMode`, not a Skia paint, for consistency with Lite's own
          approach (and because this needs to sit above the Canvas as a
          sibling, the same way Lite layers it above the Svg). */}
      <Animated.View style={[styles.flashOverlay, flashOverlayStyle]} pointerEvents="none" />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { width: '100%', aspectRatio: VIEW_W / VIEW_H, borderRadius: 4, overflow: 'hidden' },
  fill: { flex: 1 },
  canvas: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0 },
  flashOverlay: { ...StyleSheet.absoluteFill, backgroundColor: '#CDD4DE', mixBlendMode: 'screen' },
});

export const NullscapesSceneRich = memo(NullscapesSceneRichImpl);

export default NullscapesSceneRich;
