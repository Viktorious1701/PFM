/**
 * Dashboard.
 *
 * Layout follows the SDS §3.2 wireframe: net balance, wallet summary, budget
 * health, recent activity, and a prominent log-transaction call to action.
 *
 * Every figure on this screen is a hard-coded demo value. Features 03–11
 * (wallets, budgets, transactions) are out of scope for this round, so there is
 * nothing real to read — hence the DEMO markers and the prototype banner.
 * Colours come from src/theme/tokens.ts so budget health stays consistent with
 * UXR-02 (🟢 healthy · 🟡 warning · 🔴 exceeded).
 */
import { Link } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { Screen } from '../../src/components/Screen';
import { DashboardIds } from '../../src/constants/elementIds';
import { budgetHealth, color, font, radius, space } from '../../src/theme/tokens';

/** Demo data. Replaced by GET /api/v1/wallets + /budgets when those stories land. */
const DEMO = {
  netBalance: '$12,450.00',
  wallets: [
    { name: 'Checking', balance: '$10,000.00' },
    { name: 'Cash', balance: '$450.00' },
    { name: 'Savings', balance: '$2,000.00' },
  ],
  budgets: [
    { category: 'Dining Out', used: 160, limit: 200 },
    { category: 'Groceries', used: 210, limit: 400 },
    { category: 'Transport', used: 190, limit: 150 },
  ],
  recent: [
    { label: 'Grocery Store', amount: '-$85.50', kind: 'EXPENSE' as const },
    { label: 'Salary Payment', amount: '+$3,500.00', kind: 'INCOME' as const },
  ],
};

export default function DashboardScreen() {
  return (
    <Screen testID={DashboardIds.screen} note="Layout from SDS §3.2 — every figure below is demo data">
      <View style={styles.balanceCard}>
        <Text style={styles.balanceLabel}>Total Net Balance · DEMO</Text>
        <Text style={styles.balanceAmount} testID={DashboardIds.netBalance}>
          {DEMO.netBalance}
        </Text>
      </View>

      <Link href="/(tabs)/transactions/create" style={styles.primaryButton} testID={DashboardIds.logTransactionCta}>
        + Log New Transaction
      </Link>

      <Section title="My Wallets · DEMO">
        <View style={styles.walletRow}>
          {DEMO.wallets.map((w) => (
            <View key={w.name} style={styles.walletCard}>
              <Text style={styles.walletName}>{w.name}</Text>
              <Text style={styles.walletBalance}>{w.balance}</Text>
            </View>
          ))}
        </View>
      </Section>

      <Section title="Budget Health · DEMO">
        <View testID={DashboardIds.budgetAlert} style={styles.budgetList}>
          {DEMO.budgets.map((b) => (
            <BudgetBar key={b.category} {...b} />
          ))}
        </View>
      </Section>

      <Section title="Recent Transactions · DEMO">
        <View style={styles.recentList}>
          {DEMO.recent.map((t) => (
            <View key={t.label} style={styles.recentRow}>
              <Text style={styles.recentLabel}>{t.label}</Text>
              <Text
                style={[
                  styles.recentAmount,
                  { color: t.kind === 'INCOME' ? color.success.fg : color.text },
                ]}
              >
                {t.amount}
              </Text>
            </View>
          ))}
        </View>
      </Section>

      <View style={styles.quickLinks}>
        <Link href="/(tabs)/users/invite" style={styles.link}>
          📧 Invite Family Member
        </Link>
        <Link href="/(auth)/login" style={styles.link}>
          🔐 Sign In / Change Account
        </Link>
        <Link href="/activate?token=demo" style={styles.link}>
          ✉️ Open an activation link
        </Link>
        <Link href="/(tabs)/reports" style={styles.link}>
          📈 Financial Reports
        </Link>
      </View>
    </Screen>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

/** Budget progress. Health is derived, never hard-coded — see tokens.budgetHealth. */
function BudgetBar({ category, used, limit }: { category: string; used: number; limit: number }) {
  const percent = Math.round((used / limit) * 100);
  const palette = color.budget[budgetHealth(percent)];

  return (
    <View style={[styles.budgetItem, { backgroundColor: palette.bg }]}>
      <View style={styles.budgetHeader}>
        <Text style={[styles.budgetCategory, { color: palette.fg }]}>{category}</Text>
        <Text style={[styles.budgetPercent, { color: palette.fg }]}>{percent}%</Text>
      </View>
      <View style={styles.budgetTrack}>
        <View
          style={[
            styles.budgetFill,
            { width: `${Math.min(percent, 100)}%`, backgroundColor: palette.accent },
          ]}
        />
      </View>
      <Text style={[styles.budgetDetail, { color: palette.fg }]}>
        ${used} of ${limit}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  balanceCard: {
    backgroundColor: color.surfaceInverse,
    padding: space.xl,
    borderRadius: radius.lg,
    gap: space.xs + 2,
  },
  balanceLabel: { color: color.textOnInverse, fontSize: font.size.body },
  balanceAmount: {
    color: color.textInverse,
    fontSize: font.size.hero,
    fontWeight: font.weight.bold,
  },
  primaryButton: {
    backgroundColor: color.primary,
    color: color.primaryText,
    fontWeight: font.weight.semibold,
    fontSize: font.size.lg,
    paddingVertical: space.md + 2,
    borderRadius: radius.md,
    textAlign: 'center',
  },
  section: { gap: space.sm },
  sectionTitle: {
    fontSize: font.size.xl,
    fontWeight: font.weight.semibold,
    color: color.text,
  },
  walletRow: { flexDirection: 'row', flexWrap: 'wrap', gap: space.sm },
  walletCard: {
    flexGrow: 1,
    minWidth: 100,
    padding: space.md,
    borderRadius: radius.md,
    backgroundColor: color.surface,
    borderWidth: 1,
    borderColor: color.border,
    gap: 2,
  },
  walletName: { fontSize: font.size.sm, color: color.textMuted },
  walletBalance: { fontSize: font.size.lg, fontWeight: font.weight.semibold, color: color.text },
  budgetList: { gap: space.sm },
  budgetItem: { padding: space.md, borderRadius: radius.md, gap: space.xs + 2 },
  budgetHeader: { flexDirection: 'row', justifyContent: 'space-between' },
  budgetCategory: { fontSize: font.size.body, fontWeight: font.weight.semibold },
  budgetPercent: { fontSize: font.size.body, fontWeight: font.weight.bold },
  budgetTrack: {
    height: 6,
    borderRadius: radius.sm,
    backgroundColor: 'rgba(0,0,0,0.10)',
    overflow: 'hidden',
  },
  budgetFill: { height: 6, borderRadius: radius.sm },
  budgetDetail: { fontSize: font.size.sm },
  recentList: { gap: space.xs },
  recentRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: space.sm,
    paddingHorizontal: space.md,
    backgroundColor: color.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: color.border,
  },
  recentLabel: { fontSize: font.size.body, color: color.text },
  recentAmount: { fontSize: font.size.body, fontWeight: font.weight.semibold },
  quickLinks: { marginTop: space.sm, gap: space.md },
  link: { color: color.primary, fontSize: font.size.md, fontWeight: font.weight.medium },
});
