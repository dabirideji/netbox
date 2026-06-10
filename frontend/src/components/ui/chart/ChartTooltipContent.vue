<script setup lang="ts">
import type { ChartConfig } from './interface';

defineProps<{
  title?: string;
  data?: {
    name: string;
    color: string;
    value: unknown;
  }[];
  config?: ChartConfig;
  hideLabel?: boolean;
  hideIndicator?: boolean;
}>();
</script>

<template>
  <div class="ui-chart-tooltip">
    <div v-if="title" class="ui-chart-tooltip__title">{{ title }}</div>
    <div v-if="data && data.length" class="ui-chart-tooltip__rows">
      <div v-for="(item, index) in data" :key="index" class="ui-chart-tooltip__row">
        <span
          v-if="!hideIndicator"
          class="ui-chart-tooltip__swatch"
          :style="{ backgroundColor: item.color, borderColor: item.color }"
        />
        <div class="ui-chart-tooltip__copy">
          <span v-if="!hideLabel" class="ui-chart-tooltip__label">
            {{ config?.[item.name]?.label || item.name }}
          </span>
          <span class="ui-chart-tooltip__value">{{ item.value }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
