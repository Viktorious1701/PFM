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

There is no Android SDK, no `adb`, no emulator (constitution ENV-04). Web is the only run target:

```bash
npx expo start --web --clear     # then open http://localhost:8081 in Windows
```

`testID` renders as `data-testid`, so `src/constants/elementIds.ts` doubles as a selector registry.

**Metro file-watching on `/mnt/d` is unreliable** — the 9p/drvfs mount does not deliver inotify events dependably, and the dev server has silently served stale code for a whole route tree. Always verify against a freshly restarted server, or press `r` in the Metro terminal. Never trust a render you didn't get from a clean start.
