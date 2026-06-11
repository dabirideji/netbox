<script setup lang="ts">
import { computed, ref } from 'vue';
import { formatMs, formatPct } from '../../format';
import type { TargetSummary } from '../../types';
import DashboardSectionCard from './DashboardSectionCard.vue';
import { buildTargetTabs } from '../../targetTabs';
import TargetTabs from './TargetTabs.vue';

const props = defineProps<{
  sampleCount?: number;
  gatewayLatencyMs: number | null;
  worstLoss: number;
  worstJitter: number;
  targets: TargetSummary[];
}>();

const selectedTabId = ref('overview');

const tabs = computed(() => buildTargetTabs(props.targets));

const selectedTarget = computed(() =>
  selectedTabId.value === 'overview'
    ? null
    : props.targets.find((target) => target.id === selectedTabId.value) ?? null,
);

const metrics = computed(() => {
  if (!selectedTarget.value) {
    return [
      { label: 'Samples', value: props.sampleCount ?? '-' },
      { label: 'Gateway latency', value: formatMs(props.gatewayLatencyMs) },
      { label: 'Worst packet loss', value: formatPct(props.worstLoss) },
      { label: 'Worst jitter', value: formatMs(props.worstJitter) },
    ];
  }

  const target = selectedTarget.value;
  return [
    { label: 'Samples', value: String(target.samples) },
    { label: 'Last latency', value: formatMs(target.lastLatencyMs) },
    { label: 'Packet loss', value: formatPct(target.packetLossPct) },
    { label: 'Jitter', value: formatMs(target.jitterMs) },
  ];
});
</script>

<template>
  <DashboardSectionCard section-id="summary" eyebrow="Overview" title="Key metrics" :collapsible="false">
    <TargetTabs v-model="selectedTabId" :tabs="tabs" aria-label="Key metrics source" />

    <div class="summary-grid">
      <article v-for="metric in metrics" :key="metric.label" class="metric-card">
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
      </article>
    </div>
  </DashboardSectionCard>
</template>
