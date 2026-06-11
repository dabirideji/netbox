import { defineStore } from 'pinia';
import { ref } from 'vue';
import {
  clearStorage,
  fetchStorageSettings,
  fetchStorageStats,
  updateStorageSettings,
} from '../api';
import type { StorageClearScope, StorageSettings, StorageStats } from '../types';
import { useHistoryStore } from './history';
import { useSpeedTestStore } from './speedTest';

function cloneSettings(settings: StorageSettings): StorageSettings {
  return {
    autoPrune: settings.autoPrune,
    limits: { ...settings.limits },
  };
}

export const useStorageStore = defineStore(
  'storage',
  () => {
    const stats = ref<StorageStats | null>(null);
    const settings = ref<StorageSettings | null>(null);
    const isSaving = ref(false);
    const error = ref<string | null>(null);

    async function loadStats(): Promise<void> {
      try {
        stats.value = await fetchStorageStats();
      } catch {
        stats.value = stats.value;
      }
    }

    async function loadSettings(): Promise<void> {
      error.value = null;
      try {
        const response = await fetchStorageSettings();
        settings.value = cloneSettings(response.settings);
      } catch (loadError) {
        error.value = loadError instanceof Error ? loadError.message : 'Unable to load storage settings';
        if (stats.value) {
          settings.value = {
            autoPrune: stats.value.autoPrune,
            limits: { ...stats.value.limits },
          };
        }
      }
    }

    async function loadAll(): Promise<void> {
      await loadStats();
      await loadSettings();
    }

    async function saveSettings(): Promise<boolean> {
      if (!settings.value) return false;

      isSaving.value = true;
      error.value = null;

      try {
        const response = await updateStorageSettings(settings.value);
        settings.value = cloneSettings(response.settings);
        stats.value = response.stats;
        return true;
      } catch (saveError) {
        error.value = saveError instanceof Error ? saveError.message : 'Unable to save storage settings';
        return false;
      } finally {
        isSaving.value = false;
      }
    }

    async function clear(scope: StorageClearScope): Promise<boolean> {
      try {
        const response = await clearStorage(scope);
        stats.value = response.stats;
        if (scope === 'all' || scope === 'incidents') {
          useHistoryStore().resetPagination();
        }
        if (scope === 'all' || scope === 'ping') {
          await useHistoryStore().refreshHistory();
        }
        if (scope === 'all' || scope === 'speedTests') {
          useSpeedTestStore().resetPagination();
          await useSpeedTestStore().refreshTests();
        }
        return true;
      } catch {
        return false;
      }
    }

    return {
      stats,
      settings,
      isSaving,
      error,
      loadStats,
      loadSettings,
      loadAll,
      saveSettings,
      clear,
    };
  },
  {
    persist: {
      key: 'netbox-storage',
      storage: localStorage,
      pick: ['stats'],
    },
  },
);
