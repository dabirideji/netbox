import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { createPersistedState } from 'pinia-plugin-persistedstate';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../../api';
import DashboardSectionCard from './DashboardSectionCard.vue';
import {
  DASHBOARD_SECTIONS_COLLAPSED_PREF_KEY,
  applyDashboardSectionsCollapsedFromPreferences,
  resetDashboardSectionsCollapsedSyncState,
  usePersonalisationStore,
} from '../../stores';
import { useDashboardSectionsCollapsed } from '../../composables/useDashboardSectionsCollapsed';

describe('dashboard section collapse preferences', () => {
  let pinia: ReturnType<typeof createPinia>;

  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.restoreAllMocks();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ data: {} }) }));

    pinia = createPinia();
    pinia.use(createPersistedState({ storage: localStorage, auto: false }));
    setActivePinia(pinia);
    resetDashboardSectionsCollapsedSyncState();
  });

  it('toggles section collapse and syncs to the backend preferences API', async () => {
    const patchSpy = vi.spyOn(api, 'patchPreferences').mockResolvedValue({
      data: {
        [DASHBOARD_SECTIONS_COLLAPSED_PREF_KEY]: {
          timeline: true,
        },
      },
    });
    const { isSectionCollapsed, setSectionCollapsed } = useDashboardSectionsCollapsed();

    expect(isSectionCollapsed('timeline')).toBe(false);
    setSectionCollapsed('timeline', true);
    expect(isSectionCollapsed('timeline')).toBe(true);
    expect(usePersonalisationStore().sectionsCollapsed.timeline).toBe(true);

    await vi.waitFor(() => {
      expect(patchSpy).toHaveBeenCalledWith({
        [DASHBOARD_SECTIONS_COLLAPSED_PREF_KEY]: expect.objectContaining({ timeline: true }),
      });
    });
  });

  it('applies server preferences when local state is not dirty', () => {
    applyDashboardSectionsCollapsedFromPreferences({
      [DASHBOARD_SECTIONS_COLLAPSED_PREF_KEY]: {
        hero: true,
        summary: false,
        timeline: true,
        liveChecks: false,
        speedTest: false,
        incidentLog: false,
        systemRatios: false,
      },
    });

    const { isSectionCollapsed } = useDashboardSectionsCollapsed();
    expect(isSectionCollapsed('hero')).toBe(true);
    expect(isSectionCollapsed('timeline')).toBe(true);
  });

  it('renders card header chevron and toggles collapse state', async () => {
    const wrapper = mount(DashboardSectionCard, {
      props: { sectionId: 'incidentLog', eyebrow: 'Incident log', title: 'Status changes' },
      global: { plugins: [pinia] },
    });

    const collapseButton = wrapper.find('.dashboard-card__icon-button[aria-expanded]');
    expect(collapseButton.attributes('aria-expanded')).toBe('true');
    expect(wrapper.find('.dashboard-card__body').isVisible()).toBe(true);

    await collapseButton.trigger('click');

    expect(usePersonalisationStore().isSectionCollapsed('incidentLog')).toBe(true);
    expect(collapseButton.attributes('aria-expanded')).toBe('false');
  });

  it('opens a fullscreen modal for sections with the fullscreen option', async () => {
    const wrapper = mount(DashboardSectionCard, {
      props: {
        sectionId: 'timeline',
        eyebrow: 'Timeline',
        title: 'Degradation over time',
        fullscreen: true,
      },
      slots: {
        default: '<p class="section-content">Timeline body</p>',
      },
      global: { plugins: [pinia] },
      attachTo: document.body,
    });

    expect(document.querySelector('.section-modal')).toBeNull();

    await wrapper.get('button[aria-label="Open Degradation over time in fullscreen"]').trigger('click');
    await wrapper.vm.$nextTick();

    const modal = document.querySelector('.section-modal');
    expect(modal).not.toBeNull();
    expect(modal?.querySelector('.section-content')?.textContent).toBe('Timeline body');

    await modal!.querySelector<HTMLButtonElement>('.section-modal__close')!.click();
    await wrapper.vm.$nextTick();
    expect(document.querySelector('.section-modal')).toBeNull();

    wrapper.unmount();
  });
});
