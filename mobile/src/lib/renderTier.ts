/**
 * Render detail tier — `'high' | 'low'`. A performance/device-capability
 * concept, deliberately separate from `useReducedMotion()` (an OS
 * accessibility signal, left untouched wherever it's already used): a
 * capable device with motion reduced should still get the richer Skia
 * scene at a static frame, and a low-powered device without motion
 * reduced should still get the lighter SVG scene with its own motion.
 *
 * No settings UI reads or writes this yet (none exists in the app today) —
 * `computeDetailTier`'s `override` parameter is the forward-compatible
 * seam a later settings screen can use, reading/writing one stored
 * preference and passing it in, without this module's shape changing.
 *
 * The heuristic is a static one (CPU cores on web, device memory on
 * native), not a runtime FPS probe — picked deliberately: a probe needs an
 * async "render once, measure, decide" step before first paint and is real
 * over-engineering for one small illustration. Revisit only if real usage
 * shows tier mismatches.
 */
import { Platform } from 'react-native';
import * as Device from 'expo-device';

export type DetailTier = 'high' | 'low';

const LOW_MEMORY_BYTES = 3 * 1024 ** 3; // 3 GB
const LOW_CORE_COUNT = 4;

export function computeDetailTier(override?: DetailTier | null): DetailTier {
  if (override) return override;

  if (Platform.OS === 'web') {
    const cores = typeof navigator !== 'undefined' ? navigator.hardwareConcurrency : undefined;
    return typeof cores === 'number' && cores > 0 && cores <= LOW_CORE_COUNT ? 'low' : 'high';
  }

  // `Device.totalMemory` is `null` on web (confirmed in the package's own
  // types) — this branch only ever runs on native, where it's real.
  const totalMemory = Device.totalMemory;
  if (typeof totalMemory === 'number' && totalMemory < LOW_MEMORY_BYTES) return 'low';
  return 'high';
}

export const detailTier: DetailTier = computeDetailTier();
