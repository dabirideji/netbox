/** Dashboard section ids used for collapse/expand preferences. */

export const DASHBOARD_SECTION_IDS = [
  'hero',
  'summary',
  'timeline',
  'targets',
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
    targets: true,
    liveChecks: false,
    speedTest: false,
    incidentLog: false,
    systemRatios: false,
  };
}

export type DashboardNavItem = {
  id: DashboardSectionId;
  label: string;
  hint?: string;
};

/** Jump links for the sticky dashboard nav (hero is omitted - it is always at the top). */
export const DASHBOARD_NAV_ITEMS: DashboardNavItem[] = [
  { id: 'summary', label: 'Metrics' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'targets', label: 'Sources', hint: 'Add links and endpoints to monitor' },
  { id: 'liveChecks', label: 'Live checks' },
  { id: 'speedTest', label: 'Speed test' },
  { id: 'incidentLog', label: 'Incidents' },
  { id: 'systemRatios', label: 'Storage' },
];
