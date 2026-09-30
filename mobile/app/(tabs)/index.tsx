/**
 * Dashboard.
 *
 * Layout still follows the SDS §3.2 wireframe's information set — net balance,
 * wallet summary, budget health, recent activity, a prominent log-transaction
 * call to action — restyled entirely in the Cash & Carry system (DESIGN.md).
 * Only the visual system changed here; nothing about which figures appear or
 * what they mean moved.
 *
 * Every figure on this screen is a hard-coded demo value, unchanged from the
 * prior version. Features 03–11 (wallets, budgets, transactions) are out of
 * scope for this round, so there is nothing real to read — hence the DEMO
 * markers and the prototype banner. Budget colours come from
 * src/theme/tokens.ts so health stays consistent with UXR-02 (🟢 healthy ·
 * 🟡 warning · 🔴 exceeded).
 *
 * Per DESIGN.md's "One rule carried over": the budget thermometer's
 * category/percent text stays `ink` — the status hue rides the fill only —
 * so colour is never the only channel and the label clears WCAG AA on its
 * own. The recent-transaction amount's colour is likewise a supplement to
 * the `+`/`-` sign already shown, never the sole signal.
 */
import { LinearGradient } from 'expo-linear-gradient';
import { Link } from 'expo-router';
import type { ReactNode } from 'react';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Screen } from '../../src/components/Screen';
import { GroceriesGlyph, SalaryGlyph, TransportGlyph } from '../../src/components/icons/Glyphs';
import { PostmarkIcon } from '../../src/components/icons/PostmarkIcon';
import { TornEdge } from '../../src/components/icons/TornEdge';
import { DashboardIds } from '../../src/constants/elementIds';
import { budgetHealth, color, font, gradient, radius, space } from '../../src/theme/tokens';

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

type Direction = 'IN' | 'OUT';

export default function DashboardScreen() {
  // OUT (expense) is the default-active side of the toggle — expense is the
  // more frequent action, per the approved concept.
  const [direction, setDirection] = useState<Direction>('OUT');
  const [ledgerOpen, setLedgerOpen] = useState(false);

  return (
    <Screen
      testID={DashboardIds.screen}
      note="Layout from SDS §3.2, restyled Cash & Carry — every figure below is demo data"
    >
      <HeroTicket direction={direction} onChangeDirection={setDirection} />

      <BalanceTape amount={DEMO.netBalance} />

      <Pressable
        style={styles.ledgerToggle}
        onPress={() => setLedgerOpen((open) => !open)}
        accessibilityRole="button"
        accessibilityState={{ expanded: ledgerOpen }}
      >
        <Text style={styles.ledgerToggleLabel}>{ledgerOpen ? '▾' : '▸'} Ledger Book</Text>
        <Text style={styles.ledgerToggleHint}>
          {ledgerOpen ? 'Tap to close' : 'Wallets, budgets & recent activity'}
        </Text>
      </Pressable>

      {ledgerOpen ? (
        <View style={styles.ledgerBody}>
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
                <BudgetThermometer key={b.category} {...b} />
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
                      { color: t.kind === 'INCOME' ? color.income : color.expense },
                    ]}
                  >
                    {t.amount}
                  </Text>
                </View>
              ))}
            </View>
          </Section>
        </View>
      ) : null}
    </Screen>
  );
}

