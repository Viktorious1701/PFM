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
 * - **Web**: Skia runs on CanvasKit, a large WASM build loaded
 *   asynchronously. `WithSkiaWeb`'s `getComponent` takes a dynamic
 *   `import()`, which (like the native `require()` above) only resolves
 *   at call time, not at module-parse time — this matters specifically
 *   because `expo-router` eagerly evaluates every file under `app/` to
 *   build its route table before the app has even started rendering, let
 *   alone before CanvasKit has loaded; a static top-level `import` of the
 *   Skia-dependent file anywhere in that reachable chain would pull Skia's
 *   native bindings into that eager evaluation. `NullscapesSceneLite`
 *   (plain `react-native-svg`, no Skia dependency) is passed as the
 *   `fallback`, so a slow or failed WASM load degrades to the
 *   already-correct SVG illustration instead of a blank box or crash.
 *
 * `low` tier skips all of this — it's `NullscapesSceneLite` directly,
 * unconditionally, on every platform.
 */
import { Platform, type ViewStyle } from 'react-native';
import { WithSkiaWeb } from '@shopify/react-native-skia/lib/module/web';

import { detailTier } from '../../lib/renderTier';
import { NullscapesSceneLite } from './NullscapesSceneLite';
import type { NullscapesSceneRich as NullscapesSceneRichType } from './NullscapesSceneRich';

type Props = { style?: ViewStyle };

export function NullscapesScene({ style }: Props): React.JSX.Element {
  if (detailTier === 'low') {
    return <NullscapesSceneLite style={style} />;
  }

  if (Platform.OS === 'web') {
    return (
      <WithSkiaWeb
        getComponent={() => import('./NullscapesSceneRich')}
        fallback={<NullscapesSceneLite style={style} />}
        componentProps={{ style }}
      />
    );
  }

  // eslint-disable-next-line @typescript-eslint/no-require-imports -- deferred on purpose, see file doc comment
  const { NullscapesSceneRich } = require('./NullscapesSceneRich') as {
    NullscapesSceneRich: typeof NullscapesSceneRichType;
  };
  return <NullscapesSceneRich style={style} />;
}
