/**
 * Which server the app talks to, under the sign-in and activation panels.
 * The phone builds carry the family server's address (constitution ENV-06);
 * Change is the way out if that server ever moves. It is always shown, so
 * nobody types a password into a server they didn't expect.
 */
import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { serverHost, setServerAddress, useServerAddress } from '../../store/server-address';
import { font, moon } from '../../theme/moonlit';
import { Button, ErrorText, Field } from '../ui/moon';

export function ServerLine() {
  const address = useServerAddress();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const [error, setError] = useState<string | null>(null);
  const open = editing || !address;

  const save = () => {
    if (!setServerAddress(draft)) {
      setError('That isn’t a server address. It looks like laptop-name.tailnet.ts.net');
      return;
    }
    setError(null);
    setEditing(false);
  };

  if (!open) {
    return (
      <View style={styles.row}>
        <Text style={styles.label}>Server</Text>
        <Text style={styles.host} numberOfLines={1} testID="server-host">
          {serverHost(address)}
        </Text>
        <Pressable
          testID="server-change"
          accessibilityRole="button"
          accessibilityLabel="Change server address"
          onPress={() => {
            setDraft(address);
            setEditing(true);
          }}
          hitSlop={8}
        >
          <Text style={styles.change}>Change</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={styles.edit}>
      <Field
        label="Server address"
        value={draft}
        onChangeText={setDraft}
        placeholder="laptop-name.tailnet.ts.net"
        keyboardType="url"
        testID="server-field"
        onSubmitEditing={save}
      />
      {error ? <ErrorText>{error}</ErrorText> : null}
      <View style={styles.actions}>
        {address ? <Button kind="ghost" small label="Cancel" onPress={() => setEditing(false)} testID="server-cancel" /> : null}
        <Button small label="Use this server" onPress={save} testID="server-save" />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  label: { fontFamily: font.semibold, fontSize: 11, letterSpacing: 2, textTransform: 'uppercase', color: moon.muted },
  host: { flex: 1, fontFamily: font.medium, fontSize: 14, color: moon.inkSoft },
  change: { fontFamily: font.semibold, fontSize: 12, letterSpacing: 2, textTransform: 'uppercase', color: moon.ink },
  edit: { gap: 10 },
  actions: { flexDirection: 'row', justifyContent: 'flex-end', gap: 8 },
});
