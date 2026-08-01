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
import { color, font, radius, space } from '../theme/tokens';

const LABEL: Record<UserStatus, string> = {
  PENDING: 'Invited',
  ACTIVE: 'Active',
  DEACTIVATED: 'Deactivated',
};

export function StatusChip({ status, testID }: { status: UserStatus; testID?: string }) {
  const palette = color.status[status];

  return (
    <View testID={testID} style={[styles.chip, { backgroundColor: palette.bg }]}>
      <View style={[styles.dot, { backgroundColor: palette.dot }]} />
      <Text style={styles.label}>{LABEL[status]}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  chip: {
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.xs,
    paddingHorizontal: space.md,
    paddingVertical: space.xs,
    borderRadius: radius.full,
    overflow: 'hidden',
  },
  dot: { width: 6, height: 6, borderRadius: 3 },
  label: {
    fontFamily: font.family.bodyMedium,
    fontSize: font.size.sm,
    color: color.text,
    letterSpacing: 0.2,
  },
});
