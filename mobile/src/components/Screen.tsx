/**
 * Standard screen frame: Nullscapes header, prototype banner, scrolling body.
 *
 * Every screen uses this so the PROTOTYPE strip cannot be forgotten on one of
 * them. Also where `NullscapesHeader` is rendered (not by each screen
 * directly, same pattern already used for `PrototypeBanner`) — the Tabs
 * navigator's own per-screen header is gone (`headerShown: false`, see
 * `app/(tabs)/_layout.tsx`), so this is now the only header every screen
 * gets, and it needs a `title` to show.
 *
 * `background` defaults to `'transparent'`: the single animated Nullscapes
 * background sits behind the whole Tabs group now (`app/(tabs)/_layout.tsx`),
 * not behind just one screen, so every screen is meant to show it through by
 * default. `'opaque'` stays available for a screen that genuinely needs its
 * own solid fill, but nothing currently uses it.
 */
import type { ReactNode } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { USE_MOCK_API } from '../config';
import { color } from '../theme/tokens';
import { NullscapesHeader } from './NullscapesHeader';
import { PrototypeBanner } from './PrototypeBanner';

type Props = {
  children: ReactNode;
  /** Shown in the Nullscapes HUD header, right-aligned. Ignored when
   * `background="opaque"` — see that prop's own doc. */
  title: string;
  /** Extra line inside the prototype banner, e.g. which story fills this screen. */
  note?: string;
  /** Set false for screens that manage their own scrolling. */
  scroll?: boolean;
  testID?: string;
  /**
   * 'transparent' (default): the screen sits behind the shared animated
   * Nullscapes background (`app/(tabs)/_layout.tsx`) and gets the
   * `NullscapesHeader` + dark `PrototypeBanner`. Every tab screen uses this.
   *
   * 'opaque': for the two screens outside the Tabs group entirely — sign-in
   * and account activation — which have no shared background behind them
   * and are not part of this round's Nullscapes reskin. Falls back to the
   * original Cash & Carry Kraft Board fill and skips `NullscapesHeader`
   * (that HUD wordmark would look out of place on a page with nothing
   * Nullscapes behind it); `PrototypeBanner` still renders (its one dark
   * card reads fine against the cream fill — not worth a second variant).
   */
  background?: 'opaque' | 'transparent';
};

export function Screen({ children, title, note, scroll = true, testID, background = 'transparent' }: Props) {
  const insets = useSafeAreaInsets();
  const isOpaque = background === 'opaque';

  const body = <View style={styles.body}>{children}</View>;

  return (
    <View
      style={[styles.container, { paddingBottom: insets.bottom }, isOpaque && styles.containerOpaque]}
      testID={testID}
    >
      {isOpaque ? null : <NullscapesHeader title={title} />}
      {USE_MOCK_API ? <PrototypeBanner note={note} /> : null}
      {scroll ? (
        <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
          {body}
        </ScrollView>
      ) : (
        body
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: 'transparent' },
  containerOpaque: { backgroundColor: color.bg },
  scrollContent: { flexGrow: 1 },
  body: { flex: 1, paddingHorizontal: 20, paddingVertical: 16, gap: 16 },
});
