<script setup lang="ts">
import { computed } from 'vue';
import { DonutChartCard, type DonutChartSegment } from '../ui/chart';
import { formatBytes, formatCount, formatPct } from '../../format';
import type { HistoryPoint, StorageStats, TargetSummary } from '../../types';
import { countStatuses, statusSegments } from './status-mix';
import DashboardSectionCard from './DashboardSectionCard.vue';

const STATUS_DONUT_COLORS = ['#22c55e', '#eab308', '#ef4444'];
const STORAGE_DONUT_COLORS = ['#a1a1aa', '#27272a'];

interface DonutCard {
  title: string;
  eyebrow: string;
  caption: string;
  total: number;
  centralLabel?: string;
  centralSubLabel: string;
  emptyMessage: string;
  segments: DonutChartSegment[];
  colors: string[];
  metricLabel: string;
}

const props = defineProps<{
  history: HistoryPoint[];
  targets: TargetSummary[];
  storageStats: StorageStats | null;
  isRangeActive: boolean;
}>();

const statusDonutCards = computed<DonutCard[]>(() => {
  const timelineSegments = statusSegments(
    countStatuses(
      props.history.map((point) =>
        point.severity >= 2 ? 'down' : point.severity >= 1 ? 'degraded' : 'operational',
      ),
    ),
  );
  const componentSegments = statusSegments(countStatuses(props.targets.map((target) => target.currentStatus)));

  return [
    {
      title: 'Timeline ratio',
      eyebrow: 'History mix',
      caption: `${props.history.length} persisted point${props.history.length === 1 ? '' : 's'}`,
      total: props.history.length,
      centralSubLabel: 'Points',
      emptyMessage: 'No history points yet',
      segments: timelineSegments,
      colors: STATUS_DONUT_COLORS,
      metricLabel: 'Points',
    },
    {
      title: 'Component ratio',
      eyebrow: 'Live checks',
      caption: 'Current target states',
      total: props.targets.length,
      centralSubLabel: 'Targets',
      emptyMessage: 'No live targets yet',
      segments: componentSegments,
      colors: STATUS_DONUT_COLORS,
      metricLabel: 'Targets',
    },
  ];
});

const storageDonutCards = computed<DonutCard[]>(() => {
  if (!props.storageStats) {
    return [
      {
        title: 'Incidents',
        eyebrow: 'Stored records',
        caption: 'Loading storage usage…',
        total: 0,
        centralSubLabel: 'Stored',
        emptyMessage: 'Loading storage usage…',
        segments: [],
        colors: STORAGE_DONUT_COLORS,
        metricLabel: 'Incidents',
      },
      {
        title: 'Database file',
        eyebrow: 'On-disk usage',
        caption: 'Loading storage usage…',
        total: 0,
        centralSubLabel: 'Used',
        emptyMessage: 'Loading storage usage…',
        segments: [],
        colors: STORAGE_DONUT_COLORS,
        metricLabel: 'Bytes',
      },
    ];
  }

  const { usage, limits, percentUsed } = props.storageStats;
  const incidentRemaining = Math.max(0, limits.maxIncidents - usage.incidents);
  const databaseRemaining = Math.max(0, limits.maxDatabaseBytes - usage.databaseBytes);

  return [
    {
      title: 'Incidents',
      eyebrow: 'Stored records',
      caption: `${formatCount(usage.incidents)} / ${formatCount(limits.maxIncidents)} · ${formatPct(percentUsed.incidents)} full`,
      total: usage.incidents,
      centralSubLabel: 'Stored',
      emptyMessage: 'No incidents stored',
      segments: [
        {
          label: 'Stored incidents',
          count: usage.incidents,
          colorIndex: 0,
          legendValue: formatCount(usage.incidents),
        },
        {
          label: 'Remaining capacity',
          count: incidentRemaining,
          colorIndex: 1,
          legendValue: formatCount(incidentRemaining),
        },
      ],
      colors: STORAGE_DONUT_COLORS,
      metricLabel: 'Incidents',
    },
    {
      title: 'Database file',
      eyebrow: 'On-disk usage',
      caption: `${formatBytes(usage.databaseBytes)} / ${formatBytes(limits.maxDatabaseBytes)} · ${formatPct(percentUsed.database)} full`,
      total: usage.databaseBytes,
      centralLabel: formatBytes(usage.databaseBytes),
      centralSubLabel: 'Used',
      emptyMessage: 'No database usage yet',
      segments: [
        {
          label: 'Used space',
          count: usage.databaseBytes,
          colorIndex: 0,
          legendValue: formatBytes(usage.databaseBytes),
        },
        {
          label: 'Remaining capacity',
          count: databaseRemaining,
          colorIndex: 1,
          legendValue: formatBytes(databaseRemaining),
        },
      ],
      colors: STORAGE_DONUT_COLORS,
      metricLabel: 'Bytes',
    },
  ];
});
</script>

<template>
  <DashboardSectionCard section-id="systemRatios" eyebrow="System ratios" title="Storage and status mix" fullscreen>
    <template #meta>
      <span class="pill">
        {{
          storageStats
            ? storageStats.autoPrune
              ? 'Auto-prune on'
              : 'Auto-prune off'
            : 'Loading storage…'
        }}
      </span>
    </template>

    <div class="system-ratios-layout">
      <div class="donut-grid">
        <DonutChartCard
          v-for="card in statusDonutCards"
          :key="card.title"
          :eyebrow="card.eyebrow"
          :title="card.title"
          :caption="card.caption"
          :total="card.total"
          :central-label="card.centralLabel"
          :central-sub-label="card.centralSubLabel"
          :empty-message="card.emptyMessage"
          :segments="card.segments"
          :colors="card.colors"
          :metric-label="card.metricLabel"
        />
      </div>

      <div class="donut-grid">
        <DonutChartCard
          v-for="card in storageDonutCards"
          :key="card.title"
          :eyebrow="card.eyebrow"
          :title="card.title"
          :caption="card.caption"
          :total="card.total"
          :central-label="card.centralLabel"
          :central-sub-label="card.centralSubLabel"
          :empty-message="card.emptyMessage"
          :segments="card.segments"
          :colors="card.colors"
          :metric-label="card.metricLabel"
        />
      </div>
    </div>
  </DashboardSectionCard>
</template>
