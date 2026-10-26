/**
 * Session store.
 *
 * Holds the JWT and the caller's role, and is the single place that knows how
 * to end a session. Spec AC-04/AC-05 need a caller with a role, so every screen
 * that branches on ADMIN reads it from here. There is no full `UserRead` here
 * — SS-US-01's `TokenResponse` carries only the token, its expiry, and the
 * role (see `api/types.ts`'s `LoginResponse`); a profile is UM-US-04's
 * concern, out of MVP scope, so nothing here can invent one.
 *
 * SS-US-03 (guest trial) adds two things, both device-side (plan.md A15, A17,
 * A18): the active session's trial end, and the device's one *saved* guest
 * trial — written when a trial starts, kept through sign-out and through a
 * member's sign-in, and dropped once it has ended by the device's clock or the
 * server refuses it. The server keeps nothing about it.
 */
import { createContext, createElement, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';

import { confirmGuestSession, guestLogin, login as loginRequest, logout as logoutRequest } from '../api/auth';
import { setTokenProvider, setUnauthenticatedHandler } from '../api/client';
import { toApiError } from '../api/errors';
import type { UserRole } from '../api/types';
import {
  clearSavedGuestTrial,
  clearStoredRole,
  clearStoredToken,
  clearStoredTrialEnd,
  getSavedGuestTrial,
  getStoredRole,
  getStoredToken,
  getStoredTrialEnd,
  setSavedGuestTrial,
  setStoredRole,
  setStoredToken,
  setStoredTrialEnd,
  type SavedGuestTrial,
} from './session-storage';

export type { SavedGuestTrial } from './session-storage';

/** Whether a trial end (ISO instant) has passed by this device's clock. */
export function trialHasEnded(expiresAt: string, now = Date.now()): boolean {
  const end = Date.parse(expiresAt);
  return Number.isNaN(end) || end <= now;
}

const DAY_MS = 24 * 60 * 60 * 1000;

/** SS-US-03 plan.md A19 / EC-07: whole days left, rounded down, and never
 * below 1 while the trial has not ended — 6 days 23 hours reads 6, five hours
 * reads 1. */
export function trialDaysLeft(expiresAt: string, now = Date.now()): number {
  return Math.max(1, Math.floor((Date.parse(expiresAt) - now) / DAY_MS));
}

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

/** SS-US-03 AC-14: the day the trial ends, on this device's calendar —
 * e.g. "2 November 2026". Spelled out rather than locale-formatted so it reads
 * the same on every phone. */
export function formatTrialEnd(expiresAt: string): string {
  const d = new Date(expiresAt);
  return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
}

type AuthState = {
  token: string | null;
  role: UserRole | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  /** SS-US-03: signed in as a guest trial. */
  isGuest: boolean;
  /** SS-US-03: when the signed-in guest's trial ends (ISO instant), else null. */
  trialEndsAt: string | null;
  /** SS-US-03: the device's saved guest trial, if any (may have ended — see
   * `forgetEndedGuestTrial`). */
  savedGuestTrial: SavedGuestTrial | null;
  /** SS-US-03 AC-18 / EC-12: the server refused a guest trial — the sign-in
   * screen says "Your guest trial has ended." until someone signs in. */
  guestTrialEnded: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  /** SS-US-03 AC-01, AC-19: starts a brand-new trial and makes it the
   * device's saved trial, replacing any earlier one. */
  signInAsGuest: () => Promise<void>;
  /** SS-US-03 AC-16, AC-18: continues the saved trial once the server
   * confirms it is still live. */
  continueGuestTrial: () => Promise<void>;
  /** SS-US-03 AC-17: drops a saved trial that has ended by the device's
   * clock — no request, no message. */
  forgetEndedGuestTrial: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<UserRole | null>(null);
  const [trialEndsAt, setTrialEndsAt] = useState<string | null>(null);
  const [savedGuestTrial, setSavedTrial] = useState<SavedGuestTrial | null>(null);
  const [guestTrialEnded, setGuestTrialEnded] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // The client reads the token through a getter so this module can depend on it
  // without the reverse import (see client.ts). The getter reads a ref kept
  // current during render, not a value pushed in an effect: children's
  // effects run before this provider's, so a screen that fetches on mount
  // right after sign-in would otherwise send its first request with no token.
  const tokenRef = useRef<string | null>(null);
  tokenRef.current = token;
  useState(() => setTokenProvider(() => tokenRef.current));
  const roleRef = useRef<UserRole | null>(null);
  roleRef.current = role;

  /** Makes `next` the active session, in memory and on the device. */
  const activate = useCallback(async (next: { token: string; role: UserRole; trialEndsAt: string | null }) => {
    // The ref first, so a screen fetching on mount sends the new token.
    tokenRef.current = next.token;
    setToken(next.token);
    setRole(next.role);
    setTrialEndsAt(next.trialEndsAt);
    setGuestTrialEnded(false);
    await setStoredToken(next.token);
    await setStoredRole(next.role);
    if (next.trialEndsAt) await setStoredTrialEnd(next.trialEndsAt);
    else await clearStoredTrialEnd();
  }, []);

  const dropSavedTrial = useCallback(async () => {
    setSavedTrial(null);
    await clearSavedGuestTrial();
  }, []);

  const signingOut = useRef(false);
  const endSession = useCallback(async (notifyServer: boolean) => {
    if (signingOut.current) return;
    signingOut.current = true;
    const wasGuest = roleRef.current === 'GUEST';
    // Tell the server first, while the token is still attached; never let
    // a failure here keep anyone signed in. Skipped when the server has
    // just rejected the token (a 401) — that would only 401 again.
    if (notifyServer && tokenRef.current) {
      try {
        await logoutRequest();
      } catch {
        // offline, or the token had already expired — sign out locally anyway
      }
    }
    setToken(null);
    setRole(null);
    setTrialEndsAt(null);
    await clearStoredToken();
    await clearStoredRole();
    await clearStoredTrialEnd();
    // SS-US-03: signing out keeps the saved trial (AC-15, EC-11). Only the
    // server refusing a guest's session drops it, with the ended message
    // (EC-12) — the trial has ended or been deleted.
    if (!notifyServer && wasGuest) {
      await dropSavedTrial();
      setGuestTrialEnded(true);
    }
    signingOut.current = false;
  }, [dropSavedTrial]);
  const signOut = useCallback(() => endSession(true), [endSession]);

  // AC-05: a 401 anywhere clears the session rather than failing silently.
  useEffect(() => {
    setUnauthenticatedHandler(() => {
      void endSession(false);
    });
  }, [endSession]);

  // Boot: rehydrate the session, and the saved guest trial, from storage.
  useEffect(() => {
    let cancelled = false;

    (async () => {
      const stored = await getStoredToken();
      const saved = await getSavedGuestTrial();
      if (cancelled) return;

      if (stored) {
        setToken(stored);
        setRole((await getStoredRole()) as UserRole | null);
        setTrialEndsAt(await getStoredTrialEnd());
      }
      setSavedTrial(saved);
      setIsLoading(false);
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = useCallback(
    async (email: string, password: string) => {
      const result = await loginRequest(email, password);
      // SS-US-03 AC-20: a member's sign-in leaves the saved trial alone.
      await activate({ token: result.access_token, role: result.role, trialEndsAt: null });
    },
    [activate],
  );

  const signInAsGuest = useCallback(async () => {
    const result = await guestLogin();
    // BR-08 / AC-19: the newest trial is the device's one saved trial,
    // written now rather than at sign-out (plan.md A17).
    const trial = { token: result.access_token, expiresAt: result.expires_at };
    await setSavedGuestTrial(trial);
    setSavedTrial(trial);
    await activate({ token: result.access_token, role: 'GUEST', trialEndsAt: result.expires_at });
  }, [activate]);

  const continueGuestTrial = useCallback(async () => {
    const trial = savedGuestTrial ?? (await getSavedGuestTrial());
    if (!trial) return;
    try {
      await confirmGuestSession(trial.token);
    } catch (e) {
      // AC-18: the server no longer accepts it — ended or deleted. Anything
      // else (offline, 5xx) says nothing about the trial: keep it, and let
      // the caller show the error.
      if (toApiError(e).isUnauthenticated) {
        await dropSavedTrial();
        setGuestTrialEnded(true);
        return;
      }
      throw e;
    }
    await activate({ token: trial.token, role: 'GUEST', trialEndsAt: trial.expiresAt });
  }, [savedGuestTrial, activate, dropSavedTrial]);

  const forgetEndedGuestTrial = useCallback(async () => {
    if (savedGuestTrial && trialHasEnded(savedGuestTrial.expiresAt)) await dropSavedTrial();
  }, [savedGuestTrial, dropSavedTrial]);

  const value = useMemo<AuthState>(
    () => ({
      token,
      role,
      isLoading,
      isAuthenticated: token !== null,
      isAdmin: role === 'ADMIN',
      isGuest: role === 'GUEST',
      trialEndsAt,
      savedGuestTrial,
      guestTrialEnded,
      signIn,
      signOut,
      signInAsGuest,
      continueGuestTrial,
      forgetEndedGuestTrial,
    }),
    [token, role, isLoading, trialEndsAt, savedGuestTrial, guestTrialEnded, signIn, signOut, signInAsGuest, continueGuestTrial, forgetEndedGuestTrial],
  );

  return createElement(AuthContext.Provider, { value }, children);
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside <AuthProvider>. Check app/_layout.tsx.');
  }
  return ctx;
}
