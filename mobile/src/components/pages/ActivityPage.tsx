/**
 * Activity tab: every transaction, newest first, grouped by day, optionally
 * for one wallet; adding an income or expense (with a new category on the
 * spot if needed); deleting one.
 */
import { useMemo, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { createCategory, listCategories } from '../../api/categories';
import { errorMessage } from '../../api/errors';
import { createTransaction, deleteTransaction, listTransactions, updateTransaction } from '../../api/transactions';
import type { CategoryRead, CategoryType, TransactionRead, WalletRead } from '../../api/types';
import { listWallets } from '../../api/wallets';
import { font, moon } from '../../theme/moonlit';
import { amountPlaceholder, dayKey, dayLabel, parseAmount, timeLabel } from '../../utils/format';
import { DEFAULT_CURRENCY, formatMoney, isWholeUnitCurrency } from '../../utils/money';
import { useLoad } from '../../utils/useLoad';
import { CategoriesPanel } from './CategoriesPanel';
import { Button, Chips, Confirm, ErrorText, Field, LoadError, Loading, Muted, Panel, SectionHead, ui } from '../ui/moon';

const PAGE = 50;

function AddTransaction({
  wallets,
  categories,
  defaultWallet,
  onCategoriesChanged,
  onDone,
  onCancel,
}: {
  wallets: WalletRead[];
  categories: CategoryRead[];
  defaultWallet: string | null;
  onCategoriesChanged: () => Promise<void>;
  onDone: () => void;
  onCancel: () => void;
}) {
  const [type, setType] = useState<CategoryType>('EXPENSE');
  const [amount, setAmount] = useState('');
  const [walletId, setWalletId] = useState<string | null>(defaultWallet ?? wallets[0]?.id ?? null);
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [note, setNote] = useState('');
  const [newCat, setNewCat] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ofType = categories.filter((c) => c.type === type);
  const currency = wallets.find((w) => w.id === walletId)?.currency ?? DEFAULT_CURRENCY;

  const addCategory = async () => {
    if (!newCat?.trim()) return;
    setError(null);
    try {
      const c = await createCategory({ name: newCat.trim(), type });
      await onCategoriesChanged();
      setCategoryId(c.id);
      setNewCat(null);
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  const submit = async () => {
    const whole = isWholeUnitCurrency(currency);
    const value = parseAmount(amount, { wholeUnits: whole });
    if (!value || value === '0.00') return setError(whole ? 'Enter an amount above zero, like 50.000.' : 'Enter an amount above zero, like 12.50.');
    if (!walletId) return setError('Choose a wallet.');
    if (!categoryId) return setError('Choose a category.');
    setBusy(true);
    setError(null);
    try {
      await createTransaction({ wallet_id: walletId, category_id: categoryId, amount: value, type, note: note.trim() || null });
      onDone();
    } catch (e) {
      setError(errorMessage(e));
      setBusy(false);
    }
  };

  return (
    <Panel style={styles.form} testID="add-transaction-form">
      <Text style={styles.formTitle}>New transaction</Text>
      <Chips
        options={[
          { value: 'EXPENSE', label: 'Expense' },
          { value: 'INCOME', label: 'Income' },
        ]}
        value={type}
        onChange={(t) => {
          setType(t);
          setCategoryId(null);
        }}
        testID="txn-type"
      />
      <Field label={`Amount (${currency})`} value={amount} onChangeText={setAmount} placeholder={amountPlaceholder(currency)} keyboardType={isWholeUnitCurrency(currency) ? 'number-pad' : 'decimal-pad'} testID="txn-amount" autoFocus />
      {wallets.length === 0 ? (
        <Muted>Add a wallet first, on the Wallets tab.</Muted>
      ) : (
        <Chips label="Wallet" options={wallets.map((w) => ({ value: w.id, label: w.name }))} value={walletId} onChange={setWalletId} testID="txn-wallet" />
      )}
      <Chips label="Category" options={ofType.map((c) => ({ value: c.id, label: c.name }))} value={categoryId} onChange={setCategoryId} testID="txn-category" />
      {newCat === null ? (
        <View style={ui.row}>
          <Button small kind="ghost" label="New category" onPress={() => setNewCat('')} testID="new-category" />
          {ofType.length === 0 ? <Muted>No {type === 'INCOME' ? 'income' : 'expense'} categories yet.</Muted> : null}
        </View>
      ) : (
        <View style={styles.inline}>
          <View style={styles.grow}>
            <Field label={`New ${type === 'INCOME' ? 'income' : 'expense'} category`} value={newCat} onChangeText={setNewCat} testID="new-category-name" onSubmitEditing={addCategory} />
          </View>
          <Button small label="Add" onPress={() => void addCategory()} testID="new-category-add" />
        </View>
      )}
      <Field label="Note (optional)" value={note} onChangeText={setNote} placeholder="What was it for?" testID="txn-note" onSubmitEditing={submit} />
      {error ? <ErrorText>{error}</ErrorText> : null}
      <View style={ui.row}>
        <Button label={type === 'INCOME' ? 'Add income' : 'Add expense'} onPress={submit} busy={busy} testID="txn-submit" />
        <Button kind="ghost" label="Cancel" onPress={onCancel} />
      </View>
    </Panel>
  );
}

/** One transaction. Tapping it opens its details (TM-US-03) with Edit
 * (TM-US-04: amount, type, category, note — the wallet is fixed) and
 * Delete (TM-US-05). */
function Row({
  t,
  wallet,
  category,
  categories,
  onChanged,
}: {
  t: TransactionRead;
  wallet?: WalletRead;
  category?: string;
  categories: CategoryRead[];
  onChanged: () => void;
}) {
  const [mode, setMode] = useState<'closed' | 'detail' | 'edit' | 'delete'>('closed');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const currency = wallet?.currency ?? DEFAULT_CURRENCY;
  const whole = isWholeUnitCurrency(currency);

  const [type, setType] = useState<CategoryType>(t.type);
  const [amount, setAmount] = useState(whole ? t.amount.replace(/\.00$/, '') : t.amount);
  const [categoryId, setCategoryId] = useState<string | null>(t.category_id);
  const [note, setNote] = useState(t.note ?? '');

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      setBusy(false);
      setMode('closed');
      onChanged();
    } catch (e) {
      setError(errorMessage(e));
      setBusy(false);
    }
  };

  const save = () => {
    const value = parseAmount(amount, { wholeUnits: whole });
    if (!value || value === '0.00') return setError(whole ? 'Enter an amount above zero, like 50.000.' : 'Enter an amount above zero, like 12.50.');
    if (!categoryId) return setError('Choose a category.');
    void run(() => updateTransaction(t.id, { amount: value, type, category_id: categoryId, note: note.trim() || null }));
  };

  const when = new Date(t.timestamp);
  return (
    <View style={styles.rowWrap}>
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ expanded: mode !== 'closed' }}
        onPress={() => setMode(mode === 'closed' ? 'detail' : 'closed')}
        style={styles.row}
        testID={`txn-${t.id}`}
      >
        <View style={styles.rowText}>
          <Text style={styles.rowName} numberOfLines={1}>
            {category ?? 'Archived category'}
          </Text>
          <Text style={styles.rowMeta} numberOfLines={1}>
            {timeLabel(t.timestamp)} · {wallet?.name ?? 'Archived wallet'}
            {t.note ? ` · ${t.note}` : ''}
          </Text>
        </View>
        <Text style={[styles.amount, t.type === 'INCOME' && styles.income]}>
          {t.type === 'INCOME' ? '+' : '−'}
          {formatMoney(t.amount, currency)}
        </Text>
      </Pressable>

      {mode === 'detail' ? (
        <View style={styles.rowActions} testID="txn-detail">
          <View style={styles.facts}>
            <Fact label="Type" value={t.type === 'INCOME' ? 'Income' : 'Expense'} />
            <Fact label="Wallet" value={wallet ? `${wallet.name} · ${wallet.currency}` : 'Archived wallet'} />
            <Fact label="When" value={`${dayLabel(t.timestamp)} ${when.getFullYear()} · ${timeLabel(t.timestamp)}`} />
            {t.note ? <Fact label="Note" value={t.note} /> : null}
          </View>
          <View style={ui.row}>
            <Button small kind="ghost" label="Edit" onPress={() => setMode('edit')} testID="txn-edit" />
            <Button small kind="danger" label="Delete" onPress={() => setMode('delete')} testID="txn-delete" />
          </View>
        </View>
      ) : mode === 'edit' ? (
        <View style={styles.editForm} testID="txn-edit-form">
          <Chips
            options={[
              { value: 'EXPENSE', label: 'Expense' },
              { value: 'INCOME', label: 'Income' },
            ]}
            value={type}
            onChange={(v) => {
              setType(v);
              if (categories.find((c) => c.id === categoryId)?.type !== v) setCategoryId(null);
            }}
            testID="txn-edit-type"
          />
          <Field
            label={`Amount (${currency})`}
            value={amount}
            onChangeText={setAmount}
            placeholder={amountPlaceholder(currency)}
            keyboardType={whole ? 'number-pad' : 'decimal-pad'}
            testID="txn-edit-amount"
          />
          <Chips
            label="Category"
            options={categories.filter((c) => c.type === type).map((c) => ({ value: c.id, label: c.name }))}
            value={categoryId}
            onChange={setCategoryId}
            testID="txn-edit-category"
          />
          <Field label="Note (optional)" value={note} onChangeText={setNote} testID="txn-edit-note" onSubmitEditing={save} />
          <View style={ui.row}>
            <Button small label="Save" onPress={save} busy={busy} testID="txn-edit-save" />
            <Button small kind="ghost" label="Cancel" onPress={() => setMode('detail')} />
          </View>
        </View>
      ) : mode === 'delete' ? (
        <View style={styles.rowActions}>
          <Confirm
            question="Delete this transaction? Its amount goes back into the wallet's balance."
            confirmLabel="Delete"
            busy={busy}
            testID="txn-delete-confirm"
            onCancel={() => setMode('detail')}
            onConfirm={() => void run(() => deleteTransaction(t.id))}
          />
        </View>
      ) : null}
      {error && mode !== 'closed' ? <ErrorText>{error}</ErrorText> : null}
    </View>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.fact}>
      <Text style={styles.factLabel}>{label}</Text>
      <Text style={styles.factValue}>{value}</Text>
    </View>
  );
}

