/**
 * Wallets tab: every wallet with its balance, totals per currency, adding a
 * wallet, and — on a wallet you open — renaming, archiving, and its latest
 * transactions.
 */
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { listCategories } from '../../api/categories';
import { errorMessage } from '../../api/errors';
import { listTransactions } from '../../api/transactions';
import type { WalletRead } from '../../api/types';
import { archiveWallet, createWallet, listWallets, updateWallet } from '../../api/wallets';
import { font, moon } from '../../theme/moonlit';
import { amountPlaceholder, dayLabel, parseAmount, timeLabel } from '../../utils/format';
import { CURRENCIES, DEFAULT_CURRENCY, formatMoney, isWholeUnitCurrency, parseCents, sumMoney } from '../../utils/money';
import { useLoad } from '../../utils/useLoad';
import { Button, Chips, Confirm, ErrorText, Field, LoadError, Loading, Muted, Panel, SectionHead, ui } from '../ui/moon';

const TYPES = ['Bank', 'Cash', 'Credit Card', 'E-wallet'] as const;

function AddWallet({ onDone, onCancel }: { onDone: () => void; onCancel: () => void }) {
  const [name, setName] = useState('');
  const [type, setType] = useState<string>('Bank');
  const [currency, setCurrency] = useState<string>(DEFAULT_CURRENCY);
  const [balance, setBalance] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    const whole = isWholeUnitCurrency(currency);
    const amount = parseAmount(balance || '0', { allowNegative: true, wholeUnits: whole });
    if (!name.trim()) return setError('Give the wallet a name.');
    if (amount === null)
      return setError(whole ? 'Opening balance should be a whole number, like 2.500.000.' : 'Opening balance should be a number, like 250 or 99.50.');
    setBusy(true);
    setError(null);
    try {
      await createWallet({ name: name.trim(), type, currency, initial_balance: amount });
      onDone();
    } catch (e) {
      setError(errorMessage(e));
      setBusy(false);
    }
  };

  return (
    <Panel style={styles.form} testID="add-wallet-form">
      <Text style={styles.formTitle}>New wallet</Text>
      <Field label="Name" value={name} onChangeText={setName} placeholder="e.g. Joint account" testID="wallet-name" autoFocus />
      <Chips label="Type" options={TYPES.map((t) => ({ value: t, label: t }))} value={type} onChange={setType} testID="wallet-type" />
      <Chips label="Currency" options={CURRENCIES.map((c) => ({ value: c, label: c }))} value={currency} onChange={setCurrency} />
      <Field label="Opening balance" value={balance} onChangeText={setBalance} placeholder={amountPlaceholder(currency)} keyboardType={isWholeUnitCurrency(currency) ? 'number-pad' : 'decimal-pad'} testID="wallet-balance" onSubmitEditing={submit} />
      {error ? <ErrorText>{error}</ErrorText> : null}
      <View style={ui.row}>
        <Button label="Add wallet" onPress={submit} busy={busy} testID="wallet-submit" />
        <Button kind="ghost" label="Cancel" onPress={onCancel} />
      </View>
    </Panel>
  );
}

function WalletDetail({ wallet, onChanged }: { wallet: WalletRead; onChanged: () => void }) {
  const recent = useLoad(async () => {
    const [txns, cats] = await Promise.all([listTransactions({ wallet_id: wallet.id, page_size: 5 }), listCategories()]);
    const names = new Map(cats.items.map((c) => [c.id, c.name]));
    return txns.items.map((t) => ({ ...t, category: names.get(t.category_id) ?? 'Archived category' }));
  }, [wallet.id]);
  const [name, setName] = useState(wallet.name);
  const [mode, setMode] = useState<'view' | 'rename' | 'archive'>('view');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      onChanged();
    } catch (e) {
      setError(errorMessage(e));
      setBusy(false);
    }
  };

  return (
    <View style={styles.detail}>
      <View style={styles.divider} />
      <Text style={styles.subTitle}>Latest activity</Text>
      {recent.error ? (
        <ErrorText>{recent.error}</ErrorText>
      ) : !recent.data ? (
        <Muted>Loading…</Muted>
      ) : recent.data.length === 0 ? (
        <Muted>No transactions in this wallet yet.</Muted>
      ) : (
        recent.data.map((t) => (
          <View key={t.id} style={styles.txn}>
            <View style={styles.txnText}>
              <Text style={styles.txnName} numberOfLines={1}>
                {t.category}
              </Text>
              <Text style={styles.txnMeta} numberOfLines={1}>
                {dayLabel(t.timestamp)} · {timeLabel(t.timestamp)}
                {t.note ? ` · ${t.note}` : ''}
              </Text>
            </View>
            <Text style={[styles.txnAmount, t.type === 'INCOME' && styles.income]}>
              {t.type === 'INCOME' ? '+' : '−'}
              {formatMoney(t.amount, wallet.currency)}
            </Text>
          </View>
        ))
      )}

      <View style={styles.divider} />
      {mode === 'rename' ? (
        <View style={styles.form}>
          <Field label="Wallet name" value={name} onChangeText={setName} testID="rename-field" autoFocus />
          <View style={ui.row}>
            <Button small label="Save" busy={busy} testID="rename-save" onPress={() => (name.trim() ? void run(() => updateWallet(wallet.id, { name: name.trim() })) : setError('A wallet needs a name.'))} />
            <Button small kind="ghost" label="Cancel" onPress={() => setMode('view')} />
          </View>
        </View>
      ) : mode === 'archive' ? (
        <Confirm
          question={`Archive “${wallet.name}”? It leaves your wallets; its history is kept.`}
          confirmLabel="Archive"
          busy={busy}
          testID="archive-confirm"
          onConfirm={() => void run(() => archiveWallet(wallet.id))}
          onCancel={() => setMode('view')}
        />
      ) : (
        <View style={ui.row}>
          <Button small kind="ghost" label="Rename" onPress={() => setMode('rename')} testID="rename-wallet" />
          <Button small kind="danger" label="Archive" onPress={() => setMode('archive')} testID="archive-wallet" />
        </View>
      )}
      {error ? <ErrorText>{error}</ErrorText> : null}
    </View>
  );
}

