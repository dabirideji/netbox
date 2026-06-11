import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import { fetchSpeedTests, recordSpeedTest } from '../api';
import { formatClock } from '../format';
import { parseDateRange } from '../range';
import { runSpeedTest, type SpeedTestProgress } from '../speed-test';
import { throttle } from '../utils/schedule';
import type { SpeedTestPolicy, SpeedTestResult, SpeedTestStats } from '../types';
import { usePersonalisationStore } from './personalisation';

export const SPEED_TEST_PAGE_SIZE = 10;

const EMPTY_STATS: SpeedTestStats = {
  avgDownloadMbps: null,
  avgUploadMbps: null,
  minLatencyMs: null,
  totalRuns: 0,
  completedRuns: 0,
};

function speedTestAllowed(policy: SpeedTestPolicy): boolean {
  if (!policy.enabled) return false;
  if (policy.minIntervalMs <= 0 && policy.dailyRunLimit <= 0) return true;
  return policy.canRun;
}

export const useSpeedTestStore = defineStore(
  'speedTest',
  () => {
    const tests = ref<SpeedTestResult[]>([]);
    const latestTest = ref<SpeedTestResult | null>(null);
    const total = ref(0);
    const loadingPage = ref<number | null>(null);
    const policy = ref<SpeedTestPolicy | null>(null);
    const stats = ref<SpeedTestStats>({ ...EMPTY_STATS });
    const error = ref('');
    const isRunning = ref(false);
    const progress = ref<SpeedTestProgress>({
      phase: 'idle',
      downloadMbps: null,
      uploadMbps: null,
      latencyMs: null,
      message: 'Ready when you are.',
    });

    const updateProgress = throttle((nextProgress: SpeedTestProgress) => {
      progress.value = nextProgress;
    }, 120);

    function reportProgress(nextProgress: SpeedTestProgress): void {
      if (nextProgress.phase === 'saving' || nextProgress.phase === 'complete' || nextProgress.phase === 'failed') {
        progress.value = nextProgress;
        return;
      }
      updateProgress(nextProgress);
    }

    const testOffset = computed(() => usePersonalisationStore().speedTestPage * SPEED_TEST_PAGE_SIZE);

    const buttonLabel = computed(() => {
      if (isRunning.value) return 'Running…';
      if (!policy.value) return 'Loading policy…';
      if (!policy.value.enabled) return 'Disabled';
      if (!policy.value.canRun && policy.value.minIntervalMs > 0 && policy.value.nextRunAt) {
        return `Available ${formatClock(policy.value.nextRunAt)}`;
      }
      if (!policy.value.canRun && policy.value.dailyRunLimit > 0) return 'Daily limit reached';
      return 'Run speed test';
    });

    const canStart = computed(() => {
      if (isRunning.value || !policy.value) return false;
      return speedTestAllowed(policy.value);
    });

    const policyNote = computed(() => {
      if (!policy.value) return 'Loading speed-test policy…';
      if (!policy.value.enabled) return 'Speed tests are disabled in config.';

      const { providerName, dailyRunLimit, runsLast24h, minIntervalMs } = policy.value;
      const parts = [providerName];

      if (dailyRunLimit > 0) {
        parts.push(`${runsLast24h}/${dailyRunLimit} runs in the last 24h`);
      }
      if (minIntervalMs > 0) {
        parts.push(`minimum ${Math.round(minIntervalMs / 60_000)} min between runs`);
      }
      if (dailyRunLimit === 0 && minIntervalMs === 0) {
        parts.push('no run limits');
      }

      return parts.join(' · ');
    });

    function selectedRange() {
      const personalisation = usePersonalisationStore();
      return parseDateRange({ from: personalisation.rangeFrom, to: personalisation.rangeTo });
    }

    async function refreshPolicy(): Promise<void> {
      try {
        const response = await fetchSpeedTests(1, {});
        policy.value = response.policy;
      } catch {
        policy.value = policy.value;
      }
    }

    async function refreshTests(): Promise<void> {
      const personalisation = usePersonalisationStore();
      loadingPage.value = personalisation.speedTestPage + 1;

      try {
        let response = await fetchSpeedTests(SPEED_TEST_PAGE_SIZE, selectedRange(), testOffset.value);
        const maxPage = Math.max(0, Math.ceil(response.total / SPEED_TEST_PAGE_SIZE) - 1);
        if (personalisation.speedTestPage > maxPage) {
          personalisation.setSpeedTestPage(maxPage);
          loadingPage.value = personalisation.speedTestPage + 1;
          response = await fetchSpeedTests(SPEED_TEST_PAGE_SIZE, selectedRange(), testOffset.value);
        }

        tests.value = response.tests;
        total.value = response.total;
        stats.value = response.stats;
        policy.value = response.policy;

        if (personalisation.speedTestPage === 0) {
          latestTest.value = response.tests[0] ?? null;
        }
      } catch {
        tests.value = tests.value;
      } finally {
        loadingPage.value = null;
      }
    }

    const scheduleRefreshTests = throttle(() => {
      void refreshTests();
    }, 500);

    function handleStreamSpeedTest(test: SpeedTestResult): void {
      latestTest.value = test;
      scheduleRefreshTests();
    }

    function resetPagination(): void {
      usePersonalisationStore().setSpeedTestPage(0);
    }

    async function startTest(): Promise<void> {
      if (!policy.value || isRunning.value || !speedTestAllowed(policy.value)) return;

      isRunning.value = true;
      error.value = '';

      try {
        const result = await runSpeedTest({
          policy: policy.value,
          onProgress: reportProgress,
        });

        progress.value = {
          ...progress.value,
          phase: 'saving',
          message: 'Saving speed-test result…',
        };

        const saved = await recordSpeedTest(result);
        policy.value = saved.policy;
        latestTest.value = saved.test;
        usePersonalisationStore().setSpeedTestPage(0);
        await refreshTests();

        progress.value = {
          phase: result.status === 'completed' ? 'complete' : 'failed',
          downloadMbps: result.downloadMbps,
          uploadMbps: result.uploadMbps,
          latencyMs: result.latencyMs,
          message: result.status === 'completed' ? 'Speed test saved.' : result.error ?? 'Speed test failed.',
        };
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Speed test failed';
        error.value = message;
        progress.value = {
          ...progress.value,
          phase: 'failed',
          message,
        };
      } finally {
        isRunning.value = false;
        void refreshPolicy();
      }
    }

    return {
      tests,
      latestTest,
      total,
      loadingPage,
      policy,
      stats,
      error,
      isRunning,
      progress,
      buttonLabel,
      canStart,
      policyNote,
      refreshPolicy,
      refreshTests,
      handleStreamSpeedTest,
      resetPagination,
      startTest,
    };
  },
  {
    persist: {
      key: 'netbox-speed-test',
      storage: localStorage,
      pick: ['tests', 'latestTest', 'total', 'policy', 'stats'],
    },
  },
);
