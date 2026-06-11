import { defineStore } from 'pinia';
import { ref, shallowRef } from 'vue';
import { fetchStatus } from '../api';
import { formatClock } from '../format';
import { CONNECTION_STATE } from '../responses';
import type { MonitorTarget, StatusSummary, StreamPayload } from '../types';
import { coalesceToAnimationFrame } from '../utils/schedule';
import { reorderTargetsByIds } from '../targetOrder';
import { handleAlertNotification } from '../composables/useAlertNotifications';
import { slimStatusSummary } from '../utils/monitorPersist';
import { useHistoryStore } from './history';
import { useSpeedTestStore } from './speedTest';
import { useTargetsStore } from './targets';

export const RECONNECTING_STATE = CONNECTION_STATE.reconnecting.label;

export function isReconnectingState(state: string): boolean {
  return state.startsWith(RECONNECTING_STATE);
}

export const useMonitorStore = defineStore(
  'monitor',
  () => {
    const summary = shallowRef<StatusSummary | null>(null);
    const connectionState = ref<string>(CONNECTION_STATE.notConnected.label);

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
        connectionState.value = summary.value
          ? connectionState.value
          : CONNECTION_STATE.unavailable.label;
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
        syncSummaryTargets(payload.targets);
      }

      if (payload.type === 'alert') {
        void handleAlertNotification(payload.alert);
      }

      connectionState.value = summary.value
        ? `Updated ${formatClock(summary.value.now)}`
        : CONNECTION_STATE.connected.label;
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

    function reorderSummaryTargets(order: string[]): void {
      if (!summary.value) return;

      const currentOrder = summary.value.targets.map((target) => target.id);
      if (currentOrder.length === order.length && currentOrder.every((id, index) => id === order[index])) {
        return;
      }

      const reordered = reorderTargetsByIds(summary.value.targets, order);
      if (reordered.length !== summary.value.targets.length) return;

      summary.value = {
        ...summary.value,
        targets: reordered,
      };
    }

    function setTargetFavorite(targetId: string, favorite: boolean): void {
      if (!summary.value) return;

      summary.value = {
        ...summary.value,
        targets: summary.value.targets.map((target) =>
          target.id === targetId ? { ...target, isFavorite: favorite } : target,
        ),
      };
    }

    function setTargetEnabled(targetId: string, enabled: boolean): void {
      if (!summary.value) return;

      summary.value = {
        ...summary.value,
        targets: summary.value.targets.map((target) =>
          target.id === targetId ? { ...target, enabled } : target,
        ),
      };
    }

    function syncSummaryTargets(targets: MonitorTarget[]): void {
      if (!summary.value) return;

      const byId = new Map(targets.map((target) => [target.id, target]));
      summary.value = {
        ...summary.value,
        targets: summary.value.targets.map((target) => {
          const stored = byId.get(target.id);
          if (!stored) return target;
          return {
            ...target,
            enabled: stored.enabled,
            isFavorite: stored.isFavorite ?? false,
          };
        }),
      };
      reorderSummaryTargets(targets.map((target) => target.id));
    }

    return {
      summary,
      connectionState,
      loadStatus,
      applyStreamPayload,
      setConnectionState,
      seedEventsFromSummary,
      reorderSummaryTargets,
      setTargetFavorite,
      setTargetEnabled,
      syncSummaryTargets,
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
