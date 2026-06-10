<script setup lang="ts">
import { computed } from 'vue';
import { Donut } from '@unovis/ts';
import { VisDonut, VisSingleContainer } from '@unovis/vue';
import ChartContainer from './ChartContainer.vue';
import ChartSingleTooltip from './ChartSingleTooltip.vue';
import type { ChartConfig } from './interface';

export interface DonutChartSegment {
  label: string;
  count: number;
  colorIndex: number;
  legendValue?: string;
}

const props = defineProps<{
  eyebrow: string;
  title: string;
  caption: string;
  total: number;
  centralSubLabel: string;
  emptyMessage: string;
  segments: DonutChartSegment[];
  colors: string[];
  metricLabel?: string;
  centralLabel?: string;
}>();

const donutSegmentSelector = Donut.selectors.segment;
const chartHeight = 168;
const chartConfig = computed<ChartConfig>(() => ({
  count: { label: props.metricLabel ?? 'Count' },
}));

const rowsWithData = computed(() => props.segments.filter((segment) => segment.count > 0));
const segmentTotal = computed(() => rowsWithData.value.reduce((sum, segment) => sum + segment.count, 0));
const hasData = computed(() => segmentTotal.value > 0);
const chartRows = computed(() => (hasData.value ? rowsWithData.value : [{ label: 'No data', count: 1, colorIndex: 0 }]));
</script>

<template>
  <article class="donut-card">
    <div class="donut-card__copy">
      <p class="eyebrow">{{ eyebrow }}</p>
      <h3>{{ title }}</h3>
      <span>{{ caption }}</span>
    </div>

    <div class="donut-card__chart">
      <div class="donut-card__canvas" :style="{ width: `${chartHeight}px`, height: `${chartHeight}px` }">
        <ChartContainer :config="chartConfig" class="donut-card__container" :class="{ 'is-empty': !hasData }">
          <VisSingleContainer :data="chartRows" :height="chartHeight">
            <VisDonut
              :value="(segment: DonutChartSegment) => segment.count"
              :color="(segment: DonutChartSegment) =>
                hasData ? colors[segment.colorIndex % colors.length] : 'var(--faint)'"
              :arc-width="28"
              :corner-radius="2"
              :pad-angle="0.012"
              :central-label="centralLabel ?? String(total)"
              :central-sub-label="centralSubLabel"
              :show-background="hasData"
              background-color="transparent"
            />
            <ChartSingleTooltip
              v-if="hasData"
              :selector="donutSegmentSelector"
              index="label"
              :config="chartConfig"
              :donut-segment-total="segmentTotal"
              :donut-metric-label="metricLabel"
            />
          </VisSingleContainer>
        </ChartContainer>
      </div>

      <div v-if="!hasData" class="donut-card__empty">
        <span>{{ emptyMessage }}</span>
      </div>
    </div>

    <div v-if="hasData" class="donut-card__legend">
      <div v-for="segment in rowsWithData" :key="segment.label" class="donut-card__legend-item">
        <span class="donut-card__legend-swatch" :style="{ backgroundColor: colors[segment.colorIndex % colors.length] }" />
        <span class="donut-card__legend-label">{{ segment.label }}</span>
        <span class="donut-card__legend-count">({{ segment.legendValue ?? segment.count }})</span>
      </div>
    </div>

    <div v-if="$slots.default" class="donut-card__footer">
      <slot />
    </div>
  </article>
</template>
