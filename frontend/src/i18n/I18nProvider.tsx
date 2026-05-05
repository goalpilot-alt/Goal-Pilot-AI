import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import { i18n, initI18n, setLocale as persistLocale, SUPPORTED_LOCALES, LocaleCode } from './index';

type Ctx = {
  locale: LocaleCode;
  ready: boolean;
  setLocale: (code: LocaleCode) => Promise<void>;
  t: (key: string, opts?: Record<string, any>) => string;
  supported: typeof SUPPORTED_LOCALES;
};

const I18nCtx = createContext<Ctx | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<LocaleCode>('en-US');
  const [ready, setReady] = useState(false);

  useEffect(() => {
    (async () => {
      const code = await initI18n();
      setLocaleState(code);
      setReady(true);
    })();
  }, []);

  const setLocale = useCallback(async (code: LocaleCode) => {
    await persistLocale(code);
    setLocaleState(code);
  }, []);

  // re-bind t to current locale so consumers re-render when locale changes
  const t = useCallback(
    (key: string, opts?: Record<string, any>) => i18n.t(key, opts),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [locale],
  );

  return (
    <I18nCtx.Provider value={{ locale, ready, setLocale, t, supported: SUPPORTED_LOCALES }}>
      {children}
    </I18nCtx.Provider>
  );
}

export function useI18n(): Ctx {
  const ctx = useContext(I18nCtx);
  if (!ctx) throw new Error('useI18n must be used inside I18nProvider');
  return ctx;
}
