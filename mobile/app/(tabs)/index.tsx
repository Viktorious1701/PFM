/**
 * Dashboard.
 *
 * Layout still follows the SDS §3.2 wireframe's information set — net balance,
 * wallet summary, budget health, recent activity, a prominent log-transaction
 * call to action. This screen's visual system is "Nullscapes" — the dark,
 * icy-blue, Space Grotesk component language validated in the design canvas's
 * `Components.dc.html` swatch sheet (buttons, wallet cards, transaction rows,
 * budget bars), shared via `src/theme/nullscapes.ts` now that every tab uses
 * it (not just this screen).
 *
 * The animated Nullscapes background itself is NOT mounted here any more —
 * it moved to `app/(tabs)/_layout.tsx`, mounted once as a sibling of
 * `<Tabs>`, so it persists across every tab switch and animates a "camera
 * zoom" synced to the active tab (`src/lib/tabCameraScale.ts`) instead of
 * being a per-screen illustration.
 *
 * Every figure on this screen is a hard-coded demo value, unchanged from the
 * prior version. Features 03–11 (wallets, budgets, transactions) are out of
 * scope for this round, so there is nothing real to read — hence the DEMO
 * markers and the prototype banner.
 *
 * Budget colour still rides the fill only (never the sole channel of
 * meaning) — the percent figure next to it says the same thing in text,
 * carried over from the original UXR-02 rule.
 */
import { Link } from 'expo-router';
import type { ReactNode } from 'react';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Screen } from '../../src/components/Screen';
import { GroceriesGlyph, SalaryGlyph, TransportGlyph } from '../../src/components/icons/Glyphs';
import { PostmarkIcon } from '../../src/components/icons/PostmarkIcon';
import { DashboardIds } from '../../src/constants/elementIds';
import { ns, nsBudgetAccent, nsFont } from '../../src/theme/nullscapes';
import { budgetHealth } from '../../src/theme/tokens';

