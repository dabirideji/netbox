/** Speed-to-gauge helpers for download and upload arc meters. */

const GAUGE_STOPS = [50, 100, 200, 500, 1000, 2000] as const;

export function resolveGaugeMaxMbps(...values: Array<number | null | undefined>): number {
  const peak = Math.max(
    0,
    ...values.filter((value): value is number => value != null && Number.isFinite(value) && value > 0),
  );

  if (peak <= 0) return 100;

  for (const stop of GAUGE_STOPS) {
    if (peak <= stop * 0.82) return stop;
  }

  return Math.ceil(peak / 500) * 500;
}

export function mbpsToGaugeScore(mbps: number | null | undefined, maxMbps: number): number {
  if (mbps == null || !Number.isFinite(mbps) || maxMbps <= 0) return 0;
  return Math.min(100, Math.max(0, (mbps / maxMbps) * 100));
}

export function formatGaugeScaleLabel(maxMbps: number): string {
  if (maxMbps >= 1000) return `${(maxMbps / 1000).toFixed(maxMbps % 1000 === 0 ? 0 : 1)} Gbps`;
  return `${maxMbps} Mbps`;
}
