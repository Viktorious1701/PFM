/**
 * The wallet dashboard, top to bottom: total balance, every wallet with its
 * own balance, then this month's analysis (income vs. expenses on one scale,
 * net savings, and where the spending went). All figures come from the real
 * backend — `GET /wallets` and `GET /reports/summary`. The Home tab; the
 * header and tab bar around it are shared chrome (AppHeader, TabBar).
 */
import { useCallback, useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { toApiError } from '../../api/errors';
import { getSummaryReport } from '../../api/reports';
import type { SummaryReportRead, WalletRead } from '../../api/types';
import { listWallets } from '../../api/wallets';
import { font, moon } from '../../theme/moonlit';
import { DEFAULT_CURRENCY, formatMoney, parseCents, sumMoney } from '../../utils/money';
import { LoadError, Loading } from '../ui/moon';
import { ExpenseDonut } from './ExpenseDonut';

type Data = { wallets: WalletRead[]; summary: SummaryReportRead };

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

function monthLabel(period: string): string {
  const [y, m] = period.split('-').map(Number);
  return `${MONTHS[m - 1]} ${y}`;
}

/** Wallet totals per currency — balances in different currencies are never
 * added together. */
function totalsByCurrency(wallets: WalletRead[]): [string, string][] {
  const groups = new Map<string, string[]>();
  for (const w of wallets) groups.set(w.currency, [...(groups.get(w.currency) ?? []), w.balance]);
  return [...groups.entries()].map(([cur, values]) => [cur, sumMoney(values)]);
}

export function Dashboard() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [wallets, summary] = await Promise.all([listWallets(), getSummaryReport()]);
      setData({ wallets: wallets.items, summary });
    } catch (e) {
      setError(toApiError(e).message);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (!data) {
    return (
      <View style={styles.fill}>
        <View style={styles.column}>
          {error ? <LoadError message={error} onRetry={() => void load()} /> : <Loading label="Loading your wallets" />}
        </View>
      </View>
    );
  }

  const { wallets, summary } = data;
  const totals = totalsByCurrency(wallets);
  // The report has no currency of its own; it is in the wallets' currency
  // when they share one, which is the only case it is labelled with one.
  const reportCurrency = totals.length === 1 ? totals[0][0] : DEFAULT_CURRENCY;

  const income = parseCents(summary.total_income);
  const expenses = parseCents(summary.total_expenses);
  const net = parseCents(summary.net_savings);
  const scale = income > expenses ? income : expenses;
  const share = (c: bigint) => (scale > 0n ? Number((c * 10000n) / scale) / 100 : 0);
  const savingsRate = income > 0n ? Math.round(Number((net * 1000n) / income) / 10) : null;

  return (
    <ScrollView style={styles.fill} contentContainerStyle={styles.scroll}>
      <View style={styles.column}>
        {/* 1 · Total balance */}
        <View style={[styles.panel, styles.hero]} testID="total-balance">
          <Text style={styles.label}>Total balance</Text>
          {totals.length === 0 ? (
            <Text style={styles.heroValue}>{formatMoney('0', DEFAULT_CURRENCY)}</Text>
          ) : (
            totals.map(([cur, sum]) => (
              <Text key={cur} style={[styles.heroValue, totals.length > 1 && styles.heroValueMulti]}>
                {formatMoney(sum, cur)}
                {totals.length > 1 ? <Text style={styles.heroCurrency}> {cur}</Text> : null}
              </Text>
            ))
          )}
          <Text style={styles.heroSub}>
            Across {wallets.length} {wallets.length === 1 ? 'wallet' : 'wallets'}
          </Text>
        </View>

        {/* 2 · Wallets */}
        <View style={styles.section}>
          <View style={styles.sectionHead}>
            <Text style={styles.label}>Wallets</Text>
            <Text style={styles.count}>{wallets.length}</Text>
          </View>
          {wallets.length === 0 ? (
            <View style={styles.panel}>
              <Text style={styles.stateText}>No wallets yet.</Text>
            </View>
          ) : (
            <View style={styles.walletGrid}>
              {wallets.map((w) => (
                <View key={w.id} style={[styles.panel, styles.wallet]} testID={`wallet-${w.name}`}>
                  <View style={styles.walletTop}>
                    <Text style={styles.walletName} numberOfLines={1}>
                      {w.name}
                    </Text>
                    <Text style={styles.walletType}>{w.type}</Text>
                  </View>
                  <Text style={[styles.walletBalance, parseCents(w.balance) < 0n && styles.negative]}>
                    {formatMoney(w.balance, w.currency)}
                  </Text>
                </View>
              ))}
            </View>
          )}
        </View>

        {/* 3 · Analysis */}
        <View style={styles.section}>
          <View style={styles.sectionHead}>
            <Text style={styles.label}>Analysis</Text>
            <Text style={styles.count}>{monthLabel(summary.period)}</Text>
          </View>

          <View style={[styles.panel, styles.analysis]}>
            <Text style={styles.subTitle}>Income vs. expenses</Text>
            {(
              [
                ['Income', summary.total_income, income, moon.income],
                ['Expenses', summary.total_expenses, expenses, moon.expense],
              ] as const
            ).map(([name, value, cents, color]) => (
              <View key={name} style={styles.flowRow} testID={`flow-${name}`}>
                <View style={styles.flowHead}>
                  <View style={styles.flowName}>
                    <View style={[styles.swatch, { backgroundColor: color }]} />
                    <Text style={styles.flowLabel}>{name}</Text>
                  </View>
                  <Text style={styles.flowValue}>{formatMoney(value, reportCurrency)}</Text>
                </View>
                <View style={styles.bar}>
                  <View style={[styles.barFill, { width: `${share(cents)}%`, backgroundColor: color }]} />
                </View>
              </View>
            ))}

            <View style={styles.netRow} testID="net-savings">
              <Text style={styles.netLabel}>Net savings</Text>
              <View style={styles.netRight}>
                <Text style={[styles.netValue, net < 0n && styles.negative]}>
                  {formatMoney(summary.net_savings, reportCurrency, { signed: true })}
                </Text>
                {savingsRate !== null ? (
                  <Text style={styles.netRate}>
                    {net < 0n ? 'overspent by' : 'saved'} {Math.abs(savingsRate)}% of income
                  </Text>
                ) : null}
              </View>
            </View>
          </View>

          <View style={[styles.panel, styles.analysis]}>
            <Text style={styles.subTitle}>Where the money went</Text>
            <ExpenseDonut
              categories={summary.top_categories}
              totalExpenses={summary.total_expenses}
              currency={reportCurrency}
            />
          </View>
        </View>
      </View>
    </ScrollView>
  );
}

