/**
 * Token storage, split by platform.
 *
 * SDS §4.3.1 specifies `expo-secure-store` for "hardware-encrypted JWT storage".
 * That module has no web implementation — calling it in a browser throws. Since
 * the prototype's only run target is Expo web (constitution ENV-04: no Android
 * SDK, no emulator in this environment), web falls back to `localStorage`.
 *
 * `localStorage` is NOT equivalent: it is readable by any script on the origin
 * and is not hardware-backed. That is acceptable for a local dev surface and
 * unacceptable for a shipping web target. Recorded as a deviation in ADR-0009.
 *
 * The native branch is kept correct even though only web is exercised, so the
 * native round does not start from a web-shaped compromise.
 */
import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

const TOKEN_KEY = 'pfm.access_token';
// The role travels with the token so a rehydrated session knows ADMIN vs USER
// without decoding the JWT client-side — SS-US-01's TokenResponse carries no
// other identity field to persist (see store/auth.ts).
const ROLE_KEY = 'pfm.role';

const isWeb = Platform.OS === 'web';

export async function getStoredToken(): Promise<string | null> {
  try {
    if (isWeb) {
      return globalThis.localStorage?.getItem(TOKEN_KEY) ?? null;
    }
    return await SecureStore.getItemAsync(TOKEN_KEY);
  } catch {
    // A read failure must not brick app boot — treat it as "no session".
    return null;
  }
}

export async function setStoredToken(token: string): Promise<void> {
  if (isWeb) {
    globalThis.localStorage?.setItem(TOKEN_KEY, token);
    return;
  }
  await SecureStore.setItemAsync(TOKEN_KEY, token);
}

export async function clearStoredToken(): Promise<void> {
  if (isWeb) {
    globalThis.localStorage?.removeItem(TOKEN_KEY);
    return;
  }
  await SecureStore.deleteItemAsync(TOKEN_KEY);
}

export async function getStoredRole(): Promise<string | null> {
  try {
    if (isWeb) {
      return globalThis.localStorage?.getItem(ROLE_KEY) ?? null;
    }
    return await SecureStore.getItemAsync(ROLE_KEY);
  } catch {
    return null;
  }
}

export async function setStoredRole(role: string): Promise<void> {
  if (isWeb) {
    globalThis.localStorage?.setItem(ROLE_KEY, role);
    return;
  }
  await SecureStore.setItemAsync(ROLE_KEY, role);
}

export async function clearStoredRole(): Promise<void> {
  if (isWeb) {
    globalThis.localStorage?.removeItem(ROLE_KEY);
    return;
  }
  await SecureStore.deleteItemAsync(ROLE_KEY);
}
