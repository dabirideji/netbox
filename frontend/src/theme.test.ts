import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  applyThemePreference,
  cycleThemePreference,
  getStoredThemePreference,
  resolveTheme,
  setThemePreference,
  THEME_STORAGE_KEY,
  setupThemeSync,
  themePreferenceLabel,
} from './theme';

describe('theme', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'matchMedia',
      vi.fn().mockImplementation((query: string) => ({
        matches: query.includes('dark'),
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    );
  });

  afterEach(() => {
    localStorage.removeItem(THEME_STORAGE_KEY);
    vi.unstubAllGlobals();
  });

  it('resolves system preference from matchMedia', () => {
    expect(resolveTheme('light')).toBe('light');
    expect(resolveTheme('dark')).toBe('dark');
    expect(resolveTheme('system')).toBe('dark');
  });

  it('cycles light, dark, and system', () => {
    expect(cycleThemePreference('light')).toBe('dark');
    expect(cycleThemePreference('dark')).toBe('system');
    expect(cycleThemePreference('system')).toBe('light');
  });

  it('labels preferences', () => {
    expect(themePreferenceLabel('light')).toBe('Light');
    expect(themePreferenceLabel('dark')).toBe('Dark');
    expect(themePreferenceLabel('system')).toBe('System');
  });

  it('defaults to dark when nothing is stored', () => {
    expect(getStoredThemePreference()).toBe('dark');
    expect(applyThemePreference(getStoredThemePreference())).toBe('dark');
  });

  it('keeps the document theme in sync through setupThemeSync', () => {
    const cleanup = setupThemeSync();
    expect(document.documentElement.dataset.theme).toBe('dark');

    localStorage.setItem(THEME_STORAGE_KEY, 'light');
    window.dispatchEvent(new StorageEvent('storage', { key: THEME_STORAGE_KEY }));
    expect(document.documentElement.dataset.theme).toBe('light');

    cleanup();
  });

  it('persists preference and applies resolved theme to the document root', () => {
    expect(setThemePreference('dark')).toBe('dark');
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark');
    expect(document.documentElement.dataset.theme).toBe('dark');

    expect(applyThemePreference('light')).toBe('light');
    expect(document.documentElement.dataset.theme).toBe('light');
  });
});
