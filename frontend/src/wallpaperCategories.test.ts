import { describe, expect, it } from 'vitest';
import {
  DEFAULT_WALLPAPER_CATEGORY,
  normalizeWallpaperCategoryId,
  WALLPAPER_CATEGORIES,
  wallpaperCategoryLabel,
} from './wallpaperCategories';

describe('wallpaperCategories', () => {
  it('normalizes supported and unknown category ids', () => {
    expect(normalizeWallpaperCategoryId(null)).toBe(DEFAULT_WALLPAPER_CATEGORY);
    expect(normalizeWallpaperCategoryId('forest')).toBe('forest');
    expect(normalizeWallpaperCategoryId('unknown')).toBe(DEFAULT_WALLPAPER_CATEGORY);
  });

  it('returns labels for known categories', () => {
    expect(wallpaperCategoryLabel('night')).toBe('Night');
    expect(wallpaperCategoryLabel('aurora')).toBe('Aurora');
    expect(wallpaperCategoryLabel('nature')).toBe('Nature');
  });

  it('exposes 25 wallpaper categories', () => {
    expect(WALLPAPER_CATEGORIES).toHaveLength(25);
  });
});
