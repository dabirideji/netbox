import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchPlatformSettings, updatePlatformSettings } from '../api';
import { useSettingsStore } from './settings';

vi.mock('../api', () => ({
  fetchPlatformSettings: vi.fn(),
  updatePlatformSettings: vi.fn(),
}));

describe('useSettingsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('opens the modal and loads platform alert defaults', async () => {
    vi.mocked(fetchPlatformSettings).mockResolvedValue({
      settings: {
        alerts: {
          defaultNotification: false,
          defaultSound: true,
          defaultEmail: true,
          defaultEmailTo: 'ops@example.com',
          defaultOnDegraded: true,
          defaultOnDown: false,
          defaultCooldownMs: 120_000,
        },
      },
    });

    const store = useSettingsStore();
    await store.open();

    expect(store.isOpen).toBe(true);
    expect(store.platformAlerts.defaultEmailTo).toBe('ops@example.com');
    expect(store.platformAlerts.defaultCooldownMs).toBe(120_000);
  });

  it('persists platform settings', async () => {
    vi.mocked(fetchPlatformSettings).mockResolvedValue({
      settings: {
        alerts: {
          defaultNotification: true,
          defaultSound: true,
          defaultEmail: false,
          defaultEmailTo: '',
          defaultOnDegraded: true,
          defaultOnDown: true,
          defaultCooldownMs: 300_000,
        },
      },
    });
    vi.mocked(updatePlatformSettings).mockResolvedValue({
      settings: {
        alerts: {
          defaultNotification: false,
          defaultSound: false,
          defaultEmail: false,
          defaultEmailTo: '',
          defaultOnDegraded: true,
          defaultOnDown: true,
          defaultCooldownMs: 300_000,
        },
      },
    });

    const store = useSettingsStore();
    await store.open();
    store.platformAlerts.defaultNotification = false;
    store.platformAlerts.defaultSound = false;

    const saved = await store.savePlatform();

    expect(saved).toBe(true);
    expect(updatePlatformSettings).toHaveBeenCalledWith({
      alerts: expect.objectContaining({
        defaultNotification: false,
        defaultSound: false,
      }),
    });
    expect(store.message).toBe('Platform settings saved.');
  });
});
