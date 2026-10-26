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

// ---------------------------------------------------------------------------
// Guest trial (SS-US-03 plan.md A17) — same platform split as above.
// ---------------------------------------------------------------------------

// The active session's trial end, beside its token and role, so a reloaded
// guest session still knows when its trial ends (spec AC-14).
const TRIAL_ENDS_KEY = 'pfm.trial_ends_at';
// The device's one saved guest trial: kept through sign-out (AC-15) and a
// member's sign-in (AC-20), replaced when a new trial starts (AC-19).
const SAVED_TRIAL_TOKEN_KEY = 'pfm.guest_trial.token';
const SAVED_TRIAL_ENDS_KEY = 'pfm.guest_trial.expires_at';

export type SavedGuestTrial = { token: string; expiresAt: string };

async function readKey(key: string): Promise<string | null> {
  try {
    if (isWeb) return globalThis.localStorage?.getItem(key) ?? null;
    return await SecureStore.getItemAsync(key);
  } catch {
    return null;
  }
}

async function writeKey(key: string, value: string): Promise<void> {
  if (isWeb) {
    globalThis.localStorage?.setItem(key, value);
    return;
  }
  await SecureStore.setItemAsync(key, value);
}

async function removeKey(key: string): Promise<void> {
  if (isWeb) {
    globalThis.localStorage?.removeItem(key);
    return;
  }
  await SecureStore.deleteItemAsync(key);
}

export const getStoredTrialEnd = () => readKey(TRIAL_ENDS_KEY);
export const setStoredTrialEnd = (expiresAt: string) => writeKey(TRIAL_ENDS_KEY, expiresAt);
export const clearStoredTrialEnd = () => removeKey(TRIAL_ENDS_KEY);

export async function getSavedGuestTrial(): Promise<SavedGuestTrial | null> {
  const token = await readKey(SAVED_TRIAL_TOKEN_KEY);
  const expiresAt = await readKey(SAVED_TRIAL_ENDS_KEY);
  return token && expiresAt ? { token, expiresAt } : null;
}

export async function setSavedGuestTrial(trial: SavedGuestTrial): Promise<void> {
  await writeKey(SAVED_TRIAL_TOKEN_KEY, trial.token);
  await writeKey(SAVED_TRIAL_ENDS_KEY, trial.expiresAt);
}

export async function clearSavedGuestTrial(): Promise<void> {
  await removeKey(SAVED_TRIAL_TOKEN_KEY);
  await removeKey(SAVED_TRIAL_ENDS_KEY);
}
