/**
 * Invite a user via email.
 *
 * Story: SRS §6 Feature-01 · US-01-01 / SDS §5.2.1 UM-US-01
 * Endpoint: POST /api/v1/users/invite (SDS §6.4.1)
 * Spec: specs/001-user-onboarding/spec.md
 *
 * Every branch below traces to an acceptance criterion or edge case. Because the
 * backend has no routes yet, all of them are served from src/api/mock.ts — see
 * the address list at the bottom of the screen.
 *
 * This screen does NOT satisfy any TC in test_cases.md; the `[UI]` rows there
 * remain deferred (ADR-0009).
 */
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { StyleSheet, Text, View } from 'react-native';

import { ApiError, ErrorCode, fieldErrors, toApiError } from '../../../src/api/errors';
import { MOCK_INVITE_CASES } from '../../../src/api/mock';
import type { InvitationRead } from '../../../src/api/types';
import { inviteUser } from '../../../src/api/users';
import { Banner } from '../../../src/components/Banner';
import { Button } from '../../../src/components/Button';
import { Screen } from '../../../src/components/Screen';
import { TextField } from '../../../src/components/TextField';
import { USE_MOCK_API } from '../../../src/config';
import { InviteIds } from '../../../src/constants/elementIds';
import { useAuth } from '../../../src/store/auth';
import { color, font, radius, space } from '../../../src/theme/tokens';

type FormValues = { email: string };

/**
 * Client-side format check only. Constitution VL-01: Pydantic on the server is
 * the source of truth and this is UX. Deliberately no max-length rule here, so
 * an over-long address (EC-04) round-trips and proves the server is authoritative.
 */
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export default function InviteUserScreen() {
  const router = useRouter();
  const { signOut } = useAuth();

  const [result, setResult] = useState<InvitationRead | null>(null);
  const [failure, setFailure] = useState<ApiError | null>(null);

  const {
    control,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ defaultValues: { email: '' } });

  const onSubmit = async ({ email }: FormValues) => {
    setResult(null);
    setFailure(null);

    try {
      // AC-01: on success the response carries id, email, status and expiry —
      // and no token in any form (AC-08 / BR-07).
      const invitation = await inviteUser(email);
      setResult(invitation);
      reset({ email: '' });
    } catch (caught) {
      const err = toApiError(caught);

      // AC-03 / EC-04: a validation failure names the offending field, so it is
      // rendered against the input rather than as a page-level banner.
      if (err.code === ErrorCode.VALIDATION_ERROR) {
        const fields = fieldErrors(err);
        if (fields.email) {
          setError('email', { message: fields.email });
          return;
        }
      }

      // AC-05: credentials absent, invalid or expired — end the session and
      // send the caller to login rather than leaving a dead form on screen.
      if (err.isUnauthenticated) {
        await signOut();
        router.replace('/(auth)/login');
        return;
      }

      // AC-02 (409), AC-04 (403), EC-07 (502) all surface the server's message.
      setFailure(err);
    }
  };

  return (
    <Screen testID={InviteIds.screen} note="UM-US-01 · POST /api/v1/users/invite">
      <View style={styles.header}>
        <Text style={styles.title}>Invite Family Member</Text>
        <Text style={styles.description}>
          An activation email with a 24-hour expiration link will be sent to the recipient.
        </Text>
      </View>

      <Controller
        control={control}
        name="email"
        rules={{
          required: 'Please enter an email address',
          pattern: { value: EMAIL_PATTERN, message: 'Please enter a valid email address' },
        }}
        render={({ field: { onChange, onBlur, value } }) => (
          <TextField
            label="Email address"
            testID={InviteIds.emailInput}
            errorTestID={InviteIds.emailError}
            placeholder="family.member@gmail.com"
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

      <Button
        title="Send Email Invitation"
        testID={InviteIds.submit}
        onPress={handleSubmit(onSubmit)}
        pending={isSubmitting}
      />

      {result ? (
        <Banner tone="success" message={result.message} testID={InviteIds.successBanner}>
          <ResultRow testID={InviteIds.resultEmail} label="Invited" value={result.email} />
          <ResultRow testID={InviteIds.resultStatus} label="Status" value={result.status} />
          <ResultRow
            testID={InviteIds.resultExpiry}
            label="Link expires"
            value={new Date(result.token_expires_at).toLocaleString()}
          />
          <ResultRow testID={InviteIds.resultId} label="User id" value={result.id} />
        </Banner>
      ) : null}

      {failure ? (
        <Banner tone="error" message={failure.message} testID={InviteIds.errorBanner} />
      ) : null}

      {USE_MOCK_API ? <MockCaseList /> : null}
    </Screen>
  );
}

function ResultRow({
  label,
  value,
  testID,
}: {
  label: string;
  value: string;
  testID?: string;
}) {
  return (
    <Text testID={testID} style={styles.resultRow}>
      <Text style={styles.resultLabel}>{label}: </Text>
      {value}
    </Text>
  );
}

/**
 * The fixture addresses, on screen so the branches are discoverable without
 * reading src/api/mock.ts.
 */
function MockCaseList() {
  return (
    <View style={styles.cases}>
      <Text style={styles.casesTitle}>Try these addresses</Text>
      {MOCK_INVITE_CASES.map((c) => (
        <View key={c.ref + c.email} style={styles.caseRow}>
          <Text style={styles.caseEmail} numberOfLines={1}>
            {c.email.length > 40 ? `${c.email.slice(0, 20)}…(${c.email.length} chars)` : c.email}
          </Text>
          <Text style={styles.caseOutcome}>
            {c.outcome} <Text style={styles.caseRef}>({c.ref})</Text>
          </Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  header: { gap: space.sm },
  title: { fontSize: font.size.title, fontWeight: font.weight.bold, color: color.text },
  description: { fontSize: font.size.body, color: color.textMuted, lineHeight: 20 },
  resultRow: { fontSize: font.size.sm, color: color.success.fg },
  resultLabel: { fontWeight: font.weight.semibold },
  cases: {
    marginTop: space.sm,
    padding: space.md,
    backgroundColor: color.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: color.border,
    gap: space.sm,
  },
  casesTitle: {
    fontSize: font.size.xs,
    fontWeight: font.weight.bold,
    color: color.textMuted,
    letterSpacing: 0.4,
  },
  caseRow: { gap: 1 },
  caseEmail: { fontSize: font.size.sm, color: color.text, fontFamily: 'monospace' },
  caseOutcome: { fontSize: font.size.xs, color: color.textMuted },
  caseRef: { fontWeight: font.weight.bold },
});
