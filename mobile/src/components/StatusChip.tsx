/**
 * Status pill for a user record.
 *
 * The wire values are UPPER_SNAKE_CASE literals (constitution NC-05); turning
 * them into readable labels is a client concern, which is why the mapping lives
 * here rather than in the API layer.
 *
 * Per DESIGN.md "status-pill": the label always stays `ink` — the status hue
 * fails AA as small text on the sunken pill — and meaning lives in a leading
 * coloured dot instead.
 */
import { StyleSheet, Text, View } from 'react-native';

import type { UserStatus } from '../api/types';
import { ns, nsFont } from '../theme/nullscapes';

const LABEL: Record<UserStatus, string> = {
  PENDING: 'Invited',
  ACTIVE: 'Active',
  DEACTIVATED: 'Deactivated',
};

const DOT_COLOR: Record<UserStatus, string> = {
  PENDING: ns.warning,
  ACTIVE: ns.mint,
  DEACTIVATED: ns.mutedFaint,
};

export function StatusChip({ status, testID }: { status: UserStatus; testID?: string }) {
  return (
    <View testID={testID} style={styles.chip}>
      <View style={[styles.dot, { backgroundColor: DOT_COLOR[status] }]} />
      <Text style={styles.label}>{LABEL[status]}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  chip: {
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 9999,
    borderWidth: 1,
    borderColor: ns.cardBorder,
    backgroundColor: ns.card,
    overflow: 'hidden',
  },
  dot: { width: 6, height: 6, borderRadius: 3 },
  label: {
    fontFamily: nsFont.medium,
    fontSize: 12,
    color: ns.ink,
    letterSpacing: 0.2,
  },
});
