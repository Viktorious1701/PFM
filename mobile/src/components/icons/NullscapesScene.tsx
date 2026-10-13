/**
 * "Nullscapes" host component — the one name both existing empty-state
 * call sites already import (`app/(tabs)/wallets/index.tsx`,
 * `app/(tabs)/transactions/index.tsx`), so neither needed to change.
 *
 * Picks the render tier (`src/lib/renderTier.ts`) and, on the `high` tier,
 * the per-platform loading strategy for the Skia-based
 * `NullscapesSceneRich`:
 *
 * - **Native**: a deferred `require()` inside this function body — not a
 *   top-level `import`. Skia is a synchronous native module on iOS/Android
 *   (no async WASM gate), so this is just the standard way to keep a
 *   platform-specific import out of the other platform's static import
 *   graph, with no risk particular to this library.
 * - **Web is forced onto `NullscapesSceneLite` unconditionally**, regardless
 *   of `detailTier`. This is a deliberate, documented workaround, not an
 *   oversight: moving the background to a single persistent mount behind
 *   `<Tabs>` (`app/(tabs)/_layout.tsx`) exposed a reproducible bug where
 *   `NullscapesSceneRich`, loaded via `WithSkiaWeb`'s `React.lazy()` +
 *   `Suspense`, never picks up its own cover-scale transform after the
 *   initial paint — confirmed across four independent mechanisms (a
 *   wrapping `View`'s `onLayout` into `useState`; the same into a Reanimated
 *   shared value; Skia's own purpose-built `<Canvas onSize>` shared-value
 *   prop; and a `key`-forced full remount with the correct scale baked in as
 *   plain numbers on the FIRST and only commit of a fresh instance) — all
 *   four produced byte-identical, still-unscaled output. No matching
 *   upstream issue was found for `@shopify/react-native-skia` (checked
 *   2.6.2's tracker). `NullscapesSceneLite` has never exhibited this bug on
 *   any mount — it needs no custom sizing math at all, since
 *   `preserveAspectRatio="xMidYMid slice"` on its `<Svg>` does true
 *   cover-scaling natively in the browser. This only affects web: native
 *   iOS/Android loads `NullscapesSceneRich` via a synchronous `require()`
 *   below, an entirely different, non-Suspense code path, where this bug is
 *   not expected to apply (not yet verified on-device — flag if it recurs
 *   there too). Revisit this web restriction if the underlying Skia/web
 *   issue is ever root-caused or fixed upstream.
 *
 * `low` tier skips all of this — it's `NullscapesSceneLite` directly,
 * unconditionally, on every platform (this was already true before the web
 * restriction above; now web gets `NullscapesSceneLite` either way).
 */
import { Platform, type ViewStyle } from 'react-native';
import type { SharedValue } from 'react-native-reanimated';

import { detailTier } from '../../lib/renderTier';
import { NullscapesSceneLite } from './NullscapesSceneLite';
import type { NullscapesSceneRich as NullscapesSceneRichType } from './NullscapesSceneRich';

type Props = {
  style?: ViewStyle;
  /** The cross-tab "camera zoom" driver from `src/lib/tabCameraScale.ts` —
   * omitted for the handful of call sites (if any remain) that don't sit
   * behind the Tabs navigator. Each scene file defaults to its own
   * `useSharedValue(1)` when this is absent. */
  tabScale?: SharedValue<number>;
};

export function NullscapesScene({ style, tabScale }: Props): React.JSX.Element {
  if (detailTier === 'low' || Platform.OS === 'web') {
    return <NullscapesSceneLite style={style} tabScale={tabScale} />;
  }

  // eslint-disable-next-line @typescript-eslint/no-require-imports -- deferred on purpose, see file doc comment
  const { NullscapesSceneRich } = require('./NullscapesSceneRich') as {
    NullscapesSceneRich: typeof NullscapesSceneRichType;
  };
  return <NullscapesSceneRich style={style} tabScale={tabScale} />;
}
