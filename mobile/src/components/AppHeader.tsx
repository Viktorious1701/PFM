/**
 * The header above every tab: brand, the song controls, sign out. Fixed —
 * it stays put while the page under it changes. Wide screens fit it on one
 * line; on a phone the song controls take a line of their own.
 */
import type { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, useWindowDimensions, View } from 'react-native';

import { useAuth } from '../store/auth';
import { font, moon } from '../theme/moonlit';

export function AppHeader({ song }: { song: ReactNode }) {
  const { signOut } = useAuth();
  const { width } = useWindowDimensions();
  const narrow = width < 600;

  const brand = (
    <Text style={styles.brand} numberOfLines={1}>
      Family finance
    </Text>
  );
  const signOutButton = (
    <Pressable
      testID="sign-out"
      accessibilityRole="button"
      onPress={() => void signOut()}
      style={({ pressed }) => [styles.ghost, pressed && styles.pressed]}
    >
      <Text style={styles.ghostLabel}>Sign out</Text>
    </Pressable>
  );

  return (
    <View style={styles.column}>
      {narrow ? (
        <View style={styles.stack}>
          <View style={styles.row}>
            {brand}
            {signOutButton}
          </View>
          <View style={styles.songRow}>{song}</View>
        </View>
      ) : (
        <View style={styles.row}>
          {brand}
          <View style={styles.songWide}>{song}</View>
          {signOutButton}
        </View>
      )}
    </View>
  );
}

const label = {
  fontFamily: font.semibold,
  fontSize: 12,
  letterSpacing: 3,
  textTransform: 'uppercase' as const,
};

const styles = StyleSheet.create({
  column: { width: '100%', maxWidth: 720, alignSelf: 'center', paddingHorizontal: 16, paddingTop: 20, paddingBottom: 14 },
  stack: { gap: 12 },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 },
  songRow: { flexDirection: 'row' },
  songWide: { flex: 1, flexDirection: 'row', maxWidth: 440 },
  brand: { ...label, color: moon.inkSoft, flexShrink: 1 },
  ghost: {
    height: 34,
    justifyContent: 'center',
    paddingHorizontal: 16,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: moon.panelBorder,
    backgroundColor: 'rgba(10,18,32,0.55)',
  },
  ghostLabel: { ...label, fontSize: 11, color: moon.inkSoft },
  pressed: { opacity: 0.7 },
});
