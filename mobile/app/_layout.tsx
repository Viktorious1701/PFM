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
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useEffect } from 'react';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { color, font } from '../src/theme/tokens';
import { AuthProvider } from '../src/store/auth';
import { useAuthRedirect } from '../src/store/useAuthRedirect';

SplashScreen.preventAutoHideAsync().catch(() => {
  // Already hidden or unsupported on this platform (e.g. web) — not fatal.
});

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
      <AuthProvider>
        <RootNavigator />
      </AuthProvider>
    </SafeAreaProvider>
  );
}
