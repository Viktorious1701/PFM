/**
 * Root layout.
 *
 * Governs: SDS §4.3.1 (Expo Router navigation, expo-secure-store JWT storage).
 *
 * There is deliberately no auth redirect here. Route protection depends on a
 * real session, and login (SS-US-01) has neither a spec nor a backend endpoint
 * yet — guarding routes now would be guesswork against an unbuilt API. The
 * session is provided so screens can read a role for spec AC-04/AC-05, but the
 * router does not enforce it. That arrives with SS-US-01.
 */
import { Stack } from 'expo-router';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { AuthProvider } from '../src/store/auth';

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <Stack screenOptions={{ headerTitleStyle: { fontWeight: '600' } }}>
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
