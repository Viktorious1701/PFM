/**
 * Auth group layout.
 *
 * `Stack` still resolves from the 'expo-router' root in SDK 57 — unlike `Tabs`,
 * which does not. See app/(tabs)/_layout.tsx for that finding.
 */
import { Stack } from 'expo-router';

export default function AuthLayout() {
  return <Stack screenOptions={{ headerShown: false }} />;
}
