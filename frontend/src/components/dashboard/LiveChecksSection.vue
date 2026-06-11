<script setup lang="ts">
import { PhDotsSixVertical, PhPause, PhPlay, PhSpinner, PhStar } from '@phosphor-icons/vue';
import { computed, TransitionGroup, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { Pagination } from '../ui/pagination';
import { useTargetDragReorder } from '../../composables/useTargetDragReorder';
import { formatClock, formatDate, formatMs, formatPct } from '../../format';
import { reorderTargetsByIds } from '../../targetOrder';
import { isReconnectingState } from '../../stores/monitor';
import { formatTargetLastValue, sortLiveCheckTargets } from '../../liveChecks';
import { useTargetsStore } from '../../stores';
import { targetServiceIcon } from '../../targetIcons';
import { targetColorForSource } from '../../targetColors';
import type { TargetHistoryPoint, TargetSummary } from '../../types';
import DashboardSectionCard from './DashboardSectionCard.vue';
import LiveCheckRowActions from './LiveCheckRowActions.vue';
import TargetAlertModal from './TargetAlertModal.vue';
import { useAlertsStore } from '../../stores/alerts';

const props = defineProps<{
  targets: TargetSummary[];
  connectionState: string;
  page: number;
  pageSize: number;
}>();

const emit = defineEmits<{
  'update:page': [page: number];
}>();

const targetsStore = useTargetsStore();
const alertsStore = useAlertsStore();
const { isReordering, favoritingId, pausingId } = storeToRefs(targetsStore);

const isReconnecting = computed(() => isReconnectingState(props.connectionState));

const orderedTargets = computed(() => sortLiveCheckTargets(props.targets));

const {
  draggingId,
  previewOrder,
  isSettling,
  onPointerDown,
} = useTargetDragReorder({
  orderedIds: () => orderedTargets.value.map((target) => target.id),
  onReorder: (order) => targetsStore.reorderTargets(order),
  disabled: () => isReordering.value,
});

const displayTargets = computed(() => {
  const targets = orderedTargets.value;
  const reordered = reorderTargetsByIds(targets, previewOrder.value);
  const start = props.page * props.pageSize;
  return reordered.slice(start, start + props.pageSize);
});

const targetPill = computed(
  () => `${props.targets.length} target${props.targets.length === 1 ? '' : 's'}`,
);

watch(
  () => props.targets.length,
  (total) => {
    const maxPage = Math.max(0, Math.ceil(total / props.pageSize) - 1);
    if (props.page > maxPage) {
      emit('update:page', maxPage + 1);
    }
  },
);

function lastChecked(target: TargetSummary): string {
  return target.lastCheckedAt == null ? 'pending' : formatClock(target.lastCheckedAt);
}

function incidentState(target: TargetSummary): string {
  return target.activeIncident ? target.activeIncident.to : 'clear';
}

function targetTrendTitle(target: TargetSummary): string {
  const points = target.history;
  const latest = points.at(-1);
  if (!latest) return `${target.label} has no live history points yet`;
  return `${target.label} · ${formatClock(latest.at)} · ${latest.status} · ${
    latest.latencyMs == null ? latest.error ?? 'fail' : formatMs(latest.latencyMs)
  }`;
}

function targetColorFor(target: TargetSummary): string {
  return targetColorForSource(target.config, target.id);
}

function targetBarTitle(target: TargetSummary, point: TargetHistoryPoint): string {
  return `${target.label} · ${formatDate(point.at)} ${formatClock(point.at)} · ${point.status} · ${
    point.latencyMs == null ? point.error ?? 'fail' : formatMs(point.latencyMs)
  }`;
}

function openAlertModal(target: TargetSummary): void {
  void alertsStore.openAlertModal(target);
}

function toggleFavorite(target: TargetSummary): void {
  void targetsStore.setTargetFavorite(target.id, !target.isFavorite);
}

function isFavoriting(targetId: string): boolean {
  return favoritingId.value === targetId;
}

function isPausing(targetId: string): boolean {
  return pausingId.value === targetId;
}

function togglePaused(target: TargetSummary): void {
  void targetsStore.setTargetEnabled(target.id, !target.enabled);
}
</script>

<template>
  <DashboardSectionCard section-id="liveChecks" eyebrow="Components" title="Live checks" fullscreen>
    <template #meta>
      <span class="pill">{{ targetPill }}</span>
      <span class="pill" :class="{ 'pill--reconnecting': isReconnecting }">
        <template v-if="isReconnecting">
          Reconnecting<span class="pill__dots" aria-hidden="true"><span>.</span><span>.</span><span>.</span></span>
        </template>
        <template v-else>{{ connectionState }}</template>
      </span>
    </template>

    <div class="components">
      <p v-if="!targets.length" class="empty">No monitor targets yet. Add one under Sources.</p>
      <div v-else class="components-scroll">
        <div class="components-grid">
          <div class="components-grid__head" aria-hidden="true">
            <span class="components-grid__drag" />
            <span>Target</span>
            <span>IP/HOST</span>
            <span>Protocol</span>
            <span>Status</span>
            <span>Availability</span>
            <span>Last</span>
            <span>Checked</span>
            <span>Uptime</span>
            <span>Incident</span>
            <span class="components-grid__actions">Actions</span>
          </div>

          <TransitionGroup
            name="component-reorder"
            tag="div"
            class="components-grid-rows"
            :class="{ 'is-reorder-settling': isSettling }"
          >
            <article
              v-for="target in displayTargets"
              :key="target.id"
              class="component-row"
              :class="{
                'is-dragging': draggingId === target.id,
                'is-paused': !target.enabled,
              }"
              :data-reorder-id="target.id"
            >
              <button
                type="button"
                class="target-drag-handle"
                :aria-label="`Reorder ${target.label}`"
                :disabled="isReordering"
                @pointerdown="onPointerDown(target.id, $event)"
              >
                <PhDotsSixVertical weight="bold" aria-hidden="true" />
              </button>
              <div class="component-name">
              <span
                class="component-name__color"
                :style="{ backgroundColor: targetColorFor(target) }"
                :aria-label="`${target.label} source color`"
              />
              <component
                :is="targetServiceIcon(target.type, target.protocol)"
                class="component-name__icon"
                weight="bold"
                aria-hidden="true"
              />
              <div class="component-name__text">
                <PhStar
                  v-if="target.isFavorite"
                  class="component-name__favorite"
                  weight="fill"
                  aria-label="Favorite"
                />
                <strong>{{ target.label }}</strong>
              </div>
            </div>
            <div class="component-cell component-cell--ip stat">{{ target.host }}</div>
            <div class="component-cell component-cell--protocol stat">{{ target.protocol.toUpperCase() }}</div>
            <div class="component-cell component-cell--status">
              <div class="live-check-status">
                <button
                  type="button"
                  class="live-check-status__toggle"
                  :class="target.enabled ? 'is-pause' : 'is-resume'"
                  :disabled="isPausing(target.id)"
                  :aria-label="
                    target.enabled
                      ? `Pause monitoring for ${target.label}`
                      : `Resume monitoring for ${target.label}`
                  "
                  @click.stop="togglePaused(target)"
                >
                  <PhSpinner
                    v-if="isPausing(target.id)"
                    class="live-check-status__spinner"
                    weight="bold"
                    aria-hidden="true"
                  />
                  <PhPause v-else-if="target.enabled" weight="fill" aria-hidden="true" />
                  <PhPlay v-else weight="fill" aria-hidden="true" />
                </button>
                <span v-if="!target.enabled" class="status unknown">
                  <span class="dot" aria-hidden="true" />
                  paused
                </span>
                <span v-else class="status" :class="target.currentStatus">
                  <span class="dot" aria-hidden="true" />
                  {{ target.currentStatus }}
                </span>
              </div>
            </div>
            <div
              class="component-cell component-cell--history history"
              :aria-label="`${target.label} recent status bars`"
              :title="targetTrendTitle(target)"
            >
              <span
                v-for="point in target.history"
                :key="`${target.id}-${point.at}`"
                class="bar"
                :class="point.status"
                :title="targetBarTitle(target, point)"
              />
            </div>
            <div class="component-cell stat">{{ formatTargetLastValue(target) }}</div>
            <div class="component-cell stat">{{ lastChecked(target) }}</div>
            <div class="component-cell stat">{{ formatPct(target.uptimePct) }}</div>
            <div class="component-cell stat">{{ incidentState(target) }}</div>
            <div class="component-cell component-cell--actions">
              <LiveCheckRowActions
                :target="target"
                :favoriting="isFavoriting(target.id)"
                :pausing="isPausing(target.id)"
                @set-alert="openAlertModal(target)"
                @toggle-favorite="toggleFavorite(target)"
                @toggle-paused="togglePaused(target)"
              />
            </div>
            </article>
          </TransitionGroup>
        </div>
      </div>

      <TargetAlertModal />

      <Pagination
        v-if="targets.length"
        :current-page="page + 1"
        :total-items="targets.length"
        :items-per-page="pageSize"
        order-label="custom"
        @update:page="emit('update:page', $event)"
      />
    </div>
  </DashboardSectionCard>
</template>
