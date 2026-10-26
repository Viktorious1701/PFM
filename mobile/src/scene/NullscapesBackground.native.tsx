/**
 * The fullscreen Nullscapes background on Android. The scenes are drawn by
 * the same engine as the web (sequenceEngine.ts), running in a WebView
 * (sceneHtml.generated.ts), so the phone's browser canvas does the drawing
 * at browser speed. This component only keeps it in step: the song's
 * position, the tab-pan camera and the mode.
 *
 * The page keeps its own clock between syncs, so motion is paced by its own
 * frames; syncs go out every frame while the camera moves, at once on play,
 * pause, a seek or a mode change, and every half second otherwise.
 *
 * Before the song has ever played it rests on a calm frame of the moon
 * scene; while paused it holds the paused moment. Reduced motion: one still
 * frame.
 */
import type { AudioPlayer } from 'expo-audio';
import { useEffect, useRef, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { WebView } from 'react-native-webview';

import type { ScenePan } from './scenePan';
import { SCENE_HTML } from './sceneHtml.generated';
import type { SequenceMode } from './sequenceEngine';

/** The calm moon-scene moment shown before the song is first played. */
const RESTING_MS = 61000;
/** Resync this often (ms) while nothing else has changed. */
const RESYNC_MS = 500;

export function NullscapesBackground({
  player,
  pan,
  reduceMotion,
  mode,
}: {
  player: AudioPlayer;
  pan: ScenePan;
  reduceMotion: boolean;
  mode: SequenceMode;
}) {
  const web = useRef<WebView>(null);
  const [ready, setReady] = useState(false);
  // read by the loop, so changing it doesn't restart it
  const modeRef = useRef(mode);
  modeRef.current = mode;

  useEffect(() => {
    if (!ready) return;
    let raf = 0;
    let played = false;
    let sent = '';
    let sentAt = 0;
    const loop = () => {
      const pos = player.currentTime * 1000;
      if (player.playing || pos > 0) played = true;
      const still = reduceMotion || !played;
      const t = still ? RESTING_MS : pos;
      const playing = !still && player.playing;
      const cam = pan.camera.value;
      const shear = pan.lean.value[4] ?? 0; // near layer
      // what changes the picture other than time passing while playing
      const state = `${playing}|${modeRef.current}|${cam.toFixed(1)}|${shear.toFixed(4)}|${playing ? '' : Math.round(t)}`;
      const now = Date.now();
      if (state !== sent || now - sentAt >= RESYNC_MS) {
        sent = state;
        sentAt = now;
        const msg = { t: Math.round(t), playing, cam, shear, mode: modeRef.current };
        web.current?.injectJavaScript(`window.__sync && window.__sync(${JSON.stringify(msg)}); true;`);
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [ready, player, pan, reduceMotion]);

  return (
    <View style={styles.fill} pointerEvents="none" importantForAccessibility="no-hide-descendants">
      <WebView
        ref={web}
        source={{ html: SCENE_HTML }}
        originWhitelist={['*']}
        style={styles.web}
        containerStyle={styles.web}
        scrollEnabled={false}
        overScrollMode="never"
        androidLayerType="hardware"
        javaScriptEnabled
        // Android may end the page's renderer under memory pressure; unhandled,
        // that ends the app too. Reload the scene instead.
        onRenderProcessGone={() => {
          setReady(false);
          web.current?.reload();
        }}
        onMessage={(e) => {
          const data = e.nativeEvent.data;
          if (data === 'ready') setReady(true);
          // the page's own frame rate, for checking on a real phone
          else if (__DEV__) console.log(`[scene] ${data}`);
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  fill: { ...StyleSheet.absoluteFill, backgroundColor: '#0f1d33', overflow: 'hidden' },
  web: { flex: 1, backgroundColor: '#0f1d33' },
});
