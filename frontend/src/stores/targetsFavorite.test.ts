import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { setTargetFavorite as setTargetFavoriteApi } from '../api';
import { useMonitorStore } from './monitor';
import { useTargetsStore } from './targets';
import type { MonitorTarget, StatusSummary } from '../types';

vi.mock('../api', () => ({
  setTargetFavorite: vi.fn(),
}));

function sampleTarget(id: string, favorite = false): MonitorTarget {
  return {
    id,
    host: id,
    label: id,
    scope: 'external',
    type: 'host',
    protocol: 'icmp',
    group: 'Default',
    environment: 'local',
    enabled: true,
    intervalMs: 1_000,
    timeoutMs: 900,
    config: {},
    isFavorite: favorite,
  };
}

describe('useTargetsStore favorites', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('persists favorite state and updates the live summary', async () => {
    vi.mocked(setTargetFavoriteApi).mockResolvedValue({
      target: sampleTarget('gateway', true),
    });

    const targetsStore = useTargetsStore();
    const monitorStore = useMonitorStore();

    targetsStore.targets = [sampleTarget('gateway')];
    monitorStore.summary = {
      startedAt: 0,
      now: 1,
      endsAt: null,
      intervalMs: 1_000,
      durationMs: null,
      overallStatus: 'up',
      diagnosis: 'ok',
      network: { name: 'Test', ssid: null, interface: null, service: null },
      targets: [
        {
          ...sampleTarget('gateway'),
          currentStatus: 'up',
          lastOk: true,
          lastLatencyMs: 10,
          lastCheckedAt: 1,
          lastError: null,
          activeIncident: null,
          samples: 1,
          uptimePct: 100,
          packetLossPct: 0,
          avgLatencyMs: 10,
          minLatencyMs: 10,
          maxLatencyMs: 10,
          jitterMs: 0,
          recentFailures: 0,
          recentHighLatency: 0,
          history: [],
        },
      ],
      events: [],
      sampleCount: 1,
    } satisfies StatusSummary;

    const saved = await targetsStore.setTargetFavorite('gateway', true);

    expect(saved).toBe(true);
    expect(targetsStore.targets[0]?.isFavorite).toBe(true);
    expect(monitorStore.summary?.targets[0]?.isFavorite).toBe(true);
    expect(setTargetFavoriteApi).toHaveBeenCalledWith('gateway', true);
  });
});
