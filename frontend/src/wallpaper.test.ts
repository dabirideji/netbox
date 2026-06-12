import { afterEach, describe, expect, it } from 'vitest';
import {
  DEFAULT_WALLPAPER_INTERVAL_MS,
  WALLPAPER_CATEGORY_STORAGE_KEY,
  WALLPAPER_ENABLED_STORAGE_KEY,
  WALLPAPER_INTERVAL_MS_STORAGE_KEY,
  WALLPAPER_URL_STORAGE_KEY,
  applyWallpaperUrl,
  clampWallpaperIntervalMs,
  clearWallpaper,
  getWallpaperCategory,
  getWallpaperIntervalMs,
  initWallpaperFromStorage,
  isWallpaperEnabled,
  setWallpaperCategory,
  setWallpaperEnabled,
  setWallpaperIntervalMs,
} from './wallpaper';

describe('wallpaper', () => {
  afterEach(() => {
    localStorage.clear();
    clearWallpaper();
  });

  it('tracks enabled preference in localStorage', () => {
    expect(isWallpaperEnabled()).toBe(false);

    setWallpaperEnabled(true);
    expect(isWallpaperEnabled()).toBe(true);
  });

  it('applies and clears wallpaper classes on the body', () => {
    applyWallpaperUrl('https://images.pexels.com/photos/example.jpeg');

    expect(document.body.classList.contains('has-wallpaper')).toBe(true);
    expect(document.body.style.getPropertyValue('--wallpaper-image')).toContain('example.jpeg');

    clearWallpaper();

    expect(document.body.classList.contains('has-wallpaper')).toBe(false);
    expect(document.body.style.getPropertyValue('--wallpaper-image')).toBe('');
  });

  it('tracks wallpaper category in localStorage', () => {
    expect(getWallpaperCategory()).toBe('nature');

    setWallpaperCategory('ocean');
    expect(localStorage.getItem(WALLPAPER_CATEGORY_STORAGE_KEY)).toBe('ocean');
    expect(getWallpaperCategory()).toBe('ocean');
  });

  it('tracks wallpaper rotation interval in localStorage', () => {
    expect(getWallpaperIntervalMs()).toBe(DEFAULT_WALLPAPER_INTERVAL_MS);

    setWallpaperIntervalMs(45 * 60_000);
    expect(localStorage.getItem(WALLPAPER_INTERVAL_MS_STORAGE_KEY)).toBe(String(45 * 60_000));
    expect(getWallpaperIntervalMs()).toBe(45 * 60_000);
  });

  it('clamps wallpaper rotation interval to supported bounds', () => {
    expect(clampWallpaperIntervalMs(60_000)).toBe(5 * 60_000);
    expect(clampWallpaperIntervalMs(48 * 60 * 60_000)).toBe(24 * 60 * 60_000);
    expect(clampWallpaperIntervalMs(Number.NaN)).toBe(DEFAULT_WALLPAPER_INTERVAL_MS);
  });

  it('restores cached wallpaper on init when enabled', () => {
    localStorage.setItem(WALLPAPER_ENABLED_STORAGE_KEY, '1');
    localStorage.setItem(WALLPAPER_URL_STORAGE_KEY, 'https://images.pexels.com/photos/cached.jpeg');

    initWallpaperFromStorage();

    expect(document.body.classList.contains('has-wallpaper')).toBe(true);
    expect(document.body.style.getPropertyValue('--wallpaper-image')).toContain('cached.jpeg');
  });
});