/** Demo data. Replaced by GET /api/v1/wallets + /budgets when those stories land. */
const DEMO = {
  netBalance: '$12,450.00',
  wallets: [
    { name: 'Checking', balance: '$10,000.00', kind: 'BANK' },
    { name: 'Cash', balance: '$450.00', kind: 'CASH' },
    { name: 'Savings', balance: '$2,000.00', kind: 'BANK' },
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
        title="Dashboard"
        note="Layout from SDS §3.2, Nullscapes component language — every figure below is demo data"
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
                    <View style={styles.walletCardHeader}>
                      <Text style={styles.walletName}>{w.name}</Text>
                      <View style={styles.walletKindChip}>
                        <Text style={styles.walletKindLabel}>{w.kind}</Text>
                      </View>
                    </View>
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
                        { color: t.kind === 'INCOME' ? ns.mint : ns.danger },
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

/** The "ticket" hero: IN/OUT toggle, amount, category glyphs, log-entry CTA —
 * the Nullscapes glass card (`Components.dc.html`'s card/button treatment). */
function HeroTicket({
  direction,
  onChangeDirection,
}: {
  direction: Direction;
  onChangeDirection: (direction: Direction) => void;
}) {
  const isOut = direction === 'OUT';
  const tone = isOut ? ns.danger : ns.mint;

  return (
    <View style={styles.heroBody}>
      <View style={styles.toggleRow}>
        <ToggleSegment
          label="IN"
          active={!isOut}
          tone={ns.mint}
          onPress={() => onChangeDirection('IN')}
        />
        <ToggleSegment
          label="OUT"
          active={isOut}
          tone={ns.danger}
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
        <PostmarkIcon inactiveColor={ns.mintBorder}>
          <GroceriesGlyph color={ns.inkSoft} />
        </PostmarkIcon>
        <PostmarkIcon inactiveColor={ns.mintBorder}>
          <TransportGlyph color={ns.inkSoft} />
        </PostmarkIcon>
        <PostmarkIcon inactiveColor={ns.mintBorder}>
          <SalaryGlyph color={ns.inkSoft} />
        </PostmarkIcon>
      </View>

      <Link href="/(tabs)/transactions/create" asChild>
        <Pressable
          testID={DashboardIds.logTransactionCta}
          accessibilityRole="button"
          style={({ pressed }) => [styles.ctaButton, { borderColor: tone }, pressed ? styles.ctaPressed : null]}
        >
          <Text style={[styles.ctaLabel, { color: tone }]}>LOG ENTRY · {isOut ? 'OUT' : 'IN'}</Text>
        </Pressable>
      </Link>
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
      style={[
        styles.toggleSegment,
        active ? { backgroundColor: tone, shadowColor: tone } : null,
      ]}
    >
      <Text style={[styles.toggleLabel, active ? styles.toggleLabelActive : null]}>{label}</Text>
    </Pressable>
  );
}

/** Net-balance strip below the hero — a slim glass chip, not a paper tape. */
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
      <View style={styles.sectionTitleChip}>
        <Text style={styles.sectionTitle}>{title}</Text>
      </View>
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
  const accent = nsBudgetAccent[budgetHealth(percent)];

  return (
    <View style={[styles.budgetItem, { borderColor: `${accent}4D` }]}>
      <View style={styles.budgetHeader}>
        <Text style={styles.budgetCategory}>{category}</Text>
        <Text style={styles.budgetPercent}>{percent}%</Text>
      </View>
      <View style={styles.budgetTrack}>
        <View
          style={[
            styles.budgetFill,
            { width: `${Math.min(percent, 100)}%`, backgroundColor: accent, shadowColor: accent },
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
  // Hero ticket — now a Nullscapes glass card: `Components.dc.html`'s
  // card treatment (bg #10141B, mint-tinted hairline, radius 10) instead of
  // the Cash & Carry paper ticket + torn edge.
  heroBody: {
    backgroundColor: ns.card,
    borderWidth: 1,
    borderColor: ns.cardBorder,
    borderRadius: 14,
    paddingHorizontal: 20,
    paddingVertical: 20,
    gap: 4,
  },
  toggleRow: {
    flexDirection: 'row',
    borderWidth: 1,
    borderColor: ns.hairline,
    borderRadius: 8,
    overflow: 'hidden',
    marginBottom: 20,
  },
  toggleSegment: {
    flex: 1,
    paddingVertical: 12,
    alignItems: 'center',
    backgroundColor: 'transparent',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.5,
    shadowRadius: 10,
  },
  toggleLabel: {
    fontFamily: nsFont.semibold,
    fontSize: 13,
    color: ns.muted,
    letterSpacing: 1.5,
  },
  toggleLabelActive: { color: '#05070A' },
  amountBlock: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'center',
    gap: 6,
  },
  amountCurrency: {
    fontFamily: nsFont.semibold,
    fontSize: 20,
    color: ns.mutedFaint,
    marginBottom: 4,
  },
  amountFigure: {
    fontFamily: nsFont.bold,
    fontSize: 46,
    color: ns.inkSoft,
    letterSpacing: 1,
  },
  ruleLine: {
    borderBottomWidth: 1,
    borderBottomColor: ns.hairline,
    marginTop: 8,
    marginHorizontal: 32,
  },
  amountHint: {
    fontFamily: nsFont.regular,
    fontSize: 11,
    fontStyle: 'italic',
    color: ns.mutedFaint,
    textAlign: 'center',
    marginTop: 8,
    marginBottom: 20,
  },
  glyphRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 28,
    marginBottom: 20,
  },
  // Primary log-entry CTA — outline button in the direction's tone, matching
  // `Components.dc.html`'s "VIEW DETAILS" secondary-button treatment (a
  // solid glow button in two different hues per press would fight itself,
  // so the direction's own color carries the state instead of the fill).
  ctaButton: {
    borderWidth: 1,
    borderRadius: 8,
    paddingVertical: 15,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(255,255,255,0.03)',
  },
  ctaPressed: { opacity: 0.75 },
  ctaLabel: {
    fontFamily: nsFont.semibold,
    fontSize: 14,
    letterSpacing: 1.5,
  },

  // Balance tape — a slim glass chip, mint-labelled, bright figure.
  tapeWrap: {
    alignSelf: 'center',
    backgroundColor: ns.card,
    borderWidth: 1,
    borderColor: ns.cardBorder,
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 28,
    gap: 2,
  },
  tapeLabel: {
    fontFamily: nsFont.medium,
    fontSize: 10,
    letterSpacing: 1,
    color: ns.mint,
    textAlign: 'center',
    textTransform: 'uppercase',
  },
  tapeAmount: {
    fontFamily: nsFont.bold,
    fontSize: 24,
    color: ns.ink,
    textAlign: 'center',
  },

  // Ledger Book — plain useState expand/collapse, no gesture library.
  ledgerToggle: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: ns.card,
    borderWidth: 1,
    borderColor: ns.cardBorder,
    borderRadius: 10,
    paddingVertical: 14,
    paddingHorizontal: 18,
  },
  ledgerToggleLabel: { fontFamily: nsFont.semibold, fontSize: 15, color: ns.ink },
  ledgerToggleHint: {
    fontFamily: nsFont.regular,
    fontSize: 11,
    color: ns.mutedFaint,
    flexShrink: 1,
    textAlign: 'right',
    marginLeft: 12,
  },
  ledgerBody: { gap: 20 },

  section: { gap: 10 },
  sectionTitleChip: {
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
  },
  sectionTitle: {
    fontFamily: nsFont.medium,
    fontSize: 11,
    letterSpacing: 2,
    color: ns.mint,
    textTransform: 'uppercase',
  },

  walletRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  // wallet-card — `Components.dc.html`'s wallet-card swatch, verbatim.
  walletCard: {
    flexGrow: 1,
    minWidth: 110,
    padding: 16,
    borderRadius: 10,
    backgroundColor: ns.card,
    borderWidth: 1,
    borderColor: ns.cardBorder,
    gap: 8,
  },
  walletCardHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 6 },
  walletName: {
    fontFamily: nsFont.medium,
    fontSize: 10,
    letterSpacing: 1,
    color: ns.muted,
    textTransform: 'uppercase',
  },
  walletKindChip: {
    borderWidth: 1,
    borderColor: ns.mintBorder,
    borderRadius: 4,
    paddingHorizontal: 5,
    paddingVertical: 1,
  },
  walletKindLabel: { fontFamily: nsFont.medium, fontSize: 8, letterSpacing: 1, color: ns.mint },
  walletBalance: {
    fontFamily: nsFont.bold,
    fontSize: 20,
    color: ns.ink,
  },

  budgetList: { gap: 10 },
  // budget-thermometer — category/percent stay bright ink; the status hue
  // lives only in the fill and the card's own hairline, never the sole
  // channel of meaning (the percent figure says the same thing in text).
  budgetItem: {
    padding: 14,
    borderRadius: 10,
    backgroundColor: ns.card,
    borderWidth: 1,
    gap: 8,
  },
  budgetHeader: { flexDirection: 'row', justifyContent: 'space-between' },
  budgetCategory: { fontFamily: nsFont.medium, fontSize: 13, color: ns.ink },
  budgetPercent: { fontFamily: nsFont.medium, fontSize: 13, color: ns.ink },
  budgetTrack: {
    height: 6,
    borderRadius: 3,
    backgroundColor: ns.track,
    overflow: 'hidden',
  },
  budgetFill: {
    height: '100%',
    borderRadius: 3,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.6,
    shadowRadius: 8,
  },
  budgetDetail: { fontFamily: nsFont.regular, fontSize: 10, color: ns.mutedFaint },

  recentList: { gap: 1, backgroundColor: ns.cardBorder, borderRadius: 10, overflow: 'hidden' },
  // transaction-row — sign shown alongside colour, so colour is a supplement.
  recentRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 14,
    paddingHorizontal: 16,
    backgroundColor: ns.card,
  },
  recentLabel: { fontFamily: nsFont.regular, fontSize: 13, color: ns.ink },
  recentAmount: { fontFamily: nsFont.semibold, fontSize: 14 },
});