export function WalletsPage() {
  const { data, error, reload } = useLoad(async () => (await listWallets()).items);
  const [adding, setAdding] = useState(false);
  const [open, setOpen] = useState<string | null>(null);

  const totals = (() => {
    const groups = new Map<string, string[]>();
    for (const w of data ?? []) groups.set(w.currency, [...(groups.get(w.currency) ?? []), w.balance]);
    return [...groups.entries()].map(([cur, v]) => formatMoney(sumMoney(v), cur));
  })();

  return (
    <ScrollView contentContainerStyle={styles.scroll}>
      <View style={ui.column}>
        <View style={ui.section}>
          <SectionHead
            title="Wallets"
            right={!adding ? <Button small kind="ghost" label="Add wallet" onPress={() => setAdding(true)} testID="add-wallet" /> : null}
          />
          {data && data.length > 0 ? (
            <Panel style={styles.totals} testID="wallets-total">
              <Text style={styles.totalLabel}>Total across {data.length} {data.length === 1 ? 'wallet' : 'wallets'}</Text>
              <Text style={styles.totalValue}>{totals.join('  ·  ')}</Text>
            </Panel>
          ) : null}
          {adding ? (
            <AddWallet
              onCancel={() => setAdding(false)}
              onDone={() => {
                setAdding(false);
                void reload();
              }}
            />
          ) : null}

          {error ? (
            <LoadError message={error} onRetry={() => void reload()} />
          ) : !data ? (
            <Loading label="Loading wallets" />
          ) : data.length === 0 ? (
            <Panel>
              <Muted>No wallets yet. Add one to start tracking money in it.</Muted>
            </Panel>
          ) : (
            data.map((w) => (
              <Panel key={w.id} testID={`wallet-card-${w.name}`} style={styles.card}>
                <Pressable
                  accessibilityRole="button"
                  accessibilityState={{ expanded: open === w.id }}
                  onPress={() => setOpen(open === w.id ? null : w.id)}
                  style={styles.cardHead}
                >
                  <View style={styles.cardText}>
                    <Text style={styles.name} numberOfLines={1}>
                      {w.name}
                    </Text>
                    <Text style={styles.meta}>
                      {w.type} · {w.currency}
                    </Text>
                  </View>
                  <Text style={[styles.balance, parseCents(w.balance) < 0n && styles.negative]}>{formatMoney(w.balance, w.currency)}</Text>
                </Pressable>
                {open === w.id ? (
                  <WalletDetail
                    wallet={w}
                    onChanged={() => {
                      setOpen(null);
                      void reload();
                    }}
                  />
                ) : null}
              </Panel>
            ))
          )}
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { paddingTop: 4, paddingBottom: 120 },
  totals: { gap: 4, paddingVertical: 16 },
  totalLabel: { fontFamily: font.semibold, fontSize: 11, letterSpacing: 2.5, textTransform: 'uppercase', color: moon.muted },
  totalValue: { fontFamily: font.light, fontSize: 34, color: moon.ink, ...ui.num },
  form: { gap: 14 },
  formTitle: { fontFamily: font.semibold, fontSize: 18, color: moon.ink },
  card: { paddingVertical: 16, gap: 0 },
  cardHead: { flexDirection: 'row', alignItems: 'center', gap: 12, cursor: 'pointer' },
  cardText: { flex: 1, minWidth: 0, gap: 2 },
  name: { fontFamily: font.semibold, fontSize: 18, color: moon.ink },
  meta: { fontFamily: font.medium, fontSize: 13, letterSpacing: 1.5, textTransform: 'uppercase', color: moon.muted },
  balance: { fontFamily: font.regular, fontSize: 26, color: moon.ink, ...ui.num },
  negative: { color: moon.expense },
  detail: { gap: 10, paddingTop: 14 },
  divider: { height: 1, backgroundColor: moon.hairline },
  subTitle: { fontFamily: font.semibold, fontSize: 11, letterSpacing: 2.5, textTransform: 'uppercase', color: moon.muted },
  txn: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  txnText: { flex: 1, minWidth: 0 },
  txnName: { fontFamily: font.semibold, fontSize: 15, color: moon.inkSoft },
  txnMeta: { fontFamily: font.medium, fontSize: 13, color: moon.muted },
  txnAmount: { fontFamily: font.semibold, fontSize: 16, color: moon.ink, ...ui.num },
  income: { color: moon.income },
});
