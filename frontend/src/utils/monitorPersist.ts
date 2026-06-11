/** Trim monitor snapshots before writing them to localStorage. */

import type { StatusSummary } from '../types';

export function slimStatusSummary(summary: StatusSummary | null): StatusSummary | null {
  if (!summary) return null;

  return {
    ...summary,
    events: [],
    targets: summary.targets.map((target) => ({
      ...target,
      history: [],
    })),
  };
}
