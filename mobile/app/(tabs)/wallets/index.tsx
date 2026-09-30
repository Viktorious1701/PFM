/**
 * Wallets list — "Filed Folders".
 *
 * Story: SRS §6 Feature-03 · WM-US-02 / SDS §5.3 WM
 * Endpoint: GET /api/v1/wallets (SDS §6.2.1)
 *
 * Wallets are grouped by their own `type` field, preserving the order the API
 * returned them in — `type` is free text (WM-US-01 plan.md A1), so a
 * hardcoded [BANK, CASH, CREDIT, SAVINGS] list would silently drop any wallet
 * whose type isn't one of those exact strings. Each folder shows a
 * same-currency subtotal when it holds more than one wallet, or a literal
 * "Mixed currencies" label when it doesn't.
 *
 * Cards are deliberately non-interactive (plain View, no Pressable) — viewing
 * a single wallet's detail is out of scope, so nothing here should look
 * tappable with no destination behind it.
 *
 * Refetches on every focus (not just mount): Expo Router keeps this tab
 * screen mounted across push/pop, so returning from create.tsx needs an
 * explicit refetch trigger rather than a one-shot mount effect.
 */
import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback, useMemo, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { ApiError, toApiError } from '../../../src/api/errors';
import type { WalletRead } from '../../../src/api/types';
import { listWallets } from '../../../src/api/wallets';
import { Banner } from '../../../src/components/Banner';
import { Button } from '../../../src/components/Button';
import { Screen } from '../../../src/components/Screen';
import { WalletsIds } from '../../../src/constants/elementIds';
import { useAuth } from '../../../src/store/auth';
import { color, font, radius, space } from '../../../src/theme/tokens';
import { formatMoney, sumMoney } from '../../../src/utils/money';

type WalletGroup = { type: string; wallets: WalletRead[] };

/**
 * Groups wallets by their exact `type` string, in first-seen order — both the
 * folder order and each folder's own member order mirror the API response,
 * per the plan's explicit "preserve API response order" decision.
 */
function groupWalletsByType(wallets: WalletRead[]): WalletGroup[] {
  const groups: WalletGroup[] = [];
  const indexByType = new Map<string, number>();

  for (const wallet of wallets) {
    const existingIndex = indexByType.get(wallet.type);
    if (existingIndex === undefined) {
      indexByType.set(wallet.type, groups.length);
      groups.push({ type: wallet.type, wallets: [wallet] });
    } else {
      groups[existingIndex].wallets.push(wallet);
    }
  }

  return groups;
}

