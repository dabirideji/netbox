import type { DonutChartSegment } from '../ui/chart';
import type { Status } from '../../types';

export function countStatuses(statuses: Status[]): Record<'operational' | 'degraded' | 'down', number> {
  return statuses.reduce(
    (counts, status) => {
      if (status === 'down' || status === 'degraded' || status === 'operational') {
        counts[status] += 1;
      }
      return counts;
    },
    { operational: 0, degraded: 0, down: 0 },
  );
}

export function statusSegments(counts: Record<'operational' | 'degraded' | 'down', number>): DonutChartSegment[] {
  return [
    { label: 'Up', count: counts.operational, colorIndex: 0 },
    { label: 'Degraded', count: counts.degraded, colorIndex: 1 },
    { label: 'Down', count: counts.down, colorIndex: 2 },
  ];
}
