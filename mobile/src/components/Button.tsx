/**
 * Primary / secondary button with a pending state.
 *
 * Replaces react-native's `Button`, which cannot show progress or be styled.
 * The pending state matters here: mail dispatch is off the request path
 * (spec FR-19 / NFR-01), but the request still has latency the user must see.
 *
 * Shape per DESIGN.md "button-primary": a pill is the one soft, obviously-
 * tappable shape in this system. Focus uses `ink`, never `sky-deep` on
 * `sky-deep` — a same-hue ring would be invisible.
 */
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';

import { color, font, radius, space } from '../theme/tokens';

type Props = {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary';
  /** Shows a spinner and blocks re-entry — prevents double submission. */
  pending?: boolean;
  disabled?: boolean;
  testID?: string;
};

export function Button({
  title,
  onPress,
  variant = 'primary',
  pending = false,
  disabled = false,
  testID,
}: Props) {
  const isBlocked = disabled || pending;
  const isPrimary = variant === 'primary';

  return (
    <Pressable
      testID={testID}
      onPress={onPress}
      disabled={isBlocked}
      accessibilityRole="button"
      accessibilityState={{ disabled: isBlocked, busy: pending }}
      style={({ pressed }) => [
        styles.base,
        isPrimary ? styles.primary : styles.secondary,
        pressed && !isBlocked ? styles.pressed : null,
        isBlocked ? styles.blocked : null,
      ]}
    >
      <View style={styles.content}>
        {pending ? (
          <ActivityIndicator size="small" color={isBlocked ? color.textMuted : isPrimary ? color.primaryText : color.secondary} />
        ) : null}
        <Text
          style={[
            styles.label,
            isPrimary ? styles.labelPrimary : styles.labelSecondary,
            isBlocked ? styles.labelBlocked : null,
          ]}
        >
          {title}
        </Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    paddingVertical: space.md,
    paddingHorizontal: space.lg,
    borderRadius: radius.full,
    alignItems: 'center',
  },
  primary: { backgroundColor: color.primary },
  secondary: { backgroundColor: 'transparent', borderWidth: 1, borderColor: color.secondary },
  pressed: { opacity: 0.88 },
  blocked: { backgroundColor: color.surfaceSunken, borderColor: color.surfaceSunken, opacity: 1 },
  content: { flexDirection: 'row', alignItems: 'center', gap: space.sm },
  // No `fontWeight` alongside a custom `fontFamily`: Inter_500Medium is a
  // distinct loaded font asset, not a weight variant of a base family — RN
  // can't synthesize a different weight from it, and asking it to try risks
  // silently falling back to the system font on native.
  label: { fontFamily: font.family.bodyMedium, fontSize: font.size.md },
  labelPrimary: { color: color.primaryText },
  labelSecondary: { color: color.secondary },
  labelBlocked: { color: color.textMuted },
});
