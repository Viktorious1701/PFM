/**
 * "Burst" — a recreation of an effect described from a reference Nullscapes
 * level (`Nullscapes-level.gmd`, decoded and analyzed this session, not
 * part of this app's own code): a white circle emerging then exploding,
 * paired with a brief whole-background brightness flash. The level's own
 * mechanism (two native Geometry Dash systems — a Gradient Trigger for the
 * flash, a Particle object for the burst) isn't something this app can
 * read out and replicate exactly; this rebuilds the same beats — glow
 * grows in, explodes outward, background flashes, everything settles —
 * using this app's own animation primitives, not a decoded reproduction of
 * the level's internal particle math.
 *
 * Built with plain `Animated.View`s, not SVG shapes — `mixBlendMode` on a
 * raw `react-native-svg` Circle/Rect crashes on web at runtime
 * ("Indexed property setter is not supported" on CSSStyleDeclaration;
 * react-native-svg doesn't forward `style` through its own prop-extraction
 * path the way a plain `View` does). Views are the pattern already proven
 * to carry `mixBlendMode` correctly elsewhere in this app (`NullscapesButton`,
 * the Transactions FAB) — same technique, not a new one.
 *
 * Loops with a rest period between bursts so it reads as an occasional
 * event, not a constant pulse. `useReducedMotion()` freezes it on the
 * settled (post-burst) frame, same convention as every other animated
 * illustration in this folder.
 *
 * Draft / not wired into any screen yet — built standalone for review.
 */
import { memo, useEffect } from 'react';
import { StyleSheet, View, type ViewStyle } from 'react-native';
import Animated, {
  Easing,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withDelay,
  withRepeat,
  withSequence,
  withTiming,
} from 'react-native-reanimated';

import { mulberry32 } from './NullscapesSceneLite';

export const BURST_VIEW_W = 400;
export const BURST_VIEW_H = 260;

const SKY = '#05070A';
const GLOW = '#EAF6FF';

const GROW_MS = 650;
const EXPLODE_MS = 420;
const SETTLE_MS = 500;
const REST_MS = 2800;

const CORE_BASE = 20;
const RING_BASE = 28;

// Particle travel distance and the core/ring base sizes below are plain
// pixels, sized for this draft's ~400x260 preview box — not yet relative
// to container size the way the SVG viewBox scenes are. Fine for review;
// revisit before using this full-bleed at a very different aspect ratio.
type Particle = { angle: number; dist: number; size: number };

function buildParticles(count: number, seed: number): Particle[] {
  const rand = mulberry32(seed);
  const out: Particle[] = [];
  for (let i = 0; i < count; i++) {
    out.push({
      angle: rand() * Math.PI * 2,
      dist: 28 + rand() * 36, // % of the box's shorter axis, applied at render
      size: 2.5 + rand() * 3.5,
    });
  }
  return out;
}
const PARTICLES = buildParticles(26, 913);

function NullscapesBurstImpl({ style }: { style?: ViewStyle }): React.JSX.Element {
  const reduceMotion = useReducedMotion();
  // 0 = quiet, 0.35 = fully emerged, 1 = exploded peak — one shared clock
  // drives every piece below so they can never drift out of sync.
  const t = useSharedValue(0);

  useEffect(() => {
    if (reduceMotion) {
      t.value = 0;
      return;
    }
    t.value = withRepeat(
      withSequence(
        withTiming(0.35, { duration: GROW_MS, easing: Easing.out(Easing.cubic) }), // emerge
        withTiming(1, { duration: EXPLODE_MS, easing: Easing.out(Easing.quad) }), // explode
        withTiming(0, { duration: SETTLE_MS, easing: Easing.in(Easing.sin) }), // settle
        withDelay(REST_MS, withTiming(0, { duration: 1 })), // rest
      ),
      -1,
      false,
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reduceMotion]);

  const coreStyle = useAnimatedStyle(() => {
    const emerge = Math.min(t.value / 0.35, 1);
    const explode = Math.max(0, (t.value - 0.35) / 0.65);
    const scale = 0.2 + emerge * 0.5 + explode * 2.3;
    const opacity = t.value < 0.35 ? emerge * 0.9 : Math.max(0, 0.9 * (1 - explode));
    return { opacity, transform: [{ scale }] };
  });

  const ringStyle = useAnimatedStyle(() => {
    const explode = Math.max(0, (t.value - 0.35) / 0.65);
    const scale = 0.7 + explode * 4.8;
    const opacity = explode > 0 ? Math.max(0, 0.75 * (1 - explode)) : 0;
    return { opacity, borderWidth: 2 + (1 - explode) * 2, transform: [{ scale }] };
  });

  const flashStyle = useAnimatedStyle(() => {
    const explode = Math.max(0, (t.value - 0.35) / 0.65);
    const peak = explode > 0 ? Math.sin(Math.min(explode, 1) * Math.PI) : 0;
    return { opacity: peak * 0.22 };
  });

  const particleStyles = PARTICLES.map((p) =>
    useAnimatedStyle(() => {
      const explode = Math.max(0, (t.value - 0.35) / 0.65);
      const k = Math.min(explode * 1.15, 1);
      const dx = Math.cos(p.angle) * p.dist * k;
      const dy = Math.sin(p.angle) * p.dist * k;
      const opacity = explode <= 0 ? 0 : Math.max(0, 0.85 * (1 - k));
      return { opacity, transform: [{ translateX: dx }, { translateY: dy }] };
    }),
  );

  const fullBleed = StyleSheet.flatten(style)?.position === 'absolute';

  return (
    <View style={[fullBleed ? styles.fill : styles.wrap, style]} pointerEvents="none" importantForAccessibility="no-hide-descendants">
      <View style={styles.sky} />

      <Animated.View style={[styles.flash, flashStyle]} />

      <View style={styles.center}>
        {PARTICLES.map((p, i) => (
          <Animated.View
            key={i}
            style={[styles.particle, { width: p.size, height: p.size, borderRadius: p.size / 2 }, particleStyles[i]]}
          />
        ))}
        <Animated.View style={[styles.ring, ringStyle]} />
        <Animated.View style={[styles.core, coreStyle]} />
      </View>
    </View>
  );
}

export const NullscapesBurst = memo(NullscapesBurstImpl);

const styles = StyleSheet.create({
  wrap: { width: '100%', aspectRatio: BURST_VIEW_W / BURST_VIEW_H, borderRadius: 4, overflow: 'hidden' },
  fill: { flex: 1 },
  sky: { ...StyleSheet.absoluteFill, backgroundColor: SKY },
  // additive white wash over the whole frame — see the blend rule in
  // `theme/nullscapes.ts`.
  flash: { ...StyleSheet.absoluteFill, backgroundColor: '#FFFFFF', mixBlendMode: 'screen' },
  center: { ...StyleSheet.absoluteFill, alignItems: 'center', justifyContent: 'center' },
  core: {
    position: 'absolute',
    width: CORE_BASE,
    height: CORE_BASE,
    borderRadius: CORE_BASE / 2,
    backgroundColor: '#FFFFFF',
    mixBlendMode: 'screen',
  },
  ring: {
    position: 'absolute',
    width: RING_BASE,
    height: RING_BASE,
    borderRadius: RING_BASE / 2,
    borderColor: GLOW,
    backgroundColor: 'transparent',
    mixBlendMode: 'screen',
  },
  particle: {
    position: 'absolute',
    backgroundColor: GLOW,
    mixBlendMode: 'screen',
  },
});
