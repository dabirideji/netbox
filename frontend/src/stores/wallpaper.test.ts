import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchWallpaper } from '../api';
import { WALLPAPER_INTERVAL_MS_STORAGE_KEY } from '../wallpaper';
import { useWallpaperStore } from './wallpaper';

vi.mock('../api', () => ({
  fetchWallpaper: vi.fn(),
}));

describe('useWallpaperStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    vi.useFakeTimers();
    vi.mocked(fetchWallpaper).mockResolvedValue({
      url: 'https://images.pexels.com/photos/example.jpeg',
      photographer: 'Test',
      photographerUrl: 'https://example.com',
      sourceUrl: 'https://example.com/photo',
    });
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('rotates wallpaper on the configured interval while enabled', async () => {
    localStorage.setItem(WALLPAPER_INTERVAL_MS_STORAGE_KEY, String(15 * 60_000));
    const store = useWallpaperStore();

    await store.setEnabled(true);
    expect(fetchWallpaper).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(15 * 60_000);
    expect(fetchWallpaper).toHaveBeenCalledTimes(2);

    await store.setEnabled(false);
    await vi.advanceTimersByTimeAsync(15 * 60_000);
    expect(fetchWallpaper).toHaveBeenCalledTimes(2);
  });

  it('restarts rotation when the interval changes', async () => {
    const store = useWallpaperStore();

    await store.setEnabled(true);
    store.setIntervalMs(10 * 60_000);

    await vi.advanceTimersByTimeAsync(10 * 60_000);
    expect(fetchWallpaper).toHaveBeenCalledTimes(2);
  });
});
