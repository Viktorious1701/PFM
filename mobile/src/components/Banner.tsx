/**
 * Inline success / error / info message.
 *
 * Replaces `alert()`, which is a browser global rather than a React Native API:
 * it happens to work on Expo web but is undefined on a device, so a screen built
 * around it cannot survive the native round.
 */
import type { ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { ns, nsFont } from '../theme/nullscapes';
import { color, font, radius, space } from '../theme/tokens';

type Tone = 'success' | 'error' | 'info';

const TONE = {
  success: color.success,
  error: color.error,
  info: color.info,
} as const;

// Nullscapes palette — mint/danger/muted-ink rather than the Cash & Carry
// success/error/info tones above. `color.*` versions stay the default so the
// two screens outside the Tabs group (sign-in, activation) need no changes.
const NS_TONE = {
  success: { bg: ns.card, fg: ns.mint, accent: ns.mint },
  error: { bg: ns.card, fg: ns.danger, accent: ns.danger },
  info: { bg: ns.card, fg: ns.muted, accent: ns.mintBorder },
} as const;

type Props = {
  tone: Tone;
  /** Short, user-facing. Error copy comes from the API envelope's `message`. */
  message: string;
  /** Optional supporting detail, e.g. the returned record. */
  children?: ReactNode;
  testID?: string;
  /** 'cash-carry' (default): every screen outside the Tabs group, and any
   * Tabs screen not yet reskinned. 'nullscapes': the dark glass-card
   * treatment, for screens already on the Nullscapes visual system. */
  variant?: 'cash-carry' | 'nullscapes';
};

export function Banner({ tone, message, children, testID, variant = 'cash-carry' }: Props) {
  const isNullscapes = variant === 'nullscapes';
  const palette = isNullscapes ? NS_TONE[tone] : TONE[tone];

  return (
    <View
      testID={testID}
      accessibilityRole={tone === 'error' ? 'alert' : undefined}
      accessibilityLiveRegion={tone === 'error' ? 'assertive' : 'polite'}
      style={[
        styles.container,
        isNullscapes ? styles.containerNullscapes : null,
        { backgroundColor: palette.bg, borderLeftColor: palette.accent },
      ]}
    >
      <Text style={[styles.message, isNullscapes ? styles.messageNullscapes : null, { color: palette.fg }]}>
        {message}
      </Text>
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
  containerNullscapes: { borderRadius: 10, borderWidth: 1, borderColor: ns.cardBorder },
  message: {
    fontFamily: font.family.bodyMedium,
    fontSize: font.size.body,
    lineHeight: 20,
  },
  messageNullscapes: { fontFamily: nsFont.medium, fontSize: 13, lineHeight: 18 },
  detail: { gap: space.xs },
});
