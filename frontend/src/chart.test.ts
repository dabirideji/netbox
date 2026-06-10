import { describe, expect, it } from 'vitest';
import {
  liveTargetHistoryToSeverityPoints,
  severityArea,
  severityLabel,
  severityPath,
  severitySegments,
  targetTrendToSeverityPoints,
} from './chart';

describe('chart helpers', () => {
  it('builds a path for severity points', () => {
    const path = severityPath([
      { at: 1, severity: 0, avgLatencyMs: 10, failurePct: 0 },
      { at: 2, severity: 1, avgLatencyMs: 100, failurePct: 0 },
      { at: 3, severity: 2, avgLatencyMs: null, failurePct: 100 },
    ]);

    expect(path).toMatch(/^M /);
    expect(path).toContain('L');
    expect(path).toContain('M 4 10');
    expect(path).toContain('L 716 110');
  });

  it('builds an area path', () => {
    expect(severityArea([{ at: 1, severity: 1, avgLatencyMs: 10, failurePct: 0 }])).toContain('Z');
  });

  it('labels severity levels', () => {
    expect(severityLabel(0)).toBe('Operational');
    expect(severityLabel(1)).toBe('Degraded');
    expect(severityLabel(2)).toBe('Down');
  });

  it('colors line segments by worst status in the segment', () => {
    const segments = severitySegments([
      { at: 1, severity: 0, avgLatencyMs: 10, failurePct: 0 },
      { at: 2, severity: 1, avgLatencyMs: 100, failurePct: 10 },
      { at: 3, severity: 2, avgLatencyMs: null, failurePct: 100 },
      { at: 4, severity: 0, avgLatencyMs: 12, failurePct: 0 },
    ]);

    expect(segments).toHaveLength(3);
    expect(segments.map((segment) => segment.status)).toEqual(['degraded', 'down', 'down']);
  });

  it('maps target trend points onto severity coordinates', () => {
    expect(
      targetTrendToSeverityPoints([
        { at: 1, severity: 0, ok: true, latencyMs: 12 },
        { at: 2, severity: 2, ok: false, latencyMs: null },
      ]),
    ).toEqual([
      { at: 1, severity: 0, avgLatencyMs: 12, failurePct: 0 },
      { at: 2, severity: 2, avgLatencyMs: null, failurePct: 100 },
    ]);
  });

  it('maps live target bars onto severity coordinates', () => {
    expect(
      liveTargetHistoryToSeverityPoints([
        { at: 1, status: 'operational', latencyMs: 8, error: null },
        { at: 2, status: 'down', latencyMs: null, error: 'timeout' },
      ]),
    ).toEqual([
      { at: 1, severity: 0, avgLatencyMs: 8, failurePct: 0 },
      { at: 2, severity: 2, avgLatencyMs: null, failurePct: 100 },
    ]);
  });
});
