import { onMounted, ref } from 'vue';
import { fetchWallpaper } from '../api';
import {
  applyWallpaperUrl,
  clearWallpaper,
  getStoredWallpaperUrl,
  initWallpaperFromStorage,
  isWallpaperEnabled,
  setWallpaperEnabled,
} from '../wallpaper';

export function useWallpaper() {
  const enabled = ref(isWallpaperEnabled());
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function setEnabled(nextEnabled: boolean): Promise<void> {
    enabled.value = nextEnabled;
    setWallpaperEnabled(nextEnabled);
    error.value = null;

    if (!nextEnabled) {
      clearWallpaper();
      return;
    }

    initWallpaperFromStorage();

    const cachedUrl = getStoredWallpaperUrl();
    loading.value = true;
    try {
      const wallpaper = await fetchWallpaper();
      applyWallpaperUrl(wallpaper.url);
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load wallpaper';
      if (!cachedUrl) {
        enabled.value = false;
        setWallpaperEnabled(false);
        clearWallpaper();
      }
    } finally {
      loading.value = false;
    }
  }

  onMounted(() => {
    if (enabled.value) {
      void setEnabled(true);
    }
  });

  return {
    enabled,
    loading,
    error,
    setEnabled,
  };
}
