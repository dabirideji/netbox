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

function applyFavicon(theme: ResolvedTheme): void {
  if (typeof document === 'undefined') {
    return;
  }

  let link = document.querySelector<HTMLLinkElement>('link[data-netbox-icon]');
  if (!link) {
    link = document.createElement('link');
    link.rel = 'icon';
    link.type = 'image/png';
    link.dataset.netboxIcon = 'true';
    document.head.appendChild(link);
  }

  link.href = theme === 'dark' ? '/icons/white-32.png' : '/icons/black-32.png';
}

export function applyThemePreference(preference: ThemePreference): ResolvedTheme {
  const resolved = resolveTheme(preference);

  if (typeof document !== 'undefined') {
    document.documentElement.dataset.theme = resolved;
    applyFavicon(resolved);
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

/** Keep document theme in sync with storage and system preference changes. */
export function setupThemeSync(onChange?: (resolved: ResolvedTheme) => void): () => void {
  const apply = (): ResolvedTheme => {
    const resolved = applyThemePreference(getStoredThemePreference());
    onChange?.(resolved);
    return resolved;
  };

  apply();

  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  const onSystemChange = (): void => {
    if (getStoredThemePreference() === 'system') {
      apply();
    }
  };
  mediaQuery.addEventListener('change', onSystemChange);

  const onStorage = (event: StorageEvent): void => {
    if (event.key === THEME_STORAGE_KEY) {
      apply();
    }
  };
  window.addEventListener('storage', onStorage);

  return () => {
    mediaQuery.removeEventListener('change', onSystemChange);
    window.removeEventListener('storage', onStorage);
  };
}
