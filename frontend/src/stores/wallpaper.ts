import { defineStore } from 'pinia';
import { ref } from 'vue';
import { fetchWallpaper } from '../api';
import type { WallpaperCategoryId } from '../wallpaperCategories';
import {
  applyWallpaperUrl,
  clearWallpaper,
  getStoredWallpaperUrl,
  getWallpaperCategory,
  getWallpaperIntervalMs,
  initWallpaperFromStorage,
  isWallpaperEnabled,
  setWallpaperCategory,
  setWallpaperEnabled,
  setWallpaperIntervalMs,
} from '../wallpaper';

export const useWallpaperStore = defineStore('wallpaper', () => {
  const enabled = ref(isWallpaperEnabled());
  const intervalMs = ref(getWallpaperIntervalMs());
  const category = ref<WallpaperCategoryId>(getWallpaperCategory());
  const loading = ref(false);
  const error = ref<string | null>(null);

  let rotationTimer: ReturnType<typeof setInterval> | undefined;
  let started = false;

  function stopRotation(): void {
    if (rotationTimer) {
      clearInterval(rotationTimer);
      rotationTimer = undefined;
    }
  }

  function startRotation(): void {
    stopRotation();
    if (!enabled.value) {
      return;
    }

    rotationTimer = setInterval(() => {
      void refreshWallpaper();
    }, intervalMs.value);
  }

  async function refreshWallpaper(): Promise<void> {
    if (!isWallpaperEnabled()) {
      return;
    }

    const cachedUrl = getStoredWallpaperUrl();
    loading.value = true;

    try {
      const wallpaper = await fetchWallpaper(category.value);
      if (!isWallpaperEnabled()) {
        return;
      }

      applyWallpaperUrl(wallpaper.url);
      error.value = null;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load wallpaper';
      error.value = message.startsWith('Pexels request failed')
        ? `${message}. Check PEXELS_API_KEY in .env.local and your network connection, then try again.`
        : message;
      if (!cachedUrl) {
        await setEnabled(false);
      }
    } finally {
      loading.value = false;
    }
  }

  async function setEnabled(nextEnabled: boolean): Promise<void> {
    setWallpaperEnabled(nextEnabled);
    enabled.value = isWallpaperEnabled();
    error.value = null;

    if (!nextEnabled) {
      stopRotation();
      clearWallpaper();
      return;
    }

    initWallpaperFromStorage();
    await refreshWallpaper();
    startRotation();
  }

  function setIntervalMs(ms: number): void {
    setWallpaperIntervalMs(ms);
    intervalMs.value = getWallpaperIntervalMs();
    if (enabled.value) {
      startRotation();
    }
  }

  async function setCategory(nextCategory: WallpaperCategoryId): Promise<void> {
    setWallpaperCategory(nextCategory);
    category.value = getWallpaperCategory();
    if (!enabled.value) {
      return;
    }

    await refreshWallpaper();
  }

  function syncFromStorage(): void {
    enabled.value = isWallpaperEnabled();
    intervalMs.value = getWallpaperIntervalMs();
    category.value = getWallpaperCategory();
  }

  function ensureStarted(): void {
    syncFromStorage();

    if (started) {
      return;
    }

    started = true;
    if (!enabled.value) {
      return;
    }

    initWallpaperFromStorage();
    void refreshWallpaper();
    startRotation();
  }

  return {
    enabled,
    intervalMs,
    category,
    loading,
    error,
    setEnabled,
    setCategory,
    setIntervalMs,
    ensureStarted,
    syncFromStorage,
    refreshWallpaper,
  };
});
