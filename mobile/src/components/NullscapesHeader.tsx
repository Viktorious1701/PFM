/**
 * Nullscapes header — replaces the Tabs navigator's own per-screen header
 * (`headerShown: false` everywhere now, see `app/(tabs)/_layout.tsx`) with a
 * transparent, see-through HUD-style bar matching the validated
 * zoom-traversal mockups exactly: a `PFM.` wordmark (the `.` in mint) on the
 * left, the screen's own title on the right — no background fill of its
 * own, so the shared animated scene behind the whole Tabs group shows
 * straight through it.
 *
 * Rendered by `Screen` (not by each screen directly), the same pattern
 * already used for `PrototypeBanner` — reserves its own real layout space
 * (including the top safe-area inset) rather than floating absolutely,
 * since there's no `useHeaderHeight()`-style coordination needed that way.
 */
import { StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ns, nsFont } from '../theme/nullscapes';

export function NullscapesHeader({ title }: { title: string }) {
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.row, { paddingTop: insets.top + 14 }]}>
      <Text style={styles.logo}>
        PFM<Text style={styles.dot}>.</Text>
      </Text>
      <Text style={styles.title} numberOfLines={1}>
        {title}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingBottom: 14,
    gap: 12,
  },
  logo: { fontFamily: nsFont.bold, fontSize: 14, letterSpacing: 1, color: ns.inkSoft },
  dot: { color: ns.mint },
  title: {
    flexShrink: 1,
    textAlign: 'right',
    fontFamily: nsFont.medium,
    fontSize: 10,
    letterSpacing: 2,
    color: ns.muted,
    textTransform: 'uppercase',
  },
});
