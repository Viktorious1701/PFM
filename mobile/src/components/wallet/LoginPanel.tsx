/**
 * Sign-in over the moonlit scene. Real `POST /auth/login` through the
 * session store; the backend's message is shown as-is, since it already
 * collapses unknown email / wrong password into one outcome.
 *
 * SS-US-03 adds the guest trial under Sign in: "Try as a guest" always starts
 * a new trial (AC-01, AC-19); "Continue guest trial — N days left" continues
 * the device's saved one while it has not ended (AC-16, plan.md A19); and
 * "Your guest trial has ended." when the server has refused it (AC-18, EC-12).
 */
import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { errorMessage } from '../../api/errors';
import { trialDaysLeft, trialHasEnded, useAuth } from '../../store/auth';
import { useServerAddress } from '../../store/server-address';
import { font, moon } from '../../theme/moonlit';
import { ServerLine } from './ServerLine';

export function LoginPanel() {
  const { signIn, signInAsGuest, continueGuestTrial, forgetEndedGuestTrial, savedGuestTrial, guestTrialEnded } = useAuth();
  const server = useServerAddress();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [focused, setFocused] = useState<'email' | 'password' | null>(null);
  const [guestBusy, setGuestBusy] = useState<'new' | 'continue' | null>(null);

  // AC-17: a saved trial already past its end by this device's clock is
  // dropped here — no request and no message (plan.md A18).
  const savedLive = savedGuestTrial !== null && !trialHasEnded(savedGuestTrial.expiresAt);
  useEffect(() => {
    if (savedGuestTrial && !savedLive) void forgetEndedGuestTrial();
  }, [savedGuestTrial, savedLive, forgetEndedGuestTrial]);
  const daysLeft = savedLive ? trialDaysLeft(savedGuestTrial.expiresAt) : 0;

  const runGuest = async (which: 'new' | 'continue') => {
    if (busy || guestBusy) return;
    if (!server) {
      setError('Enter the server address below first.');
      return;
    }
    setGuestBusy(which);
    setError(null);
    try {
      if (which === 'new') await signInAsGuest();
      else await continueGuestTrial();
    } catch (e) {
      // A 429 / 503 / connection failure: the server's own message.
      setError(errorMessage(e));
    }
    setGuestBusy(null);
  };

  const submit = async () => {
    if (busy) return;
    if (!server) {
      setError('Enter the server address below first.');
      return;
    }
    if (!email.trim() || !password) {
      setError('Enter your email and password.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await signIn(email.trim(), password);
    } catch (e) {
      setError(errorMessage(e));
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
      {guestTrialEnded && !error ? (
        <Text style={styles.error} accessibilityRole="alert" testID="guest-trial-ended">
          Your guest trial has ended.
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

      <Pressable
        testID="login-guest"
        accessibilityRole="button"
        onPress={() => void runGuest('new')}
        disabled={guestBusy !== null}
        style={({ pressed }) => [styles.ghost, (pressed || guestBusy === 'new') && styles.buttonPressed]}
      >
        {guestBusy === 'new' ? <ActivityIndicator color={moon.ink} /> : <Text style={styles.ghostLabel}>Try as a guest</Text>}
      </Pressable>

      {savedLive ? (
        <Pressable
          testID="guest-continue"
          accessibilityRole="button"
          onPress={() => void runGuest('continue')}
          disabled={guestBusy !== null}
          style={({ pressed }) => [styles.ghost, (pressed || guestBusy === 'continue') && styles.buttonPressed]}
        >
          {guestBusy === 'continue' ? (
            <ActivityIndicator color={moon.ink} />
          ) : (
            <Text style={styles.ghostLabel}>
              {`Continue guest trial — ${daysLeft} ${daysLeft === 1 ? 'day' : 'days'} left`}
            </Text>
          )}
        </Pressable>
      ) : null}

      <View style={styles.divider} />
      <ServerLine />
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
  ghost: {
    minHeight: 42,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: moon.fieldBorder,
    backgroundColor: 'rgba(10,18,32,0.55)',
  },
  ghostLabel: {
    fontFamily: font.semibold,
    fontSize: 13,
    letterSpacing: 2,
    textTransform: 'uppercase',
    color: moon.ink,
    textAlign: 'center',
  },
  divider: { height: 1, backgroundColor: moon.panelBorder, marginTop: 4 },
  buttonLabel: {
    fontFamily: font.bold,
    fontSize: 14,
    letterSpacing: 3,
    textTransform: 'uppercase',
    color: '#0c1727',
  },
});
