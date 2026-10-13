/**
 * Standard screen frame: safe area, scrolling body, prototype banner.
 *
 * Every screen uses this so the PROTOTYPE strip cannot be forgotten on one of
 * them.
 */
import type { ReactNode } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { USE_MOCK_API } from '../config';
import { color, space } from '../theme/tokens';
import { PrototypeBanner } from './PrototypeBanner';

type Props = {
  children: ReactNode;
  /** Extra line inside the prototype banner, e.g. which story fills this screen. */
  note?: string;
  /** Set false for screens that manage their own scrolling. */
  scroll?: boolean;
  testID?: string;
  /** Page-background fill. 'opaque' (default) is the existing Kraft Board
   * fill every screen already uses. 'transparent' omits that fill so a
   * caller-supplied backdrop (currently: the Dashboard's immersive
   * Nullscapes background) shows through. Every other screen's call site
   * is unaffected by this prop's existence. */
  background?: 'opaque' | 'transparent';
};

export function Screen({ children, note, scroll = true, testID, background = 'opaque' }: Props) {
  const insets = useSafeAreaInsets();

  const body = <View style={styles.body}>{children}</View>;

  return (
    <View
      style={[
        styles.container,
        { paddingBottom: insets.bottom },
        background === 'transparent' && styles.containerTransparent,
      ]}
      testID={testID}
    >
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
  container: { flex: 1, backgroundColor: color.bg },
  containerTransparent: { backgroundColor: 'transparent' },
  scrollContent: { flexGrow: 1 },
  body: { flex: 1, paddingHorizontal: space.xl, paddingVertical: space.lg, gap: space.lg },
});
