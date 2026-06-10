import { describe, expect, it } from 'vitest';
import { gaugeNeedleAngle } from './scoreGaugeSegments';
import { mbpsToGaugeScore, resolveGaugeMaxMbps } from './speedGauge';

describe('speed gauge helpers', () => {
  it('maps mbps into a 0-100 gauge score', () => {
    expect(mbpsToGaugeScore(50, 100)).toBe(50);
    expect(mbpsToGaugeScore(150, 100)).toBe(100);
    expect(mbpsToGaugeScore(null, 100)).toBe(0);
  });

  it('chooses an adaptive max scale from observed speeds', () => {
    expect(resolveGaugeMaxMbps(12, 8)).toBe(50);
    expect(resolveGaugeMaxMbps(42, 18)).toBe(100);
    expect(resolveGaugeMaxMbps(180, 40)).toBe(500);
  });

  it('maps gauge score to semicircle needle angles', () => {
    expect(gaugeNeedleAngle(0)).toBe(0);
    expect(gaugeNeedleAngle(50)).toBe(90);
    expect(gaugeNeedleAngle(100)).toBe(180);
  });
});
