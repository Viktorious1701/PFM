/**
 * Add a wallet.
 *
 * Story: SRS §6 Feature-03 · WM-US-01 / SDS §5.3.1
 * Endpoint: POST /api/v1/wallets (SDS §6.2.1 WalletCreate)
 *
 * Wiring mirrors app/(tabs)/users/invite.tsx: react-hook-form + Controller,
 * client-side rules as a UX convenience only (constitution VL-01 — Pydantic
 * on the server is the source of truth), server 422s mapped field-by-field
 * via fieldErrors(). Unlike invite.tsx, this form has more than one field, so
 * a validation failure may name more than one of them at once — every known
 * field is checked, not just the first.
 *
 * ApiError.isUnauthenticated gets no special handling here: the global
 * auth-redirect guard (src/store/useAuthRedirect.ts) already reacts to the
 * axios interceptor's 401 callback and sends the caller to /login on its
 * own — duplicating that here would just race it.
 */
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { StyleSheet, Text, View } from 'react-native';

import { ApiError, ErrorCode, fieldErrors, toApiError } from '../../../src/api/errors';
import type { WalletCreate } from '../../../src/api/types';
import { createWallet } from '../../../src/api/wallets';
import { Banner } from '../../../src/components/Banner';
import { Button } from '../../../src/components/Button';
import { Screen } from '../../../src/components/Screen';
import { TextField } from '../../../src/components/TextField';
import { CreateWalletIds } from '../../../src/constants/elementIds';
import { color, font, space } from '../../../src/theme/tokens';

type FormValues = {
  name: string;
  type: string;
  currency: string;
  initial_balance: string;
};

const CURRENCY_PATTERN = /^[A-Z]{3}$/;
const BALANCE_PATTERN = /^-?\d{1,13}(\.\d{1,2})?$/;

/** `fieldErrors()` keys are the backend's own field names — same as `WalletCreate`'s. */
const FORM_FIELDS: (keyof FormValues)[] = ['name', 'type', 'currency', 'initial_balance'];

export default function CreateWalletScreen() {
  const router = useRouter();
  const [failure, setFailure] = useState<ApiError | null>(null);

  const {
    control,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    defaultValues: { name: '', type: '', currency: '', initial_balance: '' },
  });

  const onSubmit = async (values: FormValues) => {
    setFailure(null);

    const payload: WalletCreate = {
      name: values.name.trim(),
      type: values.type,
      currency: values.currency,
      initial_balance: values.initial_balance,
    };

    try {
      await createWallet(payload);
      router.back();
    } catch (caught) {
      const err = toApiError(caught);

      if (err.code === ErrorCode.VALIDATION_ERROR) {
        const fields = fieldErrors(err);
        let matchedAny = false;
        for (const field of FORM_FIELDS) {
          if (fields[field]) {
            setError(field, { message: fields[field] });
            matchedAny = true;
          }
        }
        if (matchedAny) return;
      }

      // Any other failure, including an unauthenticated one, surfaces here —
      // the auth-redirect guard handles navigation for the latter on its own.
      setFailure(err);
    }
  };

  return (
    <Screen testID={CreateWalletIds.screen} note="WM-US-01 · POST /api/v1/wallets">
      <View style={styles.header}>
        <Text style={styles.title}>Add a Wallet</Text>
        <Text style={styles.description}>
          Track a bank account, cash stash, credit card, or savings pot.
        </Text>
      </View>

      <Controller
        control={control}
        name="name"
        rules={{
          required: 'Please enter a wallet name',
          validate: (value) => value.trim().length > 0 || 'Please enter a wallet name',
        }}
        render={({ field: { onChange, onBlur, value } }) => (
          <TextField
            label="Name"
            testID={CreateWalletIds.nameInput}
            errorTestID={CreateWalletIds.nameError}
            placeholder="e.g. Main Checking"
            autoCapitalize="words"
            editable={!isSubmitting}
            value={value}
            onChangeText={onChange}
            onBlur={onBlur}
            error={errors.name?.message}
          />
        )}
      />

      <Controller
        control={control}
        name="type"
        rules={{ required: 'Please enter a wallet type' }}
        render={({ field: { onChange, onBlur, value } }) => (
          <TextField
            label="Type"
            testID={CreateWalletIds.typeInput}
            errorTestID={CreateWalletIds.typeError}
            hint="e.g. Bank, Cash, Credit, Savings"
            autoCapitalize="words"
            editable={!isSubmitting}
            value={value}
            onChangeText={onChange}
            onBlur={onBlur}
            error={errors.type?.message}
          />
        )}
      />

      <Controller
        control={control}
        name="currency"
        rules={{
          required: 'Please enter a currency code',
          pattern: { value: CURRENCY_PATTERN, message: 'Enter a 3-letter code, e.g. VND' },
        }}
        render={({ field: { onChange, onBlur, value } }) => (
          <TextField
            label="Currency"
            testID={CreateWalletIds.currencyInput}
            errorTestID={CreateWalletIds.currencyError}
            placeholder="VND"
            hint="3-letter code, e.g. VND"
            autoCapitalize="characters"
            autoCorrect={false}
            maxLength={3}
            editable={!isSubmitting}
            value={value}
            onChangeText={(text) => onChange(text.toUpperCase())}
            onBlur={onBlur}
            error={errors.currency?.message}
          />
        )}
      />

      <Controller
        control={control}
        name="initial_balance"
        rules={{
          required: 'Please enter an initial balance',
          pattern: { value: BALANCE_PATTERN, message: 'Enter a valid amount, e.g. 100 or -50.25' },
        }}
        render={({ field: { onChange, onBlur, value } }) => (
          <TextField
            label="Initial Balance"
            testID={CreateWalletIds.balanceInput}
            errorTestID={CreateWalletIds.balanceError}
            placeholder="0.00"
            hint="Can be negative for a credit wallet already in debt"
            keyboardType="decimal-pad"
            editable={!isSubmitting}
            value={value}
            onChangeText={onChange}
            onBlur={onBlur}
            error={errors.initial_balance?.message}
          />
        )}
      />

      <Button
        title="Add Wallet"
        testID={CreateWalletIds.submit}
        onPress={handleSubmit(onSubmit)}
        pending={isSubmitting}
      />

      {failure ? (
        <Banner tone="error" message={failure.message} testID={CreateWalletIds.errorBanner} />
      ) : null}
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
