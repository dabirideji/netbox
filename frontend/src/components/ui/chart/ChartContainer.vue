<script setup lang="ts">
import { computed } from 'vue';
import type { HTMLAttributes } from 'vue';
import type { ChartConfig } from './interface';

const props = defineProps<{
  config: ChartConfig;
  class?: HTMLAttributes['class'];
}>();

const styles = computed(() => {
  const colors: Record<string, string> = {
    '--vis-donut-background-color': 'transparent',
    '--vis-donut-segment-stroke-color': 'transparent',
    '--vis-donut-segment-stroke-width': '0px',
    '--vis-donut-central-label-text-color': 'var(--text)',
    '--vis-donut-central-sub-label-text-color': 'var(--faint)',
    '--vis-nested-donut-background-color': 'transparent',
    '--vis-nested-donut-segment-stroke-color': 'transparent',
    '--vis-nested-donut-central-label-text-color': 'var(--text)',
    '--vis-nested-donut-central-sublabel-text-color': 'var(--faint)',
  };

  Object.entries(props.config).forEach(([key, value]) => {
    if (value.theme) {
      colors[`--color-${key}`] = value.theme.light;
    } else if (value.color) {
      colors[`--color-${key}`] = value.color;
    }
  });

  return colors;
});
</script>

<template>
  <div class="ui-chart-container" :class="props.class" :style="styles">
    <slot />
  </div>
</template>
