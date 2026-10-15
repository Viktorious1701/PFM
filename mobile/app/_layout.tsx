/**
 * Root layout — deliberately bare. The app has been scratched down to a
 * single fullscreen scene (`app/index.tsx`); no auth, tabs, fonts or
 * redirects, so nothing can route away from it or paint over it.
 */
import { Slot } from 'expo-router';

export default function RootLayout() {
  return <Slot />;
}
