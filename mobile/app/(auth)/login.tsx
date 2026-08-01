/**
 * Sign in.
 *
 * Story: SRS §6 Feature-02 · US-02-01 / SDS §5.1.1 SS-US-01
 * Endpoint: POST /api/v1/auth/login (SDS §6.3 SS-API-01)
 * Spec: specs/002-system-security/spec.md
 *
 * Implemented and verified — `backend/app/services/auth_service.py`,
 * 14 tests, 100% coverage. In mock mode (`EXPO_PUBLIC_API_MOCK=1`), the
 * PENDING-account rejection is a fixture branch; with it unset, this is the
 * real `authenticate()` service, including its precedence rule: a PENDING
 * account is refused by name regardless of the password submitted (spec
 * AC-02, since it holds no password to check), while everything else checks
 * the password first (spec AC-05, BR-01).
 */
import { Link, useRouter } from 'expo-router';
import { useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { StyleSheet, Text, View } from 'react-native';

import { ApiError, ErrorCode, fieldErrors, toApiError } from '../../src/api/errors';
import { Banner } from '../../src/components/Banner';
import { Button } from '../../src/components/Button';
import { Screen } from '../../src/components/Screen';
import { TextField } from '../../src/components/TextField';
import { USE_MOCK_API } from '../../src/config';
import { LoginIds } from '../../src/constants/elementIds';
import { useAuth } from '../../src/store/auth';
import { color, font, space } from '../../src/theme/tokens';

type FormValues = { email: string; password: string };

export default function LoginScreen() {
  const router = useRouter();
  const { signIn } = useAuth();
  const [failure, setFailure] = useState<ApiError | null>(null);

  const {
    control,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ defaultValues: { email: 'admin@example.com', password: '' } });

  const onSubmit = async ({ email, password }: FormValues) => {
    setFailure(null);
    try {
      await signIn(email, password);
      router.replace('/');
    } catch (caught) {
      const err = toApiError(caught);

      if (err.code === ErrorCode.VALIDATION_ERROR) {
        const fields = fieldErrors(err);
        if (fields.password) {
          setError('password', { message: fields.password });
          return;
        }
        if (fields.email) {
          setError('email', { message: fields.email });
          return;
        }
      }

      setFailure(err);
    }
  };

  return (
    <Screen testID={LoginIds.screen} note="SS-US-01 · POST /api/v1/auth/login">
      <View style={styles.header}>
        <Text style={styles.title}>Sign in to PFM</Text>
        <Text style={styles.description}>
          Accounts are invitation-only. If you were invited, use the activation link in your
          email before signing in.
        </Text>
      </View>

      <Controller
        control={control}
        name="email"
        rules={{ required: 'Please enter your email address' }}
        render={({ field: { onChange, onBlur, value } }) => (
          <TextField
            label="Email address"
            testID={LoginIds.emailInput}
            placeholder="you@example.com"
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
            autoComplete="email"
            editable={!isSubmitting}
            value={value}
            onChangeText={onChange}
            onBlur={onBlur}
            error={errors.email?.message}
          />
        )}
      />

      <Controller
        control={control}
        name="password"
        rules={{ required: 'Please enter your password' }}
        render={({ field: { onChange, onBlur, value } }) => (
          <TextField
            label="Password"
            testID={LoginIds.passwordInput}
            placeholder="••••••••"
            secureTextEntry
            autoCapitalize="none"
            autoComplete="current-password"
            editable={!isSubmitting}
            value={value}
            onChangeText={onChange}
            onBlur={onBlur}
            error={errors.password?.message}
          />
        )}
      />

      <Button
        title="Sign in"
        testID={LoginIds.submit}
        onPress={handleSubmit(onSubmit)}
        pending={isSubmitting}
      />

      {failure ? (
        <Banner tone="error" message={failure.message} testID={LoginIds.errorBanner} />
      ) : null}

      {USE_MOCK_API ? (
        <View style={styles.hints}>
          <Text style={styles.hintsTitle}>Fixture accounts</Text>
          <Text style={styles.hint}>
            <Text style={styles.hintKey}>admin@example.com</Text> + any password → ADMIN
          </Text>
          <Text style={styles.hint}>
            <Text style={styles.hintKey}>pending@example.com</Text> → rejected, account not
            activated (SDS §5.1.1 AC-2)
          </Text>
          <Text style={styles.hint}>
            <Text style={styles.hintKey}>wrong@example.com</Text> → incorrect credentials
          </Text>
        </View>
      ) : null}

      <Link href="/" style={styles.skip}>
        Skip to the app (prototype)
      </Link>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { gap: space.sm },
  title: { fontFamily: font.family.heading, fontSize: font.size.title, color: color.text },
  description: {
    fontFamily: font.family.body,
    fontSize: font.size.body,
    color: color.textMuted,
    lineHeight: 20,
  },
  hints: { gap: space.xs, marginTop: space.sm },
  hintsTitle: {
    fontFamily: font.family.bodyMedium,
    fontSize: font.size.xs,
    color: color.textMuted,
    letterSpacing: 0.4,
  },
  hint: { fontFamily: font.family.body, fontSize: font.size.sm, color: color.textMuted },
  hintKey: { fontFamily: 'monospace', color: color.text },
  skip: {
    marginTop: space.md,
    color: color.primary,
    fontFamily: font.family.bodyMedium,
    fontSize: font.size.md,
  },
});
