/**
 * Status pill for a user record.
 *
 * The wire values are UPPER_SNAKE_CASE literals (constitution NC-05); turning
 * them into readable labels is a client concern, which is why the mapping lives
 * here rather than in the API layer.
 */
import { StyleSheet, Text } from 'react-native';

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
    <Text
      testID={testID}
      style={[styles.chip, { color: palette.fg, backgroundColor: palette.bg }]}
    >
      {LABEL[status]}
    </Text>
  );
}

const styles = StyleSheet.create({
  chip: {
    alignSelf: 'flex-start',
    fontSize: font.size.xs,
    fontWeight: font.weight.bold,
    paddingHorizontal: space.sm,
    paddingVertical: space.xs,
    borderRadius: radius.sm,
    overflow: 'hidden',
    letterSpacing: 0.3,
  },
});
