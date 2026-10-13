/**
 * Transactions list — "Carbon-Copy Receipt Feed".
 *
 * Story: SRS §6 Feature-06 · TM-US-02 / SDS §5.6 · GET /api/v1/transactions.
 * Design: the approved mockup's Concept 1 (design-explore/transactions.html
 * #concept-1) — every transaction renders as a torn carbon-copy slip stacked
 * in a continuous feed, ink-stamped red for expenses and green for income.
 *
 * Structural note: this uses a real FlatList (unbounded transaction volume),
 * NOT `Screen`'s own internal ScrollView — nesting a FlatList inside another
 * ScrollView breaks RN's virtualization. `<Screen scroll={false}>` is given a
 * single manual `flex:1` wrapper View containing [FilterRow, list area, FAB]
 * as siblings, so the FlatList gets a genuinely bounded height to virtualize
 * against.
 *
 * `TransactionRead` carries only `wallet_id`/`category_id` (see api/types.ts),
 * never a display name — so wallets and categories are fetched up front (in
 * parallel with each other) on every focus, resolved into
 * `Map<string, WalletRead>` / `Map<string, CategoryRead>`, and used to look up
 * each row's name/currency/glyph. Selecting a filter changes `walletFilter`/
 * `categoryFilter`, which — because they are dependencies of the same
 * `useCallback` passed to `useFocusEffect` — re-runs that exact fetch (see
 * `loadAll` below), matching plan.md's "re-triggers the fetch effect".
 */
