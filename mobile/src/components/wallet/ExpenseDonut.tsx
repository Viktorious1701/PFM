/**
 * Where this month's spending went: a thin donut over the report's top
 * expense categories, with whatever the top five don't cover folded into a
 * gray "Other" slice. The legend is also the table view — every slice's name,
 * amount and share in text — and hovering or pressing a row highlights its
 * slice and puts that category's figures in the donut's center. (Press
 * handlers on the SVG arcs themselves leak responder props onto DOM nodes
 * on web, so the rows are the hit targets.)
 */
import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import Svg, { Circle, G, Path } from 'react-native-svg';

import type { TopCategory } from '../../api/types';
import { formatCents, formatMoney, parseCents } from '../../utils/money';
import { CATEGORY_HUES, OTHER_HUE, font, moon } from '../../theme/moonlit';

type Slice = { key: string; name: string; amount: string; cents: bigint; color: string };

const SIZE = 180;
const R = 74;
const STROKE = 16;
const GAP_DEG = 1.6; // surface gap between neighbouring slices

function arcPath(startDeg: number, endDeg: number): string {
  const toXY = (deg: number) => {
    const rad = ((deg - 90) * Math.PI) / 180;
    return `${SIZE / 2 + R * Math.cos(rad)} ${SIZE / 2 + R * Math.sin(rad)}`;
  };
  const large = endDeg - startDeg > 180 ? 1 : 0;
  return `M ${toXY(startDeg)} A ${R} ${R} 0 ${large} 1 ${toXY(endDeg)}`;
}

export function ExpenseDonut({
  categories,
  totalExpenses,
  currency,
}: {
  categories: TopCategory[];
  totalExpenses: string;
  currency: string;
}) {
  const [active, setActive] = useState<string | null>(null);

  const { slices, total } = useMemo(() => {
    const total = parseCents(totalExpenses);
    const out: Slice[] = categories.map((c, i) => ({
      key: c.category_id,
      name: c.category_name,
      amount: c.total_amount,
      cents: parseCents(c.total_amount),
      color: CATEGORY_HUES[i] ?? OTHER_HUE,
    }));
    const rest = total - out.reduce((s, x) => s + x.cents, 0n);
    if (rest > 0n) {
      out.push({ key: 'other', name: 'Other', amount: formatCents(rest), cents: rest, color: OTHER_HUE });
    }
    return { slices: out, total };
  }, [categories, totalExpenses]);

  if (total <= 0n || slices.length === 0) {
    return <Text style={styles.empty}>No spending recorded this month.</Text>;
  }

  const pct = (c: bigint) => Number((c * 1000n) / total) / 10;
  const activeSlice = slices.find((s) => s.key === active) ?? null;

  let cursor = 0;
  const arcs = slices.map((s) => {
    const sweep = (Number(s.cents) / Number(total)) * 360;
    const start = cursor;
    cursor += sweep;
    const gap = slices.length > 1 ? Math.min(GAP_DEG, sweep / 3) : 0;
    return { ...s, start: start + gap / 2, end: start + sweep - gap / 2, sweep };
  });

  return (
    <View style={styles.wrap}>
      <View style={styles.chart} accessibilityRole="image" accessibilityLabel="Spending by category, donut chart">
        <Svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`}>
          <Circle cx={SIZE / 2} cy={SIZE / 2} r={R} stroke={moon.track} strokeWidth={STROKE} fill="none" />
          <G>
            {arcs.map((a) =>
              a.sweep >= 359.9 ? (
                <Circle
                  key={a.key}
                  cx={SIZE / 2}
                  cy={SIZE / 2}
                  r={R}
                  stroke={a.color}
                  strokeWidth={STROKE}
                  fill="none"
                />
              ) : (
                <Path
                  key={a.key}
                  d={arcPath(a.start, a.end)}
                  stroke={a.color}
                  strokeWidth={active === a.key ? STROKE + 6 : STROKE}
                  strokeOpacity={active && active !== a.key ? 0.35 : 1}
                  fill="none"
                />
              ),
            )}
          </G>
        </Svg>
        <View style={styles.center} pointerEvents="none">
          <Text style={styles.centerLabel} numberOfLines={1}>
            {activeSlice ? activeSlice.name : 'Spent'}
          </Text>
          <Text style={styles.centerValue}>
            {formatMoney(activeSlice ? activeSlice.amount : totalExpenses, currency)}
          </Text>
          {activeSlice ? <Text style={styles.centerPct}>{pct(activeSlice.cents)}%</Text> : null}
        </View>
      </View>

      <View style={styles.legend}>
        {slices.map((s) => (
          <Pressable
            key={s.key}
            testID={`category-${s.name}`}
            onHoverIn={() => setActive(s.key)}
            onHoverOut={() => setActive(null)}
            onPress={() => setActive(active === s.key ? null : s.key)}
            style={[styles.row, active === s.key && styles.rowActive]}
          >
            <View style={[styles.swatch, { backgroundColor: s.color }]} />
            <Text style={styles.rowName} numberOfLines={1}>
              {s.name}
            </Text>
            <Text style={styles.rowPct}>{pct(s.cents)}%</Text>
            <Text style={styles.rowAmount}>{formatMoney(s.amount, currency)}</Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

const num = { fontVariant: ['tabular-nums' as const] };

const styles = StyleSheet.create({
  wrap: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: 20 },
  chart: { width: SIZE, height: SIZE, alignSelf: 'center' },
  center: { ...StyleSheet.absoluteFill, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 36 },
  centerLabel: {
    fontFamily: font.semibold,
    fontSize: 11,
    letterSpacing: 2.5,
    textTransform: 'uppercase',
    color: moon.muted,
  },
  centerValue: { fontFamily: font.medium, fontSize: 22, color: moon.ink, ...num },
  centerPct: { fontFamily: font.medium, fontSize: 13, color: moon.inkSoft },
  legend: { flexGrow: 1, flexBasis: 220, gap: 2 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 7,
    paddingHorizontal: 8,
    borderRadius: 8,
  },
  rowActive: { backgroundColor: 'rgba(223,232,251,0.07)' },
  swatch: { width: 10, height: 10, borderRadius: 3 },
  rowName: { flex: 1, fontFamily: font.medium, fontSize: 16, color: moon.inkSoft },
  rowPct: { width: 52, textAlign: 'right', fontFamily: font.medium, fontSize: 14, color: moon.muted, ...num },
  rowAmount: { width: 96, textAlign: 'right', fontFamily: font.semibold, fontSize: 16, color: moon.ink, ...num },
  empty: { fontFamily: font.medium, fontSize: 15, color: moon.muted },
});
