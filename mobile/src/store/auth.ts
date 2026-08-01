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
 * In mock mode this boots pre-authenticated as ADMIN. That is a prototype
 * shortcut, active only while `EXPO_PUBLIC_API_MOCK=1` — with it unset (the
 * default once the backend is real), the real login flow takes over.
 */
import { createContext, createElement, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { login as loginRequest } from '../api/auth';
import { setTokenProvider, setUnauthenticatedHandler } from '../api/client';
import { MOCK_ADMIN } from '../api/mock';
import type { UserRole } from '../api/types';
import { USE_MOCK_API } from '../config';
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
  // without the reverse import (see client.ts).
  useEffect(() => {
    setTokenProvider(() => token);
  }, [token]);

  const signOut = useCallback(async () => {
    setToken(null);
    setRole(null);
    await clearStoredToken();
    await clearStoredRole();
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
        setRole(USE_MOCK_API ? MOCK_ADMIN.role : ((await getStoredRole()) as UserRole | null));
      } else if (USE_MOCK_API) {
        setToken('mock.jwt.token');
        setRole(MOCK_ADMIN.role);
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
