import { useAudioPlayer, useAudioPlayerStatus } from 'expo-audio';
import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Animated, { Easing, useAnimatedStyle, useReducedMotion, useSharedValue, withTiming } from 'react-native-reanimated';

import {
  FLASH_LEAD_MS,
  fireFlash,
  MoonlitScene,
  PAN_DELAY_MS,
  PAN_MS,
  SKY,
  useScenePan,
} from '../src/components/MoonlitScene';
import { useMoonBurst } from '../src/components/MoonBurst';
import { SongProgress } from '../src/components/SongProgress';
import { GlitchOverlay, type GlitchHandle } from '../src/components/GlitchOverlay';
import { CLIMAX_BURST_MS, CLIMAX_END_MS, CLIMAX_START_MS, GLITCH_MS, SNARE_MS } from '../src/components/nullscapesSnares';
import { Dashboard } from '../src/components/wallet/Dashboard';
import { LoginPanel } from '../src/components/wallet/LoginPanel';
import { useAuth } from '../src/store/auth';
import { font } from '../src/theme/moonlit';

// The song's first 1:33.5, looped (see SONG_MS in nullscapesSnares.ts).
const SONG = require('../assets/audio/creo-flow-loop.mp3');

// A snare counts as "just happened" only within this window — anything
// older is skipped silently, so resuming after a stall or a seek never
// fires a burst of stale flashes at once.
const MAX_LATE_MS = 150;

// Screen change, timed against the camera pan (Moonlit Pan study): the old
// screen leaves in the first CONTENT_OUT_MS, the new one arrives over the
// pan's last CONTENT_IN_MS.
const CONTENT_OUT_MS = 220;
const CONTENT_IN_MS = 320;
const CONTENT_DRIFT = 24;

type Screen = 'login' | 'dashboard';

/** Index of the first hit in `times` not yet reached at time `ms`. */
function nextIndex(times: readonly number[], ms: number): number {
  let i = 0;
  while (i < times.length && times[i] < ms) i++;
  return i;
}

