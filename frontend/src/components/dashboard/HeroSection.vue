<script setup lang="ts">
import { PhCube } from '@phosphor-icons/vue';
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { formatDuration, networkLabel } from '../../format';
import type { NetworkIdentity, Status } from '../../types';
import DashboardSectionCard from './DashboardSectionCard.vue';

const props = defineProps<{
  appName: string;
  overallStatus: Status | 'unknown';
  headline: string;
  diagnosis: string;
  network?: NetworkIdentity;
  isIndefinite: boolean;
  startedAt?: number;
  endsAt?: number | null;
}>();

const now = ref(Date.now());
let timer: number | undefined;

const elapsed = computed(() => formatDuration(Math.max(0, now.value - (props.startedAt ?? now.value))));
const remaining = computed(() => {
  if (!props.endsAt) return 'Live';
  return formatDuration(Math.max(0, props.endsAt - now.value));
});

onMounted(() => {
  timer = window.setInterval(() => {
    now.value = Date.now();
  }, 1000);
});

onUnmounted(() => {
  if (timer) window.clearInterval(timer);
});
</script>

<template>
  <DashboardSectionCard section-id="hero" class="dashboard-card--hero" :collapsible="false">
    <template #header>
      <p class="eyebrow hero__brand">
        <PhCube class="hero__logo" :size="16" weight="fill" aria-hidden="true" />
        <span>{{ appName }}</span>
      </p>
      <h1 :class="overallStatus">{{ headline }}</h1>
    </template>

    <div class="hero__content">
      <div>
        <p class="diagnosis">{{ diagnosis }}</p>
        <p class="network-name">{{ networkLabel(network) }}</p>
      </div>
      <div class="timer-card">
        <span>{{ isIndefinite ? 'Uptime' : 'Run window' }}</span>
        <strong>{{ isIndefinite ? elapsed : remaining }}</strong>
        <small>{{ isIndefinite ? 'Tracking until stopped' : `Elapsed ${elapsed}` }}</small>
      </div>
    </div>
  </DashboardSectionCard>
</template>
