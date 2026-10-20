import { useAudioPlayer, useAudioPlayerStatus } from 'expo-audio';
import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, usePathname } from 'expo-router';
import Animated, { Easing, useAnimatedStyle, useReducedMotion, useSharedValue, withTiming } from 'react-native-reanimated';

import { SongProgress } from '../src/components/SongProgress';
import { NullscapesBackground } from '../src/scene/NullscapesBackground';
import { PAN_DELAY_MS, panDuration, useScenePan } from '../src/scene/scenePan';
import { useSceneMode } from '../src/scene/sceneMode';
import { AppHeader } from '../src/components/AppHeader';
import { ActivityPage } from '../src/components/pages/ActivityPage';
import { BudgetsPage } from '../src/components/pages/BudgetsPage';
import { FamilyPage } from '../src/components/pages/FamilyPage';
import { WalletsPage } from '../src/components/pages/WalletsPage';
import { TabBar, type Tab } from '../src/components/TabBar';
import { Dashboard } from '../src/components/wallet/Dashboard';
import { ActivatePanel } from '../src/components/wallet/ActivatePanel';
import { LoginPanel } from '../src/components/wallet/LoginPanel';
import { useAuth } from '../src/store/auth';
import { font } from '../src/theme/moonlit';

// The whole Nullscapes track (intro, three scenes, outro), looped; the
// background draws whatever moment of it is playing (src/scene/).
const SONG = require('../assets/audio/nullscapes-sequence.mp3');

// Screen change, timed against the camera pan (Moonlit Pan study): the old
// screen leaves in the first CONTENT_OUT_MS, the new one arrives over the
// pan's last CONTENT_IN_MS.
const CONTENT_OUT_MS = 220;
const CONTENT_IN_MS = 320;
const CONTENT_DRIFT = 24;

type TabKey = 'home' | 'wallets' | 'activity' | 'budgets' | 'family';
// 'activate' is where an invitation link lands (app/activate.tsx renders
// this same screen); it sits just before sign-in along the meadow.
type Screen = 'activate' | 'login' | TabKey;
/** Screens shown without the header and tab bar. */
const isGate = (sc: Screen) => sc === 'activate' || sc === 'login';

// Left to right along the meadow; sign-in sits just before the first.
const TABS: readonly Tab<TabKey>[] = [
  { key: 'home', label: 'Home' },
  { key: 'wallets', label: 'Wallets' },
  { key: 'activity', label: 'Activity' },
  { key: 'budgets', label: 'Budgets' },
  { key: 'family', label: 'Family' }, // ADMIN only
];
const TAB_ADMIN_ONLY: ReadonlySet<TabKey> = new Set(['family']);

