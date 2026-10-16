/**
 * Budgets tab: each monthly limit (an expense category within a wallet)
 * with how much of it is spent, coloured by the backend's own status —
 * on track (<=75%), close to the limit, or over it. Adding a budget,
 * changing a limit, deleting one.
 */
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { createBudget, deleteBudget, listBudgets, updateBudget } from '../../api/budgets';
import { listCategories } from '../../api/categories';
import { toApiError } from '../../api/errors';
import type { BudgetProgressRead, CategoryRead, WalletRead } from '../../api/types';
import { listWallets } from '../../api/wallets';
import { font, moon } from '../../theme/moonlit';
import { amountPlaceholder, monthLabel, parseAmount } from '../../utils/format';
import { DEFAULT_CURRENCY, formatMoney, isWholeUnitCurrency } from '../../utils/money';
import { useLoad } from '../../utils/useLoad';
import { Button, Chips, Confirm, ErrorText, Field, LoadError, Loading, Muted, Panel, SectionHead, ui } from '../ui/moon';

const STATUS = {
  NORMAL: { label: 'On track', color: moon.income },
  WARNING: { label: 'Close to limit', color: moon.warning },
  EXCEEDED: { label: 'Over limit', color: moon.expense },
} as const;

function AddBudget({ wallets, categories, onDone, onCancel }: { wallets: WalletRead[]; categories: CategoryRead[]; onDone: () => void; onCancel: () => void }) {
  const expense = categories.filter((c) => c.type === 'EXPENSE');
  const [walletId, setWalletId] = useState<string | null>(wallets[0]?.id ?? null);
  const addCurrency = wallets.find((w) => w.id === walletId)?.currency ?? DEFAULT_CURRENCY;
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [limit, setLimit] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    const whole = isWholeUnitCurrency(addCurrency);
    const value = parseAmount(limit, { wholeUnits: whole });
    if (!walletId) return setError('Choose a wallet.');
    if (!categoryId) return setError('Choose a spending category.');
    if (!value || value === '0.00') return setError(whole ? 'Set a monthly limit above zero, like 3.000.000.' : 'Set a monthly limit above zero, like 300.');
    setBusy(true);
    setError(null);
    try {
      await createBudget({ wallet_id: walletId, category_id: categoryId, amount_limit: value });
      onDone();
    } catch (e) {
      setError(toApiError(e).message);
      setBusy(false);
    }
  };

  return (
    <Panel style={styles.form} testID="add-budget-form">
      <Text style={styles.formTitle}>New monthly budget</Text>
      <Chips label="Wallet" options={wallets.map((w) => ({ value: w.id, label: w.name }))} value={walletId} onChange={setWalletId} testID="budget-wallet" />
      {expense.length === 0 ? (
        <Muted>No spending categories yet — add one with your first expense on the Activity tab.</Muted>
      ) : (
        <Chips label="Spending on" options={expense.map((c) => ({ value: c.id, label: c.name }))} value={categoryId} onChange={setCategoryId} testID="budget-category" />
      )}
      <Field label={`Monthly limit (${addCurrency})`} value={limit} onChangeText={setLimit} placeholder={amountPlaceholder(addCurrency)} keyboardType={isWholeUnitCurrency(addCurrency) ? 'number-pad' : 'decimal-pad'} testID="budget-limit" onSubmitEditing={submit} />
      {error ? <ErrorText>{error}</ErrorText> : null}
      <View style={ui.row}>
        <Button label="Add budget" onPress={submit} busy={busy} testID="budget-submit" />
        <Button kind="ghost" label="Cancel" onPress={onCancel} />
      </View>
    </Panel>
  );
}