import { LinearGradient } from 'expo-linear-gradient';
import { useFocusEffect, useRouter } from 'expo-router';
import type { JSX } from 'react';
import { useCallback, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import Animated, {
  Easing,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withSequence,
  withTiming,
} from 'react-native-reanimated';
import Svg from 'react-native-svg';

import { toApiError } from '../../../src/api/errors';
import { listCategories } from '../../../src/api/categories';
import type { CategoryRead, TransactionRead, WalletRead } from '../../../src/api/types';
import { listTransactions } from '../../../src/api/transactions';
import { listWallets } from '../../../src/api/wallets';
import { Banner } from '../../../src/components/Banner';
import {
  DiningGlyph,
  EntertainmentGlyph,
  GroceriesGlyph,
  RentGlyph,
  SalaryGlyph,
  TransactionsGlyph,
  TransportGlyph,
  UtilitiesGlyph,
} from '../../../src/components/icons/Glyphs';
import { TornEdge } from '../../../src/components/icons/TornEdge';
import { PickerSheet, type PickerOption } from '../../../src/components/PickerSheet';
import { Screen } from '../../../src/components/Screen';
import { TransactionsIds } from '../../../src/constants/elementIds';
import { useAuth } from '../../../src/store/auth';
import { color, font, gradient, radius, space } from '../../../src/theme/tokens';
import { formatMoney } from '../../../src/utils/money';

const PAGE_SIZE = 25;

/**
 * Maps a category's exact `name` string to the glyph drawn inside its stamp.
 * `CategoryRead` has no icon field at all (deferred to a future CM-US-04), so
 * this is name-string-based and only covers the 7 category names this app's
 * demo/mockup data ever uses. A user-typed name via the inline "+ new
 * category" flow on the create screen won't always match this fixed
 * vocabulary — an accepted, documented gap, not a bug: anything unmatched
 * falls back to the muted `TransactionsGlyph` below.
 */
type GlyphComponent = (props: { color: string }) => JSX.Element;

const CATEGORY_GLYPH_BY_NAME: Record<string, GlyphComponent> = {
  Groceries: GroceriesGlyph,
  Transport: TransportGlyph,
  Salary: SalaryGlyph,
  Rent: RentGlyph,
  Utilities: UtilitiesGlyph,
  Entertainment: EntertainmentGlyph,
  'Dining Out': DiningGlyph,
};

export default function TransactionsScreen() {
  const router = useRouter();
  const { isLoading: authLoading } = useAuth();

  const [wallets, setWallets] = useState<WalletRead[]>([]);
  const [categories, setCategories] = useState<CategoryRead[]>([]);

  const [transactions, setTransactions] = useState<TransactionRead[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);

  const [loadingInitial, setLoadingInitial] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loadMoreError, setLoadMoreError] = useState<string | null>(null);

  const [walletFilter, setWalletFilter] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [walletPickerOpen, setWalletPickerOpen] = useState(false);
  const [categoryPickerOpen, setCategoryPickerOpen] = useState(false);

  const walletsById = useMemo(() => new Map(wallets.map((w) => [w.id, w])), [wallets]);
  const categoriesById = useMemo(() => new Map(categories.map((c) => [c.id, c])), [categories]);

  const hasMore = transactions.length < total;

  /**
   * Fetches wallets + categories in parallel, then the first transaction
   * page filtered by the current `walletFilter`/`categoryFilter`. Depends on
   * both filters, so selecting one gives this callback a new identity, which
   * re-runs the `useFocusEffect` below immediately (the route is already
   * focused) — the single mechanism behind both "on focus" and "on filter
   * change" loading.
   */
  const loadAll = useCallback(
    async (opts: { silent?: boolean } = {}) => {
      // Gated on auth rehydration for the same reason as the Add-Transaction
      // screen's own fetch effect (see api/client.ts + that screen's doc
      // comment): a deep link or hard reload straight into this tab would
      // otherwise fetch before a stored token had loaded, drawing a real 401
      // with no token attached and (pre-fix) wiping a valid session.
      if (authLoading) return;
      setLoadError(null);
      if (!opts.silent) setLoadingInitial(true);

      try {
        const [walletsPage, categoriesPage] = await Promise.all([
          listWallets(1, 100),
          listCategories(1, 100),
        ]);
        setWallets(walletsPage.items);
        setCategories(categoriesPage.items);

        const txPage = await listTransactions({
          page: 1,
          page_size: PAGE_SIZE,
          wallet_id: walletFilter ?? undefined,
          category_id: categoryFilter ?? undefined,
        });
        setTransactions(txPage.items);
        setTotal(txPage.total);
        setPage(1);
      } catch (caught) {
        setLoadError(toApiError(caught).message);
      } finally {
        setLoadingInitial(false);
        setRefreshing(false);
      }
    },
    [walletFilter, categoryFilter, authLoading],
  );

  useFocusEffect(
    useCallback(() => {
      void loadAll();
    }, [loadAll]),
  );

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    void loadAll({ silent: true });
  }, [loadAll]);

  const loadMore = useCallback(() => {
    if (loadingMore || loadingInitial || !hasMore) return;
    setLoadingMore(true);
    setLoadMoreError(null);

    const nextPage = page + 1;
    void listTransactions({
      page: nextPage,
      page_size: PAGE_SIZE,
      wallet_id: walletFilter ?? undefined,
      category_id: categoryFilter ?? undefined,
    })
      .then((txPage) => {
        setTransactions((prev) => [...prev, ...txPage.items]);
        setTotal(txPage.total);
        setPage(nextPage);
      })
      .catch((caught) => setLoadMoreError(toApiError(caught).message))
      .finally(() => setLoadingMore(false));
  }, [loadingMore, loadingInitial, hasMore, page, walletFilter, categoryFilter]);

  const walletOptions: PickerOption<string>[] = useMemo(
    () => wallets.map((w) => ({ value: w.id, label: w.name })),
    [wallets],
  );
  const categoryOptions: PickerOption<string>[] = useMemo(
    () => categories.map((c) => ({ value: c.id, label: c.name })),
    [categories],
  );

  const walletLabel = walletFilter ? (walletsById.get(walletFilter)?.name ?? 'All Wallets') : 'All';
  const categoryLabel = categoryFilter
    ? (categoriesById.get(categoryFilter)?.name ?? 'All Categories')
    : 'All';

  return (
    <Screen
      scroll={false}
      testID={TransactionsIds.screen}
      title="Transactions"
      note="TM-US-02 · GET /api/v1/transactions"
    >
      <View style={styles.body}>
        <View style={styles.filterRow}>
          <FilterChip
            testID={TransactionsIds.filterWalletChip}
            label={`Wallet: ${walletLabel}`}
            selected={walletFilter !== null}
            onPress={() => setWalletPickerOpen(true)}
          />
          <FilterChip
            testID={TransactionsIds.filterCategoryChip}
            label={`Category: ${categoryLabel}`}
            selected={categoryFilter !== null}
            onPress={() => setCategoryPickerOpen(true)}
          />
        </View>

        <View style={styles.listArea}>
          {loadError ? (
            <View style={styles.centerFill}>
              <Banner tone="error" message={loadError} testID={TransactionsIds.errorBanner} />
            </View>
          ) : loadingInitial ? (
            <View style={styles.centerFill}>
              <ActivityIndicator color={color.primary} />
            </View>
          ) : (
            <FlatList
              testID={TransactionsIds.list}
              style={styles.list}
              data={transactions}
              keyExtractor={(item) => item.id}
              renderItem={({ item, index }) => (
                <ReceiptSlip
                  transaction={item}
                  wallet={walletsById.get(item.wallet_id)}
                  category={categoriesById.get(item.category_id)}
                  tilt={index % 2 === 0 ? '-0.3deg' : '0.3deg'}
                />
              )}
              ItemSeparatorComponent={() => <View style={{ height: space.lg }} />}
              contentContainerStyle={styles.listContent}
              onEndReached={loadMore}
              onEndReachedThreshold={0.4}
              refreshControl={
                <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={color.primary} />
              }
              ListEmptyComponent={
                <View style={styles.centerFill}>
                  <Text style={styles.emptyText}>
                    No transactions yet. Tap "+ New Slip" to log your first one.
                  </Text>
                </View>
              }
              ListFooterComponent={
                loadingMore ? (
                  <ActivityIndicator style={styles.footerSpinner} color={color.primary} />
                ) : loadMoreError ? (
                  <Text style={styles.footerError}>{loadMoreError}</Text>
                ) : null
              }
            />
          )}
        </View>

        <Fab testID={TransactionsIds.fab} onPress={() => router.push('/(tabs)/transactions/create')} />
      </View>

      <PickerSheet
        visible={walletPickerOpen}
        title="Filter by Wallet"
        options={walletOptions}
        selected={walletFilter}
        onSelect={(value) => {
          setWalletFilter(value);
          setWalletPickerOpen(false);
        }}
        onClose={() => setWalletPickerOpen(false)}
        allowClear
        clearLabel="All Wallets"
      />

      <PickerSheet
        visible={categoryPickerOpen}
        title="Filter by Category"
        options={categoryOptions}
        selected={categoryFilter}
        onSelect={(value) => {
          setCategoryFilter(value);
          setCategoryPickerOpen(false);
        }}
        onClose={() => setCategoryPickerOpen(false)}
        allowClear
        clearLabel="All Categories"
      />
    </Screen>
  );
}