export default function Index() {
  const player = useAudioPlayer(SONG);
  const { playing } = useAudioPlayerStatus(player);
  const reduceMotion = useReducedMotion();
  const [sceneMode, setSceneMode] = useSceneMode();
  const { isAuthenticated, isLoading, isAdmin } = useAuth();
  // An invitation link opens /activate?token=…. Leaving it ("Go to sign
  // in") swaps the URL back to / in place rather than navigating, so the
  // scene, the song and the pan carry straight on.
  const pathname = usePathname();
  const { token: tokenParam } = useLocalSearchParams<{ token?: string }>();
  const [activationToken] = useState<string | null>(typeof tokenParam === 'string' && tokenParam ? tokenParam : null);
  const [activationLeft, setActivationLeft] = useState(false);
  const activating = pathname === '/activate' && !activationLeft;
  const leaveActivation = () => {
    setActivationLeft(true);
    if (Platform.OS === 'web' && typeof window !== 'undefined') window.history.replaceState(null, '', '/');
  };
  const tabs = TABS.filter((t) => isAdmin || !TAB_ADMIN_ONLY.has(t.key));
  const [tab, setTab] = useState<TabKey>('home');
  /** Where a screen sits along the meadow: sign-in 0, tabs 1..n. */
  const position = (sc: Screen) => (sc === 'activate' ? -1 : sc === 'login' ? 0 : 1 + Math.max(0, tabs.findIndex((t) => t.key === sc)));
  const { pan, startPan } = useScenePan();

  // Which screen is on display lags the request by design: on sign-in,
  // sign-out or a tab change the old screen stays up while it fades, the
  // camera pans by the distance between the two screens' places (forward
  // to the right, back to the left), and the new one fades in as the pan
  // settles. The header and tab bar stay put between tabs, and fade with
  // the page only when crossing to or from sign-in.
  const [shown, setShown] = useState<Screen | null>(null);
  const contentOpacity = useSharedValue(1);
  const contentDrift = useSharedValue(0);
  const chromeOpacity = useSharedValue(1);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const contentStyle = useAnimatedStyle(() => ({
    opacity: contentOpacity.value,
    transform: [{ translateX: contentDrift.value }],
  }));
  const chromeStyle = useAnimatedStyle(() => ({ opacity: chromeOpacity.value }));

  const target: Screen = activating
    ? 'activate'
    : !isAuthenticated
      ? 'login'
      : tabs.some((t) => t.key === tab)
        ? tab
        : 'home';

  useEffect(() => {
    if (isLoading) return;
    const next = target;
    if (isGate(next) && tab !== 'home') setTab('home'); // sign back in to Home
    if (shown === null) {
      setShown(next);
      return;
    }
    if (shown === next) return;

    timers.current.forEach(clearTimeout);
    const delta = position(next) - position(shown);
    const dir = delta > 0 ? 1 : -1;
    const steps = Math.abs(delta);
    const pan = panDuration(steps);
    const out = reduceMotion ? 200 : CONTENT_OUT_MS;
    const inStart = reduceMotion ? 200 : PAN_DELAY_MS + pan - CONTENT_IN_MS;
    const inMs = reduceMotion ? 200 : CONTENT_IN_MS;
    const drift = reduceMotion ? 0 : CONTENT_DRIFT;
    const crossesSignIn = isGate(shown) !== isGate(next);

    if (!reduceMotion) startPan(dir, steps);
    contentOpacity.value = withTiming(0, { duration: out });
    contentDrift.value = withTiming(-dir * drift, { duration: out });
    if (crossesSignIn && !isGate(shown)) chromeOpacity.value = withTiming(0, { duration: out });
    timers.current = [
      setTimeout(() => {
        setShown(next);
        contentDrift.value = dir * drift;
        if (crossesSignIn && !isGate(next)) chromeOpacity.value = 0;
      }, out),
      setTimeout(() => {
        const cfg = { duration: inMs, easing: Easing.out(Easing.cubic) };
        contentOpacity.value = withTiming(1, cfg);
        contentDrift.value = withTiming(0, cfg);
        if (crossesSignIn && !isGate(next)) chromeOpacity.value = withTiming(1, cfg);
      }, Math.max(out, inStart)),
    ];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoading, target, shown, reduceMotion, startPan, contentOpacity, contentDrift, chromeOpacity]);

  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  useEffect(() => {
    player.loop = true;
  }, [player]);

  // Back to 0:00 and playing — the background draws from the song's
  // position, so it is back at the intro's rise from black with it.
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

  // Play/Pause, restart, the moon-only switch, then the song's progress — the same row in the
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
      <Pressable
        testID="moon-only"
        role="switch"
        aria-label="Moon scene only"
        aria-checked={sceneMode === 'scene3'}
        onPress={() => setSceneMode(sceneMode === 'scene3' ? 'full' : 'scene3')}
        style={({ pressed }) => [
          styles.button,
          styles.modeButton,
          sceneMode === 'scene3' && styles.modeOn,
          pressed && styles.pressed,
        ]}
      >
        <Text style={[styles.label, sceneMode === 'scene3' && styles.modeOnLabel]}>Moon</Text>
      </Pressable>
      <SongProgress player={player} />
    </View>
  );

  return (
    <View style={styles.root}>
      <NullscapesBackground player={player} pan={pan} reduceMotion={!!reduceMotion} mode={sceneMode} />
      <SafeAreaView style={styles.overlay}>
        {shown === null ? (
          <View style={styles.center}>
            <ActivityIndicator color="#eaf0ff" />
          </View>
        ) : (
          <>
            {!isGate(shown) ? (
              <Animated.View style={chromeStyle}>
                <AppHeader song={songControls} />
              </Animated.View>
            ) : null}
            <Animated.View style={[styles.overlay, contentStyle]}>
              {shown === 'activate' ? (
                <KeyboardAvoidingView style={styles.center} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
                  <ActivatePanel token={activationToken} onSignIn={leaveActivation} />
                  <View style={styles.loginSong}>{songControls}</View>
                </KeyboardAvoidingView>
              ) : shown === 'login' ? (
                <KeyboardAvoidingView style={styles.center} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
                  <LoginPanel />
                  <View style={styles.loginSong}>{songControls}</View>
                </KeyboardAvoidingView>
              ) : shown === 'home' ? (
                <Dashboard />
              ) : shown === 'wallets' ? (
                <WalletsPage />
              ) : shown === 'activity' ? (
                <ActivityPage />
              ) : shown === 'budgets' ? (
                <BudgetsPage />
              ) : (
                <FamilyPage />
              )}
            </Animated.View>
            {!isGate(shown) ? (
              <Animated.View style={[StyleSheet.absoluteFill, chromeStyle]} pointerEvents="box-none">
                <TabBar
                  tabs={tabs}
                  active={isGate(target) ? (shown as TabKey) : (target as TabKey)}
                  onSelect={setTab}
                  glideDelayMs={PAN_DELAY_MS}
                  glideFor={panDuration}
                  instant={!!reduceMotion}
                />
              </Animated.View>
            ) : null}
          </>
        )}
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#0f1d33' },
  overlay: { flex: 1 },
  center: { flex: 1, justifyContent: 'center', padding: 16, gap: 20 },
  loginSong: { width: '100%', maxWidth: 380, alignSelf: 'center' },
  songControls: { flexDirection: 'row', alignItems: 'center', gap: 8, flex: 1 },
  playButton: { minWidth: 76, alignItems: 'center' },
  iconButton: { paddingHorizontal: 0, width: 34, alignItems: 'center' },
  icon: { fontSize: 15, letterSpacing: 0 },
  modeButton: { paddingHorizontal: 12 },
  modeOn: { backgroundColor: '#eaf0ff', borderColor: '#eaf0ff' },
  modeOnLabel: { color: '#0b1220' },
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
