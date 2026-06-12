import { formatClock, formatMbps, formatMs } from './format';
import type { NetworkDeviceSummary, NetworkSpeedSnapshot, TargetSummary } from './types';

/** Shared page sizes for dashboard target lists. */

export const LIVE_CHECKS_PAGE_SIZE = 15;
export const TARGETS_PAGE_SIZE = 6;

export type LiveCheckRow =
  | { kind: 'target'; target: TargetSummary }
  | { kind: 'networkDevice'; device: NetworkDeviceSummary };

function lastSuccessfulLatency(history: TargetSummary['history']): number | null {
  for (let index = history.length - 1; index >= 0; index -= 1) {
    const point = history[index];
    if (point?.latencyMs != null) {
      return point.latencyMs;
    }
  }
  return null;
}

/** Format the Last column for live checks, preserving the previous reading when paused or cold-started. */
export function formatTargetLastValue(target: TargetSummary): string {
  const latency = target.lastLatencyMs ?? lastSuccessfulLatency(target.history);
  if (latency != null) {
    return formatMs(latency);
  }
  if (!target.enabled) {
    return '-';
  }
  if (target.lastCheckedAt == null) {
    return 'pending';
  }
  return target.lastError ?? 'fail';
}

export function formatNetworkSpeed(speed: NetworkSpeedSnapshot | null | undefined): string {
  if (!speed) {
    return '-';
  }
  const parts = [formatMbps(speed.downloadMbps), formatMbps(speed.uploadMbps)].filter((value) => value !== '-');
  return parts.length ? parts.join(' / ') : '-';
}

export function networkSpeedTitle(speed: NetworkSpeedSnapshot | null | undefined): string | undefined {
  if (!speed) {
    return undefined;
  }
  return `Download ${formatMbps(speed.downloadMbps)} · Upload ${formatMbps(speed.uploadMbps)} · ${formatClock(speed.testedAt)}`;
}

export function buildLiveCheckRows(
  targets: TargetSummary[],
  networkDevices: NetworkDeviceSummary[] = [],
): LiveCheckRow[] {
  const deviceRows: LiveCheckRow[] = networkDevices.map((device) => ({ kind: 'networkDevice', device }));
  const targetRows: LiveCheckRow[] = targets.map((target) => ({ kind: 'target', target }));
  return [...deviceRows, ...targetRows];
}

export function liveCheckRowKey(row: LiveCheckRow): string {
  return row.kind === 'networkDevice' ? row.device.id : row.target.id;
}

export function sortLiveCheckTargets<T extends { isFavorite?: boolean }>(targets: T[]): T[] {
  return [...targets].sort((left, right) => {
    const leftFavorite = left.isFavorite ? 1 : 0;
    const rightFavorite = right.isFavorite ? 1 : 0;
    if (leftFavorite !== rightFavorite) {
      return rightFavorite - leftFavorite;
    }
    return 0;
  });
}

export function sortLiveCheckRows(rows: LiveCheckRow[]): LiveCheckRow[] {
  const devices = rows.filter((row): row is Extract<LiveCheckRow, { kind: 'networkDevice' }> => row.kind === 'networkDevice');
  const targets = sortLiveCheckTargets(
    rows
      .filter((row): row is Extract<LiveCheckRow, { kind: 'target' }> => row.kind === 'target')
      .map((row) => row.target),
  );
  return [...devices, ...targets.map((target) => ({ kind: 'target' as const, target }))];
}

export function targetNetworkSpeed(row: LiveCheckRow): NetworkSpeedSnapshot | null | undefined {
  if (row.kind === 'networkDevice') {
    return row.device.networkSpeed;
  }
  return row.target.networkSpeed;
}

export function isGatewayLikeRow(row: LiveCheckRow): boolean {
  return row.kind === 'networkDevice' || row.target.scope === 'gateway';
}
