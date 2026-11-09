export const BREAKPOINTS = {
  xs: '0px',
  sm: '576px',
  md: '768px',
  lg: '992px',
  xl: '1200px',
} as const;

export const THEME_TOKENS = {
  light: {
    primary: '#2563eb',
    primaryHover: '#1d4ed8',
    background: '#ffffff',
    surface: '#f8fafc',
    surfaceHover: '#f1f5f9',
    textPrimary: '#0f172a',
    textSecondary: '#475569',
    textMuted: '#94a3b8',
    border: '#e2e8f0',
    shadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
    shadowLg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
  },
  dark: {
    primary: '#3b82f6',
    primaryHover: '#60a5fa',
    background: '#0f172a',
    surface: '#1e293b',
    surfaceHover: '#334155',
    textPrimary: '#f8fafc',
    textSecondary: '#cbd5e1',
    textMuted: '#64748b',
    border: '#334155',
    shadow: '0 4px 6px -1px rgb(0 0 0 / 0.3), 0 2px 4px -2px rgb(0 0 0 / 0.3)',
    shadowLg: '0 10px 15px -3px rgb(0 0 0 / 0.4), 0 4px 6px -4px rgb(0 0 0 / 0.4)',
  },
  neon: {
    primary: '#22d3ee',
    primaryHover: '#67e8f9',
    background: '#020617',
    surface: '#0f172a',
    surfaceHover: '#1e293b',
    textPrimary: '#f8fafc',
    textSecondary: '#e2e8f0',
    textMuted: '#94a3b8',
    border: '#1e293b',
    shadow: '0 0 20px rgb(34 211 238 / 0.2)',
    shadowLg: '0 0 40px rgb(34 211 238 / 0.35)',
  },
} as const;

export type ThemeId = keyof typeof THEME_TOKENS;

export function isThemeId(value: string): value is ThemeId {
  return value in THEME_TOKENS;
}
