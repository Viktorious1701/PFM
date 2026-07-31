/**
 * Family members (list users).
 *
 * Story: SRS §6 Feature-01 · US-01-03 / SDS §5.2.3 UM-US-03
 * Endpoint: GET /api/v1/users (SDS §6.3 UM-API-03)
 *
 * BOILERPLATE. UM-US-03 is listed 3rd in the epic and is not specified yet —
 * `specs/001-user-onboarding/spec.md` covers UM-US-01 only, and lists
 * UM-US-02/03 as *pending*. This screen shows the shape a reviewer needs to see
 * (statuses are legible at a glance) and nothing more. Rows come from fixtures.
 */
import { Link } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { toApiError } from '../../../src/api/errors';
import type { UserRead } from '../../../src/api/types';
import { listUsers } from '../../../src/api/users';
import { Banner } from '../../../src/components/Banner';
import { Screen } from '../../../src/components/Screen';
import { StatusChip } from '../../../src/components/StatusChip';
import { UsersIds } from '../../../src/constants/elementIds';
import { color, font, radius, space } from '../../../src/theme/tokens';

export default function UsersScreen() {
  const [users, setUsers] = useState<UserRead[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const page = await listUsers();
        if (!cancelled) setUsers(page.items);
      } catch (caught) {
        if (!cancelled) setError(toApiError(caught).message);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Screen testID={UsersIds.screen} note="UM-US-03 · not yet specified — boilerplate only">
      <Link href="/(tabs)/users/invite" style={styles.cta} testID={UsersIds.inviteCta}>
        📧 Invite a family member
      </Link>

      {error ? <Banner tone="error" message={error} /> : null}

      {users === null && !error ? (
        <View style={styles.loading}>
          <ActivityIndicator color={color.primary} />
        </View>
      ) : null}

      {users ? (
        <View style={styles.list} testID={UsersIds.list}>
          {users.map((user) => (
            <View key={user.id} style={styles.row} testID={UsersIds.row(user.id)}>
              <View style={styles.rowMain}>
                <Text style={styles.name}>{user.full_name ?? '— not yet activated —'}</Text>
                <Text style={styles.email}>{user.email}</Text>
              </View>
              <View style={styles.rowMeta}>
                <StatusChip status={user.status} testID={UsersIds.statusChip(user.id)} />
                {user.role === 'ADMIN' ? <Text style={styles.role}>ADMIN</Text> : null}
              </View>
            </View>
          ))}
        </View>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  cta: { color: color.primary, fontSize: font.size.md, fontWeight: font.weight.semibold },
  loading: { paddingVertical: space.xl },
  list: { gap: space.sm },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: space.md,
    padding: space.md,
    backgroundColor: color.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: color.border,
  },
  rowMain: { flex: 1, gap: 2 },
  rowMeta: { alignItems: 'flex-end', gap: space.xs },
  name: { fontSize: font.size.md, fontWeight: font.weight.semibold, color: color.text },
  email: { fontSize: font.size.sm, color: color.textMuted },
  role: { fontSize: font.size.xs, fontWeight: font.weight.bold, color: color.textMuted },
});
