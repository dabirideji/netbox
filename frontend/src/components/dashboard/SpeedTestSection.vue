<script setup lang="ts">
import { computed } from 'vue';
import { Button } from '../ui/button';
import { resolveGaugeMaxMbps, SpeedArcGauge } from '../ui/gauge';
import { Pagination } from '../ui/pagination';
import { formatClock, formatDate, formatMbps, formatMs } from '../../format';
import type { SpeedTestPolicy, SpeedTestResult, SpeedTestStats } from '../../types';
import type { SpeedTestProgress } from '../../speed-test';
import DashboardSectionCard from './DashboardSectionCard.vue';

const props = defineProps<{
  latestSpeedTest: SpeedTestResult | null;
  speedProgress: SpeedTestProgress;
  speedPolicy: SpeedTestPolicy | null;
  speedStats: SpeedTestStats;
  speedTests: SpeedTestResult[];
  speedTestTotal: number;
  speedTestPage: number;
  speedTestPageSize: number;
  isSpeedRunning: boolean;
  canStartSpeedTest: boolean;
  speedButtonLabel: string;
  speedPolicyNote: string;
  speedError: string;
}>();

const emit = defineEmits<{
  startSpeedTest: [];
  'update:page': [page: number];
}>();

const displayDownloadMbps = computed(
  () => props.speedProgress.downloadMbps ?? props.latestSpeedTest?.downloadMbps ?? null,
);
const displayUploadMbps = computed(
  () => props.speedProgress.uploadMbps ?? props.latestSpeedTest?.uploadMbps ?? null,
);
const displayLatencyMs = computed(
  () => props.speedProgress.latencyMs ?? props.latestSpeedTest?.latencyMs ?? null,
);

const gaugeMaxMbps = computed(() =>
  resolveGaugeMaxMbps(
    displayDownloadMbps.value,
    displayUploadMbps.value,
    props.speedStats.avgDownloadMbps,
    props.speedStats.avgUploadMbps,
    ...props.speedTests.map((test) => test.downloadMbps),
    ...props.speedTests.map((test) => test.uploadMbps),
  ),
);

const downloadRunning = computed(
  () => props.isSpeedRunning && ['discovering', 'download'].includes(props.speedProgress.phase),
);
const uploadRunning = computed(() => props.isSpeedRunning && props.speedProgress.phase === 'upload');
const downloadActive = computed(() => downloadRunning.value || props.speedProgress.phase === 'complete');
const uploadActive = computed(() => uploadRunning.value || props.speedProgress.phase === 'complete');

const storedRunsLabel = computed(
  () => `${props.speedTestTotal} stored run${props.speedTestTotal === 1 ? '' : 's'}`,
);

const dailyLimitLabel = computed(() => {
  if (!props.speedPolicy) return '-';
  if (props.speedPolicy.dailyRunLimit <= 0) return 'Unlimited';
  return `${props.speedPolicy.runsLast24h}/${props.speedPolicy.dailyRunLimit}`;
});

const minIntervalLabel = computed(() => {
  if (!props.speedPolicy) return '-';
  if (props.speedPolicy.minIntervalMs <= 0) return 'None';
  return `${Math.round(props.speedPolicy.minIntervalMs / 60_000)} min`;
});
</script>

