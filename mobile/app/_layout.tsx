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
 * Fonts hold the splash screen until Lora + Inter are ready — DESIGN.md
 * forbids a heading rendering in the system font even for one frame, since the
 * two families never swap roles.
 */
import { Inter_400Regular, Inter_500Medium } from '@expo-google-fonts/inter';
import { Lora_600SemiBold, Lora_700Bold } from '@expo-google-fonts/lora';
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useEffect } from 'react';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { color } from '../src/theme/tokens';
import { AuthProvider } from '../src/store/auth';

SplashScreen.preventAutoHideAsync().catch(() => {
  // Already hidden or unsupported on this platform (e.g. web) — not fatal.
});

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    Lora_700Bold,
    Lora_600SemiBold,
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
            headerTitleStyle: { fontFamily: 'Lora_600SemiBold', fontSize: 18 },
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
