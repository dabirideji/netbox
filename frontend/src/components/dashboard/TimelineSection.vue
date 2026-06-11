<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
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
import { targetServiceIcon } from '../../targetIcons';
import type { HistoryPoint, TargetHistorySeries, TargetProtocol, TargetSummary, TargetType } from '../../types';
import DashboardSectionCard from './DashboardSectionCard.vue';

const rangeFrom = defineModel<string>('rangeFrom', { default: '' });
const rangeTo = defineModel<string>('rangeTo', { default: '' });

const props = defineProps<{
  rangeError: string;
  history: HistoryPoint[];
  targetHistory: TargetHistorySeries[];
  targets: TargetSummary[];
}>();

interface TimelineTab {
  id: string;
  label: string;
  type?: TargetType;
  protocol?: TargetProtocol;
  overview?: boolean;
}

const selectedTabId = ref<string>('overview');
const tabsScrollRef = ref<HTMLElement | null>(null);
const tabsFadeLeft = ref(false);
const tabsFadeRight = ref(false);

const tabs = computed((): TimelineTab[] => {
  const overview: TimelineTab = { id: 'overview', label: 'Overview', overview: true };
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

function updateTabsScrollFades(): void {
  const element = tabsScrollRef.value;
  if (!element) {
    tabsFadeLeft.value = false;
    tabsFadeRight.value = false;
    return;
  }

  const maxScroll = element.scrollWidth - element.clientWidth;
  tabsFadeLeft.value = element.scrollLeft > 4;
  tabsFadeRight.value = maxScroll > 4 && element.scrollLeft < maxScroll - 4;
}

let tabsResizeObserver: ResizeObserver | undefined;

onMounted(() => {
  void nextTick(updateTabsScrollFades);
  tabsResizeObserver = new ResizeObserver(() => updateTabsScrollFades());
  if (tabsScrollRef.value) {
    tabsResizeObserver.observe(tabsScrollRef.value);
  }
});

onUnmounted(() => {
  tabsResizeObserver?.disconnect();
});

watch(
  tabs,
  (next) => {
    if (selectedTabId.value !== 'overview' && !next.some((tab) => tab.id === selectedTabId.value)) {
      selectedTabId.value = 'overview';
    }

    void nextTick(() => {
      if (tabsScrollRef.value && tabsResizeObserver) {
        tabsResizeObserver.observe(tabsScrollRef.value);
      }
      updateTabsScrollFades();
    });
  },
  { immediate: true, flush: 'post' },
);

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

const isRangeActive = computed(() => Boolean(rangeFrom.value || rangeTo.value));
const chartSegments = computed(() => severitySegments(activePoints.value));
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

    <div v-if="tabs.length > 1" class="timeline-tabs-shell horizontal-scroll-shell">
      <div
        class="horizontal-scroll-fade horizontal-scroll-fade--left"
        :class="{ 'is-visible': tabsFadeLeft }"
        aria-hidden="true"
      />
      <div
        ref="tabsScrollRef"
        class="timeline-tabs-scroll horizontal-scroll-track"
        role="tablist"
        aria-label="Timeline target"
        @scroll="updateTabsScrollFades"
      >
        <button
          v-for="tab in tabs"
          :key="tab.id"
          type="button"
          role="tab"
          class="timeline-tabs__button"
          :class="{ 'is-active': selectedTabId === tab.id }"
          :aria-selected="selectedTabId === tab.id"
          @click="selectedTabId = tab.id"
        >
          <component
            :is="targetServiceIcon(tab.type, tab.protocol, tab.overview)"
            class="timeline-tabs__icon"
            weight="bold"
            aria-hidden="true"
          />
          {{ tab.label }}
        </button>
      </div>
      <div
        class="horizontal-scroll-fade horizontal-scroll-fade--right"
        :class="{ 'is-visible': tabsFadeRight }"
        aria-hidden="true"
      />
    </div>

    <div class="chart-card">
      <div class="chart-wrap">
        <div class="chart-scale" aria-hidden="true">
          <span>Up</span>
          <span>Degraded</span>
          <span>Down</span>
        </div>
        <svg class="line-chart" :viewBox="chartViewBox" role="img" :aria-label="chartAriaLabel">
          <path
            v-for="(segment, index) in chartSegments"
            :key="segment.d"
            class="chart-line"
            :class="segment.status"
            :d="segment.d"
          >
            <title>{{ segmentTitle(index, segment.status) }}</title>
          </path>
        </svg>
      </div>
      <div class="chart-footer">
        <div class="chart-legend" aria-label="Chart legend">
          <span class="operational"><i></i>Up</span>
          <span class="degraded"><i></i>Degraded</span>
          <span class="down"><i></i>Down</span>
        </div>
        <div class="chart-details">
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
        </div>
      </div>
      <p v-if="!activePoints.length" class="empty">
        {{
          selectedTabId === 'overview'
            ? 'Waiting for persisted samples.'
            : `No samples for ${activeTabLabel} in this range yet.`
        }}
      </p>
    </div>
  </DashboardSectionCard>
</template>
