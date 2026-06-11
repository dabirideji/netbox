import { describe, expect, it } from 'vitest';
import { buildTimelineOverviewSeries } from './timelineOverview';
import type { TargetHistorySeries, TargetSummary } from './types';

const target = (id: string, color: string, history: TargetSummary['history'] = []): TargetSummary => ({
  id,
  host: id,
  label: id,
  scope: 'external',
  type: 'host',
  protocol: 'icmp',
  group: 'Default',
  environment: 'local',
  enabled: true,
  intervalMs: 1000,
  timeoutMs: 900,
  config: { color },
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
  history,
});

describe('buildTimelineOverviewSeries', () => {
  it('builds one colored line per source from live history', () => {
    const series = buildTimelineOverviewSeries(
      [
        target('alpha', '#38bdf8', [{ at: 1, status: 'operational', latencyMs: 10, error: null }]),
        target('beta', '#22c55e', [{ at: 1, status: 'degraded', latencyMs: 20, error: null }]),
      ],
      [],
    );

    expect(series).toHaveLength(2);
    expect(series.map((entry) => entry.color)).toEqual(['#38bdf8', '#22c55e']);
    expect(series.every((entry) => entry.path.startsWith('M '))).toBe(true);
  });

  it('prefers persisted target history when available', () => {
    const history: TargetHistorySeries[] = [
      {
        id: 'alpha',
        host: 'alpha',
        label: 'Alpha',
        scope: 'external',
        points: [{ at: 1, severity: 0, status: 'operational', ok: true, latencyMs: 10, error: null }],
      },
    ];

    const series = buildTimelineOverviewSeries([target('alpha', '#38bdf8')], history);
    expect(series).toHaveLength(1);
    expect(series[0]?.label).toBe('Alpha');
  });
});
