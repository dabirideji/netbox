<script setup lang="ts">
import { computed } from 'vue';
import { PhSpinner } from '@phosphor-icons/vue';
import { useApiLoading } from '../composables/useApiLoading';

const { apiPendingCount } = useApiLoading();
const showSpinner = computed(() => apiPendingCount.value > 0);
</script>

<template>
  <Transition name="api-spinner-fade">
    <div
      v-if="showSpinner"
      class="api-loading-spinner"
      role="status"
      aria-live="polite"
      aria-busy="true"
      aria-label="Loading data from server"
    >
      <PhSpinner class="api-loading-spinner__icon" weight="bold" />
    </div>
  </Transition>
</template>
