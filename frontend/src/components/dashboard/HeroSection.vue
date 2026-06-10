<script setup lang="ts">
import { PhCube } from '@phosphor-icons/vue';
import { networkLabel } from '../../format';
import type { NetworkIdentity, Status } from '../../types';
import DashboardSectionCard from './DashboardSectionCard.vue';

defineProps<{
  appName: string;
  overallStatus: Status | 'unknown';
  headline: string;
  diagnosis: string;
  network?: NetworkIdentity;
  isIndefinite: boolean;
  elapsed: string;
  remaining: string;
}>();
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
