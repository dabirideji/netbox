<script setup lang="ts">
import { inject } from 'vue';
import type { PopoverContext } from './Popover.vue';

const popover = inject<PopoverContext>('ui-popover');

function onClick(): void {
  popover?.toggleOpen();
}
</script>

<template>
  <div class="ui-popover__trigger" @click.stop="onClick">
    <slot />
  </div>
</template>
