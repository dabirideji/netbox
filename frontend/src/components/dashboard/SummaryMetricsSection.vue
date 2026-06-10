<script setup lang="ts">
import { formatMs, formatPct } from '../../format';
import DashboardSectionCard from './DashboardSectionCard.vue';

defineProps<{
  sampleCount?: number;
  gatewayLatencyMs: number | null;
  worstLoss: number;
  worstJitter: number;
}>();
</script>

<template>
  <DashboardSectionCard section-id="summary" eyebrow="Overview" title="Key metrics" :collapsible="false">
    <div class="summary-grid">
      <article class="metric-card">
        <span>Samples</span>
        <strong>{{ sampleCount ?? '—' }}</strong>
      </article>
      <article class="metric-card">
        <span>Gateway latency</span>
        <strong>{{ formatMs(gatewayLatencyMs) }}</strong>
      </article>
      <article class="metric-card">
        <span>Worst packet loss</span>
        <strong>{{ formatPct(worstLoss) }}</strong>
      </article>
      <article class="metric-card">
        <span>Worst jitter</span>
        <strong>{{ formatMs(worstJitter) }}</strong>
      </article>
    </div>
  </DashboardSectionCard>
</template>
