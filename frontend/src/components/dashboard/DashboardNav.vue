<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, type Component } from 'vue';
import {
  PhChartBar,
  PhChartLine,
  PhGauge,
  PhHardDrives,
  PhLink,
  PhPulse,
  PhWarningCircle,
} from '@phosphor-icons/vue';
import { DASHBOARD_NAV_ITEMS, type DashboardSectionId } from '../../dashboardSections';
import { useDashboardSectionsCollapsed } from '../../composables/useDashboardSectionsCollapsed';

const { isSectionCollapsed, setSectionCollapsed } = useDashboardSectionsCollapsed();

const navScrollRef = ref<HTMLElement | null>(null);
const navAnchorRef = ref<HTMLElement | null>(null);
const navFadeLeft = ref(false);
const navFadeRight = ref(false);
const navIsStuck = ref(false);

const navIcons: Partial<Record<DashboardSectionId, Component>> = {
  summary: PhChartBar,
  timeline: PhChartLine,
  targets: PhLink,
  liveChecks: PhPulse,
  speedTest: PhGauge,
  incidentLog: PhWarningCircle,
  systemRatios: PhHardDrives,
};

function updateNavStuck(): void {
  const anchor = navAnchorRef.value;
  if (!anchor) {
    navIsStuck.value = false;
    return;
  }

  navIsStuck.value = anchor.getBoundingClientRect().top <= 0;
}

function updateNavScrollFades(): void {
  const element = navScrollRef.value;
  if (!element) {
    navFadeLeft.value = false;
    navFadeRight.value = false;
    return;
  }

  const maxScroll = element.scrollWidth - element.clientWidth;
  navFadeLeft.value = element.scrollLeft > 4;
  navFadeRight.value = maxScroll > 4 && element.scrollLeft < maxScroll - 4;
}

let navResizeObserver: ResizeObserver | undefined;

onMounted(() => {
  void nextTick(() => {
    updateNavScrollFades();
    updateNavStuck();
  });
  navResizeObserver = new ResizeObserver(() => {
    updateNavScrollFades();
    updateNavStuck();
  });
  if (navScrollRef.value) {
    navResizeObserver.observe(navScrollRef.value);
  }
  if (navAnchorRef.value) {
    navResizeObserver.observe(navAnchorRef.value);
  }

  window.addEventListener('scroll', updateNavStuck, { passive: true });
  window.addEventListener('resize', updateNavStuck);
});

onUnmounted(() => {
  navResizeObserver?.disconnect();
  window.removeEventListener('scroll', updateNavStuck);
  window.removeEventListener('resize', updateNavStuck);
});

async function jumpToSection(sectionId: DashboardSectionId): Promise<void> {
  if (isSectionCollapsed(sectionId)) {
    setSectionCollapsed(sectionId, false);
  }

  await nextTick();

  document.getElementById(`dashboard-section-${sectionId}`)?.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  });
}
</script>

<template>
  <div ref="navAnchorRef" class="dashboard-nav-anchor" :class="{ 'is-stuck': navIsStuck }">
    <div class="dashboard-nav-shell horizontal-scroll-shell">
    <div
      class="horizontal-scroll-fade horizontal-scroll-fade--left"
      :class="{ 'is-visible': navFadeLeft }"
      aria-hidden="true"
    >
      <span class="horizontal-scroll-fade__ellipsis">…</span>
    </div>
    <nav
      ref="navScrollRef"
      class="dashboard-nav horizontal-scroll-track"
      aria-label="Dashboard sections"
      @scroll="updateNavScrollFades"
    >
      <ul class="dashboard-nav__list">
        <li v-for="item in DASHBOARD_NAV_ITEMS" :key="item.id">
          <button
            type="button"
            class="dashboard-nav__button"
            :title="item.hint"
            @click="jumpToSection(item.id)"
          >
            <component :is="navIcons[item.id]" class="dashboard-nav__icon" weight="bold" aria-hidden="true" />
            {{ item.label }}
          </button>
        </li>
      </ul>
    </nav>
    <div
      class="horizontal-scroll-fade horizontal-scroll-fade--right"
      :class="{ 'is-visible': navFadeRight }"
      aria-hidden="true"
    >
      <span class="horizontal-scroll-fade__ellipsis">…</span>
    </div>
    </div>
  </div>
</template>