/**
 * One torn carbon-copy slip. Bespoke to this screen, not exported. No press
 * states — TM-US-03/04 (a transaction-detail screen) are out of scope, so
 * nothing here should look tappable with no destination behind it.
 */
function ReceiptSlip({
  transaction,
  wallet,
  category,
  tilt,
}: {
  transaction: TransactionRead;
  wallet: WalletRead | undefined;
  category: CategoryRead | undefined;
  tilt: `${'-' | ''}0.3deg`;
}) {
  const isIncome = transaction.type === 'INCOME';
  const stampColors = isIncome ? gradient.incomeStamp : gradient.expenseStamp;
  const Glyph = (category && CATEGORY_GLYPH_BY_NAME[category.name]) || TransactionsGlyph;
  const categoryLabel = category?.name ?? 'Uncategorized';
  const currency = wallet?.currency ?? 'USD';
  const amountColor = isIncome ? color.income : color.expense;

  return (
    <View style={[styles.slipWrap, { transform: [{ rotate: tilt }] }]} testID={TransactionsIds.slip(transaction.id)}>
      <TornEdge />
      <View style={styles.slipBody}>
        <View style={styles.slipRowTop}>
          <LinearGradient colors={stampColors} start={{ x: 0, y: 0 }} end={{ x: 0, y: 1 }} style={styles.postmark}>
            <Svg width={19} height={19} viewBox="0 0 24 24">
              <Glyph color={color.surface} />
            </Svg>
          </LinearGradient>
          <View style={styles.slipMeta}>
            <Text style={styles.slipCategory}>{categoryLabel}</Text>
            <Text style={styles.slipDate}>{formatSlipDate(transaction.timestamp)}</Text>
          </View>
          <Text style={[styles.slipAmount, { color: amountColor }]}>
            {/* TransactionRead.amount is always a positive magnitude on the
                wire (direction lives in `type` — see api/types.ts); formatMoney's
                own `-` only fires when the value itself parses negative, so the
                magnitude is negated for the expense case here. `signed` then adds
                the `+` for income. Together these guarantee every row carries a
                sign, not just its ink colour (never the sole channel — see
                Dashboard's own recentAmount for the same rule). */}
            {formatMoney(isIncome ? transaction.amount : `-${transaction.amount}`, currency, {
              signed: isIncome,
            })}
          </Text>
        </View>

        {transaction.note ? (
          <Text style={styles.slipNote}>&quot;{transaction.note}&quot;</Text>
        ) : (
          <Text style={styles.slipNoteEmpty}>— no note —</Text>
        )}

        <View style={styles.slipFooter}>
          <Text style={styles.slipWallet}>{wallet?.name ?? 'Unknown wallet'}</Text>
        </View>
      </View>
    </View>
  );
}

