import { defineStore } from 'pinia';
import { ref } from 'vue';
import { fetchStatus } from '../api';
import { formatClock } from '../format';
import type { StatusSummary, StreamPayload } from '../types';
import { useHistoryStore } from './history';
import { useSpeedTestStore } from './speedTest';

export const RECONNECTING_STATE = 'Reconnecting';

export function isReconnectingState(state: string): boolean {
  return state.startsWith(RECONNECTING_STATE);
}

export const useMonitorStore = defineStore(
  'monitor',
  () => {
    const summary = ref<StatusSummary | null>(null);
    const connectionState = ref('Not connected');

    async function loadStatus(): Promise<void> {
      try {
        summary.value = await fetchStatus();
        connectionState.value = `Updated ${formatClock(summary.value.now)}`;
      } catch {
        connectionState.value = summary.value ? connectionState.value : 'Unavailable';
      }
    }

    function applyStreamPayload(payload: StreamPayload): void {
      if (payload.type === 'status') {
        summary.value = payload.summary;
      }

      if (payload.type === 'event' && summary.value) {
        summary.value = {
          ...summary.value,
          events: [...summary.value.events, payload.event],
        };
        useHistoryStore().handleStreamEvent(payload.event);
      }

      if (payload.type === 'speedTest') {
        useSpeedTestStore().handleStreamSpeedTest(payload.test);
      }

      connectionState.value = summary.value ? `Updated ${formatClock(summary.value.now)}` : 'Connected';
    }

    function setConnectionState(state: string): void {
      connectionState.value = state;
    }

    function seedEventsFromSummary(pageSize: number): void {
      useHistoryStore().seedFromSummary(summary.value?.events ?? [], pageSize);
    }

    return {
      summary,
      connectionState,
      loadStatus,
      applyStreamPayload,
      setConnectionState,
      seedEventsFromSummary,
    };
  },
  {
    persist: {
      key: 'netbox-monitor',
      storage: localStorage,
      pick: ['summary'],
    },
  },
);
