/**
 * Financial Summary Report — "Balance Scale + Category Stamps".
 *
 * Story: FR-US-01 (SRS §6 Feature-07 / SDS §5.7.1)
 * Endpoint: GET /api/v1/reports/summary — always the current calendar month;
 * the endpoint takes no period argument.
 *
 * Ported from the approved mockup's `#c6` "Balance Scale + Category Stamps"
 * combination (design-explore/summary.html) — the tipping scale carries the
 * income / expense / net-savings story as a physical illustration; the
 * ranked stamp grid beneath it shows exactly where the expense side went.
 * This screen does NOT satisfy any TC — see CLAUDE.md, mobile is a UI layer
 * over an already-verified backend, not itself spec-driven.
 *
 * `SummaryReportRead` has no currency field at all — confirmed against
 * `backend/app/schemas/report.py` — the aggregation is already currency-naive
 * (it sums Decimal amounts across whatever wallets/currencies the caller
 * has). Every amount below renders via `formatMoney(value, 'USD')` with that
 * hardcoded placeholder; a multi-currency user's report is already ambiguous
 * upstream of this screen, not something fixable at this layer.
 */
import type { JSX } from 'react';
import { useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { Circle, G, Line, Path, Svg, Text as SvgText } from 'react-native-svg';

import { toApiError } from '../../../src/api/errors';
import { getSummaryReport } from '../../../src/api/reports';
import type { SummaryReportRead, TopCategory } from '../../../src/api/types';
import { Banner } from '../../../src/components/Banner';
import { Screen } from '../../../src/components/Screen';
import {
  BudgetsGlyph,
  DiningGlyph,
  EntertainmentGlyph,
  GroceriesGlyph,
  RentGlyph,
  SalaryGlyph,
  TransportGlyph,
  UtilitiesGlyph,
} from '../../../src/components/icons/Glyphs';
import { PostmarkIcon } from '../../../src/components/icons/PostmarkIcon';
import { ReportsIds } from '../../../src/constants/elementIds';
import { color, font, radius, space } from '../../../src/theme/tokens';
import { formatMoney } from '../../../src/utils/money';

// ---- Balance scale geometry — ported verbatim from #c6's own SVG (viewBox
// "0 0 300 200"), not redrawn from the prose description. -------------------

const SCALE_VIEWBOX = '0 0 300 200';
const PIVOT_X = 150;
const PIVOT_Y = 110;
/** `<use href="#targetRing" x="136" y="96" width="28" height="28"/>` — the
 * fulcrum symbol's own viewBox is `0 0 24 24`, so `28/24` is the scale factor
 * that reproduces the mockup's `use` sizing via a plain `G` transform. */
const FULCRUM_X = 136;
const FULCRUM_Y = 96;
const FULCRUM_SCALE = 28 / 24;

/** Clamp bound for the beam's tilt, in degrees — #c6's own two data points
 * (verified independently below) never approach this bound. */
const MAX_ANGLE = 40;

/**
 * Positive tips the expense (right) pan down, negative tips the income
 * (left) pan down. Re-derived independently against #c6's own two swatches:
 * income $3,500 / expense $2,350 → (2350-3500)/(2350+3500)×40 = -7.86°,
 * matching the mockup's `rotate(-7.9 150 110)`; income $2,100 / expense
 * $3,450 → (3450-2100)/(3450+2100)×40 = +9.73°, matching the mockup's
 * `rotate(9.7 150 110)`. Both check out.
 */
function scaleAngle(totalIncome: number, totalExpenses: number): number {
  const total = totalIncome + totalExpenses;
  if (total === 0) return 0;
  const raw = ((totalExpenses - totalIncome) / total) * MAX_ANGLE;
  return Math.max(-MAX_ANGLE, Math.min(MAX_ANGLE, raw));
}

const MONTH_NAMES = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

/** `report.period` is always `"YYYY-MM-DD"`, the 1st of the reported month —
 * read directly off the string rather than through a `Date`, so there is no
 * local-timezone risk of rolling back to the previous month. */
function formatPeriodLabel(period: string): string {
  const [year, month] = period.split('-');
  const name = MONTH_NAMES[Number(month) - 1] ?? month;
  return `${name} ${year}`;
}

// ---- Category stamp grid — falling ink-density per rank, from #c6's own
// `.c4-stamp` opacity ladder (rank1 full strength through rank5 faintest). --

const RANK_STYLES: ReadonlyArray<{ size: number; opacity: number }> = [
  { size: 44, opacity: 1 },
  { size: 40, opacity: 0.92 },
  { size: 38, opacity: 0.8 },
  { size: 34, opacity: 0.64 },
  { size: 32, opacity: 0.5 },
];

const MAX_STAMPS = 5;

type CategoryGlyph = (props: { color: string }) => JSX.Element;

/**
 * Name-string lookup against the known 7-category vocabulary — `CategoryRead`
 * has no icon field (CM-US-01 plan.md A4), so this is permanently
 * name-based. Deliberately a separate, local lookup from any equivalent
 * table the Transactions screen builds for itself — two independent bespoke
 * lookups by design, not a shared import.
 */
const CATEGORY_GLYPHS: Record<string, CategoryGlyph> = {
  Groceries: GroceriesGlyph,
  Transport: TransportGlyph,
  Salary: SalaryGlyph,
  Rent: RentGlyph,
  Utilities: UtilitiesGlyph,
  Entertainment: EntertainmentGlyph,
  'Dining Out': DiningGlyph,
};

export default function ReportsScreen() {
  const [report, setReport] = useState<SummaryReportRead | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const data = await getSummaryReport();
        if (!cancelled) setReport(data);
      } catch (caught) {
        if (!cancelled) setError(toApiError(caught).message);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Screen testID={ReportsIds.screen} note="FR-US-01 · GET /api/v1/reports/summary">
      <View style={styles.header}>
        <Text style={styles.title}>Financial Summary</Text>
        <Text style={styles.description}>Income, expenses, and where your money went this month.</Text>
      </View>

      {error ? <Banner tone="error" message={error} testID={ReportsIds.errorBanner} /> : null}

      {!report && !error ? (
        <View style={styles.loading}>
          <ActivityIndicator color={color.primary} />
        </View>
      ) : null}

      {report ? (
        <>
          <BalanceScale report={report} />

          <View style={styles.categoriesHeader}>
            <Text style={styles.categoriesTitle}>Where It Went</Text>
            <Text style={styles.categoriesSubtitle}>Top spending categories this month</Text>
          </View>
          <CategoryStampGrid categories={report.top_categories} />
        </>
      ) : null}
    </Screen>
  );
}

