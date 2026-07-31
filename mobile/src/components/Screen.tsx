/**
 * Standard screen frame: safe area, scrolling body, prototype banner.
 *
 * Every screen uses this so the PROTOTYPE strip cannot be forgotten on one of
 * them.
 */
import type { ReactNode } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { color, space } from '../theme/tokens';
import { PrototypeBanner } from './PrototypeBanner';

type Props = {
  children: ReactNode;
  /** Extra line inside the prototype banner, e.g. which story fills this screen. */
  note?: string;
  /** Set false for screens that manage their own scrolling. */
  scroll?: boolean;
  testID?: string;
};

export function Screen({ children, note, scroll = true, testID }: Props) {
  const insets = useSafeAreaInsets();

  const body = <View style={styles.body}>{children}</View>;

  return (
    <View style={[styles.container, { paddingBottom: insets.bottom }]} testID={testID}>
      <PrototypeBanner note={note} />
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
  scrollContent: { flexGrow: 1 },
  body: { flex: 1, padding: space.lg, gap: space.lg },
});