function FilterChip({
  label,
  selected,
  onPress,
  testID,
}: {
  label: string;
  selected: boolean;
  onPress: () => void;
  testID?: string;
}) {
  return (
    <Pressable
      testID={testID}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected }}
      style={[styles.filterChip, selected ? styles.filterChipSelected : null]}
    >
      <Text style={[styles.filterChipLabel, selected ? styles.filterChipLabelSelected : null]}>{label}</Text>
    </Pressable>
  );
}

/** Ink/glitch world — local to this one control (surface brief:
 * `.impeccable/surfaces/mobile-app-tabs-transactions-index-tsx.md`). Not
 * added to `tokens.ts`: this is the first flagship of a world that has not
 * replaced Cash & Carry everywhere yet (direction contract FORM/scope).
 * OWN-WORLD v2: rest stays near-black ink; the press-glitch now glows icy
 * blue-white (Nullscapes) instead of flat slate — color only shows up at
 * the moment of disruption, so it reads as the control "charging," not as
 * decoration sitting on the control at all times. */
const GLITCH_INK = '#14171A';
const GLITCH_INK_LIGHT = '#262B30';
const GLITCH_GLOW = 'rgba(146, 212, 255, 0.5)';
const GLITCH_GLOW_BRIGHT = 'rgba(214, 241, 255, 0.95)';
const FAB_GRADIENT = [GLITCH_INK_LIGHT, GLITCH_INK] as const;

/** "+ NEW SLIP" stamps a moment into the ledger: pressing it fires a brief
 * structured-displacement glitch (two offset ghost copies + a scanline
 * flash) before settling, rather than the generic scale-and-fade every
 * other finance app's add button uses (direction contract THESIS).
 * `useReducedMotion` swaps this for the plain opacity-only press feedback
 * `fabPressed` already provides (animate.md Accessibility and control). */
