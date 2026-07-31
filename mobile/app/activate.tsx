/**
 * Complete account activation.
 *
 * Story: SRS §6 Feature-01 · US-01-02 / SDS §5.2.2 UM-US-02
 * Endpoint: POST /api/v1/users/activate (SDS §6.4.2)
 *
 * BOILERPLATE. UM-US-02 is listed 2nd in the epic and is *pending* in
 * specs/001-user-onboarding/spec.md, whose "Out of scope" section names it
 * explicitly. The single-page Name + Password form follows UXR-04.
 *
 * The token is never displayed. The invited user legitimately holds it — it came
 * from their own email — but printing it on screen or passing it to an alert
 * normalises token display, and the same habit in a log would breach
 * constitution LA-01 / SEC-01. Only its presence is confirmed.
 *
 * Deep link: `pfm://activate?token=…` on native (scheme is set in app.json).
 * On web the equivalent is http://localhost:8081/activate?token=demo
 * Use `?token=expired` to see the expiry path (SDS §2.4.2, spec BR-04).
 */
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { StyleSheet, Text, View } from 'react-native';

import { ApiError, ErrorCode, fieldErrors, toApiError } from '../src/api/errors';
import { activateAccount } from '../src/api/users';
import { Banner } from '../src/components/Banner';
import { Button } from '../src/components/Button';
import { Screen } from '../src/components/Screen';
import { TextField } from '../src/components/TextField';
import { ActivateIds } from '../src/constants/elementIds';
import { color, font, space } from '../src/theme/tokens';

type FormValues = { fullName: string; password: string };

export default function ActivateScreen() {
  const { token } = useLocalSearchParams<{ token?: string }>();
  const router = useRouter();

  const [failure, setFailure] = useState<ApiError | null>(null);
  const [succeeded, setSucceeded] = useState<string | null>(null);

  const {
    control,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ defaultValues: { fullName: '', password: '' } });

  const onSubmit = async ({ fullName, password }: FormValues) => {
    setFailure(null);
    try {
      const result = await activateAccount({
        token: token ?? '',
        full_name: fullName,
        password,
      });
      setSucceeded(result.message);
    } catch (caught) {
      const err = toApiError(caught);

      if (err.code === ErrorCode.VALIDATION_ERROR) {
        const fields = fieldErrors(err);
        if (fields.password) {
          setError('password', { message: fields.password });
          return;
        }
        if (fields.full_name) {
          setError('fullName', { message: fields.full_name });
          return;
        }
      }

      setFailure(err);
    }
  };

  return (
    <Screen testID={ActivateIds.screen} note="UM-US-02 · not yet specified — boilerplate only">
      <View style={styles.header}>
        <Text style={styles.title}>Complete Account Activation</Text>
        <Text style={styles.description}>
          Choose your name and a password to finish setting up your account.
        </Text>
        <Text style={styles.tokenState}>
          {token
            ? 'Activation link recognised.'
            : 'No activation token in this link — open the link from your invitation email.'}
        </Text>
      </View>

      {succeeded ? (
        <>
          <Banner tone="success" message={succeeded} testID={ActivateIds.successBanner} />
          <Button title="Go to sign in" onPress={() => router.replace('/(auth)/login')} />
        </>
      ) : (
        <>
          <Controller
            control={control}
            name="fullName"
            rules={{ required: 'Please enter your full name' }}
            render={({ field: { onChange, onBlur, value } }) => (
              <TextField
                label="Full name"
                testID={ActivateIds.fullNameInput}
                placeholder="Jane Doe"
                autoComplete="name"
                editable={!isSubmitting}
                value={value}
                onChangeText={onChange}
                onBlur={onBlur}
                error={errors.fullName?.message}
              />
            )}
          />

          <Controller
            control={control}
            name="password"
            rules={{ required: 'Please choose a password' }}
            render={({ field: { onChange, onBlur, value } }) => (
              <TextField
                label="Password"
                testID={ActivateIds.passwordInput}
                placeholder="••••••••"
                secureTextEntry
                autoCapitalize="none"
                autoComplete="new-password"
                editable={!isSubmitting}
                value={value}
                onChangeText={onChange}
                onBlur={onBlur}
                error={errors.password?.message}
                hint="The server enforces the real password policy (constitution VL-04)."
              />
            )}
          />

          <Button
            title="Activate Account"
            testID={ActivateIds.submit}
            onPress={handleSubmit(onSubmit)}
            pending={isSubmitting}
            disabled={!token}
          />

          {failure ? (
            <Banner tone="error" message={failure.message} testID={ActivateIds.errorBanner} />
          ) : null}
        </>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { gap: space.sm },
  title: { fontSize: font.size.title, fontWeight: font.weight.bold, color: color.text },
  description: { fontSize: font.size.body, color: color.textMuted, lineHeight: 20 },
  tokenState: { fontSize: font.size.sm, color: color.textMuted, fontStyle: 'italic' },
});
