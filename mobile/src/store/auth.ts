/**
 * Session store.
 *
 * Holds the JWT and the signed-in user, and is the single place that knows how
 * to end a session. Spec AC-04/AC-05 need a caller with a role, so every screen
 * that branches on ADMIN reads it from here.
 *
 * In mock mode this boots pre-authenticated as ADMIN. That is a prototype
 * shortcut: login (SS-US-01) belongs to a different epic and has no backend, and
 * without it the invite screen — the story actually in flight — would be
 * unreachable. Set EXPO_PUBLIC_API_MOCK=0 and the real login flow takes over.
 */
import { createContext, createElement, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { login as loginRequest } from '../api/auth';
import { setTokenProvider, setUnauthenticatedHandler } from '../api/client';
import { MOCK_ADMIN } from '../api/mock';
import type { UserRead } from '../api/types';
import { USE_MOCK_API } from '../config';
import { clearStoredToken, getStoredToken, setStoredToken } from './session-storage';

type AuthState = {
  token: string | null;
  user: UserRead | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserRead | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // The client reads the token through a getter so this module can depend on it
  // without the reverse import (see client.ts).
  useEffect(() => {
    setTokenProvider(() => token);
  }, [token]);

  const signOut = useCallback(async () => {
    setToken(null);
    setUser(null);
    await clearStoredToken();
  }, []);

  // AC-05: a 401 anywhere clears the session rather than failing silently.
  useEffect(() => {
    setUnauthenticatedHandler(() => {
      void signOut();
    });
  }, [signOut]);

  // Boot: rehydrate from storage, or assume the mock ADMIN session.
  useEffect(() => {
    let cancelled = false;

    (async () => {
      const stored = await getStoredToken();
      if (cancelled) return;

      if (stored) {
        setToken(stored);
        setUser(USE_MOCK_API ? MOCK_ADMIN : null);
      } else if (USE_MOCK_API) {
        setToken('mock.jwt.token');
        setUser(MOCK_ADMIN);
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
    setUser(result.user);
    await setStoredToken(result.access_token);
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      token,
      user,
      isLoading,
      isAuthenticated: token !== null,
      isAdmin: user?.role === 'ADMIN',
      signIn,
      signOut,
    }),
    [token, user, isLoading, signIn, signOut],
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
