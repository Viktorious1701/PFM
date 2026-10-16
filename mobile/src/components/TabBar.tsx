/**
 * Floating tab bar. Tabs are places along the meadow, left to right; the
 * soft marker under the active tab glides to a new one with the camera
 * pan's own delay, length and easing, so marker, grass and page move as one
 * motion.
 */
import { useEffect, useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View, type LayoutChangeEvent } from 'react-native';
import Animated, { Easing, useAnimatedStyle, useSharedValue, withDelay, withTiming } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { font, moon } from '../theme/moonlit';

export type Tab<K extends string> = { key: K; label: string };

export function TabBar<K extends string>({
  tabs,
  active,
  onSelect,
  glideDelayMs,
  glideFor,
  instant,
}: {
  tabs: readonly Tab<K>[];
  active: K;
  onSelect: (key: K) => void;
  glideDelayMs: number;
  /** Glide length for a jump of `steps` tabs — the pan's own duration. */
  glideFor: (steps: number) => number;
  /** Reduced motion: jump the marker. */
  instant: boolean;
}) {
  const insets = useSafeAreaInsets();
  const [boxes, setBoxes] = useState<Record<string, { x: number; w: number }>>({});
  const markX = useSharedValue(0);
  const markW = useSharedValue(0);
  const placed = useSharedValue(false);
  const prev = useRef<K>(active);

  useEffect(() => {
    const b = boxes[active];
    if (!b) return;
    if (!placed.value || instant) {
      markX.value = b.x;
      markW.value = b.w;
      placed.value = true;
      return;
    }
    const steps = Math.max(1, Math.abs(tabs.findIndex((t) => t.key === active) - tabs.findIndex((t) => t.key === prev.current)));
    prev.current = active;
    const cfg = { duration: glideFor(steps), easing: Easing.inOut(Easing.cubic) };
    markX.value = withDelay(glideDelayMs, withTiming(b.x, cfg));
    markW.value = withDelay(glideDelayMs, withTiming(b.w, cfg));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, boxes]);

  const markStyle = useAnimatedStyle(() => ({
    opacity: placed.value ? 1 : 0,
    transform: [{ translateX: markX.value + markW.value * 0.2 }],
    width: markW.value * 0.6,
  }));

  return (
    <View style={[styles.dock, { bottom: 16 + insets.bottom }]} pointerEvents="box-none">
      <View style={styles.bar} accessibilityRole="tablist">
        {tabs.map((t) => {
          const on = t.key === active;
          return (
            <Pressable
              key={t.key}
              testID={`tab-${t.key}`}
              accessibilityRole="tab"
              accessibilityState={{ selected: on }}
              onPress={() => onSelect(t.key)}
              onLayout={(e: LayoutChangeEvent) => {
                const { x, width } = e.nativeEvent.layout;
                setBoxes((prev) => (prev[t.key]?.x === x && prev[t.key]?.w === width ? prev : { ...prev, [t.key]: { x, w: width } }));
              }}
              style={({ pressed }) => [styles.tab, pressed && styles.pressed]}
            >
              <Text style={[styles.label, on && styles.labelOn]} numberOfLines={1}>
                {t.label}
              </Text>
            </Pressable>
          );
        })}
        <Animated.View style={[styles.mark, markStyle]} pointerEvents="none" />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  dock: { position: 'absolute', left: 16, right: 16, alignItems: 'center' },
  bar: {
    flexDirection: 'row',
    width: '100%',
    maxWidth: 560,
    height: 52,
    paddingHorizontal: 6,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: moon.panelBorder,
    backgroundColor: '#0a1321',
  },
  tab: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  label: {
    fontFamily: font.semibold,
    fontSize: 11,
    letterSpacing: 1.6,
    textTransform: 'uppercase',
    color: moon.muted,
  },
  labelOn: { color: moon.ink },
  mark: {
    position: 'absolute',
    left: 0,
    bottom: 9,
    height: 2,
    borderRadius: 2,
    backgroundColor: '#e9eefc',
    shadowColor: '#cfe0ff',
    shadowOpacity: 0.9,
    shadowRadius: 6,
  },
  pressed: { opacity: 0.6 },
});
