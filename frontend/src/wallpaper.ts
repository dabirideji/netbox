export const WALLPAPER_ENABLED_STORAGE_KEY = 'netbox-wallpaper-enabled';
export const WALLPAPER_URL_STORAGE_KEY = 'netbox-wallpaper-url-nature-hd';

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
