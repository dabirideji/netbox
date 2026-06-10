import { defineStore } from 'pinia';
import { ref } from 'vue';
import { clearStorage, fetchStorageStats } from '../api';
import type { StorageClearScope, StorageStats } from '../types';
import { useHistoryStore } from './history';
import { useSpeedTestStore } from './speedTest';

export const useStorageStore = defineStore(
  'storage',
  () => {
    const stats = ref<StorageStats | null>(null);

    async function loadStats(): Promise<void> {
      try {
        stats.value = await fetchStorageStats();
      } catch {
        stats.value = stats.value;
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
      loadStats,
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
