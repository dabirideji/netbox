export type ThemePreference = 'light' | 'dark' | 'system';
export type ResolvedTheme = 'light' | 'dark';

export const THEME_STORAGE_KEY = 'netbox-theme';
export const DEFAULT_THEME_PREFERENCE: ThemePreference = 'dark';

const THEME_CYCLE: ThemePreference[] = ['light', 'dark', 'system'];

export function getSystemTheme(): ResolvedTheme {
  if (typeof window === 'undefined') return 'dark';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function resolveTheme(preference: ThemePreference): ResolvedTheme {
  return preference === 'system' ? getSystemTheme() : preference;
}

export function getStoredThemePreference(): ThemePreference {
  if (typeof window === 'undefined') return DEFAULT_THEME_PREFERENCE;

  const stored = localStorage.getItem(THEME_STORAGE_KEY);
  if (stored === 'light' || stored === 'dark' || stored === 'system') {
    return stored;
  }

  return DEFAULT_THEME_PREFERENCE;
}

export function applyThemePreference(preference: ThemePreference): ResolvedTheme {
  const resolved = resolveTheme(preference);

  if (typeof document !== 'undefined') {
    document.documentElement.dataset.theme = resolved;
  }

  return resolved;
}

export function setThemePreference(preference: ThemePreference): ResolvedTheme {
  if (typeof window !== 'undefined') {
    localStorage.setItem(THEME_STORAGE_KEY, preference);
  }

  return applyThemePreference(preference);
}

export function cycleThemePreference(current: ThemePreference): ThemePreference {
  const index = THEME_CYCLE.indexOf(current);
  return THEME_CYCLE[(index + 1) % THEME_CYCLE.length];
}

export function themePreferenceLabel(preference: ThemePreference): string {
  if (preference === 'light') return 'Light';
  if (preference === 'dark') return 'Dark';
  return 'System';
}
