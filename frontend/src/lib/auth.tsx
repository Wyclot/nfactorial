import { createContext, useContext, useEffect, useState, ReactNode, useCallback } from 'react';
import { api, ApiError } from './api';
import { clearTokens, getAccessToken, setTokens } from './tokens';
import type { User } from '../types';

interface AuthState {
  user: User | null;
  loading: boolean;
  signInWithGoogle: (idToken: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .me()
      .then(setUser)
      .catch((e) => {
        if (e instanceof ApiError && e.status === 401) clearTokens();
      })
      .finally(() => setLoading(false));
  }, []);

  const signInWithGoogle = useCallback(async (idToken: string) => {
    const tokens = await api.googleSignIn(idToken);
    setTokens(tokens.access_token, tokens.refresh_token);
    const me = await api.me();
    setUser(me);
  }, []);

  const signOut = useCallback(async () => {
    try {
      await api.logout();
    } catch {}
    clearTokens();
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const me = await api.me();
      setUser(me);
    } catch {}
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, signInWithGoogle, signOut, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
