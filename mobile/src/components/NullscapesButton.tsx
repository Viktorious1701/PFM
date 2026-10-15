/**
 * Nullscapes button — the shared control for every CTA on a Nullscapes
 * screen (replacing the Cash & Carry `Button` component there), carrying
 * the press-glitch (two offset ghost echoes + a scanline flash) first built
 * for the Transactions FAB, extracted here so every Nullscapes button gets
 * the same "charging" moment on press instead of a generic scale-and-fade.
 * `useReducedMotion` swaps it for the plain opacity-only press feedback.
 *
 * Two variants, both from the validated `Components.dc.html` swatch sheet:
 * - `primary` (default): the dark gradient fill + icy glow ring — "+ NEW
 *   ENTRY"-style, for the one main action on a screen.
 * - `outline`: transparent bg, mint border/text — "VIEW DETAILS"-style, for
 *   a secondary action.
 */
import { useCallback } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import Animated, {
  Easing,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withSequence,
  withTiming,
} from 'react-native-reanimated';

import { ns, nsFont } from '../theme/nullscapes';

const BUTTON_GRADIENT = [ns.buttonTop, ns.buttonBottom] as const;

type Props = {
  title: string;
  onPress: () => void;
  testID?: string;
  variant?: 'primary' | 'outline';
  accessibilityLabel?: string;
  /** Shows a spinner and blocks re-entry — prevents double submission. */
  pending?: boolean;
  disabled?: boolean;
};