/** stat-tile's replacement — the "ticket" hero: torn top, toggle, amount, stamp. */
function HeroTicket({
  direction,
  onChangeDirection,
}: {
  direction: Direction;
  onChangeDirection: (direction: Direction) => void;
}) {
  const isOut = direction === 'OUT';
  const stampColors = isOut ? gradient.expenseStamp : gradient.incomeStamp;

  return (
    <View style={styles.heroWrap}>
      <TornEdge />
      <View style={styles.heroBody}>
        <View style={styles.toggleRow}>
          <ToggleSegment
            label="IN"
            active={!isOut}
            tone={color.income}
            onPress={() => onChangeDirection('IN')}
          />
          <ToggleSegment
            label="OUT"
            active={isOut}
            tone={color.expense}
            onPress={() => onChangeDirection('OUT')}
          />
        </View>

        <View style={styles.amountBlock}>
          <Text style={styles.amountCurrency}>$</Text>
          <Text style={styles.amountFigure}>0.00</Text>
        </View>
        <View style={styles.ruleLine} />
        <Text style={styles.amountHint}>Amount entry — TM-US-01, not built yet</Text>

        <View style={styles.glyphRow}>
          <PostmarkIcon>
            <GroceriesGlyph color={color.text} />
          </PostmarkIcon>
          <PostmarkIcon>
            <TransportGlyph color={color.text} />
          </PostmarkIcon>
          <PostmarkIcon>
            <SalaryGlyph color={color.text} />
          </PostmarkIcon>
        </View>

        <Link href="/(tabs)/transactions/create" asChild>
          <Pressable
            testID={DashboardIds.logTransactionCta}
            accessibilityRole="button"
            style={({ pressed }) => (pressed ? styles.stampPressed : null)}
          >
            <LinearGradient
              colors={stampColors}
              start={{ x: 0, y: 0 }}
              end={{ x: 0, y: 1 }}
              style={styles.stampButton}
            >
              <Text style={styles.stampLabel}>STAMP IT {isOut ? '· OUT' : '· IN'}</Text>
            </LinearGradient>
          </Pressable>
        </Link>
      </View>
    </View>
  );
}

function ToggleSegment({
  label,
  active,
  tone,
  onPress,
}: {
  label: string;
  active: boolean;
  tone: string;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected: active }}
      style={[styles.toggleSegment, active ? { backgroundColor: tone } : null]}
    >
      <Text style={[styles.toggleLabel, active ? styles.toggleLabelActive : null]}>{label}</Text>
    </Pressable>
  );
}

