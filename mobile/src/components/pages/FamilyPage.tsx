/**
 * Family tab (ADMIN only — the tab is hidden for everyone else): the
 * family's members with their account status, and inviting someone by
 * email. The invitation link goes to their inbox; they appear here as
 * pending until they activate.
 */
import { useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { errorMessage } from '../../api/errors';
import type { UserStatus } from '../../api/types';
import { inviteUser, listUsers } from '../../api/users';
import { font, moon } from '../../theme/moonlit';
import { dayLabel } from '../../utils/format';
import { useLoad } from '../../utils/useLoad';
import { Button, ErrorText, Field, LoadError, Loading, Muted, Panel, SectionHead, ui } from '../ui/moon';

const STATUS: Record<UserStatus, { label: string; color: string }> = {
  ACTIVE: { label: 'Active', color: moon.income },
  PENDING: { label: 'Invited', color: moon.warning },
  DEACTIVATED: { label: 'Deactivated', color: moon.muted },
};

function Invite({ onSent }: { onSent: () => void }) {
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState<string | null>(null);

  const submit = async () => {
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) return setError('Enter an email address, like name@example.com.');
    setBusy(true);
    setError(null);
    setSent(null);
    try {
      const r = await inviteUser(email.trim());
      setSent(r.message || `Invitation sent to ${r.email}.`);
      setEmail('');
      onSent();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel style={styles.form} testID="invite-form">
      <Text style={styles.formTitle}>Invite a family member</Text>
      <Muted>They get an email with a link to set up their account. The link works for 24 hours.</Muted>
      <View style={styles.inline}>
        <View style={styles.grow}>
          <Field label="Email" value={email} onChangeText={setEmail} placeholder="name@example.com" keyboardType="email-address" testID="invite-email" onSubmitEditing={submit} />
        </View>
        <Button label="Send invite" onPress={submit} busy={busy} testID="invite-submit" />
      </View>
      {error ? <ErrorText>{error}</ErrorText> : null}
      {sent ? (
        <Text style={styles.sent} accessibilityRole="alert">
          {sent}
        </Text>
      ) : null}
    </Panel>
  );
}

export function FamilyPage() {
  const { data, error, reload } = useLoad(async () => (await listUsers(1, 100)).items);

  return (
    <ScrollView contentContainerStyle={styles.scroll}>
      <View style={ui.column}>
        <View style={ui.section}>
          <SectionHead title="Family" right={data ? `${data.length} ${data.length === 1 ? 'member' : 'members'}` : undefined} />
          <Invite onSent={() => void reload()} />
          {error ? (
            <LoadError message={error} onRetry={() => void reload()} />
          ) : !data ? (
            <Loading label="Loading family" />
          ) : (
            <Panel style={styles.list}>
              {data.map((u, i) => {
                const st = STATUS[u.status] ?? STATUS.PENDING;
                return (
                  <View key={u.id}>
                    {i > 0 ? <View style={styles.divider} /> : null}
                    <View style={styles.row} testID={`member-${u.email}`}>
                      <View style={styles.rowText}>
                        <Text style={styles.name} numberOfLines={1}>
                          {u.full_name || u.email}
                        </Text>
                        <Text style={styles.meta} numberOfLines={1}>
                          {u.full_name ? `${u.email} · ` : ''}since {dayLabel(u.created_at)}
                        </Text>
                      </View>
                      <View style={styles.statusPill}>
                        <View style={[styles.dot, { backgroundColor: st.color }]} />
                        <Text style={styles.statusText}>{st.label}</Text>
                      </View>
                    </View>
                  </View>
                );
              })}
            </Panel>
          )}
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { paddingTop: 4, paddingBottom: 120 },
  form: { gap: 12 },
  formTitle: { fontFamily: font.semibold, fontSize: 18, color: moon.ink },
  inline: { flexDirection: 'row', alignItems: 'flex-end', gap: 8, flexWrap: 'wrap' },
  grow: { flexGrow: 1, flexBasis: 220 },
  sent: { fontFamily: font.medium, fontSize: 15, color: moon.income },
  list: { paddingVertical: 4, paddingHorizontal: 16 },
  divider: { height: 1, backgroundColor: moon.hairline },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 12 },
  rowText: { flex: 1, minWidth: 0, gap: 2 },
  name: { fontFamily: font.semibold, fontSize: 16, color: moon.ink },
  meta: { fontFamily: font.medium, fontSize: 13, color: moon.muted },
  statusPill: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  statusText: { fontFamily: font.semibold, fontSize: 13, color: moon.inkSoft },
});
