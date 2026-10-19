/**
 * Account activation (UM-US-02) over the moonlit scene — where an invited
 * member's email link lands (`/activate?token=…`). Checks the token first
 * so an expired or already-used link says so before any typing; then takes
 * a name and a password and activates the account.
 */
import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { ErrorCode, errorMessage, toApiError } from '../../api/errors';
import { activateAccount, checkTokenState } from '../../api/users';
import { font, moon } from '../../theme/moonlit';
import { Button, ErrorText, Field, Muted } from '../ui/moon';

const PASSWORD_RULE = 'At least 8 characters, with an uppercase letter, a digit and a symbol.';

type Phase = 'checking' | 'ready' | 'expired' | 'unusable' | 'done';

export function ActivatePanel({ token, onSignIn }: { token: string | null; onSignIn: () => void }) {
  const [phase, setPhase] = useState<Phase>(token ? 'checking' : 'unusable');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    checkTokenState(token)
      .then((r) => {
        if (!cancelled) setPhase(r.state === 'usable' ? 'ready' : r.state === 'expired' ? 'expired' : 'unusable');
      })
      // Can't tell: let them try, and the activation call will say why.
      .catch(() => !cancelled && setPhase('ready'));
    return () => {
      cancelled = true;
    };
  }, [token]);

  const submit = async () => {
    if (!token || busy) return;
    if (!name.trim()) return setError('Enter your name.');
    if (!password) return setError(`Choose a password. ${PASSWORD_RULE}`);
    setBusy(true);
    setError(null);
    try {
      const r = await activateAccount({ token, full_name: name.trim(), password });
      setDone(r.message);
      setPhase('done');
    } catch (e) {
      const err = toApiError(e);
      if (err.code === ErrorCode.INVITATION_TOKEN_EXPIRED) setPhase('expired');
      else if (err.code === ErrorCode.INVITATION_TOKEN_INVALID) setPhase('unusable');
      else {
        setError(errorMessage(err));
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.panel} testID="activate-panel">
      <Text style={styles.eyebrow}>Family finance</Text>
      <Text style={styles.title}>{phase === 'done' ? 'You’re in' : 'Set up your account'}</Text>

      {phase === 'checking' ? (
        <Muted>Checking your invitation…</Muted>
      ) : phase === 'expired' ? (
        <>
          <Text style={styles.body} accessibilityRole="alert" testID="activate-expired">
            This invitation has expired. Ask the person who invited you to send a new one.
          </Text>
          <Button kind="ghost" label="Go to sign in" onPress={onSignIn} />
        </>
      ) : phase === 'unusable' ? (
        <>
          <Text style={styles.body} accessibilityRole="alert" testID="activate-unusable">
            This invitation link isn’t valid, or it has already been used. If you’ve already set up your account, sign in.
          </Text>
          <Button kind="ghost" label="Go to sign in" onPress={onSignIn} />
        </>
      ) : phase === 'done' ? (
        <>
          <Text style={styles.success} accessibilityRole="alert" testID="activate-done">
            {done ?? 'Your account is active.'}
          </Text>
          <Button label="Go to sign in" onPress={onSignIn} testID="activate-signin" />
        </>
      ) : (
        <>
          <Muted>You’ve been invited. Choose the name your family will see and a password.</Muted>
          <Field label="Your name" value={name} onChangeText={setName} placeholder="e.g. Linh Nguyen" testID="activate-name" autoFocus />
          <Field label="Password" value={password} onChangeText={setPassword} secure testID="activate-password" onSubmitEditing={submit} />
          <Text style={styles.hint}>{PASSWORD_RULE}</Text>
          {error ? <ErrorText>{error}</ErrorText> : null}
          <Button label="Activate account" onPress={submit} busy={busy} testID="activate-submit" />
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  panel: {
    width: '100%',
    maxWidth: 380,
    alignSelf: 'center',
    padding: 28,
    gap: 14,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: moon.panelBorder,
    backgroundColor: moon.panel,
  },
  eyebrow: { fontFamily: font.semibold, fontSize: 12, letterSpacing: 3, textTransform: 'uppercase', color: moon.muted },
  title: { fontFamily: font.light, fontSize: 32, color: moon.ink, marginTop: -8, letterSpacing: 1 },
  body: { fontFamily: font.medium, fontSize: 16, color: moon.inkSoft },
  success: { fontFamily: font.medium, fontSize: 16, color: moon.income },
  hint: { fontFamily: font.medium, fontSize: 13, color: moon.muted, marginTop: -6 },
});
