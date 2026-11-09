'use client';

import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import Cookies from 'js-cookie';
import { THEME_TOKENS, ThemeId } from '@/lib/tokens';

type ThemeConfig = typeof THEME_TOKENS[ThemeId];

interface ThemeContextType {
  theme: ThemeId;
  tokens: ThemeConfig;
  setTheme: (theme: ThemeId) => void;
}

const defaultContext: ThemeContextType = {
  theme: 'light',
  tokens: THEME_TOKENS.light,
  setTheme: () => {},
};

const ThemeContext = createContext<ThemeContextType>(defaultContext);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<ThemeId>('light');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const saved = Cookies.get('theme') as ThemeId | undefined;
    if (saved && saved in THEME_TOKENS) {
      setThemeState(saved);
    }
  }, []);

  const tokens = THEME_TOKENS[theme];

  const setTheme = useCallback((next: ThemeId) => {
    setThemeState(next);
    Cookies.set('theme', next, { expires: 365 });
    document.documentElement.setAttribute('data-theme', next);
  }, []);

  useEffect(() => {
    if (mounted) {
      document.documentElement.setAttribute('data-theme', theme);
    }
  }, [theme, mounted]);

  if (!mounted) {
    return <>{children}</>;
  }

  return (
    <ThemeContext.Provider value={{ theme, tokens, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
