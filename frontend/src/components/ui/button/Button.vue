<script setup lang="ts">
import { computed, type HTMLAttributes } from 'vue';
import { cn } from '../../../lib/utils';

/** Compact shadcn-style button primitive used across the dashboard. */
const props = withDefaults(
  defineProps<{
    variant?: 'default' | 'outline' | 'ghost';
    size?: 'default' | 'xs' | 'sm';
    disabled?: boolean;
    type?: 'button' | 'submit' | 'reset';
    class?: HTMLAttributes['class'];
  }>(),
  {
    variant: 'default',
    size: 'default',
    disabled: false,
    type: 'button',
  },
);

const classes = computed(() =>
  cn('ui-button', `ui-button--${props.variant}`, `ui-button--${props.size}`, props.disabled && 'is-disabled', props.class),
);
</script>

<template>
  <button :type="type" :disabled="disabled" :class="classes">
    <slot />
  </button>
</template>
