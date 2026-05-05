import { I18n } from 'i18n-js';
import * as Localization from 'expo-localization';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { en_US } from './en-US';
import { en_GB } from './en-GB';
import { es } from './es';
import { fr } from './fr';
import { cs } from './cs';
import { sk } from './sk';
import { ru } from './ru';
import { zh_CN } from './zh-CN';
import { api } from '../api';

export const SUPPORTED_LOCALES = [
  { code: 'en-US', label: 'English (US)' },
  { code: 'en-GB', label: 'English (UK)' },
  { code: 'es',    label: 'Español' },
  { code: 'fr',    label: 'Français' },
  { code: 'cs',    label: 'Čeština' },
  { code: 'sk',    label: 'Slovenčina' },
  { code: 'ru',    label: 'Русский' },
  { code: 'zh-CN', label: '中文 (简体)' },
] as const;

export type LocaleCode = typeof SUPPORTED_LOCALES[number]['code'];

export const i18n = new I18n({
  'en-US': en_US,
  'en-GB': en_GB,
  'en': en_US,
  es,
  fr,
  cs,
  sk,
  ru,
  'zh-CN': zh_CN,
  zh: zh_CN,
});

i18n.defaultLocale = 'en-US';
i18n.enableFallback = true;

const STORAGE_KEY = 'goalpilot_locale';

function pickDeviceLocale(): LocaleCode {
  try {
    const list = Localization.getLocales?.() ?? [];
    for (const l of list) {
      const tag = (l.languageTag || '').toLowerCase();
      const lang = (l.languageCode || '').toLowerCase();
      const region = (l.regionCode || '').toUpperCase();
      const composite = lang ? `${lang}${region ? '-' + region : ''}` : '';
      const candidates = [tag, composite, lang];
      const match = SUPPORTED_LOCALES.find(s =>
        candidates.includes(s.code.toLowerCase()) ||
        candidates.some(c => c.startsWith(s.code.toLowerCase().split('-')[0])),
      );
      if (match) return match.code;
    }
  } catch {}
  return 'en-US';
}

export async function initI18n() {
  try {
    const stored = await AsyncStorage.getItem(STORAGE_KEY);
    if (stored && SUPPORTED_LOCALES.some(s => s.code === stored)) {
      i18n.locale = stored;
      return stored as LocaleCode;
    }
  } catch {}
  const dev = pickDeviceLocale();
  i18n.locale = dev;
  return dev;
}

export async function setLocale(code: LocaleCode) {
  i18n.locale = code;
  try { await AsyncStorage.setItem(STORAGE_KEY, code); } catch {}
  // tell backend so AI replies in this language
  try { await api.post('/auth/locale', { locale: code }); } catch {}
}

export const t = (key: string, opts?: Record<string, any>) => i18n.t(key, opts);
