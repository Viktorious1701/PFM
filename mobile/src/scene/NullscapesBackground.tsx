/**
 * The fullscreen Nullscapes background: the sequence engine drawn on one
 * canvas, cover-fitted (cropped evenly) to any screen shape. Each frame it
 * reads the song's position and the tab-pan camera and draws that moment,
 * so the scenes, flashes and glitches stay locked to the music — seeking,
 * restarting and looping included.
 *
 * Before the song has ever played it rests on a calm frame of the moon
 * scene; while paused it holds the paused moment. Reduced motion: one still
 * frame. Web only (ENV-04); elsewhere it renders the scene's sky colour.
 */
import type { AudioPlayer } from 'expo-audio';
import { useEffect, useRef } from 'react';
import { Platform, StyleSheet, View } from 'react-native';

import { createSequence, type Sequence } from './sequenceEngine';
import type { ScenePan } from './scenePan';

/** The calm moon-scene moment shown before the song is first played. */
const RESTING_MS = 61000;

export function NullscapesBackground({
  player,
  pan,
  reduceMotion,
}: {
  player: AudioPlayer;
  pan: ScenePan;
  reduceMotion: boolean;
}) {
  const host = useRef<View>(null);

  useEffect(() => {
    if (Platform.OS !== 'web') return;
    const el = host.current as unknown as HTMLElement | null;
    if (!el) return;
    const canvas = document.createElement('canvas');
    canvas.width = 1280;
    canvas.height = 720;
    Object.assign(canvas.style, { width: '100%', height: '100%', objectFit: 'cover', display: 'block' });
    el.appendChild(canvas);
    const seq: Sequence = createSequence(canvas);

    let raf = 0;
    let played = false;
    let last = '';
    const frame = () => {
      const pos = player.currentTime * 1000;
      if (player.playing || pos > 0) played = true;
      const t = reduceMotion || !played ? RESTING_MS : pos;
      const cam = pan.camera.value;
      const shear = pan.lean.value[4] ?? 0; // near layer
      // Only redraw when something changed: playing, a pan, or a seek.
      const key = `${Math.round(t)}|${cam.toFixed(1)}|${shear.toFixed(4)}`;
      if (key !== last) {
        last = key;
        seq.render(t, cam, shear);
      }
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
    return () => {
      cancelAnimationFrame(raf);
      canvas.remove();
    };
  }, [player, pan, reduceMotion]);

  return <View ref={host} style={styles.fill} pointerEvents="none" importantForAccessibility="no-hide-descendants" />;
}

const styles = StyleSheet.create({
  fill: { ...StyleSheet.absoluteFill, backgroundColor: '#0f1d33', overflow: 'hidden' },
});