function Fab({ onPress, testID }: { onPress: () => void; testID?: string }) {
  const reduceMotion = useReducedMotion();
  const ghostA = useSharedValue({ x: 0, y: 0 });
  const ghostB = useSharedValue({ x: 0, y: 0 });
  const ghostOpacity = useSharedValue(0);
  const scanlineOpacity = useSharedValue(0);

  const triggerGlitch = useCallback(() => {
    if (reduceMotion) return;
    const step = (duration: number) => ({ duration, easing: Easing.linear });
    ghostOpacity.value = withSequence(withTiming(1, step(20)), withTiming(0, step(110)));
    ghostA.value = withSequence(
      withTiming({ x: -5, y: -3 }, step(30)),
      withTiming({ x: 4, y: 2 }, step(30)),
      withTiming({ x: 0, y: 0 }, step(70)),
    );
    ghostB.value = withSequence(
      withTiming({ x: 5, y: -4 }, step(30)),
      withTiming({ x: -3, y: 3 }, step(30)),
      withTiming({ x: 0, y: 0 }, step(70)),
    );
    scanlineOpacity.value = withSequence(
      withTiming(0.8, step(15)),
      withTiming(0, step(15)),
      withTiming(0.6, step(15)),
      withTiming(0, step(90)),
    );
  }, [reduceMotion, ghostA, ghostB, ghostOpacity, scanlineOpacity]);

  const ghostAStyle = useAnimatedStyle(() => ({
    opacity: ghostOpacity.value,
    transform: [{ translateX: ghostA.value.x }, { translateY: ghostA.value.y }],
  }));
  const ghostBStyle = useAnimatedStyle(() => ({
    opacity: ghostOpacity.value,
    transform: [{ translateX: ghostB.value.x }, { translateY: ghostB.value.y }],
  }));
  const scanlineStyle = useAnimatedStyle(() => ({ opacity: scanlineOpacity.value }));

  return (
    <Pressable
      testID={testID}
      onPress={onPress}
      onPressIn={triggerGlitch}
      accessibilityRole="button"
      accessibilityLabel="Log a new transaction"
      style={({ pressed }) => [styles.fabWrap, pressed ? styles.fabPressed : null]}
    >
      <View style={styles.fabStack}>
        {!reduceMotion && (
          <Animated.View
            pointerEvents="none"
            importantForAccessibility="no-hide-descendants"
            style={[styles.fabGhost, ghostBStyle]}
          />
        )}
        {!reduceMotion && (
          <Animated.View
            pointerEvents="none"
            importantForAccessibility="no-hide-descendants"
            style={[styles.fabGhost, ghostAStyle]}
          />
        )}
        <LinearGradient colors={FAB_GRADIENT} start={{ x: 0, y: 0 }} end={{ x: 0, y: 1 }} style={styles.fab}>
          <Text style={styles.fabLabel}>+ NEW SLIP</Text>
        </LinearGradient>
        {!reduceMotion && (
          <>
            <Animated.View
              pointerEvents="none"
              importantForAccessibility="no-hide-descendants"
              style={[styles.fabScanlineHalo, styles.fabScanlineTop, scanlineStyle]}
            />
            <Animated.View
              pointerEvents="none"
              importantForAccessibility="no-hide-descendants"
              style={[styles.fabScanline, styles.fabScanlineTop, scanlineStyle]}
            />
            <Animated.View
              pointerEvents="none"
              importantForAccessibility="no-hide-descendants"
              style={[styles.fabScanlineHalo, styles.fabScanlineBottom, scanlineStyle]}
            />
            <Animated.View
              pointerEvents="none"
              importantForAccessibility="no-hide-descendants"
              style={[styles.fabScanline, styles.fabScanlineBottom, scanlineStyle]}
            />
          </>
        )}
      </View>
    </Pressable>
  );
}

function formatSlipDate(iso: string): string {
  const d = new Date(iso);
  const datePart = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  const timePart = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  return `${datePart} · ${timePart}`;
}

