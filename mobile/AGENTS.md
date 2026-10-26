# Expo HAS CHANGED

Read the exact versioned docs at https://docs.expo.dev/versions/v57.0.0/ before writing any code.

**And then don't trust them.** The findings below each cost real debugging time on SDK 57.

## Navigators moved to subpaths — the root `Tabs` export is broken

`import { Tabs } from 'expo-router'` **resolves to `undefined` at runtime** and crashes the layout with *"Element type is invalid … got: undefined"*. Use:

```tsx
import { Tabs } from 'expo-router/js-tabs';   // NOT from 'expo-router'
```

The installed package says so itself:

```js
// node_modules/expo-router/build/exports.js:111
/** @deprecated Use `import { Tabs } from 'expo-router/js-tabs'` instead. */
```

Navigators live at `js-tabs`, `js-stack`, `js-top-tabs`, `tabs`, `stack`, `unstable-native-tabs`, `ui`. `Stack` still resolves from the root. `href: null` for hiding a route from the tab bar still works — `build/layouts/TabsClient.js` implements it directly.

Two rules follow:

1. **`node_modules/expo-router/build/` is the authority, not `docs.expo.dev`.** Both `/versions/v57.0.0/sdk/router/` and the Tabs guide still show the old root import. The docs are stale for 57.
2. **`tsc` cannot catch this class of bug.** `npm run typecheck` exits 0 while the app crashes, because the *type* export survives even when the runtime value does not. **A rendered page is the gate, not a green typecheck.**

## `expo-secure-store` has no web implementation

SDS §4.3.1 specifies it for "hardware-encrypted JWT storage", but it throws in a browser. `src/store/session-storage.ts` splits by platform: `localStorage` on web, `SecureStore` on native.

`localStorage` is **not** equivalent — not hardware-backed, readable by any script on the origin. Fine for the dev surface; **not acceptable if web ever becomes a delivery target.** Revisit as its own decision if that changes.

## Verifying UI changes here

There is no Android SDK, no `adb`, no emulator here (constitution ENV-04). Android is the primary target, but it is built in the EAS cloud and checked by hand on a real phone (ENV-05); everything that *can* be verified is verified on web first:

```bash
npx expo start --web --clear     # then open http://localhost:8081 in Windows
```

`testID` renders as `data-testid`, so `src/constants/elementIds.ts` doubles as a selector registry.

**Metro file-watching on `/mnt/d` is unreliable** — the 9p/drvfs mount does not deliver inotify events dependably, and the dev server has silently served stale code for a whole route tree. Always verify against a freshly restarted server, or press `r` in the Metro terminal. Never trust a render you didn't get from a clean start.

## The background on Android is the web engine in a WebView — not Skia

`src/scene/sequenceEngine.ts` is immediate-mode: every frame it repaints thousands of small shapes
through the canvas 2D API. Ported to `@shopify/react-native-skia` through a canvas shim, it ran at
**~12 fps on a high-end phone** (60–85 ms per frame) — and lowering the drawing resolution did not
help, because pixels were never the cost. Counted with Skia's headless build, a frame made
**~5,000 (moon) to ~15,000 (mountains) calls into Skia** before even counting draw and path calls;
each one crosses the JS→native (JSI) bridge, at a few µs apiece. The same engine in the phone's
Chrome played smoothly, since browser canvas calls never cross a bridge.

So `NullscapesBackground.native.tsx` runs the engine in a `react-native-webview`, from
`src/scene/sceneHtml.generated.ts` — a self-contained page (engine transpiled, Cormorant embedded,
a small clock host) built by `scripts/build-scene-html.mjs`. **After any engine edit, run
`npm run scene:html`**; `npm run typecheck` fails while the page is stale. The app only sends
`__sync({t, playing, cam, shear, mode})`; the page keeps its own clock between syncs and posts its
frame rate, which `__DEV__` builds log to Metro as `[scene] {"fps":…}`.

Don't port immediate-mode canvas code to Skia call-for-call. Skia on React Native pays per call;
it suits retained scenes (a few big paths, pictures, shaders), not thousands of tiny fills a frame.

