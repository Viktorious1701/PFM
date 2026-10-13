/**
 * Shared placeholder body for every skeleton screen (currently Budgets only).
 *
 * Exists so each screen file states *what will fill it* rather than carrying
 * throwaway markup that someone later mistakes for a real implementation.
 * Delete this component once the screens are built.
 *
 * Renders via `Screen` (not a bare `View`) so every skeleton screen gets the
 * same Nullscapes header/background/prototype-banner treatment as a built
 * screen, instead of a visually inconsistent one-off container.
 */
import { StyleSheet, Text, View } from 'react-native';

import { ns, nsFont } from '../theme/nullscapes';
import { Screen } from './Screen';

type Props = {
  /** Screen title, e.g. "Invite a user". */
  title: string;
  /** Story that will implement this screen, e.g. "UM-US-01 / US-01-01". */
  story: string;
  /** API call the screen will make once the endpoint exists. */
  endpoint?: string;
  /** What the screen must show, in one line. */
  purpose: string;
};

export function Placeholder({ title, story, endpoint, purpose }: Props) {
  return (
    <Screen title={title} note={story}>
      <View style={styles.card}>
        <Text style={styles.badge}>SKELETON — not implemented</Text>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.purpose}>{purpose}</Text>
        <View style={styles.meta}>
          <Text style={styles.metaLine}>Story: {story}</Text>
          {endpoint ? <Text style={styles.metaLine}>Endpoint: {endpoint}</Text> : null}
        </View>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: ns.card,
    borderWidth: 1,
    borderColor: ns.cardBorder,
    borderRadius: 10,
    padding: 20,
    gap: 10,
  },
  badge: {
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(255,196,110,0.12)',
    color: ns.warning,
    fontFamily: nsFont.semibold,
    fontSize: 11,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
    overflow: 'hidden',
  },
  title: { fontFamily: nsFont.bold, fontSize: 22, color: ns.ink },
  purpose: { fontFamily: nsFont.regular, fontSize: 14, lineHeight: 20, color: ns.muted },
  meta: { marginTop: 8, gap: 4 },
  metaLine: { fontSize: 12, color: ns.mutedFaint, fontFamily: 'monospace' },
});
