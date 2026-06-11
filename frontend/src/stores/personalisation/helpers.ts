import {
  createDefaultDashboardSectionsCollapsed,
  DASHBOARD_SECTION_IDS,
  type DashboardSectionsCollapsedState,
} from '../../dashboardSections';

export const CACHE_TTL = 1000 * 60 * 10;

export function normalizeSectionsCollapsed(
  value: Partial<DashboardSectionsCollapsedState> | null | undefined,
): DashboardSectionsCollapsedState {
  const defaults = createDefaultDashboardSectionsCollapsed();
  if (!value || typeof value !== 'object') return defaults;

  const next = { ...defaults };
  for (const sectionId of DASHBOARD_SECTION_IDS) {
    if (typeof value[sectionId] === 'boolean') {
      next[sectionId] = value[sectionId];
    }
  }
  return next;
}

export function formatDateTimeInput(timestamp: number): string {
  const date = new Date(timestamp);
  const offsetMs = date.getTimezoneOffset() * 60_000;
  return new Date(timestamp - offsetMs).toISOString().slice(0, 16);
}
