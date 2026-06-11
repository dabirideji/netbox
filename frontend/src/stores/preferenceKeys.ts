import type { DashboardSectionsCollapsedState } from '../dashboardSections';

/** Keys stored in ui_preferences.data on the backend. */
export const PREFERENCE_KEYS = {
  sectionsCollapsed: 'dashboard_sections_collapsed',
  timelineRange: 'timeline_range',
  eventPage: 'event_page',
  speedTestPage: 'speed_test_page',
  liveChecksPage: 'live_checks_page',
  targetsPage: 'targets_page',
  targetGroups: 'target_groups',
  targetEnvironments: 'target_environments',
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
  [PREFERENCE_KEYS.liveChecksPage]?: number;
  [PREFERENCE_KEYS.targetsPage]?: number;
  [PREFERENCE_KEYS.targetGroups]?: string[];
  [PREFERENCE_KEYS.targetEnvironments]?: string[];
}
