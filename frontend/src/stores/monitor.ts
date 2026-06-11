import { defineStore } from 'pinia';
import { ref, shallowRef } from 'vue';
import { fetchStatus } from '../api';
import { formatClock } from '../format';
import type { StatusSummary, StreamPayload } from '../types';
import { coalesceToAnimationFrame } from '../utils/schedule';
import { slimStatusSummary } from '../utils/monitorPersist';
import { useHistoryStore } from './history';
import { useSpeedTestStore } from './speedTest';
import { useTargetsStore } from './targets';

export const RECONNECTING_STATE = 'Reconnecting';

export function isReconnectingState(state: string): boolean {
  return state.startsWith(RECONNECTING_STATE);
}

export const useMonitorStore = defineStore(
  'monitor',
  () => {
    const summary = shallowRef<StatusSummary | null>(null);
    const connectionState = ref('Not connected');

    const pendingPayloads: StreamPayload[] = [];
    const flushStreamPayloads = coalesceToAnimationFrame(() => {
      if (!pendingPayloads.length) return;

      const payloads = pendingPayloads.splice(0);
      for (const payload of payloads) {
        applyStreamPayloadNow(payload);
      }
    });

    async function loadStatus(): Promise<void> {
      try {
        summary.value = await fetchStatus();
        connectionState.value = `Updated ${formatClock(summary.value.now)}`;
      } catch {
        connectionState.value = summary.value ? connectionState.value : 'Unavailable';
      }
    }

    function applyStreamPayloadNow(payload: StreamPayload): void {
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

      if (payload.type === 'targets') {
        useTargetsStore().applyTargets(payload.targets);
      }

      connectionState.value = summary.value ? `Updated ${formatClock(summary.value.now)}` : 'Connected';
    }

    function applyStreamPayload(payload: StreamPayload): void {
      pendingPayloads.push(payload);
      flushStreamPayloads();
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
      serializer: {
        serialize: (state) =>
          JSON.stringify({
            summary: slimStatusSummary((state as { summary: StatusSummary | null }).summary),
          }),
        deserialize: (raw) => JSON.parse(raw) as { summary: StatusSummary | null },
      },
    },
  },
);