export default function Index() {
  const player = useAudioPlayer(SONG);
  const { playing } = useAudioPlayerStatus(player);
  const flash = useSharedValue(0);
  const reduceMotion = useReducedMotion();
  const { isAuthenticated, isLoading } = useAuth();
  const { pan, startPan } = useScenePan();
  const { burst, fireBurst, strike, release } = useMoonBurst();
  const glitch = useRef<GlitchHandle>(null);

  // Which screen is on display lags the session by design: on sign-in or
  // sign-out the old screen stays up while it fades, the camera pans
  // (forward into the dashboard, back out to sign-in), and the new one
  // fades in as the pan settles.
  const [shown, setShown] = useState<Screen | null>(null);
  const contentOpacity = useSharedValue(1);
  const contentDrift = useSharedValue(0);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const contentStyle = useAnimatedStyle(() => ({
    opacity: contentOpacity.value,
    transform: [{ translateX: contentDrift.value }],
  }));

  useEffect(() => {
    if (isLoading) return;
    const next: Screen = isAuthenticated ? 'dashboard' : 'login';
    if (shown === null) {
      setShown(next);
      return;
    }
    if (shown === next) return;

    timers.current.forEach(clearTimeout);
    const dir = next === 'dashboard' ? 1 : -1;
    const out = reduceMotion ? 200 : CONTENT_OUT_MS;
    const inStart = reduceMotion ? 200 : PAN_DELAY_MS + PAN_MS - CONTENT_IN_MS;
    const inMs = reduceMotion ? 200 : CONTENT_IN_MS;
    const drift = reduceMotion ? 0 : CONTENT_DRIFT;

    if (!reduceMotion) startPan(dir);
    contentOpacity.value = withTiming(0, { duration: out });
    contentDrift.value = withTiming(-dir * drift, { duration: out });
    timers.current = [
      setTimeout(() => {
        setShown(next);
        contentDrift.value = dir * drift;
      }, out),
      setTimeout(() => {
        contentOpacity.value = withTiming(1, { duration: inMs, easing: Easing.out(Easing.cubic) });
        contentDrift.value = withTiming(0, { duration: inMs, easing: Easing.out(Easing.cubic) });
      }, Math.max(out, inStart)),
    ];
  }, [isLoading, isAuthenticated, shown, reduceMotion, startPan, contentOpacity, contentDrift]);

  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  useEffect(() => {
    player.loop = true;
  }, [player]);

  // Read the live playback position every frame (status events are too
  // coarse to land on a snare) and fire one flash per snare, FLASH_LEAD_MS
  // early so the flash peaks on the hit itself. Inside the climax the moon's
  // column is held, and each climax hit also fires a full explosion.
  useEffect(() => {
    if (!playing || reduceMotion) return;
    let raf = 0;
    let lastMs = player.currentTime * 1000;
    let idx = nextIndex(SNARE_MS, lastMs);
    let burstIdx = nextIndex(CLIMAX_BURST_MS, lastMs);
    let glitchIdx = nextIndex(GLITCH_MS, lastMs);
    let inClimax = false;
    const tick = () => {
      const ms = player.currentTime * 1000;
      if (ms < lastMs) {
        // looped back to the start, or restarted
        idx = nextIndex(SNARE_MS, ms);
        burstIdx = nextIndex(CLIMAX_BURST_MS, ms);
        glitchIdx = nextIndex(GLITCH_MS, ms);
      }
      lastMs = ms;
      const lead = ms + FLASH_LEAD_MS;
      while (idx < SNARE_MS.length && lead >= SNARE_MS[idx]) {
        if (lead - SNARE_MS[idx] <= MAX_LATE_MS) fireFlash(flash);
        idx++;
      }
      while (burstIdx < CLIMAX_BURST_MS.length && lead >= CLIMAX_BURST_MS[burstIdx]) {
        if (lead - CLIMAX_BURST_MS[burstIdx] <= MAX_LATE_MS) {
          fireBurst();
          fireFlash(flash);
        }
        burstIdx++;
      }
      while (glitchIdx < GLITCH_MS.length && ms >= GLITCH_MS[glitchIdx]) {
        if (ms - GLITCH_MS[glitchIdx] <= MAX_LATE_MS) glitch.current?.fire();
        glitchIdx++;
      }
      // Derived from the clock every frame, so a seek or restart into or
      // out of the climax brings the column with it.
      const climax = lead >= CLIMAX_START_MS && ms < CLIMAX_END_MS;
      if (climax !== inClimax) {
        inClimax = climax;
        if (climax) strike();
        else release();
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      // paused mid-climax: let the column go rather than leave it hanging
      if (inClimax) release();
    };
  }, [playing, player, flash, reduceMotion, fireBurst, strike, release]);

  // Back to 0:00 and playing — the snare loop sees the clock jump
  // backwards and re-finds its place, so flashes stay in sync.
  // The web player reports "not playing" for a moment while it seeks; hold
  // the label on "Pause" through that instead of flickering to "Play".
  const [restarting, setRestarting] = useState(false);
  useEffect(() => {
    if (playing) setRestarting(false);
  }, [playing]);
  const restart = async () => {
    setRestarting(true);
    await player.seekTo(0);
    player.play();
  };
  const showPause = playing || restarting;

  // Play/Pause, restart, then the song's progress — the same row in the
  // dashboard header and under the sign-in panel.
  const songControls = (
    <View style={styles.songControls}>
      <Pressable
        testID="play-song"
        accessibilityRole="button"
        accessibilityLabel={showPause ? 'Pause Nullscapes' : 'Play Nullscapes'}
        onPress={() => {
          if (showPause) {
            setRestarting(false);
            player.pause();
          } else {
            player.play();
          }
        }}
        style={({ pressed }) => [styles.button, styles.playButton, pressed && styles.pressed]}
      >
        <Text style={styles.label}>{showPause ? 'Pause' : 'Play'}</Text>
      </Pressable>
      <Pressable
        testID="restart-song"
        accessibilityRole="button"
        accessibilityLabel="Restart Nullscapes from the beginning"
        onPress={() => void restart()}
        style={({ pressed }) => [styles.button, styles.iconButton, pressed && styles.pressed]}
      >
        <Text style={[styles.label, styles.icon]}>↺</Text>
      </Pressable>
      <SongProgress player={player} />
    </View>
  );

  return (
    <View style={styles.root}>
      <MoonlitScene style={StyleSheet.absoluteFill} flash={flash} pan={pan} burst={burst} />
      <SafeAreaView style={styles.overlay}>
        {shown === null ? (
          <View style={styles.center}>
            <ActivityIndicator color="#eaf0ff" />
          </View>
        ) : (
          <Animated.View style={[styles.overlay, contentStyle]}>
            {shown === 'dashboard' ? (
              <Dashboard headerAction={songControls} />
            ) : (
              <KeyboardAvoidingView
                style={styles.center}
                behavior={Platform.OS === 'ios' ? 'padding' : undefined}
              >
                <LoginPanel />
                <View style={styles.loginSong}>{songControls}</View>
              </KeyboardAvoidingView>
            )}
          </Animated.View>
        )}
      </SafeAreaView>
      {/* Above everything, UI included, and never takes a touch: the
          glitch breaks the whole screen for its one second. */}
      <GlitchOverlay ref={glitch} />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: SKY },
  overlay: { flex: 1 },
  center: { flex: 1, justifyContent: 'center', padding: 16, gap: 20 },
  loginSong: { width: '100%', maxWidth: 380, alignSelf: 'center' },
  songControls: { flexDirection: 'row', alignItems: 'center', gap: 8, flex: 1 },
  playButton: { minWidth: 76, alignItems: 'center' },
  iconButton: { paddingHorizontal: 0, width: 34, alignItems: 'center' },
  icon: { fontSize: 15, letterSpacing: 0 },
  button: {
    height: 34,
    justifyContent: 'center',
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
