/**
 * Root layout.
 *
 * Governs: SDS §4.3.1 (Expo Router navigation, expo-secure-store JWT storage).
 *
 * There is still no auth redirect here, though SS-US-01 (login) is now real —
 * this remains a deliberate scope boundary, not an oversight. Screens read a
 * role from `useAuth()` for spec AC-04/AC-05 (invite is ADMIN-only), but
 * nothing routes an unauthenticated caller to `/login` automatically; a
 * signed-out visitor can still browse and gets a 401 from the API instead.
 * Adding a redirect guard is a separate decision, not yet made.
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

SplashScreen.preventAutoHideAsync().catch(() => {
  // Already hidden or unsupported on this platform (e.g. web) — not fatal.
});

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
      </AuthProvider>
    </SafeAreaProvider>
  );
}
