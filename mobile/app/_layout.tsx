/**
 * Root layout — fonts and the session, then the single screen
 * (`app/index.tsx`). No navigator: the scene is the whole app, and the
 * wallet UI is layered over it rather than routed away from it.
 */
import {
  Rajdhani_300Light,
  Rajdhani_400Regular,
  Rajdhani_500Medium,
  Rajdhani_600SemiBold,
  Rajdhani_700Bold,
  useFonts,
} from '@expo-google-fonts/rajdhani';
import { Slot } from 'expo-router';

import { AuthProvider } from '../src/store/auth';

export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts({
    Rajdhani_300Light,
    Rajdhani_400Regular,
    Rajdhani_500Medium,
    Rajdhani_600SemiBold,
    Rajdhani_700Bold,
  });

  // A font that fails to load falls back to the system face rather than
  // holding the app on a blank screen.
  if (!fontsLoaded && !fontError) return null;

  return (
    <AuthProvider>
      <Slot />
    </AuthProvider>
  );
}
