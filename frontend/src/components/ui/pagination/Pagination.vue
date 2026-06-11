<script setup lang="ts">
import { computed } from 'vue';
import { Button } from '../button';

/** Compact pagination for newest-first lists. Page 1 is the most recent slice. */
const props = withDefaults(
  defineProps<{
    currentPage: number;
    totalItems: number;
    itemsPerPage: number;
    orderLabel?: string;
    showSummary?: boolean;
  }>(),
  {
    currentPage: 1,
    totalItems: 0,
    itemsPerPage: 10,
    orderLabel: 'newest first',
    showSummary: true,
  },
);

const emit = defineEmits<{
  'update:page': [page: number];
}>();

const totalPages = computed(() => Math.max(1, Math.ceil(props.totalItems / props.itemsPerPage)));
const safePage = computed(() => clampPage(props.currentPage));
const startItem = computed(() => (props.totalItems === 0 ? 0 : (safePage.value - 1) * props.itemsPerPage + 1));
const endItem = computed(() => Math.min(safePage.value * props.itemsPerPage, props.totalItems));
const canGoPrevious = computed(() => safePage.value > 1);
const canGoNext = computed(() => safePage.value < totalPages.value);
const visiblePages = computed(() => {
  const windowSize = 5;
  const halfWindow = Math.floor(windowSize / 2);
  let start = Math.max(1, safePage.value - halfWindow);
  const end = Math.min(totalPages.value, start + windowSize - 1);
  start = Math.max(1, end - windowSize + 1);

  return Array.from({ length: end - start + 1 }, (_, index) => start + index);
});

function clampPage(page: number): number {
  return Math.min(Math.max(page, 1), totalPages.value);
}

function goToPage(page: number): void {
  const nextPage = clampPage(page);
  if (nextPage !== safePage.value) {
    emit('update:page', nextPage);
  }
}
</script>

<template>
  <nav class="ui-pagination" :class="{ 'ui-pagination--compact': !showSummary }" aria-label="Pagination">
    <span v-if="showSummary" class="ui-pagination__summary">
      {{ startItem }}–{{ endItem }} of {{ totalItems }} · Page {{ safePage }} of {{ totalPages }} · {{ orderLabel }}
    </span>
    <div class="ui-pagination__controls">
      <Button
        variant="ghost"
        size="xs"
        class="ui-pagination__step"
        :disabled="!canGoPrevious"
        aria-label="Previous page (more recent incidents)"
        @click="goToPage(safePage - 1)"
      >
        ‹
      </Button>
      <div class="ui-pagination__pages" aria-label="Pages">
        <Button
          v-for="page in visiblePages"
          :key="page"
          :variant="page === safePage ? 'default' : 'ghost'"
          size="xs"
          :aria-current="page === safePage ? 'page' : undefined"
          :aria-label="`Page ${page}`"
          @click="goToPage(page)"
        >
          {{ page }}
        </Button>
      </div>
      <Button
        variant="ghost"
        size="xs"
        class="ui-pagination__step"
        :disabled="!canGoNext"
        aria-label="Next page (older incidents)"
        @click="goToPage(safePage + 1)"
      >
        ›
      </Button>
    </div>
  </nav>
</template>
