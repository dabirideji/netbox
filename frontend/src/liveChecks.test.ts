import { describe, expect, it } from 'vitest';
import {
  buildLiveCheckRows,
  formatNetworkSpeed,
  formatTargetLastValue,
  sortLiveCheckRows,
  sortLiveCheckTargets,
} from './liveChecks';
import type { NetworkDeviceSummary, TargetSummary } from './types';

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
    currentStatus: 'operational',
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
    ).toBe('-');
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

function networkDevice(id: string): NetworkDeviceSummary {
  return {
    id: `network:${id}`,
    interface: id,
    service: 'Wi-Fi',
    ssid: 'Office',
    label: 'Office WiFi',
    active: true,
    hidden: false,
    networkSpeed: {
      downloadMbps: 100,
      uploadMbps: 25,
      testedAt: 1,
    },
  };
}

describe('formatNetworkSpeed', () => {
  it('formats download and upload together', () => {
    expect(formatNetworkSpeed({ downloadMbps: 100, uploadMbps: 25, testedAt: 1 })).toBe('100.0 Mbps / 25.0 Mbps');
    expect(formatNetworkSpeed(null)).toBe('-');
  });
});

describe('buildLiveCheckRows', () => {
  it('places network devices before monitor targets', () => {
    const rows = sortLiveCheckRows(buildLiveCheckRows([target('dns')], [networkDevice('en0')]));
    expect(rows.map((row) => (row.kind === 'networkDevice' ? row.device.id : row.target.id))).toEqual([
      'network:en0',
      'dns',
    ]);
  });
});
