/**
 * Root layout.
 *
 * Governs: SDS §4.3.1 (Expo Router navigation, expo-secure-store JWT storage).
 *
 * A `useAuthRedirect()` guard now runs inside `RootNavigator` (below),
 * bouncing an unauthenticated caller to `/(auth)/login` once auth has
 * finished hydrating — except inside the `(auth)` group itself and on
 * `/activate` (reached from an emailed link, pre-login), both of which must
 * stay reachable while signed out. See `src/store/useAuthRedirect.ts` for
 * the full rationale. The hook is called from `RootNavigator`, a component
 * nested *inside* `<AuthProvider>`, rather than from `RootLayout` itself,
 * because it needs `useAuth()`, which only works below the provider.
 *
 * Fonts hold the splash screen until Courier Prime + PT Serif are ready —
 * DESIGN.md forbids a heading rendering in the system font even for one
 * frame, since the two families never swap roles.
 */
import {
  CourierPrime_400Regular,
  CourierPrime_700Bold,
} from '@expo-google-fonts/courier-prime';
import { Inter_400Regular, Inter_500Medium } from '@expo-google-fonts/inter';
import {
  PTSerif_400Regular,
  PTSerif_400Regular_Italic,
  PTSerif_700Bold,
} from '@expo-google-fonts/pt-serif';
import {
  SpaceGrotesk_400Regular,
  SpaceGrotesk_500Medium,
  SpaceGrotesk_600SemiBold,
  SpaceGrotesk_700Bold,
} from '@expo-google-fonts/space-grotesk';
import { useFonts } from 'expo-font';
import { DefaultTheme, Stack, ThemeProvider } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useEffect } from 'react';
import { enableScreens } from 'react-native-screens';
import { SafeAreaProvider } from 'react-native-safe-area-context';

// Never called anywhere in this project before — `expo-router`'s own bottom-tabs
// types doc-comment says to ("Make sure to call `enableScreens`..."). Without
// it, `Screens.screensEnabled()` stays false, so the Tabs navigator's
// `MaybeScreen` (`expo-router/build/react-navigation/bottom-tabs/views/
// ScreenFallback.js`) always falls back to a bare `View` with NO inactive-tab
// hiding logic at all — `react-native-screens`'s own web `Screen` component
// (`Screen.web.tsx`) only sets `display:'none'` on an inactive screen when
// `enabled` is true, which requires this call. This went unnoticed until the
// Tabs group's per-screen background was made transparent (`transparentNavTheme`
// below) — every inactive tab's content was always being fully mounted and
// stacked, just invisibly, masked by each screen's own opaque default fill.
enableScreens();

import { color, font } from '../src/theme/tokens';
import { AuthProvider } from '../src/store/auth';
import { useAuthRedirect } from '../src/store/useAuthRedirect';

SplashScreen.preventAutoHideAsync().catch(() => {
  // Already hidden or unsupported on this platform (e.g. web) — not fatal.
});

/**
 * React Navigation's own `DefaultTheme.colors.background` is `rgb(242, 242,
 * 242)` — an opaque, full-screen fill every navigator (`Stack`, `Tabs`)
 * paints automatically behind each screen's content (`Background.js`'s
 * `<Animated.View style={{flex:1, backgroundColor: colors.background}}>`),
 * independent of anything `Screen.tsx` does. This sat BETWEEN the shared
 * Nullscapes background (mounted behind `<Tabs>`, `app/(tabs)/_layout.tsx`)
 * and every tab screen's own transparent content, fully blocking it — found
 * only after ruling out the Skia/SVG scene rendering itself (both were
 * confirmed correctly sized and painting; this opaque layer was simply
 * covering them). Login/activate (`background="opaque"` in `Screen.tsx`)
 * already paint their own full `color.bg` fill on top of this layer, so
 * making it transparent here doesn't change their appearance.
 */
const transparentNavTheme = {
  ...DefaultTheme,
  colors: { ...DefaultTheme.colors, background: 'transparent' },
};

/**
 * The actual navigator tree, split out so `useAuthRedirect()` can run inside
 * `<AuthProvider>` (it calls `useAuth()`) while `RootLayout` itself stays
 * the one place that gates on font loading.
 */
function RootNavigator() {
  useAuthRedirect();

  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: color.surface },
        headerTintColor: color.text,
        headerTitleStyle: { fontFamily: font.family.headingSemibold, fontSize: 18 },
      }}
    >
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen name="(auth)" options={{ headerShown: false }} />
      <Stack.Screen
        name="activate"
        options={{
          title: 'Activate Account',
          headerBackTitle: 'Back',
        }}
      />
    </Stack>
  );
}

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    CourierPrime_700Bold,
    CourierPrime_400Regular,
    PTSerif_400Regular,
    PTSerif_700Bold,
    PTSerif_400Regular_Italic,
    // Inter is no longer used by any token or literal in this app (PT Serif
    // took over its role — see tokens.ts) but is left installed and loaded
    // here since only Lora's removal was asked for; see the handback report.
    Inter_400Regular,
    Inter_500Medium,
    // Nullscapes component language — used across the Tabs group now,
    // never by the two screens outside it (sign-in, activation).
    SpaceGrotesk_400Regular,
    SpaceGrotesk_500Medium,
    SpaceGrotesk_600SemiBold,
    SpaceGrotesk_700Bold,
  });

  useEffect(() => {
    if (fontsLoaded) {
      SplashScreen.hideAsync().catch(() => undefined);
    }
  }, [fontsLoaded]);

  if (!fontsLoaded) {
    return null;
  }

  return (
    <SafeAreaProvider>
      <ThemeProvider value={transparentNavTheme}>
        <AuthProvider>
          <RootNavigator />
        </AuthProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
