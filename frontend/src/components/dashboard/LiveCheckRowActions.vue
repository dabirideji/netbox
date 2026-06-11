<script setup lang="ts">
import { PhBell, PhDotsThreeVertical, PhSpinner, PhStar } from '@phosphor-icons/vue';
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import type { TargetSummary } from '../../types';

const props = defineProps<{
  target: TargetSummary;
  favoriting: boolean;
}>();

const emit = defineEmits<{
  setAlert: [];
  toggleFavorite: [];
}>();

const open = ref(false);
const triggerRef = ref<HTMLButtonElement | null>(null);
const menuRef = ref<HTMLDivElement | null>(null);
const menuStyle = ref({ top: '0px', left: '0px' });

function updatePosition(): void {
  const trigger = triggerRef.value;
  if (!trigger) return;

  const rect = trigger.getBoundingClientRect();
  const menuWidth = 168;
  menuStyle.value = {
    top: `${rect.bottom + 4}px`,
    left: `${Math.max(8, rect.right - menuWidth)}px`,
  };
}

async function toggleOpen(): Promise<void> {
  open.value = !open.value;
  if (open.value) {
    await nextTick();
    updatePosition();
  }
}

function close(): void {
  open.value = false;
}

function onSetAlert(): void {
  close();
  emit('setAlert');
}

function onToggleFavorite(): void {
  if (props.favoriting) return;
  close();
  emit('toggleFavorite');
}

function onDocumentClick(event: MouseEvent): void {
  if (!open.value) return;

  const target = event.target as Node;
  if (triggerRef.value?.contains(target) || menuRef.value?.contains(target)) {
    return;
  }

  close();
}

function onDocumentKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    close();
  }
}

watch(open, (isOpen) => {
  if (isOpen) {
    void nextTick(() => updatePosition());
  }
});

onMounted(() => {
  document.addEventListener('click', onDocumentClick);
  document.addEventListener('keydown', onDocumentKeydown);
  window.addEventListener('resize', updatePosition);
  window.addEventListener('scroll', updatePosition, true);
});

onUnmounted(() => {
  document.removeEventListener('click', onDocumentClick);
  document.removeEventListener('keydown', onDocumentKeydown);
  window.removeEventListener('resize', updatePosition);
  window.removeEventListener('scroll', updatePosition, true);
});
</script>

<template>
  <div class="live-check-actions">
    <button
      ref="triggerRef"
      type="button"
      class="live-check-actions__trigger"
      :aria-label="`Actions for ${target.label}`"
      :aria-expanded="open"
      @click.stop="toggleOpen"
    >
      <PhDotsThreeVertical weight="bold" aria-hidden="true" />
    </button>

    <Teleport to="body">
      <div
        v-if="open"
        ref="menuRef"
        class="live-check-actions__menu live-check-actions__menu--portal"
        :style="menuStyle"
        role="menu"
        @click.stop
      >
        <button type="button" class="live-check-actions__item" role="menuitem" @click="onSetAlert">
          <PhBell weight="bold" aria-hidden="true" />
          <span>Set alert</span>
        </button>
        <button
          type="button"
          class="live-check-actions__item"
          role="menuitem"
          :disabled="favoriting"
          @click="onToggleFavorite"
        >
          <PhSpinner v-if="favoriting" class="live-check-actions__spinner" weight="bold" aria-hidden="true" />
          <PhStar v-else weight="bold" aria-hidden="true" />
          <span>{{ target.isFavorite ? 'Remove from favorites' : 'Add to favorite' }}</span>
        </button>
      </div>
    </Teleport>
  </div>
</template>