/**
 * The tipping scale — real `react-native-svg` primitives porting #c6's own
 * geometry, not a redrawn approximation. The fulcrum reuses `BudgetsGlyph`'s
 * own dashed-ring-target look (pixel-equivalent to the mockup's own fulcrum
 * symbol — both are `r=8` dashed / `r=4.8` solid / `r=1.4` filled-dot rings
 * on a `0 0 24 24` box) rather than drawing a second glyph for the same
 * shape. The beam group rotates by `angle`; the income/expense label groups
 * nested inside it counter-rotate by `-angle` so the text stays level
 * regardless of beam tilt, exactly as #c6's own markup nests them.
 *
 * Negative net savings is not a separate branch grafted on afterward — it
 * falls out of the same `angle`/`trend` values every other render path uses,
 * exactly matching #c6's own negative-state swatch (tipped beam, net figure
 * in `color.expense`, updated readout copy). #c6 has no "Overdrawn" ink-blot
 * badge anywhere in its markup — confirmed by reading the section directly —
 * so none is added here.
 */
function BalanceScale({ report }: { report: SummaryReportRead }) {
  const totalIncome = Number(report.total_income);
  const totalExpenses = Number(report.total_expenses);
  const angle = scaleAngle(totalIncome, totalExpenses);

  // Trend is derived from the same two Number()-converted values used for
  // the angle above, rather than a second Number() parse of net_savings —
  // one conversion site, reused, per the wire-string-arithmetic rule.
  const trend: 'surplus' | 'deficit' | 'breakEven' =
    totalExpenses < totalIncome ? 'surplus' : totalExpenses > totalIncome ? 'deficit' : 'breakEven';

  const trendLabel = trend === 'surplus' ? 'Surplus' : trend === 'deficit' ? 'Deficit' : 'Break-even';
  const netColor = trend === 'deficit' ? color.expense : trend === 'surplus' ? color.income : color.text;
  const readout =
    trend === 'surplus'
      ? 'Income outweighs expenses — the scale tips toward saving.'
      : trend === 'deficit'
        ? 'Expenses outweigh income — the scale tips into deficit.'
        : 'Income matches expenses exactly — the scale rests level.';

  return (
    <View style={styles.scaleCard} testID={ReportsIds.scale}>
      <Text style={styles.scaleCaption}>
        {formatPeriodLabel(report.period)} · {trendLabel}
      </Text>

      <Svg viewBox={SCALE_VIEWBOX} style={styles.scaleSvg}>
        {/* Fulcrum — BudgetsGlyph's own ring/target, positioned + scaled to
            reproduce #c6's `use x=136 y=96 width=28 height=28`. */}
        <G transform={`translate(${FULCRUM_X}, ${FULCRUM_Y}) scale(${FULCRUM_SCALE})`}>
          <BudgetsGlyph color={color.text} />
        </G>

        {/* Stand — static, outside the rotated beam group. */}
        <Path
          d="M120,190 L180,190 L163,112 L137,112 Z"
          fill="none"
          stroke={color.text}
          strokeWidth={2}
          strokeLinejoin="round"
        />

        <G transform={`rotate(${angle.toFixed(2)} ${PIVOT_X} ${PIVOT_Y})`}>
          <Line x1={40} y1={110} x2={260} y2={110} stroke={color.text} strokeWidth={2.2} strokeLinecap="round" />
          <Line x1={40} y1={110} x2={40} y2={134} stroke={color.text} strokeWidth={1.6} />
          <Line x1={260} y1={110} x2={260} y2={134} stroke={color.text} strokeWidth={1.6} />
          <Path d="M14,134 Q40,160 66,134 Z" fill={color.sageSoft} stroke={color.text} strokeWidth={1.6} />
          {/* color.expense (#8A3324) at 22% opacity — tokens.ts has no alpha
              variant, so this is ported as a literal rgba, same as #c6's own
              CSS (`rgba(138,51,36,.22)`). */}
          <Path d="M234,134 Q260,160 286,134 Z" fill="rgba(138,51,36,0.22)" stroke={color.text} strokeWidth={1.6} />

          <G transform={`translate(40, 150) rotate(${(-angle).toFixed(2)})`}>
            <SvgText
              x={0}
              y={-8}
              textAnchor="middle"
              fontFamily={font.family.bodyMedium}
              fontSize={9}
              letterSpacing={0.5}
              fill={color.text}
            >
              INCOME
            </SvgText>
            <SvgText x={0} y={10} textAnchor="middle" fontFamily={font.family.heading} fontSize={11} fill={color.income}>
              {formatMoney(report.total_income, 'USD')}
            </SvgText>
          </G>
          <G transform={`translate(260, 150) rotate(${(-angle).toFixed(2)})`}>
            <SvgText
              x={0}
              y={-8}
              textAnchor="middle"
              fontFamily={font.family.bodyMedium}
              fontSize={9}
              letterSpacing={0.5}
              fill={color.text}
            >
              EXPENSES
            </SvgText>
            <SvgText
              x={0}
              y={10}
              textAnchor="middle"
              fontFamily={font.family.heading}
              fontSize={11}
              fill={color.expense}
            >
              {formatMoney(report.total_expenses, 'USD')}
            </SvgText>
          </G>
        </G>
      </Svg>

      <Text style={styles.scaleReadout}>{readout}</Text>

      <View style={styles.netRow}>
        <Text style={styles.netLabel}>Net</Text>
        <Text style={[styles.netFigure, { color: netColor }]} testID={ReportsIds.netFigure}>
          {formatMoney(report.net_savings, 'USD', { signed: true })}
        </Text>
      </View>
    </View>
  );
}

