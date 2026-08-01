/**
 * Family members (list users).
 *
 * Story: SRS §6 Feature-01 · US-01-03 / SDS §5.2.3 UM-US-03
 * Endpoint: GET /api/v1/users (SDS §6.3 UM-API-03)
 *
 * UM-US-03 is listed 3rd in the epic and is not specified or built yet —
 * `specs/001-user-onboarding/spec.md` covers UM-US-01/02 only. In mock mode
 * this screen shows fixture rows; against the real backend the route simply
 * does not exist, so the request 404s — handled below as "not built yet",
 * not as a broken feature.
 *
 * Also hosts the Family > Invites dev tool (UM-US-01 A13/A14): reading
 * recently-sent activation links from the file outbox, gated by
 * SHOW_DEV_TOOLS so it can never be mistaken for a real feature.
 */
import { Link } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Platform, StyleSheet, Text, View } from 'react-native';

import { getOutbox } from '../../../src/api/dev';
import { ErrorCode, toApiError } from '../../../src/api/errors';
import type { OutboxMessage, UserRead } from '../../../src/api/types';
import { listUsers } from '../../../src/api/users';
import { Banner } from '../../../src/components/Banner';
import { Button } from '../../../src/components/Button';
import { PrototypeBanner } from '../../../src/components/PrototypeBanner';
import { Screen } from '../../../src/components/Screen';
import { StatusChip } from '../../../src/components/StatusChip';
import { SHOW_DEV_TOOLS, USE_MOCK_API } from '../../../src/config';
import { UsersIds } from '../../../src/constants/elementIds';
import { color, font, radius, space } from '../../../src/theme/tokens';

export default function UsersScreen() {
  const [users, setUsers] = useState<UserRead[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notBuilt, setNotBuilt] = useState(false);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const page = await listUsers();
        if (!cancelled) setUsers(page.items);
      } catch (caught) {
        if (cancelled) return;
        const err = toApiError(caught);
        if (err.code === ErrorCode.NOT_FOUND) {
          setNotBuilt(true);
        } else {
          setError(err.message);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Screen testID={UsersIds.screen} note="UM-US-03 · GET /api/v1/users — not built yet">
      <Link href="/(tabs)/users/invite" style={styles.cta} testID={UsersIds.inviteCta}>
        📧 Invite a family member
      </Link>

      {error ? <Banner tone="error" message={error} /> : null}

      {notBuilt ? (
        <Banner tone="info" message="Family list isn't built yet — UM-US-03 is still pending." />
      ) : null}

      {users === null && !error && !notBuilt ? (
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

      {SHOW_DEV_TOOLS && !USE_MOCK_API ? <OutboxSection /> : null}
    </Screen>
  );
}

/**
 * Reads recently-sent activation links via GET /api/v1/dev/outbox
 * (ADMIN, non-production only — 404s server-side otherwise). Exists because
 * this environment has no convenient mailbox to check for every invite sent
 * during testing (UM-US-01 A13/A14).
 */
function OutboxSection() {
  const [messages, setMessages] = useState<OutboxMessage[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null);

  const load = async () => {
    setError(null);
    try {
      const result = await getOutbox();
      setMessages(result.messages);
    } catch (caught) {
      setError(toApiError(caught).message);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const copyLink = async (url: string) => {
    if (Platform.OS === 'web' && globalThis.navigator?.clipboard) {
      await globalThis.navigator.clipboard.writeText(url);
    }
    setCopiedUrl(url);
  };

  return (
    <View style={styles.outbox}>
      <PrototypeBanner note="Dev tool — reads the file outbox (EMAIL_TRANSPORT=outbox), not a real feature" />
      <View style={styles.outboxHeader}>
        <Text style={styles.outboxTitle}>Recent activation links</Text>
        <Button title="Refresh" variant="secondary" onPress={() => void load()} />
      </View>

      {error ? <Banner tone="error" message={error} /> : null}

      {messages && messages.length === 0 ? (
        <Text style={styles.outboxEmpty}>
          Nothing sent yet — invite someone, then refresh.
        </Text>
      ) : null}

      {messages?.map((message, index) => (
        <View key={`${message.to}-${index}`} style={styles.outboxRow}>
          <View style={styles.rowMain}>
            <Text style={styles.name}>{message.to}</Text>
            <Text style={styles.email} numberOfLines={1}>
              {message.activation_url ?? 'no link found in this message'}
            </Text>
          </View>
          {message.activation_url ? (
            <Button
              title={copiedUrl === message.activation_url ? 'Copied' : 'Copy link'}
              variant="secondary"
              onPress={() => void copyLink(message.activation_url as string)}
            />
          ) : null}
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  cta: { color: color.primary, fontFamily: font.family.bodyMedium, fontSize: font.size.md },
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
  name: { fontFamily: font.family.headingSemibold, fontSize: font.size.md, color: color.text },
  email: { fontFamily: font.family.body, fontSize: font.size.sm, color: color.textMuted },
  role: {
    fontFamily: font.family.bodyMedium,
    fontSize: font.size.xs,
    color: color.textMuted,
  },
  outbox: { marginTop: space.md, gap: space.sm },
  outboxHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  outboxTitle: { fontFamily: font.family.headingSemibold, fontSize: font.size.xl, color: color.text },
  outboxEmpty: { fontFamily: font.family.body, fontSize: font.size.sm, color: color.textMuted },
  outboxRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: space.md,
    padding: space.md,
    backgroundColor: color.surfaceSunken,
    borderRadius: radius.md,
  },
});
