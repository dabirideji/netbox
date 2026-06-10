import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import { fetchPreferences, patchPreferences } from '../api';
import {
  createDefaultDashboardSectionsCollapsed,
  DASHBOARD_SECTION_IDS,
  type DashboardSectionId,
  type DashboardSectionsCollapsedState,
} from '../dashboardSections';
import { PREFERENCE_KEYS, type TimelineRangePreference } from './preferenceKeys';

const CACHE_TTL = 1000 * 60 * 10;

function normalizeSectionsCollapsed(
  value: Partial<DashboardSectionsCollapsedState> | null | undefined,
): DashboardSectionsCollapsedState {
  const defaults = createDefaultDashboardSectionsCollapsed();
  if (!value || typeof value !== 'object') return defaults;

  const next = { ...defaults };
  for (const sectionId of DASHBOARD_SECTION_IDS) {
    if (typeof value[sectionId] === 'boolean') {
      next[sectionId] = value[sectionId];
    }
  }
  return next;
}

function formatDateTimeInput(timestamp: number): string {
  const date = new Date(timestamp);
  const offsetMs = date.getTimezoneOffset() * 60_000;
  return new Date(timestamp - offsetMs).toISOString().slice(0, 16);
}

export const usePersonalisationStore = defineStore(
  'personalisation',
  () => {
    const preferences = ref<Record<string, unknown>>({});
    const loading = ref(false);
    const error = ref<string | null>(null);
    const lastFetch = ref(0);

    const sectionsCollapsed = ref<DashboardSectionsCollapsedState>(createDefaultDashboardSectionsCollapsed());
    const rangeFrom = ref('');
    const rangeTo = ref('');
    const eventPage = ref(0);
    const speedTestPage = ref(0);

    let localUiDirty = false;
    let pendingRemotePatch: Record<string, unknown> | null = null;
    let remoteSyncRunning = false;

    const hasData = computed(() => Object.keys(preferences.value).length > 0);

    function buildUiPreferencePatch(): Record<string, unknown> {
      return {
        [PREFERENCE_KEYS.sectionsCollapsed]: { ...sectionsCollapsed.value },
        [PREFERENCE_KEYS.timelineRange]: {
          from: rangeFrom.value,
          to: rangeTo.value,
        } satisfies TimelineRangePreference,
        [PREFERENCE_KEYS.eventPage]: eventPage.value,
        [PREFERENCE_KEYS.speedTestPage]: speedTestPage.value,
      };
    }

    function applyPreferencesFromServer(prefs: Record<string, unknown> | null | undefined): void {
      if (!prefs || localUiDirty) return;

      const collapsed = prefs[PREFERENCE_KEYS.sectionsCollapsed];
      if (collapsed && typeof collapsed === 'object') {
        sectionsCollapsed.value = normalizeSectionsCollapsed(collapsed as Partial<DashboardSectionsCollapsedState>);
      }

      const timelineRange = prefs[PREFERENCE_KEYS.timelineRange];
      if (timelineRange && typeof timelineRange === 'object') {
        const range = timelineRange as Partial<TimelineRangePreference>;
        if (typeof range.from === 'string') rangeFrom.value = range.from;
        if (typeof range.to === 'string') rangeTo.value = range.to;
      }

      if (typeof prefs[PREFERENCE_KEYS.eventPage] === 'number') {
        eventPage.value = Math.max(0, prefs[PREFERENCE_KEYS.eventPage] as number);
      }
      if (typeof prefs[PREFERENCE_KEYS.speedTestPage] === 'number') {
        speedTestPage.value = Math.max(0, prefs[PREFERENCE_KEYS.speedTestPage] as number);
      }
    }

    async function flushRemoteQueue(): Promise<void> {
      if (remoteSyncRunning) return;
      remoteSyncRunning = true;

      try {
        while (pendingRemotePatch !== null) {
          const patch = pendingRemotePatch;
          try {
            const response = await patchPreferences(patch);
            preferences.value = response.data;
            lastFetch.value = Date.now();

            if (pendingRemotePatch === patch) {
              pendingRemotePatch = null;
            }
          } catch (err) {
            console.error('Error syncing UI preferences:', err);
            pendingRemotePatch = patch;
            break;
          }
        }

        if (pendingRemotePatch === null) {
          localUiDirty = false;
        }
      } finally {
        remoteSyncRunning = false;
        if (pendingRemotePatch !== null) {
          void flushRemoteQueue();
        }
      }
    }

    function queuePreferencePatch(patch: Record<string, unknown>): void {
      pendingRemotePatch = { ...(pendingRemotePatch ?? {}), ...patch };
      localUiDirty = true;
      void flushRemoteQueue();
    }

    function queueRemoteSync(): void {
      queuePreferencePatch(buildUiPreferencePatch());
    }

    function markUiDirtyAndSync(): void {
      queueRemoteSync();
    }

    async function fetchPreferencesFromServer(force = false): Promise<Record<string, unknown>> {
      if (!force && hasData.value && Date.now() - lastFetch.value < CACHE_TTL) {
        applyPreferencesFromServer(preferences.value);
        return preferences.value;
      }

      loading.value = true;
      error.value = null;

      try {
        const response = await fetchPreferences();
        preferences.value = response.data;
        lastFetch.value = Date.now();
        applyPreferencesFromServer(preferences.value);
        return preferences.value;
      } catch (err) {
        error.value = err instanceof Error ? err.message : 'Failed to fetch preferences';
        if (!hasData.value) throw err;
        return preferences.value;
      } finally {
        loading.value = false;
      }
    }

    async function updatePreferences(updates: Record<string, unknown>): Promise<boolean> {
      loading.value = true;
      error.value = null;

      try {
        const response = await patchPreferences(updates);
        preferences.value = response.data;
        lastFetch.value = Date.now();
        applyPreferencesFromServer(preferences.value);
        return true;
      } catch (err) {
        error.value = err instanceof Error ? err.message : 'Failed to update preferences';
        return false;
      } finally {
        loading.value = false;
      }
    }

    function isSectionCollapsed(sectionId: DashboardSectionId): boolean {
      return sectionsCollapsed.value[sectionId] ?? false;
    }

    function setSectionCollapsed(sectionId: DashboardSectionId, collapsed: boolean): void {
      sectionsCollapsed.value = {
        ...sectionsCollapsed.value,
        [sectionId]: collapsed,
      };
      queuePreferencePatch({
        [PREFERENCE_KEYS.sectionsCollapsed]: { ...sectionsCollapsed.value },
      });
    }

    function setDashboardSectionsCollapsed(state: DashboardSectionsCollapsedState): void {
      sectionsCollapsed.value = normalizeSectionsCollapsed(state);
      queuePreferencePatch({
        [PREFERENCE_KEYS.sectionsCollapsed]: { ...sectionsCollapsed.value },
      });
    }

    function setRangeFrom(value: string): void {
      rangeFrom.value = value;
    }

    function setRangeTo(value: string): void {
      rangeTo.value = value;
    }

    function commitTimelineRange(): void {
      markUiDirtyAndSync();
    }

    function setEventPage(page: number): void {
      eventPage.value = Math.max(0, page);
      markUiDirtyAndSync();
    }

    function setSpeedTestPage(page: number): void {
      speedTestPage.value = Math.max(0, page);
      markUiDirtyAndSync();
    }

    function resetRangePagination(): void {
      eventPage.value = 0;
      speedTestPage.value = 0;
      markUiDirtyAndSync();
    }

    function clearRange(): void {
      rangeFrom.value = '';
      rangeTo.value = '';
      eventPage.value = 0;
      speedTestPage.value = 0;
      markUiDirtyAndSync();
    }

    function setLastHourRange(): void {
      const end = Date.now();
      rangeFrom.value = formatDateTimeInput(end - 60 * 60 * 1000);
      rangeTo.value = formatDateTimeInput(end);
      eventPage.value = 0;
      speedTestPage.value = 0;
      markUiDirtyAndSync();
    }

    function setTodayRange(): void {
      const start = new Date();
      start.setHours(0, 0, 0, 0);
      rangeFrom.value = formatDateTimeInput(start.getTime());
      rangeTo.value = formatDateTimeInput(Date.now());
      eventPage.value = 0;
      speedTestPage.value = 0;
      markUiDirtyAndSync();
    }

    function resetSyncState(): void {
      localUiDirty = false;
      pendingRemotePatch = null;
      remoteSyncRunning = false;
    }

    function resetUiState(): void {
      resetSyncState();
      sectionsCollapsed.value = createDefaultDashboardSectionsCollapsed();
      rangeFrom.value = '';
      rangeTo.value = '';
      eventPage.value = 0;
      speedTestPage.value = 0;
    }

    return {
      preferences,
      loading,
      error,
      lastFetch,
      hasData,
      sectionsCollapsed,
      rangeFrom,
      rangeTo,
      eventPage,
      speedTestPage,
      fetchPreferences: fetchPreferencesFromServer,
      updatePreferences,
      applyPreferencesFromServer,
      isSectionCollapsed,
      setSectionCollapsed,
      setDashboardSectionsCollapsed,
      setRangeFrom,
      setRangeTo,
      commitTimelineRange,
      setEventPage,
      setSpeedTestPage,
      resetRangePagination,
      clearRange,
      setLastHourRange,
      setTodayRange,
      resetSyncState,
      resetUiState,
    };
  },
  {
    persist: {
      key: 'netbox-personalisation',
      storage: localStorage,
      pick: [
        'preferences',
        'lastFetch',
        'rangeFrom',
        'rangeTo',
        'eventPage',
        'speedTestPage',
      ],
    },
  },
);

/** @deprecated Use PREFERENCE_KEYS.sectionsCollapsed */
export const DASHBOARD_SECTIONS_COLLAPSED_PREF_KEY = PREFERENCE_KEYS.sectionsCollapsed;

/** @deprecated Pinia persist replaces direct localStorage access */
export const DASHBOARD_SECTIONS_COLLAPSED_STORAGE_KEY = 'netbox_dashboard_sections_collapsed';

export function applyDashboardSectionsCollapsedFromPreferences(
  prefs: Record<string, unknown> | null | undefined,
): void {
  usePersonalisationStore().applyPreferencesFromServer(prefs);
}

export function resetDashboardSectionsCollapsedSyncState(): void {
  usePersonalisationStore().resetUiState();
}
