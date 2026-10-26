/**
 * The header above every tab: brand, the song controls, sign out. Fixed —
 * it stays put while the page under it changes. Wide screens fit it on one
 * line; on a phone the song controls take a line of their own.
 *
 * A guest also sees the trial notice under it, on every tab (SS-US-03 AC-14).
 * Sign out is the same one tap for a guest as for a member: it deletes
 * nothing, so there is nothing to confirm (AC-15).
 */
import type { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, useWindowDimensions, View } from 'react-native';

import { formatTrialEnd, useAuth } from '../store/auth';
import { font, moon } from '../theme/moonlit';

export function AppHeader({ song }: { song: ReactNode }) {
  const { signOut, isGuest, trialEndsAt } = useAuth();
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
      {isGuest && trialEndsAt ? (
        <Text style={styles.banner} testID="guest-banner" accessibilityRole="text">
          {`Guest trial — deleted on ${formatTrialEnd(trialEndsAt)}. Ask your family's admin for an invitation to keep using PFM.`}
        </Text>
      ) : null}
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
  banner: {
    marginTop: 12,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(255,196,110,0.35)',
    backgroundColor: 'rgba(10,18,32,0.7)',
    color: moon.warning,
    fontFamily: font.medium,
    fontSize: 14,
  },
});
