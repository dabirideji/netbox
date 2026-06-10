<script setup lang="ts">
import { computed, type HTMLAttributes } from 'vue';
import { cn } from '../../../lib/utils';

/** Compact shadcn-style label primitive. */
const props = defineProps<{
  class?: HTMLAttributes['class'];
}>();

const classes = computed(() => cn('ui-label', props.class));
</script>

<template>
  <label :class="classes">
    <slot />
  </label>
</template>
