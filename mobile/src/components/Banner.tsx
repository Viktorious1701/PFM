/**
 * Inline success / error / info message.
 *
 * Replaces `alert()`, which is a browser global rather than a React Native API:
 * it happens to work on Expo web but is undefined on a device, so a screen built
 * around it cannot survive the native round.
 */
import type { ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { color, font, radius, space } from '../theme/tokens';

type Tone = 'success' | 'error' | 'info';

const TONE = {
  success: color.success,
  error: color.error,
  info: color.info,
} as const;

type Props = {
  tone: Tone;
  /** Short, user-facing. Error copy comes from the API envelope's `message`. */
  message: string;
  /** Optional supporting detail, e.g. the returned record. */
  children?: ReactNode;
  testID?: string;
};

export function Banner({ tone, message, children, testID }: Props) {
  const palette = TONE[tone];

  return (
    <View
      testID={testID}
      accessibilityRole={tone === 'error' ? 'alert' : undefined}
      accessibilityLiveRegion={tone === 'error' ? 'assertive' : 'polite'}
      style={[styles.container, { backgroundColor: palette.bg, borderLeftColor: palette.accent }]}
    >
      <Text style={[styles.message, { color: palette.fg }]}>{message}</Text>
      {children ? <View style={styles.detail}>{children}</View> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderLeftWidth: 4,
    borderRadius: radius.md,
    padding: space.md,
    gap: space.sm,
  },
  message: { fontSize: font.size.body, fontWeight: font.weight.semibold, lineHeight: 20 },
  detail: { gap: space.xs },
});
