import { describe, expect, it } from 'vitest';
import { slimStatusSummary } from './monitorPersist';
import type { StatusSummary } from '../types';

function sampleSummary(): StatusSummary {
  return {
    now: 1,
    startedAt: 1,
    endsAt: null,
    intervalMs: 1000,
    durationMs: null,
    overallStatus: 'operational',
    diagnosis: 'ok',
    sampleCount: 1,
    network: { name: 'Test', ssid: null, interface: null, service: null },
    events: [
      {
        at: 1,
        targetId: 'a',
        targetLabel: 'A',
        from: 'down',
        to: 'operational',
        message: 'recovered',
      },
    ],
    targets: [
      {
        id: 'a',
        label: 'A',
        host: 'example.com',
        scope: 'external',
        type: 'website',
        protocol: 'https',
        group: 'Default',
        environment: 'local',
        enabled: true,
        intervalMs: 1000,
        timeoutMs: 900,
        config: {},
        currentStatus: 'operational',
        lastOk: true,
        lastLatencyMs: 10,
        lastCheckedAt: 1,
        lastError: null,
        samples: 1,
        packetLossPct: 0,
        avgLatencyMs: 10,
        minLatencyMs: 10,
        maxLatencyMs: 10,
        jitterMs: 0,
        uptimePct: 100,
        activeIncident: null,
        recentFailures: 0,
        recentHighLatency: 0,
        history: [{ at: 1, status: 'operational', latencyMs: 10, error: null }],
      },
    ],
  };
}

describe('slimStatusSummary', () => {
  it('drops target history and events before persistence', () => {
    const slim = slimStatusSummary(sampleSummary());
    expect(slim?.events).toEqual([]);
    expect(slim?.targets[0]?.history).toEqual([]);
  });
});
