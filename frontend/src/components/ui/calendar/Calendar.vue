<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { Button } from '../button';
import {
  addMonths,
  buildCalendarDays,
  monthLabel,
  parseIsoDate,
  weekdayLabels,
} from './calendar';

const model = defineModel<string>({ default: '' });

const props = withDefaults(
  defineProps<{
    ariaLabel?: string;
  }>(),
  {
    ariaLabel: 'Choose date',
  },
);

const today = new Date();
const viewYear = ref(today.getFullYear());
const viewMonth = ref(today.getMonth());

const selectedDate = computed(() => parseIsoDate(model.value));
const days = computed(() => buildCalendarDays(viewYear.value, viewMonth.value));
const monthTitle = computed(() => monthLabel(viewYear.value, viewMonth.value));

watch(
  () => model.value,
  (value) => {
    const parsed = parseIsoDate(value);
    if (!parsed) return;
    viewYear.value = parsed.year;
    viewMonth.value = parsed.month;
  },
  { immediate: true },
);

function selectDay(isoDate: string): void {
  model.value = isoDate;
}

function shiftMonth(delta: number): void {
  const next = addMonths(viewYear.value, viewMonth.value, delta);
  viewYear.value = next.year;
  viewMonth.value = next.month;
}
</script>

<template>
  <div class="ui-calendar" role="grid" :aria-label="props.ariaLabel">
    <div class="ui-calendar__header">
      <Button type="button" variant="ghost" size="xs" class="ui-calendar__nav" aria-label="Previous month" @click="shiftMonth(-1)">
        ‹
      </Button>
      <span class="ui-calendar__title">{{ monthTitle }}</span>
      <Button type="button" variant="ghost" size="xs" class="ui-calendar__nav" aria-label="Next month" @click="shiftMonth(1)">
        ›
      </Button>
    </div>

    <div class="ui-calendar__weekdays" aria-hidden="true">
      <span v-for="weekday in weekdayLabels()" :key="weekday" class="ui-calendar__weekday">{{ weekday }}</span>
    </div>

    <div class="ui-calendar__days">
      <button
        v-for="day in days"
        :key="day.isoDate"
        type="button"
        class="ui-calendar__day"
        :class="{
          'is-outside': !day.isCurrentMonth,
          'is-today': day.isToday,
          'is-selected': day.isoDate === model,
        }"
        :aria-label="day.isoDate"
        :aria-pressed="day.isoDate === model"
        @click="selectDay(day.isoDate)"
      >
        {{ day.day }}
      </button>
    </div>
  </div>
</template>
