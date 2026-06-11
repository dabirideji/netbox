<script setup lang="ts">
import { PhArrowsIn, PhArrowsOut } from '@phosphor-icons/vue';
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { fetchStatus, subscribeStatus } from '../api';
import { formatClock, formatMs } from '../format';
import { isReconnectingState } from '../stores/monitor';
import { targetServiceIcon } from '../targetIcons';
import {
  compareTargetsByScopeThenLabel,
  shouldShowScopeHeader,
  targetScopeLabel,
} from '../targetScope';
import { isTrayCompactEnabled, setTrayCompact } from '../trayCompact';
import type { StatusSummary, TargetHistoryPoint, TargetSummary } from '../types';

const summary = ref<StatusSummary | null>(null);
const compact = ref(isTrayCompactEnabled());
const connectionState = ref('connecting');
let eventSource: EventSource | undefined;

const targets = computed(() => summary.value?.targets ?? []);
const sortedTargets = computed(() => [...targets.value].sort(compareTargetsByScopeThenLabel));
const isReconnecting = computed(() => isReconnectingState(connectionState.value));
const overallStatus = computed(() => summary.value?.overallStatus ?? 'unknown');

function applySummary(payload: StatusSummary): void {
  summary.value = payload;
  connectionState.value = 'live';
}

function lastValue(target: TargetSummary): string {
  return target.lastLatencyMs == null ? target.lastError ?? 'fail' : formatMs(target.lastLatencyMs);
}

function toggleCompact(): void {
  compact.value = !compact.value;
  setTrayCompact(compact.value);
}

function targetBarTitle(target: TargetSummary, point: TargetHistoryPoint): string {
  return `${target.label} · ${formatClock(point.at)} · ${point.status} · ${
    point.latencyMs == null ? point.error ?? 'fail' : formatMs(point.latencyMs)
  }`;
}

onMounted(async () => {
  try {
    applySummary(await fetchStatus());
  } catch {
    connectionState.value = 'offline';
  }

  eventSource = subscribeStatus(
    (payload) => {
      if (payload.type === 'status' && payload.summary) {
        applySummary(payload.summary);
      }
    },
    () => {
      connectionState.value = 'reconnecting';
    },
  );
});

onUnmounted(() => {
  eventSource?.close();
});
</script>

<template>
  <div class="tray-panel" :class="{ 'tray-panel--compact': compact }">
    <header class="tray-panel__header" title="Drag to move">
      <div class="tray-panel__header-title">
        <svg class="tray-panel__drag" viewBox="0 0 12 16" aria-hidden="true">
          <circle cx="3.5" cy="3.5" r="1.1" fill="currentColor" />
          <circle cx="8.5" cy="3.5" r="1.1" fill="currentColor" />
          <circle cx="3.5" cy="8" r="1.1" fill="currentColor" />
          <circle cx="8.5" cy="8" r="1.1" fill="currentColor" />
          <circle cx="3.5" cy="12.5" r="1.1" fill="currentColor" />
          <circle cx="8.5" cy="12.5" r="1.1" fill="currentColor" />
        </svg>
        <div>
          <p class="tray-panel__eyebrow">Live checks</p>
          <h1 class="tray-panel__title">Netbox</h1>
        </div>
      </div>
      <div class="tray-panel__header-actions">
        <button
          type="button"
          class="tray-panel__mode"
          :aria-pressed="compact"
          :title="compact ? 'Switch to comfortable dock mode' : 'Switch to compact dock mode'"
          @click="toggleCompact"
        >
          <PhArrowsIn v-if="!compact" weight="bold" aria-hidden="true" />
          <PhArrowsOut v-else weight="bold" aria-hidden="true" />
          <span class="sr-only">{{ compact ? 'Comfortable mode' : 'Compact mode' }}</span>
        </button>
        <span class="tray-panel__status" :class="overallStatus">
          <span class="dot" />
          <span class="tray-panel__status-label">
            {{ isReconnecting ? 'Reconnecting' : overallStatus }}
          </span>
        </span>
      </div>
    </header>

    <p v-if="!sortedTargets.length" class="tray-panel__empty">No monitor targets configured yet.</p>

    <div v-else class="tray-panel__list">
      <template v-for="(target, index) in sortedTargets" :key="target.id">
        <div
          v-if="shouldShowScopeHeader(sortedTargets, index)"
          class="tray-panel__scope"
          role="presentation"
        >
          {{ targetScopeLabel(target.scope) }}
        </div>

        <article class="tray-row">
          <div class="tray-row__main">
            <component
              :is="targetServiceIcon(target.type, target.protocol)"
              class="tray-row__icon"
              weight="bold"
              aria-hidden="true"
            />
            <div class="tray-row__text">
              <strong>{{ target.label }}</strong>
              <small v-if="!compact">{{ target.host }}</small>
            </div>
            <span class="tray-row__latency tray-row__latency--inline">{{ lastValue(target) }}</span>
            <span class="tray-row__status status" :class="target.currentStatus">
              <span class="dot" />
              <span class="tray-row__status-label">{{ target.currentStatus }}</span>
            </span>
          </div>

          <div v-if="!compact" class="tray-row__meta">
            <div
              class="tray-row__history history"
              :aria-label="`${target.label} recent status bars`"
            >
              <span
                v-for="point in target.history"
                :key="`${target.id}-${point.at}`"
                class="bar"
                :class="point.status"
                :title="targetBarTitle(target, point)"
              />
            </div>
            <span class="tray-row__latency">{{ lastValue(target) }}</span>
          </div>
        </article>
      </template>
    </div>
  </div>
</template>
