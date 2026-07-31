/**
 * Persistent "this is not real" strip.
 *
 * Deliberately loud. CLAUDE.md §5 and aif-review-checklist.md both record mobile
 * as deferred until Feature-01 is verified, and the backend has no routes yet —
 * so every figure on every screen is demo data. This banner is what stops a
 * screenshot of this app being mistaken for working software (ADR-0009).
 */
import { StyleSheet, Text, View } from 'react-native';

import { color, font, radius, space } from '../theme/tokens';

export function PrototypeBanner({ note }: { note?: string }) {
  return (
    <View style={styles.container}>
      <Text style={styles.label}>PROTOTYPE — demo data, no backend</Text>
      {note ? <Text style={styles.note}>{note}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: color.prototype.bg,
    borderLeftWidth: 4,
    borderLeftColor: color.prototype.border,
    paddingVertical: space.sm,
    paddingHorizontal: space.md,
    gap: 2,
  },
  label: {
    color: color.prototype.fg,
    fontSize: font.size.xs,
    fontWeight: font.weight.bold,
    letterSpacing: 0.4,
  },
  note: { color: color.prototype.fg, fontSize: font.size.xs },
});

export const prototypeBannerRadius = radius.sm;