/** Net-balance strip below the hero — styled like a strip of tape tacked onto the ledger. */
function BalanceTape({ amount }: { amount: string }) {
  return (
    <View style={styles.tapeWrap}>
      <Text style={styles.tapeLabel}>Total Net Balance · DEMO</Text>
      <Text style={styles.tapeAmount} testID={DashboardIds.netBalance}>
        {amount}
      </Text>
    </View>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

/** Budget progress. Health is derived, never hard-coded — see tokens.budgetHealth. */
function BudgetThermometer({
  category,
  used,
  limit,
}: {
  category: string;
  used: number;
  limit: number;
}) {
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
  // Hero ticket — DESIGN.md "Components → hero ticket."
  heroWrap: {},
  heroBody: {
    backgroundColor: color.surface,
    borderLeftWidth: 1,
    borderRightWidth: 1,
    borderBottomWidth: 1,
    borderColor: color.border,
    borderBottomLeftRadius: radius.md,
    borderBottomRightRadius: radius.md,
    paddingHorizontal: space.lg,
    paddingTop: space.sm,
    paddingBottom: space.lg,
  },
  toggleRow: {
    flexDirection: 'row',
    borderWidth: 1,
    borderColor: color.border,
    borderRadius: radius.sm,
    overflow: 'hidden',
    marginBottom: space.lg,
  },
  toggleSegment: {
    flex: 1,
    paddingVertical: space.sm,
    alignItems: 'center',
    backgroundColor: color.surface,
  },
  toggleLabel: {
    fontFamily: font.family.bodyMedium,
    fontSize: font.size.md,
    color: color.text,
    letterSpacing: 1,
  },
  toggleLabelActive: { color: color.primaryText },
  amountBlock: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'center',
    gap: space.xs,
  },
  amountCurrency: {
    fontFamily: font.family.heading,
    fontSize: font.size.xl,
    color: color.textMuted,
    marginBottom: 4,
  },
  amountFigure: {
    fontFamily: font.family.heading,
    fontSize: 46,
    color: color.textMuted,
    letterSpacing: 1,
  },
  ruleLine: {
    borderBottomWidth: 1,
    borderBottomColor: color.border,
    marginTop: space.xs,
    marginHorizontal: space.xl,
  },
  amountHint: {
    fontFamily: font.family.bodyItalic,
    fontSize: font.size.xs,
    color: color.textMuted,
    textAlign: 'center',
    marginTop: space.xs,
    marginBottom: space.lg,
  },
  glyphRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: space.xl,
    marginBottom: space.lg,
  },
  stampButton: {
    borderRadius: radius.stamp,
    paddingVertical: space.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stampPressed: { opacity: 0.85 },
  stampLabel: {
    fontFamily: font.family.heading,
    color: color.primaryText,
    fontSize: font.size.lg,
    letterSpacing: 1.5,
  },

  // Balance tape — a strip of tape tacked below the ticket.
  tapeWrap: {
    alignSelf: 'center',
    backgroundColor: color.surfaceSunken,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderStyle: 'dashed',
    borderColor: color.textMuted,
    paddingVertical: space.sm,
    paddingHorizontal: space.xxl,
    transform: [{ rotate: '-1deg' }],
    gap: 2,
  },
  tapeLabel: {
    fontFamily: font.family.bodyItalic,
    fontSize: font.size.xs,
    color: color.textMuted,
    textAlign: 'center',
  },
  tapeAmount: {
    fontFamily: font.family.heading,
    fontSize: font.size.title,
    color: color.text,
    textAlign: 'center',
  },

  // Ledger Book — plain useState expand/collapse, no gesture library.
  ledgerToggle: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: color.surface,
    borderWidth: 1,
    borderColor: color.border,
    borderRadius: radius.md,
    paddingVertical: space.md,
    paddingHorizontal: space.lg,
  },
  ledgerToggleLabel: { fontFamily: font.family.heading, fontSize: font.size.lg, color: color.text },
  ledgerToggleHint: {
    fontFamily: font.family.body,
    fontSize: font.size.xs,
    color: color.textMuted,
    flexShrink: 1,
    textAlign: 'right',
    marginLeft: space.md,
  },
  ledgerBody: { gap: space.lg },

  section: { gap: space.sm },
  sectionTitle: { fontFamily: font.family.headingSemibold, fontSize: 20, color: color.text },

  walletRow: { flexDirection: 'row', flexWrap: 'wrap', gap: space.sm },
  // wallet-card — DESIGN.md: Ledger Paper card, hairline, name muted body, balance heading.
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
  walletBalance: {
    fontFamily: font.family.headingSemibold,
    fontSize: font.size.xl,
    color: color.text,
  },

  budgetList: { gap: space.sm },
  // budget-thermometer — DESIGN.md: category/percent stay ink; the status hue
  // lives only in the fill (never the sole channel of meaning) — UXR-02.
  budgetItem: {
    padding: space.md,
    borderRadius: radius.md,
    backgroundColor: color.surfaceSunken,
    gap: space.xs + 2,
  },
  budgetHeader: { flexDirection: 'row', justifyContent: 'space-between' },
  budgetCategory: { fontFamily: font.family.bodyMedium, fontSize: font.size.sm, color: color.text },
  budgetPercent: { fontFamily: font.family.bodyMedium, fontSize: font.size.sm, color: color.text },
  budgetTrack: {
    height: 8,
    borderRadius: radius.sm,
    backgroundColor: 'rgba(43,36,32,0.12)',
    overflow: 'hidden',
  },
  budgetFill: { height: 8, borderRadius: radius.sm },
  budgetDetail: { fontFamily: font.family.body, fontSize: font.size.xs, color: color.textMuted },

  recentList: { gap: space.xs },
  // transaction-row — sign shown alongside colour, so colour is a supplement.
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
});
