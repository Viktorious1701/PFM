import { useAudioPlayer, useAudioPlayerStatus } from 'expo-audio';
import { useEffect } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useReducedMotion, useSharedValue } from 'react-native-reanimated';

import { FLASH_LEAD_MS, fireFlash, MoonlitScene, SKY } from '../src/components/MoonlitScene';
import { SNARE_MS } from '../src/components/nullscapesSnares';
import { Dashboard } from '../src/components/wallet/Dashboard';
import { LoginPanel } from '../src/components/wallet/LoginPanel';
import { useAuth } from '../src/store/auth';
import { font } from '../src/theme/moonlit';

const SONG = require('../assets/audio/creo-flow.mp3');

// A snare counts as "just happened" only within this window — anything
// older is skipped silently, so resuming after a stall or a seek never
// fires a burst of stale flashes at once.
const MAX_LATE_MS = 150;

/** Index of the first snare not yet reached at time `ms`. */
function nextSnareIndex(ms: number): number {
  let i = 0;
  while (i < SNARE_MS.length && SNARE_MS[i] < ms) i++;
  return i;
}

export default function Index() {
  const player = useAudioPlayer(SONG);
  const { playing } = useAudioPlayerStatus(player);
  const flash = useSharedValue(0);
  const reduceMotion = useReducedMotion();
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    player.loop = true;
  }, [player]);

  // Read the live playback position every frame (status events are too
  // coarse to land on a snare) and fire one flash per snare, FLASH_LEAD_MS
  // early so the flash peaks on the hit itself.
  useEffect(() => {
    if (!playing || reduceMotion) return;
    let raf = 0;
    let lastMs = player.currentTime * 1000;
    let idx = nextSnareIndex(lastMs);
    const tick = () => {
      const ms = player.currentTime * 1000;
      if (ms < lastMs) idx = nextSnareIndex(ms); // looped back to the start
      lastMs = ms;
      while (idx < SNARE_MS.length && ms + FLASH_LEAD_MS >= SNARE_MS[idx]) {
        if (ms + FLASH_LEAD_MS - SNARE_MS[idx] <= MAX_LATE_MS) fireFlash(flash);
        idx++;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing, player, flash, reduceMotion]);

  const songButton = (compact: boolean) => (
    <Pressable
      testID="play-song"
      accessibilityRole="button"
      accessibilityLabel={playing ? 'Pause Nullscapes' : 'Play Nullscapes'}
      onPress={() => (playing ? player.pause() : player.play())}
      style={({ pressed }) => [styles.button, pressed && styles.pressed]}
    >
      <Text style={styles.label}>{playing ? 'Pause' : compact ? 'Play' : 'Play Nullscapes'}</Text>
    </Pressable>
  );

  return (
    <View style={styles.root}>
      <MoonlitScene style={StyleSheet.absoluteFill} flash={flash} />
      <SafeAreaView style={styles.overlay}>
        {isLoading ? (
          <View style={styles.center}>
            <ActivityIndicator color="#eaf0ff" />
          </View>
        ) : isAuthenticated ? (
          <Dashboard headerAction={songButton(true)} />
        ) : (
          <KeyboardAvoidingView
            style={styles.center}
            behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          >
            <LoginPanel />
            <View style={styles.loginSong}>{songButton(false)}</View>
          </KeyboardAvoidingView>
        )}
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: SKY },
  overlay: { flex: 1 },
  center: { flex: 1, justifyContent: 'center', padding: 16, gap: 20 },
  loginSong: { alignItems: 'center' },
  button: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: 'rgba(223,232,251,0.45)',
    backgroundColor: 'rgba(10,18,32,0.55)',
  },
  pressed: { opacity: 0.7 },
  label: {
    color: '#eaf0ff',
    fontFamily: font.semibold,
    fontSize: 11,
    letterSpacing: 3,
    textTransform: 'uppercase',
  },
});
