<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue';
import { formatClock, formatMbps } from '../../../format';
import {
  buildRatingSegments,
  clampGaugeScore,
  gaugeNeedleAngle,
  RATING_SEGMENT_INACTIVE_SOLID,
} from './scoreGaugeSegments';
import { mbpsToGaugeScore } from './speedGauge';

const props = withDefaults(
  defineProps<{
    label: string;
    valueMbps: number | null;
    maxMbps: number;
    testedAt?: number | null;
    active?: boolean;
    running?: boolean;
  }>(),
  {
    testedAt: null,
    active: false,
    running: false,
  },
);

const gaugeScore = computed(() => mbpsToGaugeScore(props.valueMbps, props.maxMbps));
const clampedScore = computed(() => clampGaugeScore(gaugeScore.value));
const targetNeedleAngle = computed(() => gaugeNeedleAngle(clampedScore.value));
const displayNeedleAngle = ref(0);
const ratingSegments = computed(() => buildRatingSegments(clampedScore.value, 'arc', RATING_SEGMENT_INACTIVE_SOLID));
const displayValue = computed(() => formatMbps(props.valueMbps));

let animationFrame: number | undefined;

watch(
  targetNeedleAngle,
  (target) => {
    if (animationFrame) window.cancelAnimationFrame(animationFrame);

    const start = displayNeedleAngle.value;
    const delta = target - start;
    const startedAt = performance.now();
    const durationMs = 550;

    function step(now: number): void {
      const progress = Math.min(1, (now - startedAt) / durationMs);
      const eased = 1 - (1 - progress) ** 3;
      displayNeedleAngle.value = start + delta * eased;
      if (progress < 1) {
        animationFrame = window.requestAnimationFrame(step);
      }
    }

    animationFrame = window.requestAnimationFrame(step);
  },
  { immediate: true },
);

onUnmounted(() => {
  if (animationFrame) window.cancelAnimationFrame(animationFrame);
});
</script>

<template>
  <article
    class="speed-arc-gauge"
    :class="{ 'is-active': active, 'is-running': running }"
    role="img"
    :aria-label="`${label} ${displayValue}`"
  >
    <div class="speed-arc-gauge__header">
      <span class="speed-arc-gauge__label">{{ label }}</span>
      <span v-if="running" class="speed-arc-gauge__meta speed-arc-gauge__live speed-running-label">
        <PhSpinner class="speed-running-label__icon" weight="bold" aria-hidden="true" />
        Running
      </span>
      <time
        v-else-if="testedAt"
        class="speed-arc-gauge__meta speed-arc-gauge__time"
        :datetime="new Date(testedAt).toISOString()"
      >
        {{ formatClock(testedAt) }}
      </time>
    </div>

    <div class="speed-arc-gauge__visual">
      <svg class="speed-arc-gauge__svg" viewBox="0 0 120 68" fill="none" aria-hidden="true">
        <path
          v-for="(segment, index) in ratingSegments"
          :key="index"
          class="speed-arc-gauge__segment"
          :class="{ 'speed-arc-gauge__segment--active': segment.active }"
          :d="segment.path"
          fill="none"
          :stroke="segment.color"
          stroke-width="14"
          stroke-linecap="butt"
        />
        <g class="speed-arc-gauge__needle" :transform="`rotate(${displayNeedleAngle} 60 60)`">
          <line x1="60" y1="60" x2="16" y2="60" class="speed-arc-gauge__needle-stem" />
          <circle cx="60" cy="60" r="5" class="speed-arc-gauge__needle-hub" />
        </g>
      </svg>
    </div>

    <div class="speed-arc-gauge__value-wrap">
      <strong class="speed-arc-gauge__value">{{ displayValue }}</strong>
      <span class="speed-arc-gauge__scale">0 – {{ maxMbps >= 1000 ? `${maxMbps / 1000}G` : `${maxMbps}M` }}</span>
    </div>
  </article>
</template>
