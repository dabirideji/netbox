<script setup lang="ts">
import { computed, ref } from 'vue';
import {
  chartViewBox,
  liveTargetHistoryToSeverityPoints,
  severityLabel,
  severitySegments,
  targetTrendToSeverityPoints,
  type SeverityPoint,
  type SeveritySegment,
} from '../../chart';
import { Button } from '../ui/button';
import { DateTimeInput } from '../ui/date-time-input';
import { formatClock, formatDate, formatMs, formatPct } from '../../format';
import { buildTimelineOverviewSeries } from '../../timelineOverview';
import type { HistoryPoint, TargetHistorySeries, TargetSummary } from '../../types';
import DashboardSectionCard from './DashboardSectionCard.vue';
import type { TargetTab } from '../../targetTabs';
import TargetTabs from './TargetTabs.vue';

const rangeFrom = defineModel<string>('rangeFrom', { default: '' });
const rangeTo = defineModel<string>('rangeTo', { default: '' });

const props = defineProps<{
  rangeError: string;
  history: HistoryPoint[];
  targetHistory: TargetHistorySeries[];
  targets: TargetSummary[];
}>();

const selectedTabId = ref<string>('overview');

const tabs = computed((): TargetTab[] => {
  const overview: TargetTab = { id: 'overview', label: 'Overview', overview: true };
  if (props.targetHistory.length) {
    return [
      overview,
      ...props.targetHistory.map((target) => ({
        id: target.id,
        label: target.label,
        type: target.type,
        protocol: target.protocol,
      })),
    ];
  }
  return [
    overview,
    ...props.targets.map((target) => ({
      id: target.id,
      label: target.label,
      type: target.type,
      protocol: target.protocol,
    })),
  ];
});

const activeTabLabel = computed(
  () => tabs.value.find((tab) => tab.id === selectedTabId.value)?.label ?? 'Overview',
);

const activePoints = computed((): SeverityPoint[] => {
  if (selectedTabId.value === 'overview') {
    return props.history;
  }

  const series = props.targetHistory.find((target) => target.id === selectedTabId.value);
  if (series?.points.length) {
    return targetTrendToSeverityPoints(series.points);
  }

  const live = props.targets.find((target) => target.id === selectedTabId.value);
  if (live?.history.length) {
    return liveTargetHistoryToSeverityPoints(live.history);
  }

  return [];
});

const isOverview = computed(() => selectedTabId.value === 'overview');
const overviewSeries = computed(() =>
  isOverview.value ? buildTimelineOverviewSeries(props.targets, props.targetHistory) : [],
);
const isRangeActive = computed(() => Boolean(rangeFrom.value || rangeTo.value));
const chartSegments = computed(() => (isOverview.value ? [] : severitySegments(activePoints.value)));
const latestHistoryPoint = computed(() => activePoints.value.at(-1) ?? null);
const worstHistoryPoint = computed(() =>
  activePoints.value.reduce<SeverityPoint | null>(
    (worst, point) => (worst == null || point.severity > worst.severity ? point : worst),
    null,
  ),
);
const worstHistoryLabel = computed(() => severityLabel(worstHistoryPoint.value?.severity ?? 0));
const chartAriaLabel = computed(() => `Network degradation line chart for ${activeTabLabel.value}`);

function segmentTitle(index: number, status: SeveritySegment['status']): string {
  const points = activePoints.value;
  const point = points[Math.min(index + 1, points.length - 1)] ?? points[index];
  if (!point) return 'No chart data yet';
  const timestamp = point.at ?? 0;
  return `${activeTabLabel.value} · ${formatDate(timestamp)} ${formatClock(timestamp)} · ${status} · ${formatMs(
    point.avgLatencyMs ?? null,
  )} avg · ${formatPct(point.failurePct ?? 0)} loss`;
}

const emit = defineEmits<{
  applyRange: [];
  setLastHour: [];
  setToday: [];
  clearRange: [];
}>();
</script>

<template>
  <DashboardSectionCard
    section-id="timeline"
    eyebrow="Timeline"
    title="Degradation over time"
    fullscreen
  >
    <div class="range-filter" aria-label="Date range filter">
      <DateTimeInput v-model="rangeFrom" label="From" />
      <DateTimeInput v-model="rangeTo" label="To" />
      <Button size="xs" @click="emit('applyRange')">Apply</Button>
      <Button variant="ghost" size="xs" @click="emit('setLastHour')">Last hour</Button>
      <Button variant="ghost" size="xs" @click="emit('setToday')">Today</Button>
      <Button variant="ghost" size="xs" @click="emit('clearRange')">All</Button>
    </div>
    <p v-if="rangeError" class="range-error">{{ rangeError }}</p>

    <TargetTabs v-model="selectedTabId" :tabs="tabs" aria-label="Timeline target" />

    <div class="chart-card">
      <div class="chart-wrap">
        <div class="chart-scale" aria-hidden="true">
          <span>Up</span>
          <span>Degraded</span>
          <span>Down</span>
        </div>
        <svg class="line-chart" :viewBox="chartViewBox" role="img" :aria-label="chartAriaLabel">
          <template v-if="isOverview">
            <path
              v-for="series in overviewSeries"
              :key="series.id"
              class="chart-line chart-line--overview"
              :style="{ stroke: series.color }"
              :d="series.path"
            >
              <title>{{ series.label }}</title>
            </path>
          </template>
          <template v-else>
            <path
              v-for="(segment, index) in chartSegments"
              :key="segment.d"
              class="chart-line chart-line--target"
              :class="segment.status"
              :d="segment.d"
            >
              <title>{{ segmentTitle(index, segment.status) }}</title>
            </path>
          </template>
        </svg>
      </div>
      <div class="chart-footer">
        <div
          v-if="isOverview"
          class="chart-legend chart-legend--sources"
          aria-label="Source colors"
        >
          <span v-for="series in overviewSeries" :key="series.id" class="chart-legend__source">
            <i :style="{ backgroundColor: series.color }" />
            {{ series.label }}
          </span>
        </div>
        <div v-else class="chart-legend" aria-label="Chart legend">
          <span class="operational"><i></i>Up</span>
          <span class="degraded"><i></i>Degraded</span>
          <span class="down"><i></i>Down</span>
        </div>
        <div class="chart-details">
          <template v-if="isOverview">
            <span>{{ overviewSeries.length }} sources</span>
            <span>
              {{
                overviewSeries.reduce((total, series) => total + series.pointCount, 0)
              }}
              points{{ isRangeActive ? ' in range' : '' }}
            </span>
          </template>
          <template v-else>
            <span>
              Latest
              {{
                latestHistoryPoint
                  ? `${formatMs(latestHistoryPoint.avgLatencyMs ?? null)} · ${formatPct(latestHistoryPoint.failurePct ?? 0)} loss`
                  : '-'
              }}
            </span>
            <span>Worst {{ activePoints.length ? worstHistoryLabel : '-' }}</span>
            <span>{{ activePoints.length }} points{{ isRangeActive ? ' in range' : '' }}</span>
          </template>
        </div>
      </div>
      <p v-if="isOverview ? !overviewSeries.length : !activePoints.length" class="empty">
        {{
          isOverview
            ? 'Waiting for source samples.'
            : `No samples for ${activeTabLabel} in this range yet.`
        }}
      </p>
    </div>
  </DashboardSectionCard>
</template>