export function NullscapesButton({
  title,
  onPress,
  testID,
  variant = 'primary',
  accessibilityLabel,
  pending = false,
  disabled = false,
}: Props) {
  const isBlocked = disabled || pending;
  const reduceMotion = useReducedMotion();
  const ghostA = useSharedValue({ x: 0, y: 0 });
  const ghostB = useSharedValue({ x: 0, y: 0 });
  const ghostOpacity = useSharedValue(0);
  const scanlineOpacity = useSharedValue(0);

  const triggerGlitch = useCallback(() => {
    if (reduceMotion || isBlocked) return;
    const step = (duration: number) => ({ duration, easing: Easing.linear });
    ghostOpacity.value = withSequence(withTiming(1, step(20)), withTiming(0, step(110)));
    ghostA.value = withSequence(
      withTiming({ x: -5, y: -3 }, step(30)),
      withTiming({ x: 4, y: 2 }, step(30)),
      withTiming({ x: 0, y: 0 }, step(70)),
    );
    ghostB.value = withSequence(
      withTiming({ x: 5, y: -4 }, step(30)),
      withTiming({ x: -3, y: 3 }, step(30)),
      withTiming({ x: 0, y: 0 }, step(70)),
    );
    scanlineOpacity.value = withSequence(
      withTiming(0.8, step(15)),
      withTiming(0, step(15)),
      withTiming(0.6, step(15)),
      withTiming(0, step(90)),
    );
  }, [reduceMotion, isBlocked, ghostA, ghostB, ghostOpacity, scanlineOpacity]);

  const ghostAStyle = useAnimatedStyle(() => ({
    opacity: ghostOpacity.value,
    transform: [{ translateX: ghostA.value.x }, { translateY: ghostA.value.y }],
  }));
  const ghostBStyle = useAnimatedStyle(() => ({
    opacity: ghostOpacity.value,
    transform: [{ translateX: ghostB.value.x }, { translateY: ghostB.value.y }],
  }));
  const scanlineStyle = useAnimatedStyle(() => ({ opacity: scanlineOpacity.value }));

  const label = (
    <View style={styles.labelRow}>
      {pending ? (
        <ActivityIndicator size="small" color={variant === 'primary' ? ns.ink : ns.mint} />
      ) : null}
      <Text style={[variant === 'primary' ? styles.primaryLabel : styles.outlineLabel, isBlocked && styles.labelBlocked]}>
        {title}
      </Text>
    </View>
  );
  const content =
    variant === 'primary' ? (
      <LinearGradient
        colors={BUTTON_GRADIENT}
        start={{ x: 0, y: 0 }}
        end={{ x: 0, y: 1 }}
        style={[styles.primary, isBlocked && styles.blocked]}
      >
        {label}
      </LinearGradient>
    ) : (
      <View style={[styles.outline, isBlocked && styles.blocked]}>{label}</View>
    );

  return (
    <Pressable
      testID={testID}
      onPress={onPress}
      onPressIn={triggerGlitch}
      disabled={isBlocked}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? title}
      accessibilityState={{ disabled: isBlocked, busy: pending }}
      style={({ pressed }) => [styles.wrap, pressed && !isBlocked ? styles.pressed : null]}
    >
      <View style={styles.stack}>
        {!reduceMotion && (
          <Animated.View
            pointerEvents="none"
            importantForAccessibility="no-hide-descendants"
            style={[styles.ghost, ghostBStyle]}
          />
        )}
        {!reduceMotion && (
          <Animated.View
            pointerEvents="none"
            importantForAccessibility="no-hide-descendants"
            style={[styles.ghost, ghostAStyle]}
          />
        )}
        {content}
        {!reduceMotion && (
          <>
            <Animated.View
              pointerEvents="none"
              importantForAccessibility="no-hide-descendants"
              style={[styles.scanlineHalo, styles.scanlineTop, scanlineStyle]}
            />
            <Animated.View
              pointerEvents="none"
              importantForAccessibility="no-hide-descendants"
              style={[styles.scanline, styles.scanlineTop, scanlineStyle]}
            />
            <Animated.View
              pointerEvents="none"
              importantForAccessibility="no-hide-descendants"
              style={[styles.scanlineHalo, styles.scanlineBottom, scanlineStyle]}
            />
            <Animated.View
              pointerEvents="none"
              importantForAccessibility="no-hide-descendants"
              style={[styles.scanline, styles.scanlineBottom, scanlineStyle]}
            />
          </>
        )}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  wrap: {},
  pressed: { opacity: 0.88 },
  blocked: { opacity: 0.5 },
  stack: { position: 'relative' },
  labelRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  labelBlocked: { color: ns.mutedFaint },

  primary: {
    borderRadius: 8,
    borderWidth: 1,
    borderColor: ns.buttonRing,
    paddingVertical: 14,
    paddingHorizontal: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryLabel: {
    fontFamily: nsFont.semibold,
    fontSize: 14,
    color: ns.ink,
    letterSpacing: 1,
  },

  outline: {
    borderRadius: 8,
    borderWidth: 1,
    borderColor: ns.mintBorder,
    backgroundColor: 'transparent',
    paddingVertical: 13,
    paddingHorizontal: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  outlineLabel: {
    fontFamily: nsFont.semibold,
    fontSize: 14,
    color: ns.mint,
    letterSpacing: 1,
  },

  // Offset duplicate of the button's own box — see `NullscapesScene`'s
  // sibling FAB implementation this was extracted from for the full
  // rationale (no label on the echo, fills `stack` via its own siblings).
  // `mixBlendMode: 'screen'` on every glow layer below: the reference
  // Nullscapes scene reserves additive blending for accent-hue channels
  // only (see `ns.glitchGlow`'s doc comment) — a flat `backgroundColor`
  // composite reads as a colored rectangle flashing over the button, not
  // light being added to it.
  ghost: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: ns.glitchGlow,
    borderRadius: 8,
    mixBlendMode: 'screen',
  },
  scanlineHalo: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 10,
    marginTop: -4,
    backgroundColor: ns.glitchGlow,
    borderRadius: 2,
    mixBlendMode: 'screen',
  },
  scanline: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 2,
    backgroundColor: ns.glitchGlowBright,
    shadowColor: ns.glitchGlowBright,
    shadowOpacity: 0.9,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 0 },
    mixBlendMode: 'screen',
  },
  scanlineTop: { top: '32%' },
  scanlineBottom: { top: '62%' },
});
