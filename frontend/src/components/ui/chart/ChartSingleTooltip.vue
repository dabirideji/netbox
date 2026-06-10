<script setup lang="ts">
import type { BulletLegendItemInterface } from '@unovis/ts';
import { omit } from '@unovis/ts';
import { VisTooltip } from '@unovis/vue';
import { createApp, onMounted, onUnmounted, ref, type App, type Component } from 'vue';
import { DONUT_TOOLTIP_META_KEYS, formatDonutTooltipMetric } from './chartDonutTooltip';
import ChartTooltipContent from './ChartTooltipContent.vue';
import type { ChartConfig } from './interface';

const tooltipContainer = ref<HTMLElement | undefined>(undefined);
let activeTooltipApp: App | null = null;

function destroyActiveTooltipApp(): void {
  if (activeTooltipApp) {
    activeTooltipApp.unmount();
    activeTooltipApp = null;
  }
}

onMounted(() => {
  tooltipContainer.value = typeof document !== 'undefined' ? document.body : undefined;
});

onUnmounted(() => {
  destroyActiveTooltipApp();
});

const props = defineProps<{
  selector: string;
  index: string;
  items?: BulletLegendItemInterface[];
  valueFormatter?: (tick: number, i?: number, ticks?: number[]) => string;
  customTooltip?: Component;
  config?: ChartConfig;
  titleFormatter?: (value: unknown) => string;
  donutSegmentTotal?: number;
  donutValueKey?: string;
  donutMetricLabel?: string;
}>();

const wm = new WeakMap<object, string>();

function template(d: Record<string, unknown>, i: number, elements: (HTMLElement | SVGElement)[]): string {
  const valueFormatter = props.valueFormatter ?? ((tick: number) => `${tick}`);
  const titleFormatter = props.titleFormatter ?? ((value: unknown) => `${value}`);
  const donutVk = props.donutValueKey ?? 'count';
  const configRestrictsKeys =
    props.config != null && typeof props.config === 'object' && Object.keys(props.config).length > 0;
  const cacheTooltip = props.donutSegmentTotal == null;

  const data =
    props.index in d ? d : d.data && typeof d.data === 'object' && props.index in d.data ? (d.data as Record<string, unknown>) : d;

  if (cacheTooltip && wm.has(d)) {
    return wm.get(d) as string;
  }

  const resolvedConfig: ChartConfig = { ...(props.config ?? {}) };
  if (props.donutSegmentTotal != null && props.donutSegmentTotal >= 0) {
    const existing = resolvedConfig[donutVk];
    const inherited =
      typeof existing === 'object' && existing && 'label' in existing && existing.label != null
        ? String(existing.label)
        : undefined;
    resolvedConfig[donutVk] = {
      ...(typeof existing === 'object' && existing ? existing : {}),
      label: inherited ?? props.donutMetricLabel ?? 'Records',
    };
  }

  let elementColor: string | undefined;
  if (elements && elements[i]) {
    elementColor = getComputedStyle(elements[i]).fill;
  }

  const omittedData = Object.entries(omit(data, [props.index]))
    .filter(([key]) => {
      if (key === 'id') return false;
      if (DONUT_TOOLTIP_META_KEYS.has(key)) return false;
      if (configRestrictsKeys) return Boolean(props.config?.[key]);
      return true;
    })
    .map(([key, value]) => {
      const legendReference = props.items?.find((item) => item.name === key);
      const color = legendReference?.color || elementColor;
      let displayValue: string;
      if (props.donutSegmentTotal != null && props.donutSegmentTotal >= 0 && key === donutVk) {
        displayValue = formatDonutTooltipMetric(value, props.donutSegmentTotal);
      } else {
        const n = typeof value === 'number' ? value : Number(value);
        displayValue = valueFormatter(Number.isFinite(n) ? n : 0);
      }
      return { ...legendReference, value: displayValue, name: key, color };
    });

  const TooltipComponent = props.customTooltip ?? ChartTooltipContent;
  destroyActiveTooltipApp();
  const mountHost = document.createElement('div');
  activeTooltipApp = createApp(TooltipComponent, {
    title: titleFormatter(data[props.index]),
    data: omittedData,
    config: resolvedConfig,
  });
  activeTooltipApp.mount(mountHost);

  const html = mountHost.innerHTML;
  destroyActiveTooltipApp();
  if (cacheTooltip) wm.set(d, html);
  return html;
}
</script>

<template>
  <VisTooltip
    :container="tooltipContainer"
    :horizontal-shift="20"
    :vertical-shift="20"
    :triggers="{ [selector]: template }"
    class-name="custom-tooltip-container"
  />
</template>
