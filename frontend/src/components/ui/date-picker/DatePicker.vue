<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { formatDatePickerLabel } from '../../../format';
import { Button } from '../button';
import { Calendar } from '../calendar';
import { Popover, PopoverContent, PopoverTrigger } from '../popover';

const model = defineModel<string>({ default: '' });
const open = ref(false);

const props = withDefaults(
  defineProps<{
    ariaLabel?: string;
    placeholder?: string;
  }>(),
  {
    ariaLabel: 'Date',
    placeholder: 'Pick date',
  },
);

const displayLabel = computed(() => formatDatePickerLabel(model.value) || props.placeholder);

watch(model, (value, previous) => {
  if (value && value !== previous) {
    open.value = false;
  }
});
</script>

<template>
  <Popover v-model:open="open">
    <PopoverTrigger>
      <Button
        type="button"
        variant="outline"
        size="xs"
        class="ui-date-picker-trigger"
        :aria-label="props.ariaLabel"
      >
        <svg
          class="ui-date-picker-trigger__icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.75"
          aria-hidden="true"
        >
          <rect x="3" y="4" width="18" height="18" rx="2" />
          <path d="M16 2v4M8 2v4M3 10h18" />
        </svg>
        <span class="ui-date-picker-trigger__value" :class="{ 'is-placeholder': !model }">{{ displayLabel }}</span>
      </Button>
    </PopoverTrigger>
    <PopoverContent class="ui-date-picker-content">
      <Calendar v-model="model" :aria-label="props.ariaLabel" />
    </PopoverContent>
  </Popover>
</template>
