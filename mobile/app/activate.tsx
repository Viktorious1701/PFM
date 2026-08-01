import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { StyleSheet, Text, View } from 'react-native';

import { ApiError, ErrorCode, fieldErrors, toApiError } from '../src/api/errors';
import { activateAccount, checkTokenState } from '../src/api/users';
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
  const [tokenUsable, setTokenUsable] = useState<boolean>(true);

  const {
    control,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ defaultValues: { fullName: '', password: '' } });

  useEffect(() => {
    if (!token) return;
    let cancelled = false;

    (async () => {
      try {
        const stateResult = await checkTokenState(token);
        if (cancelled) return;
        if (stateResult.state === 'expired') {
          setTokenUsable(false);
          setFailure(
            new ApiError(
              'INVITATION_TOKEN_EXPIRED',
              'The provided invitation link has expired. Please request a new invitation.',
              400
            )
          );
        } else if (stateResult.state === 'not_usable') {
          setTokenUsable(false);
          setFailure(
            new ApiError(
              'INVITATION_TOKEN_INVALID',
              'The provided invitation link is invalid or has already been used.',
              400
            )
          );
        }
      } catch {
        // Fallback: user can still attempt submission
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [token]);

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
    <Screen testID={ActivateIds.screen} note="UM-US-02 · POST /api/v1/users/activate">
      <View style={styles.header}>
        <Text style={styles.title}>Complete Account Activation</Text>
        <Text style={styles.description}>
          Choose your name and a password to finish setting up your account.
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
                editable={!isSubmitting && tokenUsable}
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
                editable={!isSubmitting && tokenUsable}
                value={value}
                onChangeText={onChange}
                onBlur={onBlur}
                error={errors.password?.message}
              />
            )}
          />

          <Button
            title="Activate Account"
            testID={ActivateIds.submit}
            onPress={handleSubmit(onSubmit)}
            pending={isSubmitting}
            disabled={!token || !tokenUsable}
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
  title: { fontFamily: font.family.heading, fontSize: font.size.title, color: color.text },
  description: {
    fontFamily: font.family.body,
    fontSize: font.size.body,
    color: color.textMuted,
    lineHeight: 20,
  },
});