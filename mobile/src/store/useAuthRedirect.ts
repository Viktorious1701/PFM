/**
 * Auth-redirect guard.
 *
 * `useSegments()` returns the RAW, un-normalised route-name segments — group
 * folders keep their parentheses (e.g. `"(auth)"`, `"(tabs)"`). Confirmed
 * directly against `node_modules/expo-router/build/global-state/
 * getRouteInfoFromState.js`: the paren-stripping normalisation there only
 * ever applies to the computed `pathname`, never to the `segments` array
 * itself, which is returned as-is from the matched route names. So
 * `segments[0] === '(auth)'` is a correct, real check, not an assumption —
 * matching the exact literal `'/(auth)/login'` path `users/invite.tsx`
 * already redirects to on a 401.
 *
 * Both `useRouter` and `useSegments` are real root exports of `expo-router`
 * (confirmed the same way — `exports.js` re-exports both from `./hooks`),
 * unlike `Tabs`, which this codebase already knows must come from
 * `expo-router/js-tabs` instead.
 *
 * **Real bug found and fixed**: a live verification pass found that
 * reloading or deep-linking into any tab route (not just one screen) bounced
 * to `/login` even with a valid stored session, and stayed there — not a
 * transient flicker but a permanent strand, because nothing ever routes an
 * authenticated caller *away* from `/login` once the redirect has already
 * fired once. Root cause: on a fresh navigation, the router can render one
 * or more passes before it has resolved its *actual* initial route (the
 * deep-linked one) — gating on `useAuth()`'s `isLoading` alone says nothing
 * about whether the *router itself* has settled yet, so this effect could
 * see `isLoading === false` (auth already rehydrated) while `segments` still
 * reflected a transient, not-yet-resolved state, misfire the redirect once,
 * and there is no recovery from a single incorrect `router.replace()`.
 * `useRootNavigationState()?.key` is Expo Router's own documented signal for
 * "the root navigator has finished resolving its initial state, including
 * any deep link" (`node_modules/expo-router/build/hooks/
 * useRootNavigationState.js` — returns the underlying React Navigation
 * `NavigationState`, whose `key` is unset until that resolution completes).
 * Gating on it here closes the race at its source instead of guessing at a
 * delay.
 */
import { useRootNavigationState, useRouter, useSegments } from 'expo-router';
import { useEffect } from 'react';

import { useAuth } from './auth';

export function useAuthRedirect(): void {
  const { isAuthenticated, isLoading } = useAuth();
  const segments = useSegments();
  const router = useRouter();
  const rootNavigationState = useRootNavigationState();

  useEffect(() => {
    // Wait for storage rehydration (store/auth.ts's boot effect) — otherwise
    // every cold boot would flash the login screen before a stored token
    // has a chance to load. Mock mode never reaches this branch: useAuth()
    // auto-boots authenticated there, so isAuthenticated is already true.
    if (isLoading) return;

    // Wait for the router itself to have resolved its real initial route
    // (including a deep link) — see the doc comment above for the exact bug
    // this closes. Without `.key`, this effect can fire against a route the
    // router hasn't actually settled on yet.
    if (!rootNavigationState?.key) return;

    const inAuthGroup = segments[0] === '(auth)';
    // Reached from an emailed link, pre-login (UM-US-02) — must stay
    // reachable while signed out, so it is excluded the same way the
    // `(auth)` group itself is.
    const onActivateScreen = segments[0] === 'activate';

    if (!isAuthenticated && !inAuthGroup && !onActivateScreen) {
      router.replace('/(auth)/login');
    }
  }, [isAuthenticated, isLoading, segments, router, rootNavigationState?.key]);
}
