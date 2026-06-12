<script setup lang="ts">
import { PhCheckCircle, PhDotsSixVertical, PhPause, PhPlay, PhSpinner, PhStar, PhWifiHigh } from '@phosphor-icons/vue';
import { computed, TransitionGroup, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { Pagination } from '../ui/pagination';
import { useTargetDragReorder } from '../../composables/useTargetDragReorder';
import { formatClock, formatDate, formatMs, formatPct } from '../../format';
import { reorderTargetsByIds } from '../../targetOrder';
import { isReconnectingState } from '../../stores/monitor';
import {
  buildLiveCheckRows,
  formatNetworkSpeed,
  formatTargetLastValue,
  liveCheckRowKey,
  networkSpeedTitle,
  sortLiveCheckRows,
  type LiveCheckRow,
} from '../../liveChecks';
import { useTargetsStore } from '../../stores';
import { targetServiceIcon } from '../../targetIcons';
import { targetColorForSource } from '../../targetColors';
import type { NetworkDeviceSummary, TargetHistoryPoint, TargetSummary } from '../../types';
import DashboardSectionCard from './DashboardSectionCard.vue';
import LiveCheckRowActions from './LiveCheckRowActions.vue';
import TargetAlertModal from './TargetAlertModal.vue';
import { useAlertsStore } from '../../stores/alerts';

const props = defineProps<{
  targets: TargetSummary[];
  networkDevices?: NetworkDeviceSummary[];
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

const orderedRows = computed(() =>
  sortLiveCheckRows(buildLiveCheckRows(props.targets, props.networkDevices ?? [])),
);

const targetOnlyIds = computed(() =>
  orderedRows.value
    .filter((row): row is Extract<LiveCheckRow, { kind: 'target' }> => row.kind === 'target')
    .map((row) => row.target.id),
);

const {
  draggingId,
  previewOrder,
  isSettling,
  onPointerDown,
} = useTargetDragReorder({
  orderedIds: () => targetOnlyIds.value,
  onReorder: (order) => targetsStore.reorderTargets(order),
  disabled: () => isReordering.value,
});

const displayRows = computed(() => {
  const rows = orderedRows.value;
  const targetRows = rows.filter((row): row is Extract<LiveCheckRow, { kind: 'target' }> => row.kind === 'target');
  const deviceRows = rows.filter((row): row is Extract<LiveCheckRow, { kind: 'networkDevice' }> => row.kind === 'networkDevice');
  const reorderedTargets = reorderTargetsByIds(
    targetRows.map((row) => row.target),
    previewOrder.value,
  );
  const mergedRows: LiveCheckRow[] = [
    ...deviceRows,
    ...reorderedTargets.map((target) => ({ kind: 'target' as const, target })),
  ];
  const start = props.page * props.pageSize;
  return mergedRows.slice(start, start + props.pageSize);
});

const rowPill = computed(() => {
  const total = orderedRows.value.length;
  return `${total} check${total === 1 ? '' : 's'}`;
});

watch(
  () => orderedRows.value.length,
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

function networkDeviceChecked(device: NetworkDeviceSummary): string {
  const testedAt = device.networkSpeed?.testedAt;
  return testedAt == null ? '-' : formatClock(testedAt);
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

function networkDeviceProtocol(device: NetworkDeviceSummary): string {
  if (device.service === 'Wi-Fi') return 'WIFI';
  if (device.service === 'Ethernet') return 'ETH';
  return 'NET';
}

function networkDeviceStatus(device: NetworkDeviceSummary): string {
  return device.active ? 'operational' : 'unknown';
}
</script>

<template>
  <DashboardSectionCard section-id="liveChecks" eyebrow="Components" title="Live checks" fullscreen>
    <template #meta>
      <span class="pill">{{ rowPill }}</span>
      <span class="pill" :class="{ 'pill--reconnecting': isReconnecting }">
        <template v-if="isReconnecting">
          Reconnecting<span class="pill__dots" aria-hidden="true"><span>.</span><span>.</span><span>.</span></span>
        </template>
        <template v-else>{{ connectionState }}</template>
      </span>
    </template>

    <div class="components">
      <p v-if="!orderedRows.length" class="empty">No monitor targets yet. Add one under Sources.</p>
      <div v-else class="components-scroll">
        <div class="components-grid">
          <div class="components-grid__head" aria-hidden="true">
            <span class="components-grid__drag" />
            <span>Target</span>
            <span>IP/HOST</span>
            <span>Protocol</span>
            <span>Status</span>
            <span>Availability</span>
            <span>Speed</span>
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
              v-for="row in displayRows"
              :key="liveCheckRowKey(row)"
              class="component-row"
              :class="{
                'is-dragging': row.kind === 'target' && draggingId === row.target.id,
                'is-paused': row.kind === 'target' && !row.target.enabled,
                'component-row--network-device': row.kind === 'networkDevice',
              }"
              :data-reorder-id="row.kind === 'target' ? row.target.id : undefined"
            >
              <span
                v-if="row.kind === 'networkDevice'"
                class="target-drag-handle target-drag-handle--static"
                aria-hidden="true"
              />
              <button
                v-else
                type="button"
                class="target-drag-handle"
                :aria-label="`Reorder ${row.target.label}`"
                :disabled="isReordering"
                @pointerdown="onPointerDown(row.target.id, $event)"
              >
                <PhDotsSixVertical weight="bold" aria-hidden="true" />
              </button>

              <template v-if="row.kind === 'networkDevice'">
                <div class="component-name">
                  <span
                    class="component-name__color component-name__color--network"
                    aria-hidden="true"
                  />
                  <PhWifiHigh class="component-name__icon" weight="bold" aria-hidden="true" />
                  <div class="component-name__text">
                    <strong>{{ row.device.label }}</strong>
                  </div>
                </div>
                <div class="component-cell component-cell--ip stat">{{ row.device.interface }}</div>
                <div class="component-cell component-cell--protocol stat">{{ networkDeviceProtocol(row.device) }}</div>
                <div class="component-cell component-cell--status">
                  <span class="status" :class="networkDeviceStatus(row.device)">
                    <span class="dot" aria-hidden="true" />
                    {{ row.device.active ? 'active' : 'idle' }}
                  </span>
                </div>
                <div class="component-cell component-cell--history history history--empty" aria-hidden="true" />
                <div
                  class="component-cell component-cell--speed stat"
                  :title="networkSpeedTitle(row.device.networkSpeed)"
                >
                  {{ formatNetworkSpeed(row.device.networkSpeed) }}
                </div>
                <div class="component-cell stat">-</div>
                <div class="component-cell stat">{{ networkDeviceChecked(row.device) }}</div>
                <div class="component-cell stat">-</div>
                <div class="component-cell stat">-</div>
                <div class="component-cell component-cell--actions">
                  <span class="live-check-actions live-check-actions--network" aria-hidden="true">
                    <PhCheckCircle weight="fill" />
                  </span>
                </div>
              </template>

              <template v-else>
                <div class="component-name">
                  <span
                    class="component-name__color"
                    :style="{ backgroundColor: targetColorFor(row.target) }"
                    :aria-label="`${row.target.label} source color`"
                  />
                  <component
                    :is="targetServiceIcon(row.target.type, row.target.protocol)"
                    class="component-name__icon"
                    weight="bold"
                    aria-hidden="true"
                  />
                  <div class="component-name__text">
                    <PhStar
                      v-if="row.target.isFavorite"
                      class="component-name__favorite"
                      weight="fill"
                      aria-label="Favorite"
                    />
                    <strong>{{ row.target.label }}</strong>
                  </div>
                </div>
                <div class="component-cell component-cell--ip stat">{{ row.target.host }}</div>
                <div class="component-cell component-cell--protocol stat">{{ row.target.protocol.toUpperCase() }}</div>
                <div class="component-cell component-cell--status">
                  <div class="live-check-status">
                    <button
                      type="button"
                      class="live-check-status__toggle"
                      :class="row.target.enabled ? 'is-pause' : 'is-resume'"
                      :disabled="isPausing(row.target.id)"
                      :aria-label="
                        row.target.enabled
                          ? `Pause monitoring for ${row.target.label}`
                          : `Resume monitoring for ${row.target.label}`
                      "
                      @click.stop="togglePaused(row.target)"
                    >
                      <PhSpinner
                        v-if="isPausing(row.target.id)"
                        class="live-check-status__spinner"
                        weight="bold"
                        aria-hidden="true"
                      />
                      <PhPause v-else-if="row.target.enabled" weight="fill" aria-hidden="true" />
                      <PhPlay v-else weight="fill" aria-hidden="true" />
                    </button>
                    <span v-if="!row.target.enabled" class="status unknown">
                      <span class="dot" aria-hidden="true" />
                      paused
                    </span>
                    <span v-else class="status" :class="row.target.currentStatus">
                      <span class="dot" aria-hidden="true" />
                      {{ row.target.currentStatus }}
                    </span>
                  </div>
                </div>
                <div
                  class="component-cell component-cell--history history"
                  :aria-label="`${row.target.label} recent status bars`"
                  :title="targetTrendTitle(row.target)"
                >
                  <span
                    v-for="point in row.target.history"
                    :key="`${row.target.id}-${point.at}`"
                    class="bar"
                    :class="point.status"
                    :title="targetBarTitle(row.target, point)"
                  />
                </div>
                <div
                  class="component-cell component-cell--speed stat"
                  :title="networkSpeedTitle(row.target.networkSpeed)"
                >
                  {{ row.target.scope === 'gateway' ? formatNetworkSpeed(row.target.networkSpeed) : '-' }}
                </div>
                <div class="component-cell stat">{{ formatTargetLastValue(row.target) }}</div>
                <div class="component-cell stat">{{ lastChecked(row.target) }}</div>
                <div class="component-cell stat">{{ formatPct(row.target.uptimePct) }}</div>
                <div class="component-cell stat">{{ incidentState(row.target) }}</div>
                <div class="component-cell component-cell--actions">
                  <LiveCheckRowActions
                    :target="row.target"
                    :favoriting="isFavoriting(row.target.id)"
                    :pausing="isPausing(row.target.id)"
                    @set-alert="openAlertModal(row.target)"
                    @toggle-favorite="toggleFavorite(row.target)"
                    @toggle-paused="togglePaused(row.target)"
                  />
                </div>
              </template>
            </article>
          </TransitionGroup>
        </div>
      </div>

      <TargetAlertModal />

      <Pagination
        v-if="orderedRows.length"
        :current-page="page + 1"
        :total-items="orderedRows.length"
        :items-per-page="pageSize"
        order-label="custom"
        @update:page="emit('update:page', $event)"
      />
    </div>
  </DashboardSectionCard>
</template>
