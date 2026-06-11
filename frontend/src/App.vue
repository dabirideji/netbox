<script setup lang="ts">
import { PhGithubLogo } from '@phosphor-icons/vue';
import { computed, onMounted, onUnmounted } from 'vue';
import { storeToRefs } from 'pinia';
import { subscribeStatus } from './api';
import AppChrome from './components/AppChrome.vue';
import DashboardNav from './components/dashboard/DashboardNav.vue';
import {
  HeroSection,
  IncidentLogSection,
  LiveChecksSection,
  SpeedTestSection,
  SummaryMetricsSection,
  SystemRatiosSection,
  TargetsConfigSection,
  TimelineSection,
} from './components/dashboard';
import { statusHeadline } from './format';
import {
  EVENT_PAGE_SIZE,
  LIVE_CHECKS_PAGE_SIZE,
  SPEED_TEST_PAGE_SIZE,
  RECONNECTING_STATE,
  useHistoryStore,
  useMonitorStore,
  usePersonalisationStore,
  useSpeedTestStore,
  useStorageStore,
  useTargetsStore,
} from './stores';

const appName = __NETBOX_APP_NAME__;

const monitor = useMonitorStore();
const history = useHistoryStore();
const speedTest = useSpeedTestStore();
const storage = useStorageStore();
const personalisation = usePersonalisationStore();
const targetsStore = useTargetsStore();

const { summary, connectionState } = storeToRefs(monitor);
const { points: historyPoints, targetSeries, events, eventTotal, rangeError, isRangeActive } = storeToRefs(history);
const {
  latestTest: latestSpeedTest,
  progress: speedProgress,
  policy: speedPolicy,
  stats: speedStats,
  tests: speedTests,
  total: speedTestTotal,
  isRunning: isSpeedRunning,
  error: speedError,
  buttonLabel: speedButtonLabel,
  canStart: canStartSpeedTest,
  policyNote: speedPolicyNote,
} = storeToRefs(speedTest);
const { stats: storageStats } = storeToRefs(storage);
const { eventPage, speedTestPage, liveChecksPage } = storeToRefs(personalisation);

const rangeFrom = computed({
  get: () => personalisation.rangeFrom,
  set: (value: string) => personalisation.setRangeFrom(value),
});
const rangeTo = computed({
  get: () => personalisation.rangeTo,
  set: (value: string) => personalisation.setRangeTo(value),
});

let historyTimer: number | undefined;
let eventSource: EventSource | undefined;

const headline = computed(() => statusHeadline(summary.value?.overallStatus ?? 'unknown'));
const isIndefinite = computed(() => summary.value?.endsAt == null);
const gateway = computed(() => summary.value?.targets.find((target) => target.scope === 'gateway'));
const worstLoss = computed(() => Math.max(...(summary.value?.targets.map((target) => target.packetLossPct) ?? [0])));
const worstJitter = computed(() => Math.max(...(summary.value?.targets.map((target) => target.jitterMs ?? 0) ?? [0])));

async function refreshRangeData(): Promise<void> {
  await Promise.all([history.refreshAll(), speedTest.refreshTests(), storage.loadStats()]);
}

function applyRange(): void {
  personalisation.resetRangePagination();
  personalisation.commitTimelineRange();
  void refreshRangeData();
}

function clearRange(): void {
  personalisation.clearRange();
  history.clearRangeError();
  void refreshRangeData();
}

function setLastHour(): void {
  personalisation.setLastHourRange();
  void refreshRangeData();
}

function setToday(): void {
  personalisation.setTodayRange();
  void refreshRangeData();
}

function setEventPage(page: number): void {
  personalisation.setEventPage(Math.max(0, page - 1));
  void history.refreshEvents();
}

function setSpeedTestPage(page: number): void {
  personalisation.setSpeedTestPage(Math.max(0, page - 1));
  void speedTest.refreshTests();
}

function setLiveChecksPage(page: number): void {
  personalisation.setLiveChecksPage(Math.max(0, page - 1));
}

function startHistoryRefresh(): void {
  if (historyTimer) window.clearInterval(historyTimer);
  historyTimer = window.setInterval(() => {
    if (document.visibilityState === 'hidden') return;
    void refreshRangeData();
  }, 10_000);
}

