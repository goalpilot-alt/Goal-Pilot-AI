import axios from 'axios';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const BASE = process.env.EXPO_PUBLIC_BACKEND_URL;

export const api = axios.create({ baseURL: `${BASE}/api`, timeout: 180000 });

const TOKEN_KEY = 'goalpilot_token';

async function storeGet(key: string): Promise<string | null> {
  if (Platform.OS === 'web') {
    try { return typeof localStorage !== 'undefined' ? localStorage.getItem(key) : null; } catch { return null; }
  }
  return await SecureStore.getItemAsync(key);
}
async function storeSet(key: string, value: string) {
  if (Platform.OS === 'web') {
    try { if (typeof localStorage !== 'undefined') localStorage.setItem(key, value); } catch {}
    return;
  }
  await SecureStore.setItemAsync(key, value);
}
async function storeDel(key: string) {
  if (Platform.OS === 'web') {
    try { if (typeof localStorage !== 'undefined') localStorage.removeItem(key); } catch {}
    return;
  }
  await SecureStore.deleteItemAsync(key);
}

export async function setToken(token: string) { await storeSet(TOKEN_KEY, token); }
export async function getToken(): Promise<string | null> { return await storeGet(TOKEN_KEY); }
export async function clearToken() { await storeDel(TOKEN_KEY); }

api.interceptors.request.use(async (config) => {
  const token = await getToken();
  if (token) {
    config.headers = config.headers ?? {};
    (config.headers as any).Authorization = `Bearer ${token}`;
  }
  return config;
});
