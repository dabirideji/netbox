import { liveTargetHistoryToSeverityPoints, severityPath, targetTrendToSeverityPoints } from './chart';
import { targetColor } from './targetColors';
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
  const colorIndexById = new Map(targets.map((target, index) => [target.id, index]));

  if (targetHistory.length) {
    return targetHistory
      .map((series, index) => {
        const points = targetTrendToSeverityPoints(series.points);
        return {
          id: series.id,
          label: series.label,
          color: targetColor(
            targets.find((target) => target.id === series.id)?.config,
            colorIndexById.get(series.id) ?? index,
          ),
          path: severityPath(points),
          pointCount: points.length,
        };
      })
      .filter((series) => series.pointCount > 0);
  }

  return targets
    .map((target, index) => {
      const points = liveTargetHistoryToSeverityPoints(target.history);
      return {
        id: target.id,
        label: target.label,
        color: targetColor(target.config, index),
        path: severityPath(points),
        pointCount: points.length,
      };
    })
    .filter((series) => series.pointCount > 0);
}
