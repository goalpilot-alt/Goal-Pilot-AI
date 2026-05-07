import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { api, setToken, clearToken, getToken } from './api';
import { i18n } from './i18n';

type User = { id: string; email: string; name: string; plan: string; locale?: string } | null;

type AuthState = {
  user: User;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  deleteAccount: () => Promise<void>;
};

const Ctx = createContext<AuthState | null>(null);

async function syncLocaleToBackend() {
  try { await api.post('/auth/locale', { locale: i18n.locale }); } catch {}
}

async function syncTimezoneToBackend() {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (tz) await api.post('/auth/timezone', { timezone: tz });
  } catch {}
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User>(null);
  const [loading, setLoading] = useState(true);

  async function bootstrap() {
    const t = await getToken();
    if (!t) { setLoading(false); return; }
    try {
      const { data } = await api.get('/auth/me');
      setUser(data);
      // ensure backend knows current locale + timezone (used by AI prompts + scheduler)
      syncLocaleToBackend();
      syncTimezoneToBackend();
    } catch {
      await clearToken();
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { bootstrap(); }, []);

  async function login(email: string, password: string) {
    const { data } = await api.post('/auth/login', { email, password });
    await setToken(data.token);
    setUser(data.user);
    syncLocaleToBackend();
    syncTimezoneToBackend();
  }

  async function register(email: string, password: string, name: string) {
    const { data } = await api.post('/auth/register', { email, password, name });
    await setToken(data.token);
    setUser(data.user);
    syncLocaleToBackend();
    syncTimezoneToBackend();
  }

  async function logout() {
    await clearToken();
    setUser(null);
  }

  async function refreshUser() {
    try {
      const { data } = await api.get('/auth/me');
      setUser(data);
    } catch {}
  }

  async function deleteAccount() {
    try { await api.delete('/auth/account'); } catch {}
    await clearToken();
    setUser(null);
  }

  return <Ctx.Provider value={{ user, loading, login, register, logout, refreshUser, deleteAccount }}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
