<script setup lang="ts">
import { computed, watch } from 'vue';
import { Pagination } from '../ui/pagination';
import { formatClock, formatDate, formatMs, formatPct } from '../../format';
import { isReconnectingState } from '../../stores/monitor';
import { targetServiceIcon } from '../../targetIcons';
import {
  compareTargetsByScopeThenLabel,
  shouldShowScopeHeader,
  targetScopeLabel,
} from '../../targetScope';
import type { TargetHistoryPoint, TargetSummary } from '../../types';
import DashboardSectionCard from './DashboardSectionCard.vue';

const props = defineProps<{
  targets: TargetSummary[];
  connectionState: string;
  page: number;
  pageSize: number;
}>();

const emit = defineEmits<{
  'update:page': [page: number];
}>();

const isReconnecting = computed(() => isReconnectingState(props.connectionState));

const sortedTargets = computed(() => [...props.targets].sort(compareTargetsByScopeThenLabel));

const paginatedTargets = computed(() => {
  const start = props.page * props.pageSize;
  return sortedTargets.value.slice(start, start + props.pageSize);
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

function lastValue(target: TargetSummary): string {
  return target.lastLatencyMs == null ? target.lastError ?? 'fail' : formatMs(target.lastLatencyMs);
}

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

function targetBarTitle(target: TargetSummary, point: TargetHistoryPoint): string {
  return `${target.label} · ${formatDate(point.at)} ${formatClock(point.at)} · ${point.status} · ${
    point.latencyMs == null ? point.error ?? 'fail' : formatMs(point.latencyMs)
  }`;
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
            <span>Target</span>
            <span>Protocol</span>
            <span>Status</span>
            <span>Availability</span>
            <span>Last</span>
            <span>Checked</span>
            <span>Uptime</span>
            <span>Incident</span>
          </div>

          <template v-for="(target, index) in paginatedTargets" :key="target.id">
            <div
              v-if="shouldShowScopeHeader(paginatedTargets, index)"
              class="components-scope-head"
              role="presentation"
            >
              <span class="components-scope-head__label">{{ targetScopeLabel(target.scope) }}</span>
              <span class="components-scope-head__hint">
                {{ target.scope === 'gateway' ? 'Router and LAN' : 'Online services' }}
              </span>
            </div>

            <article
            v-memo="[
              target.id,
              target.scope,
              target.type,
              target.protocol,
              target.currentStatus,
              target.lastLatencyMs,
              target.lastCheckedAt,
              target.uptimePct,
              target.activeIncident?.to,
              target.history.length,
              target.history.at(-1)?.at,
              target.history.at(-1)?.status,
            ]"
            class="component-row"
          >
            <div class="component-name">
              <component
                :is="targetServiceIcon(target.type, target.protocol)"
                class="component-name__icon"
                weight="bold"
                aria-hidden="true"
              />
              <div class="component-name__text">
                <strong>{{ target.label }}</strong>
                <small>{{ target.host }}</small>
              </div>
            </div>
            <div class="component-cell component-cell--protocol stat">{{ target.protocol.toUpperCase() }}</div>
            <div class="component-cell component-cell--status">
              <span class="status" :class="target.currentStatus">
                <span class="dot"></span>
                {{ target.currentStatus }}
              </span>
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
            <div class="component-cell stat" :title="lastValue(target)">{{ lastValue(target) }}</div>
            <div class="component-cell stat">{{ lastChecked(target) }}</div>
            <div class="component-cell stat">{{ formatPct(target.uptimePct) }}</div>
            <div class="component-cell stat">{{ incidentState(target) }}</div>
            </article>
          </template>
        </div>
      </div>

      <Pagination
        v-if="targets.length"
        :current-page="page + 1"
        :total-items="targets.length"
        :items-per-page="pageSize"
        order-label="alphabetical"
        @update:page="emit('update:page', $event)"
      />
    </div>
  </DashboardSectionCard>
</template>
