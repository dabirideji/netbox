/** Dashboard section ids used for collapse/expand preferences. */

export const DASHBOARD_SECTION_IDS = [
  'hero',
  'summary',
  'timeline',
  'liveChecks',
  'speedTest',
  'incidentLog',
  'systemRatios',
] as const;

export type DashboardSectionId = (typeof DASHBOARD_SECTION_IDS)[number];

export type DashboardSectionsCollapsedState = Record<DashboardSectionId, boolean>;

export function createDefaultDashboardSectionsCollapsed(): DashboardSectionsCollapsedState {
  return {
    hero: false,
    summary: false,
    timeline: false,
    liveChecks: false,
    speedTest: false,
    incidentLog: false,
    systemRatios: false,
  };
}
