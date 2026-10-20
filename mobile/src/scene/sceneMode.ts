/**
 * Which background sequence plays: the full four scenes, or the moon scene
 * for the whole song. Remembered per browser; storage that is blocked or
 * cleared just falls back to the full sequence.
 */
import { useState } from 'react';

import type { SequenceMode } from './sequenceEngine';

const KEY = 'pfm.sceneMode';

function load(): SequenceMode {
  try {
    return globalThis.localStorage?.getItem(KEY) === 'scene3' ? 'scene3' : 'full';
  } catch {
    return 'full';
  }
}

export function useSceneMode(): [SequenceMode, (mode: SequenceMode) => void] {
  const [mode, setMode] = useState<SequenceMode>(load);
  const set = (next: SequenceMode) => {
    setMode(next);
    try {
      globalThis.localStorage?.setItem(KEY, next);
    } catch {
      // not remembered; the choice still holds for this visit
    }
  };
  return [mode, set];
}