const num = { fontVariant: ['tabular-nums' as const] };
const label = {
  fontFamily: font.semibold,
  fontSize: 12,
  letterSpacing: 3,
  textTransform: 'uppercase' as const,
  color: moon.muted,
};

const styles = StyleSheet.create({
  fill: { flex: 1 },
  scroll: { paddingTop: 4, paddingBottom: 120 },
  column: { width: '100%', maxWidth: 720, alignSelf: 'center', paddingHorizontal: 16, gap: 22 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 20,
    gap: 12,
  },
  brand: { ...label, color: moon.inkSoft, flexShrink: 1 },
  headerStack: { gap: 12 },
  headerSong: { flexDirection: 'row' },
  headerSongWide: { flex: 1, flexDirection: 'row', maxWidth: 440 },
  ghostButton: {
    height: 34,
    justifyContent: 'center',
    paddingHorizontal: 16,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: moon.panelBorder,
    backgroundColor: 'rgba(10,18,32,0.55)',
    alignSelf: 'center',
  },
  ghostLabel: { ...label, fontSize: 11, color: moon.inkSoft },
  pressed: { opacity: 0.7 },
  state: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 16 },
  statePanel: { alignItems: 'center', gap: 14, maxWidth: 380 },
  stateText: { fontFamily: font.medium, fontSize: 16, color: moon.inkSoft, textAlign: 'center' },

  panel: {
    padding: 20,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: moon.panelBorder,
    backgroundColor: moon.panel,
  },
  label,
  count: { ...label, color: moon.inkSoft },
  section: { gap: 12 },
  sectionHead: { flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between', paddingHorizontal: 4 },

  hero: { paddingVertical: 26, gap: 4 },
  heroValue: { fontFamily: font.light, fontSize: 60, lineHeight: 66, color: moon.ink, letterSpacing: 0.5, ...num },
  heroValueMulti: { fontSize: 40, lineHeight: 46 },
  heroCurrency: { fontFamily: font.medium, fontSize: 18, color: moon.muted },
  heroSub: { fontFamily: font.medium, fontSize: 15, color: moon.muted, letterSpacing: 0.5 },

  walletGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  wallet: { flexGrow: 1, flexBasis: 260, gap: 14, paddingVertical: 18 },
  walletTop: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 },
  walletName: { flexShrink: 1, fontFamily: font.semibold, fontSize: 18, color: moon.ink, letterSpacing: 0.3 },
  walletType: { ...label, fontSize: 10, letterSpacing: 2 },
  walletBalance: { fontFamily: font.regular, fontSize: 28, color: moon.ink, ...num },
  negative: { color: moon.expense },

  analysis: { gap: 16 },
  subTitle: { fontFamily: font.semibold, fontSize: 17, color: moon.ink, letterSpacing: 0.3 },
  flowRow: { gap: 8 },
  flowHead: { flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between' },
  flowName: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  swatch: { width: 10, height: 10, borderRadius: 3 },
  flowLabel: { fontFamily: font.medium, fontSize: 16, color: moon.inkSoft },
  flowValue: { fontFamily: font.semibold, fontSize: 18, color: moon.ink, ...num },
  bar: { height: 10, borderRadius: 4, backgroundColor: moon.track, overflow: 'hidden' },
  barFill: { height: '100%', borderRadius: 4 },
  netRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: 8,
    paddingTop: 14,
    borderTopWidth: 1,
    borderTopColor: moon.hairline,
  },
  netLabel: { ...label, color: moon.inkSoft },
  netRight: { alignItems: 'flex-end' },
  netValue: { fontFamily: font.regular, fontSize: 30, color: moon.income, ...num },
  netRate: { fontFamily: font.medium, fontSize: 14, color: moon.muted },
});
