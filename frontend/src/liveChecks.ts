import { formatMs } from './format';
import type { TargetHistoryPoint, TargetSummary } from './types';

/** Shared page sizes for dashboard target lists. */

export const LIVE_CHECKS_PAGE_SIZE = 15;
export const TARGETS_PAGE_SIZE = 6;

function lastSuccessfulLatency(history: TargetHistoryPoint[]): number | null {
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
    return '—';
  }
  if (target.lastCheckedAt == null) {
    return 'pending';
  }
  return target.lastError ?? 'fail';
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
