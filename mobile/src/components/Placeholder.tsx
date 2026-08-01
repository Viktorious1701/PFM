/**
 * Shared placeholder body for every skeleton screen.
 *
 * Exists so each screen file states *what will fill it* rather than carrying
 * throwaway markup that someone later mistakes for a real implementation.
 * Delete this component once the screens are built.
 */
import { StyleSheet, Text, View } from 'react-native';

import { color, font, radius, space } from '../theme/tokens';

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
    <View style={styles.container}>
      <Text style={styles.badge}>SKELETON — not implemented</Text>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.purpose}>{purpose}</Text>
      <View style={styles.meta}>
        <Text style={styles.metaLine}>Story: {story}</Text>
        {endpoint ? <Text style={styles.metaLine}>Endpoint: {endpoint}</Text> : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: space.xxl, gap: space.md, backgroundColor: color.surface },
  badge: {
    alignSelf: 'flex-start',
    backgroundColor: color.prototype.bg,
    color: color.prototype.fg,
    fontSize: font.size.xs,
    fontWeight: font.weight.bold,
    paddingHorizontal: space.sm,
    paddingVertical: space.xs,
    borderRadius: radius.sm,
    overflow: 'hidden',
  },
  title: { fontFamily: font.family.heading, fontSize: font.size.title, color: color.text },
  purpose: { fontFamily: font.family.body, fontSize: font.size.md, lineHeight: 22, color: color.textMuted },
  meta: { marginTop: space.sm, gap: space.xs },
  metaLine: { fontSize: font.size.sm, color: color.textMuted, fontFamily: 'monospace' },
});
