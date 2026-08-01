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
 *
 * Per DESIGN.md's "One real conflict" note: the budget meter's category/percent
 * text stays `ink` — the status hue rides the fill bar, not the label — so
 * colour is never the only channel and the label clears WCAG AA on its own.
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
    <View style={styles.budgetItem}>
      <View style={styles.budgetHeader}>
        <Text style={styles.budgetCategory}>{category}</Text>
        <Text style={styles.budgetPercent}>{percent}%</Text>
      </View>
      <View style={styles.budgetTrack}>
        <View
          style={[
            styles.budgetFill,
            { width: `${Math.min(percent, 100)}%`, backgroundColor: palette.accent },
          ]}
        />
      </View>
      <Text style={styles.budgetDetail}>
        ${used} of ${limit}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  // stat-tile — DESIGN.md: sky-deep fill, white hero figure.
  balanceCard: {
    backgroundColor: color.surfaceInverse,
    padding: space.xl,
    borderRadius: radius.md,
    gap: space.xs + 2,
  },
  balanceLabel: {
    fontFamily: font.family.bodyMedium,
    color: color.textOnInverse,
    fontSize: font.size.body,
  },
  balanceAmount: {
    fontFamily: font.family.heading,
    color: color.textInverse,
    fontSize: font.size.hero,
  },
  primaryButton: {
    backgroundColor: color.primary,
    color: color.primaryText,
    fontFamily: font.family.bodyMedium,
    fontSize: font.size.md,
    paddingVertical: space.md,
    borderRadius: radius.full,
    textAlign: 'center',
  },
  section: { gap: space.sm },
  sectionTitle: {
    fontFamily: font.family.headingSemibold,
    fontSize: 20,
    color: color.text,
  },
  walletRow: { flexDirection: 'row', flexWrap: 'wrap', gap: space.sm },
  // wallet-card — DESIGN.md: surface card, hairline, name muted body, balance h3.
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
  walletName: { fontFamily: font.family.body, fontSize: font.size.sm, color: color.textMuted },
  walletBalance: { fontFamily: font.family.headingSemibold, fontSize: font.size.xl, color: color.text },
  budgetList: { gap: space.sm },
  // budget-meter — DESIGN.md: surface-sunken field; category/percent stay ink,
  // the status hue lives only in the fill (never the sole channel of meaning).
  budgetItem: {
    padding: space.md,
    borderRadius: radius.md,
    backgroundColor: color.surfaceSunken,
    gap: space.xs + 2,
  },
  budgetHeader: { flexDirection: 'row', justifyContent: 'space-between' },
  budgetCategory: {
    fontFamily: font.family.bodyMedium,
    fontSize: font.size.sm,
    color: color.text,
  },
  budgetPercent: { fontFamily: font.family.bodyMedium, fontSize: font.size.sm, color: color.text },
  budgetTrack: {
    height: 6,
    borderRadius: radius.sm,
    backgroundColor: 'rgba(59,65,71,0.12)',
    overflow: 'hidden',
  },
  budgetFill: { height: 6, borderRadius: radius.sm },
  budgetDetail: { fontFamily: font.family.body, fontSize: font.size.xs, color: color.textMuted },
  recentList: { gap: space.xs },
  // transaction-row — DESIGN.md: surface row, hairline; sign shown alongside
  // colour, so income green is a supplement, not the only signal.
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
  recentLabel: { fontFamily: font.family.body, fontSize: font.size.body, color: color.text },
  recentAmount: { fontFamily: font.family.bodyMedium, fontSize: font.size.body },
  quickLinks: { marginTop: space.sm, gap: space.md },
  link: { color: color.primary, fontFamily: font.family.bodyMedium, fontSize: font.size.md },
});
