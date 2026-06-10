import type { DashboardSectionsCollapsedState } from '../dashboardSections';

/** Keys stored in ui_preferences.data on the backend. */
export const PREFERENCE_KEYS = {
  sectionsCollapsed: 'dashboard_sections_collapsed',
  timelineRange: 'timeline_range',
  eventPage: 'event_page',
  speedTestPage: 'speed_test_page',
} as const;

export interface TimelineRangePreference {
  from: string;
  to: string;
}

export interface UiPreferences {
  [PREFERENCE_KEYS.sectionsCollapsed]?: DashboardSectionsCollapsedState;
  [PREFERENCE_KEYS.timelineRange]?: TimelineRangePreference;
  [PREFERENCE_KEYS.eventPage]?: number;
  [PREFERENCE_KEYS.speedTestPage]?: number;
}
