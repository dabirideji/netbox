import {
  DEFAULT_WALLPAPER_CATEGORY,
  normalizeWallpaperCategoryId,
  type WallpaperCategoryId,
} from './wallpaperCategories';

export const WALLPAPER_ENABLED_STORAGE_KEY = 'netbox-wallpaper-enabled';
export const WALLPAPER_URL_STORAGE_KEY = 'netbox-wallpaper-url-nature-hd';
export const WALLPAPER_INTERVAL_MS_STORAGE_KEY = 'netbox-wallpaper-interval-ms';
export const WALLPAPER_CATEGORY_STORAGE_KEY = 'netbox-wallpaper-category';

export const DEFAULT_WALLPAPER_INTERVAL_MS = 30 * 60_000;
export const MIN_WALLPAPER_INTERVAL_MS = 5 * 60_000;
export const MAX_WALLPAPER_INTERVAL_MS = 24 * 60 * 60_000;

export function clampWallpaperIntervalMs(ms: number): number {
  if (!Number.isFinite(ms)) {
    return DEFAULT_WALLPAPER_INTERVAL_MS;
  }

  return Math.max(
    MIN_WALLPAPER_INTERVAL_MS,
    Math.min(MAX_WALLPAPER_INTERVAL_MS, Math.round(ms)),
  );
}

export function getWallpaperIntervalMs(): number {
  if (typeof window === 'undefined') {
    return DEFAULT_WALLPAPER_INTERVAL_MS;
  }

  const raw = localStorage.getItem(WALLPAPER_INTERVAL_MS_STORAGE_KEY);
  if (!raw) {
    return DEFAULT_WALLPAPER_INTERVAL_MS;
  }

  return clampWallpaperIntervalMs(Number.parseInt(raw, 10));
}

export function setWallpaperIntervalMs(ms: number): void {
  if (typeof window === 'undefined') {
    return;
  }

  localStorage.setItem(WALLPAPER_INTERVAL_MS_STORAGE_KEY, String(clampWallpaperIntervalMs(ms)));
}

export function getWallpaperCategory(): WallpaperCategoryId {
  if (typeof window === 'undefined') {
    return DEFAULT_WALLPAPER_CATEGORY;
  }

  return normalizeWallpaperCategoryId(localStorage.getItem(WALLPAPER_CATEGORY_STORAGE_KEY));
}

export function setWallpaperCategory(category: WallpaperCategoryId): void {
  if (typeof window === 'undefined') {
    return;
  }

  localStorage.setItem(
    WALLPAPER_CATEGORY_STORAGE_KEY,
    normalizeWallpaperCategoryId(category),
  );
}

export function isWallpaperEnabled(): boolean {
  if (typeof window === 'undefined') return false;
  return localStorage.getItem(WALLPAPER_ENABLED_STORAGE_KEY) === '1';
}

export function getStoredWallpaperUrl(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(WALLPAPER_URL_STORAGE_KEY);
}

export function applyWallpaperUrl(url: string): void {
  if (typeof document === 'undefined') return;

  document.body.classList.add('has-wallpaper');
  document.body.style.setProperty('--wallpaper-image', `url("${url.replace(/"/g, '\\"')}")`);
  localStorage.setItem(WALLPAPER_URL_STORAGE_KEY, url);
}

export function clearWallpaper(): void {
  if (typeof document === 'undefined') return;

  document.body.classList.remove('has-wallpaper');
  document.body.style.removeProperty('--wallpaper-image');
}

export function setWallpaperEnabled(enabled: boolean): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(WALLPAPER_ENABLED_STORAGE_KEY, enabled ? '1' : '0');
}

/** Apply a cached wallpaper synchronously before the app mounts. */
export function initWallpaperFromStorage(): void {
  if (!isWallpaperEnabled()) return;

  const cachedUrl = getStoredWallpaperUrl();
  if (cachedUrl) {
    applyWallpaperUrl(cachedUrl);
  }
}
