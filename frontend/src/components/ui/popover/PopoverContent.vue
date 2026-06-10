<script setup lang="ts">
import { computed, inject, type HTMLAttributes } from 'vue';
import { cn } from '../../../lib/utils';
import type { PopoverContext } from './Popover.vue';

const props = defineProps<{
  class?: HTMLAttributes['class'];
}>();

const popover = inject<PopoverContext>('ui-popover');
const isOpen = computed(() => popover?.open.value ?? false);
const classes = computed(() => cn('ui-popover__content', props.class));
</script>

<template>
  <div v-if="isOpen" :class="classes" @click.stop>
    <slot />
  </div>
</template>
