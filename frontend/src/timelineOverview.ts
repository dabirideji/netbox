import { liveTargetHistoryToSeverityPoints, severityPath, targetTrendToSeverityPoints } from './chart';
import { targetColorForSource } from './targetColors';
import type { TargetHistorySeries, TargetSummary } from './types';

export interface TimelineOverviewSeries {
  id: string;
  label: string;
  color: string;
  path: string;
  pointCount: number;
}

export function buildTimelineOverviewSeries(
  targets: TargetSummary[],
  targetHistory: TargetHistorySeries[],
): TimelineOverviewSeries[] {
  if (targetHistory.length) {
    return targetHistory
      .map((series) => {
        const points = targetTrendToSeverityPoints(series.points);
        const target = targets.find((entry) => entry.id === series.id);
        return {
          id: series.id,
          label: series.label,
          color: targetColorForSource(target?.config, series.id),
          path: severityPath(points),
          pointCount: points.length,
        };
      })
      .filter((series) => series.pointCount > 0);
  }

  return targets
    .map((target) => {
      const points = liveTargetHistoryToSeverityPoints(target.history);
      return {
        id: target.id,
        label: target.label,
        color: targetColorForSource(target.config, target.id),
        path: severityPath(points),
        pointCount: points.length,
      };
    })
    .filter((series) => series.pointCount > 0);
}
