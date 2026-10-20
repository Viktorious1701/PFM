/**
 * The tab-pan camera: each screen is a place along the field, and moving
 * between them pans the camera (forward = right) with the field leaning
 * against the motion and springing back. Values tuned in the Moonlit Pan
 * study (artifact GEGeQYdk1ZE7j9GgvetNT4). The background engine reads
 * `camera` (scene units) and the near layer's `lean` each frame.
 */
import { useCallback, useMemo } from 'react';
import { useFrameCallback, useSharedValue, type SharedValue } from 'react-native-reanimated';

/** The background's own coordinate width (the 1280x720 scene). */
const W = 1280;
/** Lean per depth layer, far → near. */
const LEAN_SCALES = [0.3, 0.6, 1];

// ---- camera pan ----
// Values tuned in the Moonlit Pan study: 1100 ms pan, near grass travels
// 60% of the frame width, 2° lean at full speed, 10% spring-back wobble.
export const PAN_DELAY_MS = 120;
export const PAN_MS = 1100;
const NEAR_TRAVEL = 0.6 * W; // per step
/** A pan of `steps` tab positions travels `steps` x NEAR_TRAVEL but takes
 * only 250 ms longer per extra step, so a long jump reads as faster rather
 * than slower. The lean is capped by speed, not distance. */
export function panDuration(steps: number): number {
  return PAN_MS + 250 * (Math.max(1, steps) - 1);
}
const LEAN_MAX = Math.tan((2 * Math.PI) / 180);
const SPRING_K = 160;
const SPRING_C = 2 * (1 - 0.75 * 0.1) * Math.sqrt(SPRING_K);
/** Shared state of the camera, owned by the caller (`useScenePan`) and read
 * by the background. */
export type ScenePan = {
  /** Near-layer distance travelled, scene units. */
  camera: SharedValue<number>;
  /** Per layer lean spring: [x0, v0, x1, v1, x2, v2], x as tan(angle). */
  lean: SharedValue<number[]>;
  /** Running pan: elapsed ms, start camera, direction, tab steps;
   * elapsed < 0 = idle. */
  run: SharedValue<{ elapsed: number; from: number; dir: number; steps: number }>;
};

function easeInOutCubic(t: number) {
  'worklet';
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}
function easeInOutCubicSlope(t: number) {
  'worklet';
  return t < 0.5 ? 12 * t * t : 3 * Math.pow(-2 * t + 2, 2); // peaks at 3
}

/** Owns the camera and drives it each frame. `startPan(1)` slides the field
 * forward (camera right, grass slides left), `startPan(-1)` back; `steps`
 * is how many tab positions the move covers. Starting a pan mid-pan
 * re-aims from wherever the camera is. */
export function useScenePan(): { pan: ScenePan; startPan: (dir: 1 | -1, steps?: number) => void } {
  const camera = useSharedValue(0);
  const lean = useSharedValue<number[]>(LEAN_SCALES.flatMap(() => [0, 0]));
  const run = useSharedValue({ elapsed: -1, from: 0, dir: 1, steps: 1 });

  // Always registered, but returns at once while the camera is at rest and
  // every lean has settled. (It can't switch itself off: on web the
  // callback captures its own handle before that handle exists.)
  useFrameCallback((info) => {
    'worklet';
    const r = run.value;
    if (r.elapsed < 0 && lean.value.every((n) => n === 0)) return;
    const dt = Math.min(50, info.timeSincePreviousFrame ?? 16);
    let speed = 0;
    if (r.elapsed >= 0) {
      const elapsed = r.elapsed + dt;
      const dur = PAN_MS + 250 * (r.steps - 1);
      const t = Math.min(1, Math.max(0, (elapsed - PAN_DELAY_MS) / dur));
      camera.value = r.from - r.dir * NEAR_TRAVEL * r.steps * easeInOutCubic(t);
      if (elapsed > PAN_DELAY_MS && t < 1) speed = (-r.dir * easeInOutCubicSlope(t)) / 3;
      run.value = { ...r, elapsed: t >= 1 ? -1 : elapsed };
    }
    // Damped spring per layer toward a lean set by the camera's speed:
    // the field slides one way, the tips trail the other.
    const next = lean.value.slice();
    const steps = Math.max(1, Math.ceil(dt / 4));
    const h = dt / 1000 / steps;
    for (let i = 0; i < LEAN_SCALES.length; i++) {
      const target = -speed * LEAN_MAX * LEAN_SCALES[i];
      let x = next[i * 2];
      let v = next[i * 2 + 1];
      for (let n = 0; n < steps; n++) {
        v += (-SPRING_K * (x - target) - SPRING_C * v) * h;
        x += v * h;
      }
      if (Math.abs(x) < 1e-5 && Math.abs(v) < 1e-4 && target === 0) {
        x = 0;
        v = 0;
      }
      next[i * 2] = x;
      next[i * 2 + 1] = v;
    }
    lean.value = next;
  });

  const startPan = useCallback(
    (dir: 1 | -1, steps = 1) => {
      run.value = { elapsed: 0, from: camera.value, dir, steps: Math.max(1, steps) };
    },
    [camera, run],
  );

  // Stable identity, so the background isn't re-created on every render of
  // the screen that owns the pan.
  const pan = useMemo(() => ({ camera, lean, run }), [camera, lean, run]);
  return { pan, startPan };
}
