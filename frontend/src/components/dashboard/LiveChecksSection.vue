<script setup lang="ts">
import { computed } from 'vue';
import { formatClock, formatDate, formatMs, formatPct } from '../../format';
import { isReconnectingState } from '../../stores/monitor';
import type { TargetHistoryPoint, TargetSummary } from '../../types';
import DashboardSectionCard from './DashboardSectionCard.vue';

const props = defineProps<{
  targets: TargetSummary[];
  connectionState: string;
}>();

const isReconnecting = computed(() => isReconnectingState(props.connectionState));

function lastValue(target: TargetSummary): string {
  return target.lastLatencyMs == null ? target.lastError ?? 'fail' : formatMs(target.lastLatencyMs);
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
      <span class="pill" :class="{ 'pill--reconnecting': isReconnecting }">
        <template v-if="isReconnecting">
          Reconnecting<span class="pill__dots" aria-hidden="true"><span>.</span><span>.</span><span>.</span></span>
        </template>
        <template v-else>{{ connectionState }}</template>
      </span>
    </template>

    <div class="components">
      <article v-for="target in targets" :key="target.id" class="component-row">
        <div class="component-name">
          <strong>{{ target.label }}</strong>
          <small>{{ target.host }} · {{ target.scope }}</small>
        </div>
        <div class="status" :class="target.currentStatus">
          <span class="dot"></span>
          {{ target.currentStatus }}
        </div>
        <div class="history" :aria-label="`${target.label} recent status bars`" :title="targetTrendTitle(target)">
          <span
            v-for="point in target.history"
            :key="`${target.id}-${point.at}`"
            class="bar"
            :class="point.status"
            :title="targetBarTitle(target, point)"
          ></span>
        </div>
        <div class="stat">
          <span class="stat-label">Last</span>
          <strong>{{ lastValue(target) }}</strong>
        </div>
        <div class="stat">
          <span class="stat-label">Loss</span>
          <strong>{{ formatPct(target.packetLossPct) }}</strong>
        </div>
        <div class="stat">
          <span class="stat-label">Avg</span>
          <strong>{{ formatMs(target.avgLatencyMs) }}</strong>
        </div>
        <div class="stat">
          <span class="stat-label">Jitter</span>
          <strong>{{ formatMs(target.jitterMs) }}</strong>
        </div>
      </article>
    </div>
  </DashboardSectionCard>
</template>