function handleVisibilityChange(): void {
  if (document.visibilityState === 'visible') {
    void refreshRangeData();
  }
}

onMounted(async () => {
  await Promise.all([personalisation.fetchPreferences(true), monitor.loadStatus()]);
  monitor.seedEventsFromSummary(EVENT_PAGE_SIZE);

  await Promise.allSettled([targetsStore.loadTargets(), speedTest.refreshPolicy(), refreshRangeData()]);
  startHistoryRefresh();
  document.addEventListener('visibilitychange', handleVisibilityChange);

  eventSource = subscribeStatus(
    (payload) => monitor.applyStreamPayload(payload),
    () => monitor.setConnectionState(RECONNECTING_STATE),
  );
});

onUnmounted(() => {
  if (historyTimer) window.clearInterval(historyTimer);
  document.removeEventListener('visibilitychange', handleVisibilityChange);
  eventSource?.close();
});
</script>

<template>
  <AppChrome />
  <main class="shell">
    <DashboardNav />
    <HeroSection
      :app-name="appName"
      :overall-status="summary?.overallStatus ?? 'unknown'"
      :headline="headline"
      :diagnosis="summary?.diagnosis ?? 'The dashboard will update every second.'"
      :network="summary?.network"
      :is-indefinite="isIndefinite"
      :started-at="summary?.startedAt"
      :ends-at="summary?.endsAt"
    />

    <SummaryMetricsSection
      :sample-count="summary?.sampleCount"
      :gateway-latency-ms="gateway?.lastLatencyMs ?? null"
      :worst-loss="worstLoss"
      :worst-jitter="worstJitter"
      :targets="summary?.targets ?? []"
    />

    <TimelineSection
      v-model:range-from="rangeFrom"
      v-model:range-to="rangeTo"
      :range-error="rangeError"
      :history="historyPoints"
      :target-history="targetSeries"
      :targets="summary?.targets ?? []"
      @apply-range="applyRange"
      @set-last-hour="setLastHour"
      @set-today="setToday"
      @clear-range="clearRange"
    />

    <TargetsConfigSection />

    <LiveChecksSection
      :targets="summary?.targets ?? []"
      :connection-state="connectionState"
      :page="liveChecksPage"
      :page-size="LIVE_CHECKS_PAGE_SIZE"
      @update:page="setLiveChecksPage"
    />

    <SpeedTestSection
      :latest-speed-test="latestSpeedTest"
      :speed-progress="speedProgress"
      :speed-policy="speedPolicy"
      :speed-stats="speedStats"
      :speed-tests="speedTests"
      :speed-test-total="speedTestTotal"
      :speed-test-page="speedTestPage"
      :speed-test-page-size="SPEED_TEST_PAGE_SIZE"
      :is-speed-running="isSpeedRunning"
      :can-start-speed-test="canStartSpeedTest"
      :speed-button-label="speedButtonLabel"
      :speed-policy-note="speedPolicyNote"
      :speed-error="speedError"
      @start-speed-test="speedTest.startTest"
      @update:page="setSpeedTestPage"
    />

    <IncidentLogSection
      :events="events"
      :event-total="eventTotal"
      :event-page="eventPage"
      :event-page-size="EVENT_PAGE_SIZE"
      @update:page="setEventPage"
    />

    <SystemRatiosSection
      :history="historyPoints"
      :targets="summary?.targets ?? []"
      :storage-stats="storageStats"
      :is-range-active="isRangeActive"
    />
  </main>
  <footer class="site-footer">
    <p>
      Built on Vibes by
      <a href="https://solomonmarvel.com" target="_blank" rel="noopener noreferrer">Marvelous Solomon</a>
      <a
        class="site-footer__github"
        href="https://github.com/solomonmarvel97"
        target="_blank"
        rel="noopener noreferrer"
        aria-label="Marvelous Solomon on GitHub"
      >
        <PhGithubLogo class="site-footer__github-icon" weight="fill" aria-hidden="true" />
      </a>
    </p>
  </footer>
</template>
