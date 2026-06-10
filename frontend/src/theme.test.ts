import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  applyThemePreference,
  cycleThemePreference,
  resolveTheme,
  setThemePreference,
  THEME_STORAGE_KEY,
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

  it('persists preference and applies resolved theme to the document root', () => {
    expect(setThemePreference('dark')).toBe('dark');
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark');
    expect(document.documentElement.dataset.theme).toBe('dark');

    expect(applyThemePreference('light')).toBe('light');
    expect(document.documentElement.dataset.theme).toBe('light');
  });
});
