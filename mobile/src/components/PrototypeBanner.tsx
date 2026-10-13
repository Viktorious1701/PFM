/**
 * Persistent "this is not real" strip.
 *
 * Deliberately loud. CLAUDE.md §5 and aif-review-checklist.md both record mobile
 * as deferred until Feature-01 is verified, and the backend has no routes yet —
 * so every figure on every screen is demo data. This banner is what stops a
 * screenshot of this app being mistaken for working software (ADR-0009).
 */
import { StyleSheet, Text, View } from 'react-native';

import { ns, nsFont } from '../theme/nullscapes';

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
    backgroundColor: ns.card,
    borderWidth: 1,
    borderColor: ns.cardBorder,
    borderLeftWidth: 3,
    borderLeftColor: ns.warning,
    marginHorizontal: 20,
    marginBottom: 12,
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 14,
    gap: 2,
  },
  label: {
    color: ns.warning,
    fontFamily: nsFont.semibold,
    fontSize: 11,
    letterSpacing: 0.6,
  },
  note: { color: ns.muted, fontFamily: nsFont.regular, fontSize: 11 },
});

export const prototypeBannerRadius = 8;
