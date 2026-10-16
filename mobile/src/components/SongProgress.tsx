/**
 * Song progress: the track's waveform, filled in as it plays, with the
 * elapsed / total time beside it. Clicking or tapping anywhere on the
 * waveform jumps the song to that point. Reads the player directly (its own
 * per-frame loop while playing), so ticking along never re-renders the
 * screen around it.
 */
import { useAudioPlayerStatus, type AudioPlayer } from 'expo-audio';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View, type GestureResponderEvent, type LayoutChangeEvent } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue } from 'react-native-reanimated';
import Svg, { Rect } from 'react-native-svg';

import { font } from '../theme/moonlit';
import { SONG_WAVEFORM } from './songWaveform';

const BAR_H = 20;
const BAR_PITCH = 4; // px per bar (2.5 px bar + gap), whatever the width

function clock(sec: number): string {
  const s = Math.max(0, Math.floor(sec));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

/** The waveform merged down to one bar per BAR_PITCH px (each bar takes
 * the loudest of the samples it covers), so a short bar stays crisp
 * instead of cramming 120 bars into a blur. */
function barsFor(width: number): number[] {
  const n = Math.max(8, Math.min(SONG_WAVEFORM.length, Math.floor(width / BAR_PITCH)));
  return Array.from({ length: n }, (_, i) => {
    const from = Math.floor((i * SONG_WAVEFORM.length) / n);
    const to = Math.max(from + 1, Math.floor(((i + 1) * SONG_WAVEFORM.length) / n));
    return Math.max(...SONG_WAVEFORM.slice(from, to));
  });
}

function Bars({ color, width, bars }: { color: string; width: number; bars: number[] }) {
  const pitch = width / bars.length;
  return (
    <Svg width={width} height={BAR_H}>
      {bars.map((v, i) => {
        const h = Math.max(2, v * BAR_H);
        return <Rect key={i} x={i * pitch} y={(BAR_H - h) / 2} width={pitch * 0.62} height={h} rx={1} fill={color} />;
      })}
    </Svg>
  );
}

export function SongProgress({ player }: { player: AudioPlayer }) {
  const { playing, duration, currentTime } = useAudioPlayerStatus(player);
  const [width, setWidth] = useState(0);
  const [shownSec, setShownSec] = useState(0);
  const progress = useSharedValue(0);
  const lastShown = useRef(-1);

  const show = (sec: number) => {
    const total = duration || player.duration || 0;
    progress.value = total > 0 ? Math.min(1, sec / total) : 0;
    const whole = Math.floor(sec);
    if (whole !== lastShown.current) {
      lastShown.current = whole;
      setShownSec(whole);
    }
  };

  // While playing: follow the live position every frame (status events
  // are too coarse for a smooth fill). While paused: follow the status.
  useEffect(() => {
    if (!playing) {
      show(currentTime);
      return;
    }
    let raf = 0;
    const tick = () => {
      show(player.currentTime);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, player, duration, currentTime]);

  const fillStyle = useAnimatedStyle(() => ({ width: `${progress.value * 100}%` }));

  const seek = (e: GestureResponderEvent) => {
    const total = duration || player.duration || 0;
    if (!width || !total) return;
    const ne = e.nativeEvent as unknown as { locationX?: number; offsetX?: number };
    const x = ne.locationX ?? ne.offsetX ?? 0;
    const ratio = Math.min(1, Math.max(0, x / width));
    void player.seekTo(ratio * total);
    show(ratio * total);
  };

  const total = duration || player.duration || 0;
  const bars = useMemo(() => barsFor(width), [width]);

  return (
    <View style={styles.wrap}>
      <Pressable
        testID="song-progress"
        accessibilityRole="adjustable"
        accessibilityLabel="Song position — tap to jump"
        accessibilityValue={{ min: 0, max: Math.round(total), now: shownSec, text: `${clock(shownSec)} of ${clock(total)}` }}
        onPress={seek}
        onLayout={(e: LayoutChangeEvent) => setWidth(e.nativeEvent.layout.width)}
        style={styles.track}
      >
        {width > 0 ? (
          <>
            <Bars color="rgba(223,232,251,0.28)" width={width} bars={bars} />
            <Animated.View style={[styles.fill, fillStyle]} pointerEvents="none">
              <Bars color="#eaf0ff" width={width} bars={bars} />
            </Animated.View>
          </>
        ) : null}
      </Pressable>
      <Text style={styles.time} testID="song-time">
        {clock(shownSec)} / {clock(total)}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    minWidth: 0,
    height: 34,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 14,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: 'rgba(223,232,251,0.25)',
    backgroundColor: 'rgba(10,18,32,0.55)',
  },
  track: { flex: 1, height: BAR_H, justifyContent: 'center', cursor: 'pointer' },
  fill: { position: 'absolute', left: 0, top: 0, bottom: 0, overflow: 'hidden' },
  time: {
    fontFamily: font.semibold,
    fontSize: 12,
    letterSpacing: 1,
    color: '#eaf0ff',
    fontVariant: ['tabular-nums'],
    minWidth: 70,
    textAlign: 'right',
  },
});
