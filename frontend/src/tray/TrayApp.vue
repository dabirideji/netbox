<script setup lang="ts">
import { PhArrowsIn, PhArrowsOut, PhDotsSixVertical, PhX } from '@phosphor-icons/vue';
import { computed, onMounted, onUnmounted, ref, TransitionGroup } from 'vue';
import { fetchStatus, reorderTargets as reorderTargetsApi, subscribeStatus } from '../api';
import { useTargetDragReorder } from '../composables/useTargetDragReorder';
import { formatClock, formatMs } from '../format';
import { formatTargetLastValue } from '../liveChecks';
import { targetServiceIcon } from '../targetIcons';
import { targetColorForSource } from '../targetColors';
import { reorderTargetsByIds } from '../targetOrder';
import { isTrayCompactEnabled, setTrayCompact } from '../trayCompact';
import type { StatusSummary, TargetHistoryPoint, TargetSummary } from '../types';
import { useTrayDrag } from './useTrayDrag';

const summary = ref<StatusSummary | null>(null);
const compact = ref(isTrayCompactEnabled());
const {
  dragging: isDraggingTray,
  onPointerDown: onTrayDragDown,
  onPointerMove: onTrayDragMove,
  onPointerUp: onTrayDragUp,
  onPointerCancel: onTrayDragCancel,
} = useTrayDrag();
let eventSource: EventSource | undefined;

const targets = computed(() => summary.value?.targets ?? []);
const sortedTargets = computed(() => targets.value);

function reorderSummaryTargets(order: string[]): void {
  if (!summary.value) return;

  const reordered = reorderTargetsByIds(summary.value.targets, order);
  if (reordered.length !== summary.value.targets.length) return;

  summary.value = {
    ...summary.value,
    targets: reordered,
  };
}

async function commitTargetReorder(order: string[]): Promise<void> {
  if (!summary.value) return;

  const previous = [...summary.value.targets];
  reorderSummaryTargets(order);

  try {
    await reorderTargetsApi(order);
  } catch (caught) {
    summary.value = {
      ...summary.value,
      targets: previous,
    };
    throw caught;
  }
}

const {
  draggingId,
  previewOrder,
  isSettling,
  isReordering,
  onPointerDown,
} = useTargetDragReorder({
  orderedIds: () => sortedTargets.value.map((target) => target.id),
  onReorder: commitTargetReorder,
  disabled: () => isReordering.value,
});

const displayTargets = computed(() =>
  reorderTargetsByIds(sortedTargets.value, previewOrder.value),
);

function applySummary(payload: StatusSummary): void {
  summary.value = payload;
}

function toggleCompact(): void {
  compact.value = !compact.value;
  setTrayCompact(compact.value);
}

function closeTray(): void {
  window.netboxDesktop?.hideTray?.();
}

function targetColorFor(target: TargetSummary): string {
  return targetColorForSource(target.config, target.id);
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
    // Status stream will retry on reconnect.
  }

  eventSource = subscribeStatus(
    (payload) => {
      if (payload.type === 'status' && payload.summary) {
        applySummary(payload.summary);
      }
    },
    () => {},
  );
});

onUnmounted(() => {
  eventSource?.close();
});
</script>

<template>
  <div class="tray-panel" :class="{ 'tray-panel--compact': compact }">
    <header class="tray-panel__header">
      <div
        class="tray-panel__header-drag"
        :class="{ 'is-dragging': isDraggingTray }"
        title="Drag to reposition"
        @pointerdown="onTrayDragDown"
        @pointermove="onTrayDragMove"
        @pointerup="onTrayDragUp"
        @pointercancel="onTrayDragCancel"
      >
        <svg class="tray-panel__drag" viewBox="0 0 12 16" aria-hidden="true">
          <circle cx="3.5" cy="3.5" r="1.1" fill="currentColor" />
          <circle cx="8.5" cy="3.5" r="1.1" fill="currentColor" />
          <circle cx="3.5" cy="8" r="1.1" fill="currentColor" />
          <circle cx="8.5" cy="8" r="1.1" fill="currentColor" />
          <circle cx="3.5" cy="12.5" r="1.1" fill="currentColor" />
          <circle cx="8.5" cy="12.5" r="1.1" fill="currentColor" />
        </svg>
        <p class="tray-panel__eyebrow">Live checks</p>
      </div>
      <div class="tray-panel__header-actions">
        <button
          type="button"
          class="tray-panel__icon-button"
          :aria-pressed="compact"
          :title="compact ? 'Switch to comfortable dock mode' : 'Switch to compact dock mode'"
          @click="toggleCompact"
        >
          <PhArrowsIn v-if="!compact" weight="bold" aria-hidden="true" />
          <PhArrowsOut v-else weight="bold" aria-hidden="true" />
          <span class="sr-only">{{ compact ? 'Comfortable mode' : 'Compact mode' }}</span>
        </button>
        <button
          type="button"
          class="tray-panel__icon-button"
          title="Close"
          aria-label="Close"
          @click="closeTray"
        >
          <PhX weight="bold" aria-hidden="true" />
        </button>
      </div>
    </header>

    <p v-if="!sortedTargets.length" class="tray-panel__empty">No monitor targets configured yet.</p>

    <TransitionGroup
      v-else
      name="tray-reorder"
      tag="div"
      class="tray-panel__list"
      :class="{ 'is-reorder-settling': isSettling }"
    >
      <article
        v-for="target in displayTargets"
        :key="target.id"
        class="tray-row"
        :class="{ 'is-dragging': draggingId === target.id }"
        :data-reorder-id="target.id"
      >
        <div class="tray-row__main">
          <button
            type="button"
            class="target-drag-handle tray-row__drag"
            :aria-label="`Reorder ${target.label}`"
            :disabled="isReordering"
            @pointerdown="onPointerDown(target.id, $event)"
          >
            <PhDotsSixVertical weight="bold" aria-hidden="true" />
          </button>
          <span
            class="tray-row__color"
            :style="{ backgroundColor: targetColorFor(target) }"
            :aria-label="`${target.label} source color`"
          />
            <component
              :is="targetServiceIcon(target.type, target.protocol)"
              class="tray-row__icon"
              weight="bold"
              aria-hidden="true"
            />
            <div class="tray-row__text">
              <strong>{{ target.label }}</strong>
            </div>
            <span class="tray-row__ip">{{ target.host }}</span>
            <span class="tray-row__latency tray-row__latency--inline">{{ formatTargetLastValue(target) }}</span>
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
            <span class="tray-row__latency">{{ formatTargetLastValue(target) }}</span>
          </div>
      </article>
    </TransitionGroup>
  </div>
</template>
