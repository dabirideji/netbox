<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue';
import { PhCaretDown, PhCaretUp, PhFrameCorners } from '@phosphor-icons/vue';
import type { DashboardSectionId } from '../../dashboardSections';
import { useDashboardSectionsCollapsed } from '../../composables/useDashboardSectionsCollapsed';
import { SectionModal } from '../ui/section-modal';

const props = withDefaults(
  defineProps<{
    sectionId: DashboardSectionId;
    eyebrow?: string;
    title?: string;
    collapsible?: boolean;
    fullscreen?: boolean;
  }>(),
  {
    collapsible: true,
    fullscreen: false,
  },
);

const { isSectionCollapsed, setSectionCollapsed } = useDashboardSectionsCollapsed();
const collapsed = computed(() => props.collapsible && isSectionCollapsed(props.sectionId));
const fullscreenOpen = ref(false);

const sectionLabel = computed(() => props.title ?? 'section');
const expandLabel = computed(() => `Open ${sectionLabel.value} in fullscreen`);
const collapseLabel = computed(() =>
  collapsed.value ? `Expand ${sectionLabel.value}` : `Collapse ${sectionLabel.value}`,
);
const showSectionContent = computed(() => !collapsed.value || fullscreenOpen.value);

function toggle(): void {
  if (!props.collapsible) return;
  setSectionCollapsed(props.sectionId, !collapsed.value);
}

function openFullscreen(): void {
  if (!props.fullscreen) return;
  fullscreenOpen.value = true;
}

function closeFullscreen(): void {
  fullscreenOpen.value = false;
}

function lockBodyScroll(locked: boolean): void {
  document.body.style.overflow = locked ? 'hidden' : '';
}

watch(fullscreenOpen, (open) => {
  lockBodyScroll(open);
});

onUnmounted(() => {
  if (fullscreenOpen.value) {
    lockBodyScroll(false);
  }
});
</script>

<template>
  <section class="dashboard-card" :class="{ 'is-collapsed': collapsible && collapsed, 'is-fullscreen-open': fullscreenOpen }">
    <header class="dashboard-card__header">
      <component
        :is="collapsible ? 'button' : 'div'"
        :type="collapsible ? 'button' : undefined"
        class="dashboard-card__header-button"
        :class="{ 'dashboard-card__header-button--static': !collapsible }"
        :aria-expanded="collapsible ? !collapsed : undefined"
        :aria-label="collapsible ? collapseLabel : undefined"
        @click="toggle"
      >
        <div class="dashboard-card__titles">
          <slot name="header">
            <p v-if="eyebrow" class="eyebrow">{{ eyebrow }}</p>
            <h2 v-if="title">{{ title }}</h2>
          </slot>
        </div>
      </component>

      <div v-if="collapsible || fullscreen || $slots.meta" class="dashboard-card__header-actions">
        <div v-if="$slots.meta" class="dashboard-card__meta">
          <slot name="meta" />
        </div>
        <button
          v-if="fullscreen"
          type="button"
          class="dashboard-card__icon-button"
          :aria-label="expandLabel"
          @click="openFullscreen"
        >
          <PhFrameCorners class="dashboard-card__icon-button-icon" weight="bold" aria-hidden="true" />
        </button>
        <button
          v-if="collapsible"
          type="button"
          class="dashboard-card__icon-button"
          :aria-expanded="!collapsed"
          :aria-label="collapseLabel"
          @click="toggle"
        >
          <PhCaretUp v-if="!collapsed" class="dashboard-card__icon-button-icon" weight="bold" aria-hidden="true" />
          <PhCaretDown v-else class="dashboard-card__icon-button-icon" weight="bold" aria-hidden="true" />
        </button>
      </div>
    </header>

    <div v-show="showSectionContent" class="dashboard-card__content-anchor">
      <Teleport to="body" :disabled="!fullscreenOpen">
        <SectionModal
          :mode="fullscreenOpen ? 'modal' : 'inline'"
          :eyebrow="eyebrow"
          :title="title"
          @close="closeFullscreen"
        >
          <slot />
        </SectionModal>
      </Teleport>
    </div>
  </section>
</template>
