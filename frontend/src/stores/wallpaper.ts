import { defineStore } from 'pinia';
import { ref } from 'vue';
import { fetchWallpaper } from '../api';
import {
  applyWallpaperUrl,
  clearWallpaper,
  getStoredWallpaperUrl,
  getWallpaperIntervalMs,
  initWallpaperFromStorage,
  isWallpaperEnabled,
  setWallpaperEnabled,
  setWallpaperIntervalMs,
} from '../wallpaper';

export const useWallpaperStore = defineStore('wallpaper', () => {
  const enabled = ref(isWallpaperEnabled());
  const intervalMs = ref(getWallpaperIntervalMs());
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
      const wallpaper = await fetchWallpaper();
      if (!isWallpaperEnabled()) {
        return;
      }

      applyWallpaperUrl(wallpaper.url);
      error.value = null;
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load wallpaper';
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

  function syncFromStorage(): void {
    enabled.value = isWallpaperEnabled();
    intervalMs.value = getWallpaperIntervalMs();
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
    loading,
    error,
    setEnabled,
    setIntervalMs,
    ensureStarted,
    syncFromStorage,
    refreshWallpaper,
  };
});
