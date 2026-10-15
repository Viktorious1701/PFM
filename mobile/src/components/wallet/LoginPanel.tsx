/**
 * Sign-in over the moonlit scene. Real `POST /auth/login` through the
 * session store; the backend's message is shown as-is, since it already
 * collapses unknown email / wrong password into one outcome.
 */
import { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { toApiError } from '../../api/errors';
import { useAuth } from '../../store/auth';
import { font, moon } from '../../theme/moonlit';

export function LoginPanel() {
  const { signIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [focused, setFocused] = useState<'email' | 'password' | null>(null);

  const submit = async () => {
    if (busy) return;
    if (!email.trim() || !password) {
      setError('Enter your email and password.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await signIn(email.trim(), password);
    } catch (e) {
      setError(toApiError(e).message);
      setBusy(false);
    }
  };

  return (
    <View style={styles.panel}>
      <Text style={styles.eyebrow}>Family finance</Text>
      <Text style={styles.title}>Sign in</Text>

      <View style={styles.fieldGroup}>
        <Text style={styles.label} nativeID="email-label">Email</Text>
        <TextInput
          testID="login-email"
          accessibilityLabelledBy="email-label"
          value={email}
          onChangeText={setEmail}
          onFocus={() => setFocused('email')}
          onBlur={() => setFocused(null)}
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          placeholder="you@example.com"
          placeholderTextColor={moon.muted}
          style={[styles.input, focused === 'email' && styles.inputFocused]}
          onSubmitEditing={submit}
        />
      </View>

      <View style={styles.fieldGroup}>
        <Text style={styles.label} nativeID="password-label">Password</Text>
        <TextInput
          testID="login-password"
          accessibilityLabelledBy="password-label"
          value={password}
          onChangeText={setPassword}
          onFocus={() => setFocused('password')}
          onBlur={() => setFocused(null)}
          secureTextEntry
          autoComplete="current-password"
          style={[styles.input, focused === 'password' && styles.inputFocused]}
          onSubmitEditing={submit}
        />
      </View>

      {error ? (
        <Text style={styles.error} accessibilityRole="alert">
          {error}
        </Text>
      ) : null}

      <Pressable
        testID="login-submit"
        accessibilityRole="button"
        onPress={submit}
        disabled={busy}
        style={({ pressed }) => [styles.button, (pressed || busy) && styles.buttonPressed]}
      >
        {busy ? <ActivityIndicator color={moon.ink} /> : <Text style={styles.buttonLabel}>Sign in</Text>}
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  panel: {
    width: '100%',
    maxWidth: 380,
    alignSelf: 'center',
    padding: 28,
    gap: 16,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: moon.panelBorder,
    backgroundColor: moon.panel,
  },
  eyebrow: {
    fontFamily: font.semibold,
    fontSize: 12,
    letterSpacing: 3,
    textTransform: 'uppercase',
    color: moon.muted,
  },
  title: { fontFamily: font.light, fontSize: 34, color: moon.ink, marginTop: -10, letterSpacing: 1 },
  fieldGroup: { gap: 6 },
  label: {
    fontFamily: font.semibold,
    fontSize: 12,
    letterSpacing: 2,
    textTransform: 'uppercase',
    color: moon.inkSoft,
  },
  input: {
    fontFamily: font.medium,
    fontSize: 17,
    color: moon.ink,
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: moon.fieldBorder,
    backgroundColor: moon.field,
  },
  inputFocused: { borderColor: moon.focus },
  error: { fontFamily: font.medium, fontSize: 15, color: moon.danger },
  button: {
    marginTop: 4,
    height: 46,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 999,
    backgroundColor: 'rgba(223,232,251,0.9)',
  },
  buttonPressed: { opacity: 0.75 },
  buttonLabel: {
    fontFamily: font.bold,
    fontSize: 14,
    letterSpacing: 3,
    textTransform: 'uppercase',
    color: '#0c1727',
  },
});
