import { defineStore } from 'pinia';
import { ref } from 'vue';
import { fetchPlatformSettings, updatePlatformSettings } from '../api';
import type { PlatformAlertDefaults } from '../types';

function defaultPlatformAlerts(): PlatformAlertDefaults {
  return {
    defaultNotification: true,
    defaultSound: true,
    defaultEmail: false,
    defaultEmailTo: '',
    defaultOnDegraded: true,
    defaultOnDown: true,
    defaultCooldownMs: 300_000,
  };
}

export const useSettingsStore = defineStore('settings', () => {
  const isOpen = ref(false);
  const platformAlerts = ref<PlatformAlertDefaults>(defaultPlatformAlerts());
  const isLoading = ref(false);
  const isSaving = ref(false);
  const error = ref<string | null>(null);
  const message = ref<string | null>(null);

  async function loadPlatform(): Promise<void> {
    error.value = null;
    try {
      const response = await fetchPlatformSettings();
      platformAlerts.value = { ...response.settings.alerts };
    } catch (loadError) {
      error.value = loadError instanceof Error ? loadError.message : 'Unable to load platform settings';
    }
  }

  async function open(): Promise<void> {
    isOpen.value = true;
    message.value = null;
    isLoading.value = true;
    await loadPlatform();
    isLoading.value = false;
  }

  function close(): void {
    isOpen.value = false;
    error.value = null;
    message.value = null;
  }

  async function savePlatform(): Promise<boolean> {
    isSaving.value = true;
    error.value = null;
    message.value = null;

    try {
      const response = await updatePlatformSettings({ alerts: platformAlerts.value });
      platformAlerts.value = { ...response.settings.alerts };
      message.value = 'Platform settings saved.';
      return true;
    } catch (saveError) {
      error.value = saveError instanceof Error ? saveError.message : 'Unable to save platform settings';
      return false;
    } finally {
      isSaving.value = false;
    }
  }

  return {
    isOpen,
    platformAlerts,
    isLoading,
    isSaving,
    error,
    message,
    open,
    close,
    loadPlatform,
    savePlatform,
  };
});
