<script setup lang="ts">
import { computed } from 'vue';
import { cn } from '../../../lib/utils';

/** Compact shadcn-style switch primitive. */
const props = withDefaults(
  defineProps<{
    modelValue?: boolean;
    disabled?: boolean;
    id?: string;
    class?: string;
  }>(),
  {
    modelValue: false,
    disabled: false,
  },
);

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
}>();

const classes = computed(() =>
  cn('ui-switch', props.modelValue && 'is-checked', props.disabled && 'is-disabled', props.class),
);

function toggle(): void {
  if (props.disabled) return;
  emit('update:modelValue', !props.modelValue);
}
</script>

<template>
  <button
    :id="id"
    type="button"
    role="switch"
    :class="classes"
    :aria-checked="modelValue"
    :disabled="disabled"
    @click="toggle"
  >
    <span class="ui-switch__thumb" aria-hidden="true" />
  </button>
</template>
