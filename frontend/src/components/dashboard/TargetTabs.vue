<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { targetServiceIcon } from '../../targetIcons';
import type { TargetTab } from '../../targetTabs';

const selectedTabId = defineModel<string>({ required: true });

const props = defineProps<{
  tabs: TargetTab[];
  ariaLabel?: string;
}>();

const tabsScrollRef = ref<HTMLElement | null>(null);
const tabsFadeLeft = ref(false);
const tabsFadeRight = ref(false);

const showTabs = computed(() => props.tabs.length > 1);

function updateTabsScrollFades(): void {
  const element = tabsScrollRef.value;
  if (!element) {
    tabsFadeLeft.value = false;
    tabsFadeRight.value = false;
    return;
  }

  const maxScroll = element.scrollWidth - element.clientWidth;
  tabsFadeLeft.value = element.scrollLeft > 4;
  tabsFadeRight.value = maxScroll > 4 && element.scrollLeft < maxScroll - 4;
}

let tabsResizeObserver: ResizeObserver | undefined;

onMounted(() => {
  void nextTick(updateTabsScrollFades);
  if (typeof ResizeObserver !== 'undefined') {
    tabsResizeObserver = new ResizeObserver(() => updateTabsScrollFades());
    if (tabsScrollRef.value) {
      tabsResizeObserver.observe(tabsScrollRef.value);
    }
  }
});

onUnmounted(() => {
  tabsResizeObserver?.disconnect();
});

watch(
  () => props.tabs,
  (next) => {
    if (selectedTabId.value !== 'overview' && !next.some((tab) => tab.id === selectedTabId.value)) {
      selectedTabId.value = 'overview';
    }

    void nextTick(() => {
      if (tabsScrollRef.value && tabsResizeObserver && typeof ResizeObserver !== 'undefined') {
        tabsResizeObserver.observe(tabsScrollRef.value);
      }
      updateTabsScrollFades();
    });
  },
  { immediate: true, flush: 'post' },
);
</script>

<template>
  <div v-if="showTabs" class="timeline-tabs-shell horizontal-scroll-shell">
    <div
      class="horizontal-scroll-fade horizontal-scroll-fade--left"
      :class="{ 'is-visible': tabsFadeLeft }"
      aria-hidden="true"
    />
    <div
      ref="tabsScrollRef"
      class="timeline-tabs-scroll horizontal-scroll-track"
      role="tablist"
      :aria-label="ariaLabel ?? 'Monitor target'"
      @scroll="updateTabsScrollFades"
    >
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        role="tab"
        class="timeline-tabs__button"
        :class="{ 'is-active': selectedTabId === tab.id }"
        :aria-selected="selectedTabId === tab.id"
        @click="selectedTabId = tab.id"
      >
        <component
          :is="targetServiceIcon(tab.type, tab.protocol, tab.overview)"
          class="timeline-tabs__icon"
          weight="bold"
          aria-hidden="true"
        />
        {{ tab.label }}
      </button>
    </div>
    <div
      class="horizontal-scroll-fade horizontal-scroll-fade--right"
      :class="{ 'is-visible': tabsFadeRight }"
      aria-hidden="true"
    />
  </div>
</template>
