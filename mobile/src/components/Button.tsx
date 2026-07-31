/**
 * Primary / secondary button with a pending state.
 *
 * Replaces react-native's `Button`, which cannot show progress or be styled.
 * The pending state matters here: mail dispatch is off the request path
 * (spec FR-19 / NFR-01), but the request still has latency the user must see.
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
          <ActivityIndicator size="small" color={isPrimary ? color.primaryText : color.primary} />
        ) : null}
        <Text style={[styles.label, isPrimary ? styles.labelPrimary : styles.labelSecondary]}>
          {title}
        </Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: { paddingVertical: space.md + 2, borderRadius: radius.md, alignItems: 'center' },
  primary: { backgroundColor: color.primary },
  secondary: { backgroundColor: color.surface, borderWidth: 1, borderColor: color.border },
  pressed: { opacity: 0.85 },
  blocked: { opacity: 0.5 },
  content: { flexDirection: 'row', alignItems: 'center', gap: space.sm },
  label: { fontSize: font.size.lg, fontWeight: font.weight.semibold },
  labelPrimary: { color: color.primaryText },
  labelSecondary: { color: color.primary },
});
