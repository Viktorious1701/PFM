/**
 * Log a transaction.
 *
 * Story: SRS §6 Feature-06 · TM-US-01 / SDS §5.6 · POST /api/v1/transactions.
 * UXR-01 constrains this screen: logging an expense must take no more than 3
 * taps and under 10 seconds — direction defaults to EXPENSE (the more
 * frequent action), and the category picker is pre-filtered to the selected
 * direction's type so a mismatched pick is impossible through this UI.
 *
 * Closest precedent: app/(tabs)/users/invite.tsx for the react-hook-form +
 * Controller + fieldErrors() wiring.
 */
import { useRouter } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { createCategory, listCategories } from '../../../src/api/categories';
import { ErrorCode, fieldErrors, toApiError } from '../../../src/api/errors';
import { createTransaction } from '../../../src/api/transactions';
import type { CategoryRead, CategoryType, TransactionCreate, WalletRead } from '../../../src/api/types';
import { listWallets } from '../../../src/api/wallets';
import { Banner } from '../../../src/components/Banner';
import { Button } from '../../../src/components/Button';
import { PostedTicketPicker, type PostedTicketOption } from '../../../src/components/PostedTicketPicker';
import { Screen } from '../../../src/components/Screen';
import { TextField } from '../../../src/components/TextField';
import { TransactionCreateIds } from '../../../src/constants/elementIds';
import { useAuth } from '../../../src/store/auth';
import { color, font, radius, space } from '../../../src/theme/tokens';

type FormValues = {
  direction: CategoryType;
  amount: string;
  walletId: string;
  categoryId: string;
  note: string;
};

/** Client pattern only (constitution VL-01) — the server is authoritative. */
const AMOUNT_PATTERN = /^\d{1,13}(\.\d{1,2})?$/;

/**
 * Quick-amount chips — common VND banknote denominations, so a caller
 * doesn't have to type out "1,000,000" digit by digit. Tapping one fills the
 * Amount field exactly as typing would (same `onChange`); it stays a plain
 * editable text field afterward, so a chip is a shortcut, never a lock-in —
 * the user can still adjust or replace it by hand.
 */
const AMOUNT_QUICK_PICKS: ReadonlyArray<{ label: string; value: string }> = [
  { label: '10,000', value: '10000' },
  { label: '20,000', value: '20000' },
  { label: '50,000', value: '50000' },
  { label: '100,000', value: '100000' },
  { label: '200,000', value: '200000' },
  { label: '500,000', value: '500000' },
];