const styles = StyleSheet.create({
  body: { flex: 1 },

  filterRow: {
    flexDirection: 'row',
    gap: space.sm,
    paddingBottom: space.md,
    borderBottomWidth: 1,
    borderBottomColor: color.border,
    marginBottom: space.md,
  },
  filterChip: {
    borderRadius: radius.full,
    borderWidth: 1.5,
    borderStyle: 'dashed',
    borderColor: color.borderInteractive,
    backgroundColor: color.surface,
    paddingVertical: space.sm,
    paddingHorizontal: space.md,
  },
  filterChipSelected: { backgroundColor: color.text, borderColor: color.text, borderStyle: 'solid' },
  filterChipLabel: { fontFamily: font.family.bodyMedium, fontSize: font.size.sm, color: color.text },
  filterChipLabelSelected: { color: color.surface },

  listArea: { flex: 1 },
  list: { flex: 1 },
  listContent: { paddingBottom: 96, flexGrow: 1 },
  centerFill: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: space.xl },
  emptyText: {
    fontFamily: font.family.body,
    fontSize: font.size.body,
    color: color.textMuted,
    textAlign: 'center',
  },
  footerSpinner: { marginVertical: space.lg },
  footerError: {
    fontFamily: font.family.body,
    fontSize: font.size.sm,
    color: color.error.fg,
    textAlign: 'center',
    marginVertical: space.lg,
  },

  // Receipt slip — DESIGN.md carbon-copy concept: torn top, no shadow, a
  // hairline-bordered body with no top border (the torn edge stands in for it).
  slipWrap: {},
  slipBody: {
    backgroundColor: color.surface,
    borderLeftWidth: 1,
    borderRightWidth: 1,
    borderBottomWidth: 1,
    borderColor: color.border,
    borderBottomLeftRadius: radius.sm,
    borderBottomRightRadius: radius.sm,
    paddingHorizontal: space.md,
    paddingBottom: space.md,
    paddingTop: 2,
  },
  slipRowTop: { flexDirection: 'row', alignItems: 'center', gap: space.sm },
  postmark: { width: 38, height: 38, borderRadius: 19, alignItems: 'center', justifyContent: 'center' },
  slipMeta: { flex: 1, minWidth: 0, gap: 2 },
  slipCategory: { fontFamily: font.family.heading, fontSize: font.size.md, color: color.text },
  slipDate: { fontFamily: font.family.body, fontSize: font.size.xs, color: color.textMuted },
  slipAmount: { fontFamily: font.family.heading, fontSize: font.size.lg },
  slipNote: {
    fontFamily: font.family.bodyItalic,
    fontSize: font.size.sm,
    color: color.captionDeep,
    marginLeft: 48,
    marginTop: space.sm,
  },
  slipNoteEmpty: {
    fontFamily: font.family.bodyItalic,
    fontSize: font.size.sm,
    color: color.textMuted,
    marginLeft: 48,
    marginTop: space.sm,
  },
  slipFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginLeft: 48,
    marginTop: space.sm,
    paddingTop: space.sm,
    borderTopWidth: 1,
    borderStyle: 'dashed',
    borderTopColor: color.border,
  },
  slipWallet: {
    fontFamily: font.family.body,
    fontSize: font.size.xs,
    color: color.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },

  // FAB — DESIGN.md's flat-depth rule: no shadow, a stamped-ticket radius.
  fabWrap: { position: 'absolute', right: 0, bottom: 0 },
  fabPressed: { opacity: 0.88 },
  fabStack: { position: 'relative' },
  fab: {
    borderRadius: radius.stamp,
    paddingVertical: space.md,
    paddingHorizontal: space.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  fabLabel: {
    fontFamily: font.family.heading,
    fontSize: font.size.sm,
    color: color.primaryText,
    letterSpacing: 1,
  },
  // Offset duplicate of the fab's own box (no label — the displaced
  // silhouette alone reads as the glitch echo; a doubled label would also
  // get double-announced to a screen reader). Fills fabStack exactly
  // because fabStack's own size is set by the one normal-flow fab child.
  fabGhost: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: GLITCH_GLOW,
    borderRadius: radius.stamp,
  },
  // Two thin flashes rather than one full-height bar — a single bar across
  // the whole control reads as a solid overlay, not a scanline. Each pairs
  // a soft wide halo (fakes bloom on Android, where View shadowColor is
  // ignored) with a bright 2px core, so the flash reads as glowing rather
  // than a flat tinted stripe.
  fabScanlineHalo: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 10,
    marginTop: -4,
    backgroundColor: GLITCH_GLOW,
    borderRadius: radius.sm,
  },
  fabScanline: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 2,
    backgroundColor: GLITCH_GLOW_BRIGHT,
    shadowColor: GLITCH_GLOW_BRIGHT,
    shadowOpacity: 0.9,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 0 },
  },
  fabScanlineTop: { top: '32%' },
  fabScanlineBottom: { top: '62%' },
});
