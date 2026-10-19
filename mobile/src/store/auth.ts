/**
 * Session store.
 *
 * Holds the JWT and the caller's role, and is the single place that knows how
 * to end a session. Spec AC-04/AC-05 need a caller with a role, so every screen
 * that branches on ADMIN reads it from here. There is no full `UserRead` here
 * — SS-US-01's `TokenResponse` carries only the token, its expiry, and the
 * role (see `api/types.ts`'s `LoginResponse`); a profile is UM-US-04's
 * concern, out of MVP scope, so nothing here can invent one.
 */
import { createContext, createElement, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';

import { login as loginRequest, logout as logoutRequest } from '../api/auth';
import { setTokenProvider, setUnauthenticatedHandler } from '../api/client';
import type { UserRole } from '../api/types';
import { clearStoredToken, getStoredRole, getStoredToken, setStoredRole, clearStoredRole, setStoredToken } from './session-storage';

type AuthState = {
  token: string | null;
  role: UserRole | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<UserRole | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // The client reads the token through a getter so this module can depend on it
  // without the reverse import (see client.ts). The getter reads a ref kept
  // current during render, not a value pushed in an effect: children's
  // effects run before this provider's, so a screen that fetches on mount
  // right after sign-in would otherwise send its first request with no token.
  const tokenRef = useRef<string | null>(null);
  tokenRef.current = token;
  useState(() => setTokenProvider(() => tokenRef.current));

  const signingOut = useRef(false);
  const endSession = useCallback(async (notifyServer: boolean) => {
    if (signingOut.current) return;
    signingOut.current = true;
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
    await clearStoredToken();
    await clearStoredRole();
    signingOut.current = false;
  }, []);
  const signOut = useCallback(() => endSession(true), [endSession]);

  // AC-05: a 401 anywhere clears the session rather than failing silently.
  useEffect(() => {
    setUnauthenticatedHandler(() => {
      void endSession(false);
    });
  }, [endSession]);

  // Boot: rehydrate the session from storage.
  useEffect(() => {
    let cancelled = false;

    (async () => {
      const stored = await getStoredToken();
      if (cancelled) return;

      if (stored) {
        setToken(stored);
        setRole((await getStoredRole()) as UserRole | null);
      }
      setIsLoading(false);
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const result = await loginRequest(email, password);
    setToken(result.access_token);
    setRole(result.role);
    await setStoredToken(result.access_token);
    await setStoredRole(result.role);
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      token,
      role,
      isLoading,
      isAuthenticated: token !== null,
      isAdmin: role === 'ADMIN',
      signIn,
      signOut,
    }),
    [token, role, isLoading, signIn, signOut],
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