export default function CreateTransactionScreen() {
  const router = useRouter();
  const { isLoading: authLoading } = useAuth();

  const [wallets, setWallets] = useState<WalletRead[]>([]);
  const [categories, setCategories] = useState<CategoryRead[]>([]);
  const [loadingFoundation, setLoadingFoundation] = useState(true);
  const [foundationError, setFoundationError] = useState<string | null>(null);

  const [newCategoryFormOpen, setNewCategoryFormOpen] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [newCategoryError, setNewCategoryError] = useState<string | null>(null);
  const [creatingCategory, setCreatingCategory] = useState(false);

  const [bannerError, setBannerError] = useState<string | null>(null);

  const {
    control,
    handleSubmit,
    watch,
    setValue,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    defaultValues: { direction: 'EXPENSE', amount: '', walletId: '', categoryId: '', note: '' },
  });

  const direction = watch('direction');
  const categoryId = watch('categoryId');

  // Fetched once auth has rehydrated (parallel) — this is a routed
  // sub-screen closed via router.back() on success, not a persistently-
  // focused tab. Gating on `authLoading` matters on a direct deep link or a
  // hard reload straight into this screen: without it, this effect fired
  // immediately on mount, before `AuthProvider`'s boot effect had read the
  // stored token, so the request went out with no Authorization header at
  // all — a real bug, found live via exactly that navigation. See
  // `api/client.ts`'s response interceptor for the other half of the fix.
  useEffect(() => {
    if (authLoading) return;
    let cancelled = false;
    (async () => {
      try {
        const [walletsPage, categoriesPage] = await Promise.all([listWallets(1, 100), listCategories(1, 100)]);
        if (cancelled) return;
        setWallets(walletsPage.items);
        setCategories(categoriesPage.items);
      } catch (caught) {
        if (!cancelled) setFoundationError(toApiError(caught).message);
      } finally {
        if (!cancelled) setLoadingFoundation(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authLoading]);

  const categoryOptions: PostedTicketOption<string>[] = useMemo(
    () => categories.filter((c) => c.type === direction).map((c) => ({ value: c.id, label: c.name })),
    [categories, direction],
  );

  const handleDirectionChange = (next: CategoryType, onChange: (value: CategoryType) => void) => {
    onChange(next);
    if (categoryId) {
      const selected = categories.find((c) => c.id === categoryId);
      if (selected && selected.type !== next) {
        setValue('categoryId', '');
      }
    }
  };

  const handleCreateCategory = async () => {
    const name = newCategoryName.trim();
    if (!name) {
      setNewCategoryError('Please enter a category name');
      return;
    }
    setCreatingCategory(true);
    setNewCategoryError(null);
    try {
      const created = await createCategory({ name, type: direction });
      setCategories((prev) => [...prev, created]);
      setValue('categoryId', created.id, { shouldValidate: true });
      setNewCategoryFormOpen(false);
      setNewCategoryName('');
    } catch (caught) {
      const err = toApiError(caught);
      if (err.code === ErrorCode.VALIDATION_ERROR) {
        const fields = fieldErrors(err);
        setNewCategoryError(fields.name ?? err.message);
      } else {
        setNewCategoryError(err.message);
      }
    } finally {
      setCreatingCategory(false);
    }
  };

  const onSubmit = async (values: FormValues) => {
    setBannerError(null);
    const note = values.note.trim();
    const payload: TransactionCreate = {
      wallet_id: values.walletId,
      category_id: values.categoryId,
      amount: values.amount,
      type: values.direction,
      ...(note ? { note } : {}),
    };

    try {
      await createTransaction(payload);
      router.back();
    } catch (caught) {
      const err = toApiError(caught);

      if (err.code === ErrorCode.VALIDATION_ERROR) {
        const fields = fieldErrors(err);
        if (fields.amount) return setError('amount', { message: fields.amount });
        if (fields.wallet_id) return setError('walletId', { message: fields.wallet_id });
        if (fields.category_id) return setError('categoryId', { message: fields.category_id });
        if (fields.note) return setError('note', { message: fields.note });
        setBannerError(err.message);
        return;
      }

      if (err.code === ErrorCode.TRANSACTION_INSUFFICIENT_BALANCE) {
        setError('amount', { message: "This wallet doesn't have enough balance for this expense." });
        return;
      }

      if (err.code === ErrorCode.TRANSACTION_CATEGORY_TYPE_MISMATCH) {
        setError('categoryId', {
          message: "This category doesn't match the selected direction — pick another.",
        });
        return;
      }

      // TRANSACTION_WALLET_NOT_FOUND / TRANSACTION_CATEGORY_NOT_FOUND (stale
      // picker data, not a fixable-in-place field) and anything else.
      setBannerError(err.message);
    }
  };

  const categoryFooter = newCategoryFormOpen ? (
    <View style={styles.newCategoryForm}>
      <TextField
        label="New category name"
        testID={TransactionCreateIds.newCategoryNameInput}
        errorTestID={TransactionCreateIds.newCategoryNameError}
        placeholder={direction === 'EXPENSE' ? 'e.g. Subscriptions' : 'e.g. Freelance'}
        value={newCategoryName}
        onChangeText={(text) => {
          setNewCategoryName(text);
          setNewCategoryError(null);
        }}
        editable={!creatingCategory}
        error={newCategoryError}
      />
      <View style={styles.newCategoryActions}>
        <Button
          title="Cancel"
          variant="secondary"
          disabled={creatingCategory}
          onPress={() => {
            setNewCategoryFormOpen(false);
            setNewCategoryName('');
            setNewCategoryError(null);
          }}
        />
        <Button
          title="Create"
          testID={TransactionCreateIds.newCategorySubmit}
          pending={creatingCategory}
          onPress={() => void handleCreateCategory()}
        />
      </View>
    </View>
  ) : (
    <Pressable
      testID={TransactionCreateIds.newCategoryTrigger}
      onPress={() => setNewCategoryFormOpen(true)}
      accessibilityRole="button"
      style={styles.newCategoryTrigger}
    >
      <Text style={styles.newCategoryTriggerLabel}>+ New category</Text>
    </Pressable>
  );

  return (
    <Screen testID={TransactionCreateIds.screen} note="TM-US-01 · POST /api/v1/transactions">
      <View style={styles.header}>
        <Text style={styles.title}>Log Transaction</Text>
      </View>

      {foundationError ? <Banner tone="error" message={foundationError} /> : null}

      <Controller
        control={control}
        name="direction"
        render={({ field: { value, onChange } }) => (
          <View style={styles.toggleRow}>
            <Pressable
              testID={TransactionCreateIds.directionExpense}
              onPress={() => handleDirectionChange('EXPENSE', onChange)}
              accessibilityRole="button"
              accessibilityState={{ selected: value === 'EXPENSE' }}
              style={[styles.toggleSegment, value === 'EXPENSE' ? styles.toggleSegmentExpenseActive : null]}
            >
              <Text style={[styles.toggleLabel, value === 'EXPENSE' ? styles.toggleLabelActive : null]}>
                Expense
              </Text>
            </Pressable>
            <Pressable
              testID={TransactionCreateIds.directionIncome}
              onPress={() => handleDirectionChange('INCOME', onChange)}
              accessibilityRole="button"
              accessibilityState={{ selected: value === 'INCOME' }}
              style={[styles.toggleSegment, value === 'INCOME' ? styles.toggleSegmentIncomeActive : null]}
            >
              <Text style={[styles.toggleLabel, value === 'INCOME' ? styles.toggleLabelActive : null]}>
                Income
              </Text>
            </Pressable>
          </View>
        )}
      />

      <Controller
        control={control}
        name="amount"
        rules={{
          required: 'Please enter an amount',
          pattern: { value: AMOUNT_PATTERN, message: 'Enter a valid amount (up to 2 decimal places)' },
          validate: (value) => parseFloat(value) > 0 || 'Amount must be greater than zero',
        }}
        render={({ field: { onChange, onBlur, value } }) => (
          <View style={styles.amountGroup}>
            <TextField
              label="Amount"
              testID={TransactionCreateIds.amountInput}
              errorTestID={TransactionCreateIds.amountError}
              placeholder="0.00"
              keyboardType="decimal-pad"
              editable={!isSubmitting}
              value={value}
              onChangeText={onChange}
              onBlur={onBlur}
              error={errors.amount?.message}
            />
            <View style={styles.amountChipRow}>
              {AMOUNT_QUICK_PICKS.map((pick) => (
                <AmountChip
                  key={pick.value}
                  label={pick.label}
                  testID={TransactionCreateIds.amountChip(pick.value)}
                  disabled={isSubmitting}
                  onPress={() => onChange(pick.value)}
                />
              ))}
            </View>
          </View>
        )}
      />

      <Controller
        control={control}
        name="walletId"
        rules={{ required: 'Please select a wallet' }}
        render={({ field: { value, onChange } }) => (
          <View style={styles.fieldGroup}>
            <Text style={styles.fieldLabel}>Wallet</Text>
            <PostedTicketPicker
              options={wallets.map((w) => ({ value: w.id, label: w.name, sublabel: w.currency }))}
              selected={value || null}
              onSelect={(next) => onChange(next)}
              disabled={isSubmitting}
              emptyLabel={loadingFoundation ? 'Loading wallets…' : 'No wallets yet — add one first'}
              error={errors.walletId?.message}
              errorTestID={TransactionCreateIds.walletError}
              ticketTestID={TransactionCreateIds.walletTicket}
            />
          </View>
        )}
      />

      <Controller
        control={control}
        name="categoryId"
        rules={{ required: 'Please select a category' }}
        render={({ field: { value, onChange } }) => (
          <View style={styles.fieldGroup}>
            <Text style={styles.fieldLabel}>{`Category (${direction === 'EXPENSE' ? 'Expense' : 'Income'})`}</Text>
            <PostedTicketPicker
              options={categoryOptions}
              selected={value || null}
              onSelect={(next) => onChange(next)}
              disabled={isSubmitting}
              emptyLabel={loadingFoundation ? 'Loading categories…' : 'No categories yet — add one below'}
              error={errors.categoryId?.message}
              errorTestID={TransactionCreateIds.categoryError}
              ticketTestID={TransactionCreateIds.categoryTicket}
              footer={categoryFooter}
            />
          </View>
        )}
      />

      <Controller
        control={control}
        name="note"
        render={({ field: { onChange, onBlur, value } }) => (
          <TextField
            label="Note (optional)"
            testID={TransactionCreateIds.noteInput}
            placeholder="Add a note"
            editable={!isSubmitting}
            value={value}
            onChangeText={onChange}
            onBlur={onBlur}
            error={errors.note?.message}
          />
        )}
      />

      <Button
        title="Save Transaction"
        testID={TransactionCreateIds.submit}
        onPress={handleSubmit(onSubmit)}
        pending={isSubmitting}
      />

      {bannerError ? (
        <Banner tone="error" message={bannerError} testID={TransactionCreateIds.errorBanner} />
      ) : null}
    </Screen>
  );
}

/**
 * A tappable "fill the amount field" suggestion — visually a plain pill
 * (dashed border, no fill), mirroring `transactions/index.tsx`'s `FilterChip`
 * template. Unlike that chip, this one has no "selected" state: tapping it
 * doesn't toggle anything, it just fills the Amount field and nothing stays
 * visually picked, so `pressed` (a momentary press-down cue) is the only
 * state this component tracks.
 */
function AmountChip({
  label,
  onPress,
  disabled,
  testID,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  testID?: string;
}) {
  return (
    <Pressable
      testID={testID}
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityLabel={`Fill amount ${label}`}
      style={({ pressed }) => [
        styles.amountChip,
        pressed ? styles.amountChipPressed : null,
        disabled ? styles.amountChipDisabled : null,
      ]}
    >
      <Text style={styles.amountChipLabel}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  header: { gap: space.sm },
  title: { fontFamily: font.family.heading, fontSize: font.size.title, color: color.text },

  toggleRow: {
    flexDirection: 'row',
    borderWidth: 1,
    borderColor: color.border,
    borderRadius: radius.sm,
    overflow: 'hidden',
  },
  toggleSegment: { flex: 1, paddingVertical: space.md, alignItems: 'center', backgroundColor: color.surface },
  toggleSegmentExpenseActive: { backgroundColor: color.expense },
  toggleSegmentIncomeActive: { backgroundColor: color.income },
  toggleLabel: {
    fontFamily: font.family.bodyMedium,
    fontSize: font.size.md,
    color: color.text,
    letterSpacing: 1,
  },
  toggleLabelActive: { color: color.primaryText },

  amountGroup: { gap: space.sm },
  amountChipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: space.xs },
  amountChip: {
    borderRadius: radius.full,
    borderWidth: 1.5,
    borderStyle: 'dashed',
    borderColor: color.borderInteractive,
    backgroundColor: color.surface,
    paddingVertical: space.xs,
    paddingHorizontal: space.md,
  },
  amountChipPressed: { backgroundColor: color.surfaceSunken },
  amountChipDisabled: { opacity: 0.5 },
  amountChipLabel: { fontFamily: font.family.bodyMedium, fontSize: font.size.sm, color: color.text },

  fieldGroup: { gap: space.xs },
  fieldLabel: { fontFamily: font.family.bodyMedium, fontSize: font.size.sm, color: color.text },

  newCategoryTrigger: { paddingVertical: space.sm, alignItems: 'center' },
  newCategoryTriggerLabel: { fontFamily: font.family.bodyMedium, fontSize: font.size.sm, color: color.text },
  newCategoryForm: { gap: space.sm },
  newCategoryActions: { flexDirection: 'row', gap: space.sm, justifyContent: 'flex-end' },
});
