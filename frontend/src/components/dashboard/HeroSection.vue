<script setup lang="ts">
import { PhSpinner } from '@phosphor-icons/vue';
import NetboxLogo from '../NetboxLogo.vue';
import { computed, onMounted, onUnmounted, ref, toRef } from 'vue';
import { Button } from '../ui/button';
import { useNetworkAccess } from '../../composables/useNetworkAccess';
import { formatDuration, networkLabel } from '../../format';
import type { NetworkIdentity, Status } from '../../types';
import DashboardSectionCard from './DashboardSectionCard.vue';
import NetworkAccessModal from './NetworkAccessModal.vue';

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

const {
  isRefreshing,
  statusMessage,
  modalOpen,
  activeInterface,
  interfaces,
  interfacesLoading,
  closeModal,
  openNetworkModal,
  refreshNetworkList,
  selectNetworkInterface,
  saveManualNetworkName,
} = useNetworkAccess(toRef(props, 'network'));

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
        <NetboxLogo class="hero__logo" :size="18" />
        <span>{{ appName }}</span>
      </p>
      <h1 :class="overallStatus">{{ headline }}</h1>
    </template>

    <div class="hero__content">
      <div>
        <p class="diagnosis">{{ diagnosis }}</p>
        <div class="network-name-row">
          <p class="network-name">{{ networkLabel(network) }}</p>
          <Button
            type="button"
            variant="ghost"
            size="xs"
            class="network-name-row__action"
            :disabled="isRefreshing"
            @click="openNetworkModal"
          >
            <PhSpinner v-if="isRefreshing" class="network-name-row__spinner" weight="bold" aria-hidden="true" />
            {{ isRefreshing ? 'Loading…' : 'Choose network' }}
          </Button>
        </div>
        <p v-if="statusMessage && !modalOpen" class="network-name-hint">{{ statusMessage }}</p>
      </div>
      <div class="timer-card">
        <span>{{ isIndefinite ? 'Uptime' : 'Run window' }}</span>
        <strong>{{ isIndefinite ? elapsed : remaining }}</strong>
        <small>{{ isIndefinite ? 'Tracking until stopped' : `Elapsed ${elapsed}` }}</small>
      </div>
    </div>
  </DashboardSectionCard>

  <NetworkAccessModal
    :open="modalOpen"
    :busy="isRefreshing"
    :status-message="statusMessage"
    :interfaces="interfaces"
    :interfaces-loading="interfacesLoading"
    :active-interface="activeInterface"
    @close="closeModal"
    @refresh="refreshNetworkList"
    @select-interface="selectNetworkInterface"
    @save-manual="saveManualNetworkName"
  />
</template>
