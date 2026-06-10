<script setup lang="ts">
import { onMounted, onUnmounted, provide, ref, type Ref } from 'vue';

export interface PopoverContext {
  open: Ref<boolean>;
  setOpen: (value: boolean) => void;
  toggleOpen: () => void;
}

const open = defineModel<boolean>('open', { default: false });
const root = ref<HTMLElement | null>(null);

function setOpen(value: boolean): void {
  open.value = value;
}

function toggleOpen(): void {
  open.value = !open.value;
}

provide<PopoverContext>('ui-popover', { open, setOpen, toggleOpen });

function onDocumentClick(event: MouseEvent): void {
  if (!open.value || !root.value) return;
  if (!root.value.contains(event.target as Node)) {
    open.value = false;
  }
}

function onDocumentKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    open.value = false;
  }
}

onMounted(() => {
  document.addEventListener('click', onDocumentClick);
  document.addEventListener('keydown', onDocumentKeydown);
});

onUnmounted(() => {
  document.removeEventListener('click', onDocumentClick);
  document.removeEventListener('keydown', onDocumentKeydown);
});
</script>

<template>
  <div ref="root" class="ui-popover">
    <slot />
  </div>
</template>
