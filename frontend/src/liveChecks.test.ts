import { describe, expect, it } from 'vitest';
import { formatTargetLastValue, sortLiveCheckTargets } from './liveChecks';
import type { TargetSummary } from './types';

function target(id: string, favorite = false): TargetSummary {
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
    isFavorite: favorite,
    intervalMs: 1_000,
    timeoutMs: 900,
    config: {},
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
  };
}

describe('formatTargetLastValue', () => {
  it('keeps the last latency reading when a target is paused without a fresh sample', () => {
    const value = formatTargetLastValue({
      ...target('dns'),
      enabled: false,
      lastLatencyMs: null,
      lastError: 'timeout',
      history: [{ at: 1, status: 'operational', latencyMs: 42, error: null }],
    });

    expect(value).toBe('42.0ms');
  });

  it('shows a dash instead of fail when paused with no prior reading', () => {
    expect(
      formatTargetLastValue({
        ...target('dns'),
        enabled: false,
        lastLatencyMs: null,
        lastError: null,
        history: [],
      }),
    ).toBe('—');
  });

  it('shows pending before the first enabled check after startup', () => {
    expect(
      formatTargetLastValue({
        ...target('dns'),
        enabled: true,
        lastLatencyMs: null,
        lastCheckedAt: null,
        lastError: null,
        history: [],
      }),
    ).toBe('pending');
  });
});

describe('sortLiveCheckTargets', () => {
  it('keeps favorites above non-favorites while preserving relative order', () => {
    const sorted = sortLiveCheckTargets([target('a'), target('b', true), target('c'), target('d', true)]);

    expect(sorted.map((entry) => entry.id)).toEqual(['b', 'd', 'a', 'c']);
  });
});
