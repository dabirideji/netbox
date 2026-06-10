<script setup lang="ts">
import { ref, watch } from 'vue';
import { DatePicker } from '../date-picker';
import { Label } from '../label';
import { TimePicker } from '../time-picker';

/** Shadcn-style date-time range field with separate date and time dropdowns. */
const model = defineModel<string>({ default: '' });

defineProps<{
  label: string;
}>();

const datePart = ref('');
const timePart = ref('');

watch(
  () => model.value,
  (value) => {
    if (!value) {
      datePart.value = '';
      timePart.value = '';
      return;
    }

    const [date, time] = value.split('T');
    datePart.value = date ?? '';
    timePart.value = (time ?? '').slice(0, 5);
  },
  { immediate: true },
);

watch([datePart, timePart], () => {
  if (!datePart.value && !timePart.value) {
    model.value = '';
    return;
  }

  if (!datePart.value) return;

  model.value = `${datePart.value}T${timePart.value || '00:00'}`;
});
</script>

<template>
  <Label class="ui-date-time-field">
    <span class="ui-date-time-field__label">{{ label }}</span>
    <div class="ui-date-time-controls">
      <DatePicker v-model="datePart" :aria-label="`${label} date`" />
      <TimePicker v-model="timePart" :aria-label="`${label} time`" />
    </div>
  </Label>
</template>
