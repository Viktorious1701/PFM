/**
 * Sign in.
 *
 * Story: SRS §6 Feature-02 · US-02-01 / SDS §5.1.1 SS-US-01
 * Endpoint: POST /api/v1/auth/login (SDS §6.3 SS-API-01)
 *
 * BOILERPLATE. SS-US-01 belongs to specs/002-system-security/, which does not
 * exist yet — no spec, no plan, no test cases. This screen exists because the
 * invite story's AC-04/AC-05 need an authenticated ADMIN to stand behind, and a
 * 401 has to land somewhere. Nothing here is a substitute for specifying login.
 *
 * The PENDING-account rejection (SDS §5.1.1 AC-2 / spec BR-06) is demonstrated
 * as a fixture branch, not implemented logic.
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
    <Screen testID={LoginIds.screen} note="SS-US-01 · not yet specified — boilerplate only">
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
  title: { fontSize: font.size.title, fontWeight: font.weight.bold, color: color.text },
  description: { fontSize: font.size.body, color: color.textMuted, lineHeight: 20 },
  hints: { gap: space.xs, marginTop: space.sm },
  hintsTitle: {
    fontSize: font.size.xs,
    fontWeight: font.weight.bold,
    color: color.textMuted,
    letterSpacing: 0.4,
  },
  hint: { fontSize: font.size.sm, color: color.textMuted },
  hintKey: { fontFamily: 'monospace', color: color.text },
  skip: {
    marginTop: space.md,
    color: color.primary,
    fontSize: font.size.md,
    fontWeight: font.weight.medium,
  },
});