function BudgetCard({ b, wallet, category, onChanged }: { b: BudgetProgressRead; wallet?: WalletRead; category?: string; onChanged: () => void }) {
  const [mode, setMode] = useState<'view' | 'menu' | 'edit' | 'delete'>('view');
  const [limit, setLimit] = useState(
    isWholeUnitCurrency(wallet?.currency ?? DEFAULT_CURRENCY) ? b.amount_limit.replace(/\.00$/, '') : b.amount_limit,
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const currency = wallet?.currency ?? DEFAULT_CURRENCY;
  const st = STATUS[b.status] ?? STATUS.NORMAL;
  const pct = Math.max(0, Number(b.progress_percentage));

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      setBusy(false);
      setMode('view');
      onChanged();
    } catch (e) {
      setError(toApiError(e).message);
      setBusy(false);
    }
  };

  return (
    <Panel style={styles.card} testID={`budget-${category ?? b.id}`}>
      <Pressable accessibilityRole="button" onPress={() => setMode(mode === 'view' ? 'menu' : 'view')} style={styles.cardBody}>
        <View style={styles.cardTop}>
          <View style={styles.cardText}>
            <Text style={styles.name} numberOfLines={1}>
              {category ?? 'Category'}
            </Text>
            <Text style={styles.meta} numberOfLines={1}>
              {wallet?.name ?? 'Archived wallet'}
            </Text>
          </View>
          <View style={styles.statusPill}>
            <View style={[styles.dot, { backgroundColor: st.color }]} />
            <Text style={styles.statusText}>{st.label}</Text>
          </View>
        </View>
        <View style={styles.track} accessibilityRole="progressbar" accessibilityValue={{ min: 0, max: 100, now: Math.min(100, Math.round(pct)) }}>
          <View style={[styles.fill, { width: `${Math.min(100, pct)}%`, backgroundColor: st.color }]} />
        </View>
        <View style={styles.cardTop}>
          <Text style={styles.spent}>
            {formatMoney(b.amount_spent, currency)} <Text style={styles.of}>of {formatMoney(b.amount_limit, currency)}</Text>
          </Text>
          <Text style={styles.pct}>{Math.round(pct)}%</Text>
        </View>
      </Pressable>

      {mode === 'menu' ? (
        <View style={ui.row}>
          <Button small kind="ghost" label="Change limit" onPress={() => setMode('edit')} testID="budget-edit" />
          <Button small kind="danger" label="Delete" onPress={() => setMode('delete')} testID="budget-delete" />
        </View>
      ) : mode === 'edit' ? (
        <View style={styles.form}>
          <Field label="Monthly limit" value={limit} onChangeText={setLimit} keyboardType="decimal-pad" testID="budget-limit-edit" autoFocus />
          <View style={ui.row}>
            <Button
              small
              label="Save"
              busy={busy}
              testID="budget-limit-save"
              onPress={() => {
                const v = parseAmount(limit, { wholeUnits: isWholeUnitCurrency(currency) });
                if (!v || v === '0.00') return setError('Set a limit above zero.');
                void run(() => updateBudget(b.id, v));
              }}
            />
            <Button small kind="ghost" label="Cancel" onPress={() => setMode('view')} />
          </View>
        </View>
      ) : mode === 'delete' ? (
        <Confirm
          question={`Delete the ${category ?? ''} budget? Your transactions are not affected.`}
          confirmLabel="Delete"
          busy={busy}
          testID="budget-delete-confirm"
          onConfirm={() => void run(() => deleteBudget(b.id))}
          onCancel={() => setMode('view')}
        />
      ) : null}
      {error ? <ErrorText>{error}</ErrorText> : null}
    </Panel>
  );
}

export function BudgetsPage() {
  const { data, error, reload } = useLoad(async () => {
    const [b, w, c] = await Promise.all([listBudgets(), listWallets(), listCategories()]);
    return { budgets: b.items, wallets: w.items, categories: c.items };
  });
  const [adding, setAdding] = useState(false);
  const walletById = new Map((data?.wallets ?? []).map((w) => [w.id, w]));
  const catName = new Map((data?.categories ?? []).map((c) => [c.id, c.name]));
  const period = data?.budgets[0]?.period;

  return (
    <ScrollView contentContainerStyle={styles.scroll}>
      <View style={ui.column}>
        <View style={ui.section}>
          <SectionHead
            title={period ? `Budgets · ${monthLabel(period)}` : 'Budgets'}
            right={!adding && data ? <Button small kind="ghost" label="Add budget" onPress={() => setAdding(true)} testID="add-budget" /> : null}
          />
          {adding && data ? (
            data.wallets.length === 0 ? (
              <Panel>
                <Muted>Add a wallet first, on the Wallets tab.</Muted>
              </Panel>
            ) : (
              <AddBudget
                wallets={data.wallets}
                categories={data.categories}
                onCancel={() => setAdding(false)}
                onDone={() => {
                  setAdding(false);
                  void reload();
                }}
              />
            )
          ) : null}
          {error ? (
            <LoadError message={error} onRetry={() => void reload()} />
          ) : !data ? (
            <Loading label="Loading budgets" />
          ) : data.budgets.length === 0 ? (
            <Panel>
              <Muted>No budgets yet. Set a monthly limit on a spending category to see how close you are.</Muted>
            </Panel>
          ) : (
            data.budgets.map((b) => (
              <BudgetCard key={b.id} b={b} wallet={walletById.get(b.wallet_id)} category={catName.get(b.category_id)} onChanged={() => void reload()} />
            ))
          )}
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { paddingTop: 4, paddingBottom: 120 },
  form: { gap: 14 },
  formTitle: { fontFamily: font.semibold, fontSize: 18, color: moon.ink },
  card: { gap: 14 },
  cardBody: { gap: 12, cursor: 'pointer' },
  cardTop: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 },
  cardText: { flex: 1, minWidth: 0, gap: 2 },
  name: { fontFamily: font.semibold, fontSize: 18, color: moon.ink },
  meta: { fontFamily: font.medium, fontSize: 13, letterSpacing: 1.5, textTransform: 'uppercase', color: moon.muted },
  statusPill: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  statusText: { fontFamily: font.semibold, fontSize: 13, color: moon.inkSoft },
  track: { height: 8, borderRadius: 4, backgroundColor: moon.track, overflow: 'hidden' },
  fill: { height: '100%', borderRadius: 4 },
  spent: { fontFamily: font.semibold, fontSize: 17, color: moon.ink, ...ui.num },
  of: { fontFamily: font.medium, fontSize: 15, color: moon.muted },
  pct: { fontFamily: font.semibold, fontSize: 15, color: moon.inkSoft, ...ui.num },
});