/**
 * `report.top_categories` (already ranked, ≤5) mapped onto `PostmarkIcon`:
 * rank 0 is the solid stamped badge, ranks 1-4 the dashed ring — the same
 * active/inactive vocabulary the rest of this app already uses, sized and
 * faded per `RANK_STYLES` for the falling-ink-density look. Always renders
 * exactly `MAX_STAMPS` slots: real categories first, then dashed "no data"
 * phantoms padding out the rest — not #c6's own static illustration, which
 * always shows one phantom after 5 real stamps to document what a 6th slot
 * looks like; that is a documentation swatch, not a live-count rule.
 */
function CategoryStampGrid({ categories }: { categories: TopCategory[] }) {
  const ranked = categories.slice(0, MAX_STAMPS);
  const phantomCount = Math.max(0, MAX_STAMPS - ranked.length);

  return (
    <View style={styles.grid}>
      {ranked.map((category, rank) => {
        const Glyph = CATEGORY_GLYPHS[category.category_name];
        const { size, opacity } = RANK_STYLES[rank];
        const active = rank === 0;
        const glyphColor = active ? color.surface : color.text;

        return (
          <View
            key={category.category_id}
            style={[styles.stamp, { opacity }]}
            testID={ReportsIds.categoryStamp(category.category_id)}
          >
            <PostmarkIcon active={active} size={size}>
              {Glyph ? <Glyph color={glyphColor} /> : <Circle cx={12} cy={12} r={5} fill={glyphColor} stroke="none" />}
            </PostmarkIcon>
            <Text style={styles.stampName} numberOfLines={1}>
              {category.category_name}
            </Text>
            <Text style={styles.stampAmt}>{formatMoney(category.total_amount, 'USD')}</Text>
          </View>
        );
      })}

      {Array.from({ length: phantomCount }, (_, index) => (
        <View key={`phantom-${index}`} style={styles.stamp}>
          <Svg width={32} height={32} viewBox="0 0 24 24">
            <Circle
              cx={12}
              cy={12}
              r={10.5}
              fill="none"
              stroke={color.textMuted}
              strokeWidth={1.3}
              strokeDasharray="2 3"
            />
          </Svg>
          <Text style={[styles.stampName, styles.stampMuted]}>—</Text>
          <Text style={[styles.stampAmt, styles.stampMuted]}>No data</Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  header: { gap: 2 },
  title: { fontFamily: font.family.heading, fontSize: font.size.title, color: color.text },
  description: { fontFamily: font.family.body, fontSize: font.size.sm, color: color.textMuted },
  loading: { paddingVertical: space.xl },

  // Balance scale card — #c6's own `.c2-block`.
  scaleCard: {
    backgroundColor: color.surface,
    borderWidth: 1,
    borderColor: color.border,
    borderRadius: radius.md,
    paddingHorizontal: space.md,
    paddingTop: space.lg,
    paddingBottom: space.xl,
    gap: space.xs,
  },
  scaleCaption: {
    fontFamily: font.family.heading,
    fontSize: 12,
    letterSpacing: 0.7,
    textAlign: 'center',
    textTransform: 'uppercase',
    color: color.textMuted,
  },
  scaleSvg: { width: '100%', aspectRatio: 300 / 200 },
  scaleReadout: {
    fontFamily: font.family.bodyItalic,
    fontSize: 12.5,
    textAlign: 'center',
    color: color.textMuted,
    marginTop: space.xs,
  },
  netRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'baseline',
    gap: space.xs,
    marginTop: space.sm,
  },
  netLabel: {
    fontFamily: font.family.bodyMedium,
    fontSize: 11,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
    color: color.textMuted,
  },
  netFigure: { fontFamily: font.family.heading, fontSize: 19 },

  // Category stamp grid — #c6's own `.c4-grid`, minus the concept-4 card
  // chrome (dashed brass border, lined-paper background) this combination
  // dropped in favor of the plain PostmarkIcon stamp system already used
  // elsewhere in this app (Dashboard's glyph row, the tab bar).
  categoriesHeader: { gap: 2, marginTop: space.sm },
  categoriesTitle: { fontFamily: font.family.headingSemibold, fontSize: font.size.xl, color: color.text },
  categoriesSubtitle: {
    fontFamily: font.family.bodyItalic,
    fontSize: font.size.xs,
    color: color.textMuted,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: space.md,
  },
  stamp: { width: 88, alignItems: 'center', gap: 2 },
  stampName: {
    fontFamily: font.family.bodyMedium,
    fontSize: 11,
    color: color.text,
    textAlign: 'center',
  },
  stampAmt: { fontFamily: font.family.heading, fontSize: 12, color: color.text },
  stampMuted: { color: color.textMuted },
});
