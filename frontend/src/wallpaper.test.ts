import { afterEach, describe, expect, it } from 'vitest';
import {
  WALLPAPER_ENABLED_STORAGE_KEY,
  WALLPAPER_URL_STORAGE_KEY,
  applyWallpaperUrl,
  clearWallpaper,
  initWallpaperFromStorage,
  isWallpaperEnabled,
  setWallpaperEnabled,
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

  it('restores cached wallpaper on init when enabled', () => {
    localStorage.setItem(WALLPAPER_ENABLED_STORAGE_KEY, '1');
    localStorage.setItem(WALLPAPER_URL_STORAGE_KEY, 'https://images.pexels.com/photos/cached.jpeg');

    initWallpaperFromStorage();

    expect(document.body.classList.contains('has-wallpaper')).toBe(true);
    expect(document.body.style.getPropertyValue('--wallpaper-image')).toContain('cached.jpeg');
  });
});