export function ActivityPage() {
  const [walletFilter, setWalletFilter] = useState<string>('all');
  // Older pages fetched by "Show more", appended after page 1.
  const [older, setOlder] = useState<TransactionRead[]>([]);
  const [olderBusy, setOlderBusy] = useState(false);
  const lookups = useLoad(async () => {
    const [w, c] = await Promise.all([listWallets(), listCategories()]);
    return { wallets: w.items, categories: c.items };
  });
  const walletParam = walletFilter === 'all' ? undefined : walletFilter;
  const feed = useLoad(async () => {
    const first = await listTransactions({ page: 1, page_size: PAGE, wallet_id: walletParam });
    setOlder([]);
    return first;
  }, [walletParam]);
  const items = useMemo(() => [...(feed.data?.items ?? []), ...older], [feed.data, older]);
  const showMore = async () => {
    setOlderBusy(true);
    try {
      const next = await listTransactions({ page: 1 + Math.ceil(items.length / PAGE), page_size: PAGE, wallet_id: walletParam });
      setOlder((o) => [...o, ...next.items]);
    } finally {
      setOlderBusy(false);
    }
  };
  const [adding, setAdding] = useState(false);
  const [managing, setManaging] = useState(false);

  const byDay = useMemo(() => {
    const groups: { key: string; label: string; items: TransactionRead[] }[] = [];
    for (const t of items) {
      const k = dayKey(t.timestamp);
      const last = groups[groups.length - 1];
      if (last && last.key === k) last.items.push(t);
      else groups.push({ key: k, label: dayLabel(t.timestamp), items: [t] });
    }
    return groups;
  }, [items]);

  const wallets = lookups.data?.wallets ?? [];
  const walletById = new Map(wallets.map((w) => [w.id, w]));
  const catName = new Map((lookups.data?.categories ?? []).map((c) => [c.id, c.name]));
  const error = lookups.error ?? feed.error;

  return (
    <ScrollView contentContainerStyle={styles.scroll}>
      <View style={ui.column}>
        <View style={ui.section}>
          <SectionHead
            title="Activity"
            right={
              lookups.data && !adding && !managing ? (
                <View style={ui.row}>
                  <Button small kind="ghost" label="Categories" onPress={() => setManaging(true)} testID="manage-categories" />
                  <Button small kind="ghost" label="Add" onPress={() => setAdding(true)} testID="add-transaction" />
                </View>
              ) : null
            }
          />
          {managing && lookups.data ? (
            <CategoriesPanel
              categories={lookups.data.categories}
              onChanged={lookups.reload}
              onClose={() => {
                setManaging(false);
                void feed.reload();
              }}
            />
          ) : null}
          {adding && lookups.data ? (
            <AddTransaction
              wallets={wallets}
              categories={lookups.data.categories}
              defaultWallet={walletFilter === 'all' ? null : walletFilter}
              onCategoriesChanged={lookups.reload}
              onCancel={() => setAdding(false)}
              onDone={() => {
                setAdding(false);
                void feed.reload();
              }}
            />
          ) : null}
          {wallets.length > 1 ? (
            <Chips
              options={[{ value: 'all', label: 'All wallets' }, ...wallets.map((w) => ({ value: w.id, label: w.name }))]}
              value={walletFilter}
              onChange={setWalletFilter}
              testID="filter"
            />
          ) : null}

          {error ? (
            <LoadError
              message={error}
              onRetry={() => {
                void lookups.reload();
                void feed.reload();
              }}
            />
          ) : !feed.data || !lookups.data ? (
            <Loading label="Loading activity" />
          ) : feed.data.items.length === 0 ? (
            <Panel>
              <Muted>No transactions yet. Add your first income or expense.</Muted>
            </Panel>
          ) : (
            <>
              {byDay.map((g) => (
                <View key={g.key} style={styles.day}>
                  <SectionHead title={g.label} />
                  <Panel style={styles.dayPanel}>
                    {g.items.map((t, i) => (
                      <View key={t.id}>
                        {i > 0 ? <View style={styles.divider} /> : null}
                        <Row
                          t={t}
                          wallet={walletById.get(t.wallet_id)}
                          category={catName.get(t.category_id)}
                          categories={lookups.data?.categories ?? []}
                          onChanged={() => void feed.reload()}
                        />
                      </View>
                    ))}
                  </Panel>
                </View>
              ))}
              {feed.data.total > items.length ? (
                <View style={styles.more}>
                  <Button kind="ghost" small busy={olderBusy} label={`Show more (${feed.data.total - items.length} older)`} onPress={() => void showMore()} />
                </View>
              ) : null}
            </>
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
  inline: { flexDirection: 'row', alignItems: 'flex-end', gap: 8 },
  grow: { flex: 1 },
  day: { gap: 8 },
  dayPanel: { paddingVertical: 6, paddingHorizontal: 16 },
  divider: { height: 1, backgroundColor: moon.hairline },
  rowWrap: { paddingVertical: 10, gap: 10 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, cursor: 'pointer' },
  rowText: { flex: 1, minWidth: 0, gap: 2 },
  rowName: { fontFamily: font.semibold, fontSize: 16, color: moon.ink },
  rowMeta: { fontFamily: font.medium, fontSize: 13, color: moon.muted },
  amount: { fontFamily: font.semibold, fontSize: 17, color: moon.ink, ...ui.num },
  income: { color: moon.income },
  rowActions: { gap: 12 },
  editForm: { gap: 12, paddingTop: 4 },
  facts: { gap: 6 },
  fact: { flexDirection: 'row', gap: 12 },
  factLabel: { width: 64, fontFamily: font.semibold, fontSize: 11, letterSpacing: 2, textTransform: 'uppercase', color: moon.muted, paddingTop: 2 },
  factValue: { flex: 1, fontFamily: font.medium, fontSize: 15, color: moon.inkSoft },
  more: { alignItems: 'center' },
});
