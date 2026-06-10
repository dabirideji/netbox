<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { formatTimePickerLabel } from '../../../format';
import { Button } from '../button';
import { Popover, PopoverContent, PopoverTrigger } from '../popover';
import { normalizeTimeValue, TIME_OPTIONS } from './time';

const model = defineModel<string>({ default: '' });
const open = ref(false);

const props = withDefaults(
  defineProps<{
    ariaLabel?: string;
    placeholder?: string;
  }>(),
  {
    ariaLabel: 'Time',
    placeholder: 'Pick time',
  },
);

const displayLabel = computed(() => formatTimePickerLabel(model.value) || props.placeholder);
const normalizedValue = computed(() => normalizeTimeValue(model.value));

function selectTime(value: string): void {
  model.value = value;
}

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
        class="ui-time-picker-trigger"
        :aria-label="props.ariaLabel"
      >
        <svg
          class="ui-time-picker-trigger__icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.75"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7v5l3 2" />
        </svg>
        <span class="ui-time-picker-trigger__value" :class="{ 'is-placeholder': !model }">{{ displayLabel }}</span>
      </Button>
    </PopoverTrigger>
    <PopoverContent class="ui-time-picker-content">
      <div class="ui-time-picker-list" role="listbox" :aria-label="props.ariaLabel">
        <button
          v-for="time in TIME_OPTIONS"
          :key="time"
          type="button"
          class="ui-time-picker-option"
          :class="{ 'is-selected': time === normalizedValue }"
          role="option"
          :aria-selected="time === normalizedValue"
          @click="selectTime(time)"
        >
          {{ formatTimePickerLabel(time) }}
        </button>
      </div>
    </PopoverContent>
  </Popover>
</template>