<template>
  <DashboardSectionCard
    section-id="speedTest"
    class="speed-panel"
    eyebrow="Speed test"
    title="Network speed"
    fullscreen
  >
    <template #meta>
      <span class="pill">{{ isSpeedRunning ? 'Testing…' : latestSpeedTest ? 'Latest run' : 'Not tested yet' }}</span>
    </template>

    <div class="speed-shell">
      <div class="speed-main">
        <div class="speed-gauge-grid">
          <SpeedArcGauge
            label="Download"
            :value-mbps="displayDownloadMbps"
            :max-mbps="gaugeMaxMbps"
            :tested-at="latestSpeedTest?.testedAt ?? null"
            :active="downloadActive"
            :running="downloadRunning"
          />
          <SpeedArcGauge
            label="Upload"
            :value-mbps="displayUploadMbps"
            :max-mbps="gaugeMaxMbps"
            :tested-at="latestSpeedTest?.testedAt ?? null"
            :active="uploadActive"
            :running="uploadRunning"
          />
        </div>

        <div class="speed-actions">
          <Button size="xs" :disabled="!canStartSpeedTest" @click="emit('startSpeedTest')">
            {{ speedButtonLabel }}
          </Button>
          <span class="speed-phase" :class="speedProgress.phase">{{ speedProgress.message }}</span>
        </div>

        <p class="speed-note">
          {{ speedPolicyNote }}. Each test uses real download/upload traffic through M-Lab when you press the button.
          <a v-if="speedPolicy" :href="speedPolicy.dataPolicyUrl" target="_blank" rel="noreferrer">Data policy</a>
        </p>
        <p v-if="speedError" class="range-error">{{ speedError }}</p>
      </div>

      <aside class="speed-insights">
        <div class="speed-insights__header">
          <span>Session insights</span>
          <strong>24h window</strong>
        </div>

        <div class="speed-insight-grid">
          <article class="speed-insight-card">
            <span>Latency</span>
            <strong>{{ formatMs(displayLatencyMs) }}</strong>
          </article>
          <article class="speed-insight-card">
            <span>Best latency</span>
            <strong>{{ formatMs(speedStats.minLatencyMs) }}</strong>
          </article>
          <article class="speed-insight-card">
            <span>Runs</span>
            <strong>{{ speedStats.completedRuns }}/{{ speedStats.totalRuns }}</strong>
          </article>
          <article class="speed-insight-card">
            <span>Avg download</span>
            <strong>{{ formatMbps(speedStats.avgDownloadMbps) }}</strong>
          </article>
          <article class="speed-insight-card">
            <span>Avg upload</span>
            <strong>{{ formatMbps(speedStats.avgUploadMbps) }}</strong>
          </article>
          <article class="speed-insight-card">
            <span>Peak download</span>
            <strong>{{ formatMbps(displayDownloadMbps) }}</strong>
          </article>
          <article class="speed-insight-card">
            <span>Peak upload</span>
            <strong>{{ formatMbps(displayUploadMbps) }}</strong>
          </article>
        </div>

        <dl class="speed-policy-list">
          <div>
            <dt>Provider</dt>
            <dd>{{ speedPolicy?.providerName ?? '-' }}</dd>
          </div>
          <div>
            <dt>Daily limit</dt>
            <dd>{{ dailyLimitLabel }}</dd>
          </div>
          <div>
            <dt>Min interval</dt>
            <dd>{{ minIntervalLabel }}</dd>
          </div>
        </dl>
      </aside>
    </div>

    <div class="speed-history">
      <div class="speed-history__header">
        <h3>Recent runs</h3>
        <span>{{ storedRunsLabel }}</span>
      </div>

      <p v-if="!speedTests.length" class="empty">No speed tests recorded yet.</p>
      <div v-else class="speed-history__table" role="table" aria-label="Recent speed tests">
        <div class="speed-history__row speed-history__row--head" role="row">
          <span role="columnheader">Status</span>
          <span role="columnheader">Server</span>
          <span role="columnheader">Download</span>
          <span role="columnheader">Upload</span>
          <span role="columnheader">Latency</span>
          <span role="columnheader">When</span>
        </div>
        <article
          v-for="test in speedTests"
          :key="test.id"
          class="speed-history__row"
          :class="test.status"
          role="row"
        >
          <span class="speed-history__status" role="cell">
            <i aria-hidden="true"></i>
            {{ test.status === 'completed' ? 'Completed' : 'Failed' }}
          </span>
          <span class="speed-history__server" role="cell">
            <strong>{{ test.serverLocation || test.serverName || test.provider }}</strong>
            <small v-if="test.error">{{ test.error }}</small>
          </span>
          <span role="cell">{{ formatMbps(test.downloadMbps) }}</span>
          <span role="cell">{{ formatMbps(test.uploadMbps) }}</span>
          <span role="cell">{{ formatMs(test.latencyMs) }}</span>
          <time role="cell" :datetime="new Date(test.testedAt).toISOString()">
            <span>{{ formatClock(test.testedAt) }}</span>
            <small>{{ formatDate(test.testedAt) }}</small>
          </time>
        </article>
      </div>

      <Pagination
        :current-page="speedTestPage + 1"
        :total-items="speedTestTotal"
        :items-per-page="speedTestPageSize"
        @update:page="emit('update:page', $event)"
      />
    </div>
  </DashboardSectionCard>
</template>
