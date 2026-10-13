/**
 * Drives the Nullscapes background's "camera zoom" as the user moves
 * between tabs — the zoom-traversal concept recovered from an earlier,
 * never-built design pass (5 `.dc.html` mockups): the background scales up
 * by a fixed step per tab, reading as "we flew one step further into the
 * grass" on each arrival.
 *
 * `tabNearScale` is a module-level Reanimated mutable, not React state or
 * Context — there is exactly one Nullscapes background and exactly one
 * Tabs navigator for the life of the app, so a singleton the scene files
 * read directly (via a prop, see `NullscapesScene.tsx`) is the simplest
 * true source of truth, with zero Provider wrapping and zero React
 * re-renders anywhere in this path (the zoom runs entirely on the UI
 * thread). `TabCameraSync` is the one place that WRITES to it, kept as its
 * own null-rendering component so `<NullscapesScene>`'s own props never
 * change identity on a tab switch — no reconciliation of its 80-100+
 * element child tree, ever.
 */
import { useEffect, useRef } from 'react';
import { useSegments } from 'expo-router';
import { Easing, makeMutable, useReducedMotion, withTiming, type SharedValue } from 'react-native-reanimated';

/** Linear +0.22 step per tab, per the validated mockups (Main/Tab2-5.dc.html). */
const TAB_NEAR_SCALE: Record<string, number> = {
  index: 1.0,
  transactions: 1.22,
  wallets: 1.44,
  budgets: 1.66,
  users: 1.88,
  // `reports` has no entry in the original 5-screen mockup set — defaults
  // to Dashboard's 1.00x rather than inventing an unvalidated value.
  reports: 1.0,
};

const APPROACH_STEP_BACK = 0.14;
const APPROACH_DURATION_MS = 650;
// cubic-bezier(0.16, 1, 0.3, 1) — the mockups' own "approach" easing.
const APPROACH_EASING = Easing.bezier(0.16, 1, 0.3, 1);

export const tabNearScale: SharedValue<number> = makeMutable(TAB_NEAR_SCALE.index);

/**
 * Mounted once as a sibling of `<Tabs>` in `app/(tabs)/_layout.tsx`. Renders
 * nothing — it only subscribes to route changes and writes `tabNearScale`.
 */
export function TabCameraSync(): null {
  const segments = useSegments();
  const reduceMotion = useReducedMotion();
  const isFirstRun = useRef(true);

  // The first non-route-group segment maps a hidden sub-route (e.g.
  // 'transactions/create', 'wallets/create', 'users/invite') onto its
  // parent tab's zoom for free, with no path-prefix parsing.
  const tabKey = segments.find((segment) => !segment.startsWith('(')) ?? 'index';

  useEffect(() => {
    const target = TAB_NEAR_SCALE[tabKey];
    if (target === undefined) return; // unmapped route — leave the camera where it is

    if (isFirstRun.current) {
      // Don't play the approach animation as an app-boot flourish — land on
      // the correct zoom for whatever tab the app opens on, instantly.
      isFirstRun.current = false;
      tabNearScale.value = target;
      return;
    }

    if (reduceMotion) {
      tabNearScale.value = target;
      return;
    }

    tabNearScale.value = target - APPROACH_STEP_BACK;
    tabNearScale.value = withTiming(target, {
      duration: APPROACH_DURATION_MS,
      easing: APPROACH_EASING,
    });
  }, [tabKey, reduceMotion]);

  return null;
}
