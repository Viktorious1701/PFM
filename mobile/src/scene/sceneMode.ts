/**
 * Which background sequence plays: the full four scenes, or the moon scene
 * for the whole song. Remembered per device; storage that is blocked or
 * cleared just falls back to the full sequence.
 */
import { useEffect, useState } from 'react';
import { Platform } from 'react-native';

import { readSetting, writeSetting } from '../store/device-storage';
import type { SequenceMode } from './sequenceEngine';

const KEY = 'pfm.sceneMode';

const parse = (v: string | null): SequenceMode => (v === 'scene3' ? 'scene3' : 'full');

// Web can read its storage synchronously, so the first frame is already right.
function initial(): SequenceMode {
  if (Platform.OS !== 'web') return 'full';
  try {
    return parse(globalThis.localStorage?.getItem(KEY) ?? null);
  } catch {
    return 'full';
  }
}

export function useSceneMode(): [SequenceMode, (mode: SequenceMode) => void] {
  const [mode, setMode] = useState<SequenceMode>(initial);
  useEffect(() => {
    if (Platform.OS === 'web') return;
    let cancelled = false;
    void readSetting(KEY).then((v) => !cancelled && setMode(parse(v)));
    return () => {
      cancelled = true;
    };
  }, []);
  const set = (next: SequenceMode) => {
    setMode(next);
    void writeSetting(KEY, next);
  };
  return [mode, set];
}