/** Folder tab label — the type string, title-cased word by word. */
function titleCase(value: string): string {
  return value
    .trim()
    .split(/\s+/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

type Subtotal =
  | { kind: 'none' }
  | { kind: 'mixed' }
  | { kind: 'sum'; amount: string; currency: string };

/** Only shown when a folder has more than one wallet (per the design). */
function folderSubtotal(wallets: WalletRead[]): Subtotal {
  if (wallets.length <= 1) return { kind: 'none' };

  const currency = wallets[0].currency;
  const sameCurrency = wallets.every((w) => w.currency === currency);
  if (!sameCurrency) return { kind: 'mixed' };

  return { kind: 'sum', amount: sumMoney(wallets.map((w) => w.balance)), currency };
}

export default function WalletsScreen() {
  const router = useRouter();
  const { isLoading: authLoading } = useAuth();
  const [wallets, setWallets] = useState<WalletRead[] | null>(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<ApiError | null>(null);

  // `authLoading` in the dep array both gates the fetch until auth has
  // rehydrated and re-triggers it the instant that finishes (mirroring how
  // `transactions/index.tsx`'s `loadAll` re-runs on a filter change while
  // already focused) — needed for a direct deep link or hard reload into
  // this tab, where the fetch would otherwise fire before a stored token had
  // been read, get a real 401 with no token attached, and (pre-fix, see
  // `api/client.ts`) wipe a perfectly valid session. Found live via exactly
  // that navigation on the Add-Transaction screen; the same race exists here.
  useFocusEffect(
    useCallback(() => {
      if (authLoading) return;
      let isActive = true;
      setError(null);

      (async () => {
        try {
          const page = await listWallets(1, 100);
          if (isActive) {
            setWallets(page.items);
            setTotal(page.total);
          }
        } catch (caught) {
          if (isActive) setError(toApiError(caught));
        }
      })();

      return () => {
        isActive = false;
      };
    }, [authLoading]),
  );

  const groups = useMemo(() => (wallets ? groupWalletsByType(wallets) : []), [wallets]);

  return (
    <Screen testID={WalletsIds.screen} note="WM-US-02 · GET /api/v1/wallets">
      <Button
        title="+ Add Wallet"
        testID={WalletsIds.addCta}
        onPress={() => router.push('/(tabs)/wallets/create')}
      />

      {error ? (
        <Banner tone="error" message={error.message} testID={WalletsIds.errorBanner} />
      ) : null}

      {wallets === null && !error ? (
        <View style={styles.loading}>
          <ActivityIndicator color={color.primary} />
        </View>
      ) : null}

      {wallets && wallets.length === 0 ? (
        <Text style={styles.empty} testID={WalletsIds.empty}>
          No wallets yet — add your first one to get started.
        </Text>
      ) : null}

      {wallets && wallets.length > 0 ? (
        <View style={styles.folderWrap} testID={WalletsIds.list}>
          {groups.map((group) => (
            <FolderSection key={group.type} group={group} />
          ))}
        </View>
      ) : null}

      {total > 100 ? (
        <Text style={styles.overflowNote}>Showing the first 100 wallets.</Text>
      ) : null}
    </Screen>
  );
}

function FolderSection({ group }: { group: WalletGroup }) {
  const subtotal = folderSubtotal(group.wallets);

  return (
    <View style={styles.folder} testID={WalletsIds.folder(group.type)}>
      <View style={styles.folderTab}>
        <Text style={styles.folderTabLabel}>{titleCase(group.type)}</Text>
      </View>
      <View style={styles.folderBody}>
        {group.wallets.map((wallet, index) => (
          <WalletFolderCard key={wallet.id} wallet={wallet} index={index} />
        ))}

        {subtotal.kind !== 'none' ? (
          <View style={styles.subtotalRow} testID={WalletsIds.folderSubtotal(group.type)}>
            {subtotal.kind === 'mixed' ? (
              <Text style={styles.subtotalLabel}>Mixed currencies</Text>
            ) : (
              <>
                <Text style={styles.subtotalLabel}>Subtotal</Text>
                <Text
                  style={[
                    styles.subtotalValue,
                    subtotal.amount.startsWith('-') ? styles.negative : null,
                  ]}
                >
                  {formatMoney(subtotal.amount, subtotal.currency)}
                </Text>
              </>
            )}
          </View>
        ) : null}
      </View>
    </View>
  );
}

/** Alternates a slight rotation by index parity, for the "tucked into a folder" look. */
function WalletFolderCard({ wallet, index }: { wallet: WalletRead; index: number }) {
  const negative = wallet.balance.trim().startsWith('-');
  const rotation = index % 2 === 0 ? '-0.6deg' : '0.5deg';

  return (
    <View
      style={[styles.card, { transform: [{ rotate: rotation }] }]}
      testID={WalletsIds.card(wallet.id)}
    >
      <View style={styles.cardMain}>
        <Text style={styles.cardName} numberOfLines={1}>
          {wallet.name}
        </Text>
        <Text style={styles.cardMeta}>{wallet.currency}</Text>
      </View>
      <Text style={[styles.cardBalance, negative ? styles.negative : null]}>
        {formatMoney(wallet.balance, wallet.currency)}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  loading: { paddingVertical: space.xl },
  empty: {
    fontFamily: font.family.body,
    fontSize: font.size.body,
    color: color.textMuted,
    paddingVertical: space.lg,
  },
  overflowNote: { fontFamily: font.family.body, fontSize: font.size.xs, color: color.textMuted },

  folderWrap: { gap: space.xxl },

  // `marginTop` here and `top` on `folderTab` below are a matched pair — the
  // tab is absolutely positioned and pokes up into the space this margin
  // reserves, giving the "tab sticking out of a manila folder" look.
  folder: { position: 'relative', marginTop: 18 },
  folderTab: {
    position: 'absolute',
    top: -18,
    left: 16,
    zIndex: 2,
    minWidth: 84,
    alignItems: 'center',
    backgroundColor: color.surfaceSunken,
    borderWidth: 1,
    borderColor: color.primary,
    borderBottomWidth: 0,
    borderTopLeftRadius: radius.sm + 3,
    borderTopRightRadius: radius.sm + 3,
    paddingHorizontal: space.md,
    paddingTop: space.xs,
    paddingBottom: space.sm,
  },
  folderTabLabel: {
    fontFamily: font.family.heading,
    fontSize: font.size.xs,
    color: color.text,
    letterSpacing: 0.6,
    textAlign: 'center',
  },
  folderBody: {
    position: 'relative',
    zIndex: 1,
    backgroundColor: color.surfaceSunken,
    borderWidth: 1,
    borderColor: color.primary,
    borderTopLeftRadius: radius.sm,
    borderTopRightRadius: radius.lg,
    borderBottomLeftRadius: radius.lg,
    borderBottomRightRadius: radius.lg,
    padding: space.md,
    gap: space.sm,
  },

  card: {
    backgroundColor: color.surface,
    borderWidth: 1,
    borderColor: color.border,
    borderRadius: radius.md,
    paddingVertical: space.sm + 2,
    paddingHorizontal: space.md,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: space.md,
  },
  cardMain: { flex: 1, gap: 1 },
  cardName: { fontFamily: font.family.bodyMedium, fontSize: font.size.sm, color: color.text },
  cardMeta: { fontFamily: font.family.body, fontSize: font.size.xs - 1, color: color.textMuted },
  cardBalance: {
    fontFamily: font.family.heading,
    fontSize: font.size.md - 1,
    color: color.text,
  },

  subtotalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: space.md,
    paddingTop: space.xs,
  },
  subtotalLabel: {
    fontFamily: font.family.bodyItalic,
    fontSize: font.size.xs,
    color: color.textMuted,
  },
  subtotalValue: {
    fontFamily: font.family.bodyItalic,
    fontSize: font.size.xs,
    color: color.textMuted,
  },
  negative: { color: color.expense },
});
