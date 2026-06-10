import { computed } from 'vue';
import type { DashboardSectionId, DashboardSectionsCollapsedState } from '../dashboardSections';
import { usePersonalisationStore } from '../stores';

export {
  DASHBOARD_SECTIONS_COLLAPSED_PREF_KEY,
  DASHBOARD_SECTIONS_COLLAPSED_STORAGE_KEY,
  applyDashboardSectionsCollapsedFromPreferences,
  resetDashboardSectionsCollapsedSyncState,
} from '../stores/personalisation';

export function useDashboardSectionsCollapsed() {
  const store = usePersonalisationStore();

  return {
    dashboardSectionsCollapsed: computed(() => store.sectionsCollapsed),
    isSectionCollapsed: (sectionId: DashboardSectionId) => store.isSectionCollapsed(sectionId),
    setSectionCollapsed: (sectionId: DashboardSectionId, collapsed: boolean) =>
      store.setSectionCollapsed(sectionId, collapsed),
    setDashboardSectionsCollapsed: (state: DashboardSectionsCollapsedState) =>
      store.setDashboardSectionsCollapsed(state),
  };
}
